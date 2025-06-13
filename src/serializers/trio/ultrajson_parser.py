"""
trio_ultrajson_server.py

Enhanced Trio/OTP GenServer for Ultra-JSON streaming parser,
leveraging Trio-Parallel for multi-core, non-blocking parsing,
with OTP-style supervision, mailbox orchestration, and completion flags.
"""
import trio
import trio_parallel
from triotp import gen_server, supervisor, DynamicSupervisor
from ultrajson_parser import StreamingJsonParser
from typing import Optional, Any, Tuple

# === GenServer callbacks ===
async def init(_init_arg) -> StreamingJsonParser:
    """
    Initialize parser state as a fresh StreamingJsonParser.
    """
    return StreamingJsonParser()

async def handle_cast(
    message: Tuple[str, trio.abc.ReceiveChannel],
    parser: StreamingJsonParser
) -> Tuple[None, StreamingJsonParser]:
    """
    Handle a one-way chunk message: (chunk_str, reply_to_channel).
    Offload parser.consume to a process via trio-parallel for true parallelism.
    Reply with (state, is_complete), reset parser on completion.
    """
    chunk_str, reply_to = message

    # Offload blocking parse to separate process
    await trio_parallel.run_sync(
        parser.consume,
        chunk_str,
        kill_on_cancel=True
    )

    # Retrieve parse state and completion flag
    current_state = parser.get().copy()
    is_complete = bool(current_state)
    await gen_server.reply(reply_to, (current_state, is_complete))

    # Reset on full parse
    if is_complete:
        parser = StreamingJsonParser()
    return (None, parser)

async def handle_call(
    request: Any,
    caller,
    parser: StreamingJsonParser
) -> Tuple[Any, StreamingJsonParser]:
    """
    Handle synchronous calls:
    - 'get': return (state, False)
    - 'stop': stop the GenServer
    """
    if request == 'get':
        return ((parser.get().copy(), False), parser)
    if request == 'stop':
        await gen_server.stop(caller)
        return (None, parser)
    return (None, parser)

# === Supervisor and DynamicSupervisor ===
async def run(
    name: str,
    nursery: trio.Nursery,
    monitor_interval: float = 5.0
) -> None:
    """
    Start a supervisor with GenServer and a dynamic supervisor for monitors.
    """
    # Primary parser GenServer
    server_child = supervisor.child_spec(
        id=f'{name}-server',
        task=gen_server.start,
        args=[name, __name__, None],
        restart=supervisor.restart_strategy.TRANSIENT
    )
    # Monitor that restarts the server on stalls
    monitor_child = supervisor.child_spec(
        id=f'{name}-monitor',
        task=_monitor,
        args=[name, monitor_interval],
        restart=supervisor.restart_strategy.TRANSIENT
    )
    opts = supervisor.options()
    await nursery.start(supervisor.start, [server_child, monitor_child], opts)

async def consume(
    name: str,
    chunk: str,
    reply_to: trio.abc.ReceiveChannel
) -> None:
    """Cast a JSON chunk into the parser GenServer mailbox. """
    await gen_server.cast(name, (chunk, reply_to))

async def get(
    name: str,
    chunk: Optional[str] = None,
    timeout: Optional[float] = None
) -> Tuple[dict, bool]:
    """
    Optionally send one chunk then await a (state, is_complete) reply.
    Cleans up mailbox afterwards.
    """
    send_chan, recv_chan = trio.open_memory_channel(0)
    if chunk is not None:
        await consume(name, chunk, send_chan.clone())
    try:
        if timeout:
            with trio.move_on_after(timeout):
                state, complete = await recv_chan.receive()
        else:
            state, complete = await recv_chan.receive()
    except (trio.EndOfChannel, trio.Cancelled):
        state, complete = {}, False
    finally:
        await send_chan.aclose()
    return state, complete

async def stop(name: str) -> None:
    """Stop the GenServer cleanly via synchronous call."""
    await gen_server.call(name, 'stop')

# === Monitor Task ===
async def _monitor(name: str, interval: float) -> None:
    """
    Periodically poll 'get'; if no response, restart the GenServer.
    """
    while True:
        with trio.move_on_after(interval) as cs:
            await gen_server.call(name, 'get')
        if cs.cancelled_caught:
            # Restart the parser server if stalled
            await gen_server.start(name, __name__, None)
        await trio.sleep(interval)
