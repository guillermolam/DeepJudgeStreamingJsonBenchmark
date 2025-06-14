#!/usr/bin/env python3
"""
Test script to identify which parsers are working correctly
in a reactive environment
"""

import asyncio
import io
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import pytest
import trio

from serializers.raw.ultrajson_parser import StreamingJsonParser


# ---------------------
# Trio-based reactive test
# ---------------------
@pytest.mark.trio
async def test_reactive_parser_producer_consumer():
    """
    Test a reactive producer-consumer setup using Trio memory channels.
    Producer simulates blocking I/O by using trio.to_thread.run_sync to sleep.
    Consumer parses incoming JSON chunks as they arrive.
    """
    send_chan, recv_chan = trio.open_memory_channel(0)

    async def producer():
        async with send_chan:
            # Simulate blocking I/O without stalling the event loop
            await trio.to_thread.run_sync(time.sleep, 0.01)
            # Send two partial JSON chunks
            await send_chan.send('{"a": 1}')
            await trio.sleep(0)
            await send_chan.send('{"b": 2}')

    async def consumer():
        parser = StreamingJsonParser()
        results = []
        async with recv_chan:
            async for chunk in recv_chan:
                parser.consume(chunk)
                results.append(parser.get().copy())
        # At the end, we should have parsed both objects
        assert results == [{"a": 1}, {"a": 1, "b": 2}]

    async with trio.open_nursery() as nursery:
        nursery.start_soon(producer)
        nursery.start_soon(consumer)


# ---------------------
# Two producers, one consumer
# ---------------------
@pytest.mark.trio
async def test_two_producers_single_consumer():
    """
    Test two producers sending JSON chunks to a single consumer via one channel.
    """
    send_chan, recv_chan = trio.open_memory_channel(0)

    async def producer1():
        async with send_chan.clone():
            await trio.sleep(0)
            await send_chan.send('{"p1": 1}')

    async def producer2():
        async with send_chan.clone():
            await trio.sleep(0)
            await send_chan.send('{"p2": 2}')

    async def consumer():
        parser = StreamingJsonParser()
        results = []
        async with recv_chan:
            async for chunk in recv_chan:
                parser.consume(chunk)
                results.append(parser.get().copy())
        # Combined state after both producers
        assert results == [{"p1": 1}, {"p1": 1, "p2": 2}]

    async with trio.open_nursery() as nursery:
        nursery.start_soon(producer1)
        nursery.start_soon(producer2)
        nursery.start_soon(consumer)


# ---------------------
# Two producers, two consumers
# ---------------------
@pytest.mark.trio
async def test_two_producers_two_consumers():
    """
    Test two producers broadcasting to two independent consumer pipelines.
    Each consumer has its own channel but receives the same data from both producers.
    """
    # Create two channel pairs for two pipelines
    send_chan1, recv_chan1 = trio.open_memory_channel(0)
    send_chan2, recv_chan2 = trio.open_memory_channel(0)

    async def producer1():
        async with send_chan1.clone(), send_chan2.clone():
            await trio.sleep(0)
            for chunk in [json.dumps({"x": 1}), json.dumps({"y": 2})]:
                await send_chan1.send(chunk)
                await send_chan2.send(chunk)

    async def producer2():
        async with send_chan1.clone(), send_chan2.clone():
            await trio.sleep(0)
            # repeat same values to simulate two producers
            for chunk in [json.dumps({"x": 1}), json.dumps({"y": 2})]:
                await send_chan1.send(chunk)
                await send_chan2.send(chunk)

    results1 = []
    results2 = []

    async def consumer1():
        parser = StreamingJsonParser()
        async with recv_chan1:
            async for chunk in recv_chan1:
                parser.consume(chunk)
                results1.append(parser.get().copy())

    async def consumer2():
        parser = StreamingJsonParser()
        async with recv_chan2:
            async for chunk in recv_chan2:
                parser.consume(chunk)
                results2.append(parser.get().copy())

    async with trio.open_nursery() as nursery:
        nursery.start_soon(producer1)
        nursery.start_soon(producer2)
        nursery.start_soon(consumer1)
        nursery.start_soon(consumer2)

    # Both consumers should have processed four chunks (two from each producer)
    assert len(results1) == 4
    assert len(results2) == 4
    # Final state should combine x and y
    assert results1[-1] == {"x": 1, "y": 2}
    assert results2[-1] == {"x": 1, "y": 2}


# ---------------------
# Asyncio interoperability tests
# ---------------------
async def async_read_stdin() -> str:
    """
    Read a line from stdin without blocking the event loop.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sys.stdin.readline)


async def connect_stdin_stdout():
    """
    Connect asyncio StreamReader/StreamWriter to sys.stdin and sys.stdout.
    """
    loop = asyncio.get_event_loop()
    # Reader
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    # Writer
    w_transport, w_protocol = await loop.connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)
    return reader, writer


@pytest.mark.asyncio
async def test_async_read_stdin(monkeypatch):
    """
    Verify async_read_stdin wraps blocking readline in executor.
    """
    expected = "hello world\n"
    monkeypatch.setattr(sys.stdin, 'readline', lambda: expected)
    result = await async_read_stdin()
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.xfail(reason="connect_read_pipe may not work in test environment")
async def test_connect_stdin_stdout_types(monkeypatch):
    """
    Verify connect_stdin_stdout returns correct reader and writer types.
    """
    # Use StringIO as a stand-in for stdin/stdout
    buf_in = io.StringIO("data\n")
    buf_out = io.StringIO()
    monkeypatch.setattr(sys, 'stdin', buf_in)
    monkeypatch.setattr(sys, 'stdout', buf_out)
    reader, writer = await connect_stdin_stdout()
    assert isinstance(reader, asyncio.StreamReader)
    assert hasattr(writer, 'write') and callable(writer.write)
    assert hasattr(writer, 'drain') and callable(writer.drain)


# ---------------------
# CPU-bound executor tests
# ---------------------

def cpu_bound(number):
    """Simple CPU-bound function for testing executors."""
    return sum(i * i for i in range(number))


@pytest.mark.asyncio
async def test_cpu_bound_thread_pool():
    """
    Run cpu_bound in a ThreadPoolExecutor via run_in_executor.
    """
    loop = asyncio.get_event_loop()
    numbers = [1000 + i for i in range(5)]
    with ThreadPoolExecutor() as executor:
        results = await loop.run_in_executor(executor, lambda: [cpu_bound(n) for n in numbers])
    assert results == [cpu_bound(n) for n in numbers]


@pytest.mark.asyncio
async def test_cpu_bound_process_pool():
    """
    Run cpu_bound in a ProcessPoolExecutor via run_in_executor.
    """
    loop = asyncio.get_event_loop()
    numbers = [1000 + i for i in range(5)]
    with ProcessPoolExecutor() as executor:
        results = await loop.run_in_executor(executor, lambda: [cpu_bound(n) for n in numbers])
    assert results == [cpu_bound(n) for n in numbers]


# ---------------------
# Asyncio synchronization primitives tests
# ---------------------

@pytest.mark.asyncio
async def test_asyncio_event():
    """
    Test basic asyncio.Event behavior.
    """
    event = asyncio.Event()
    results = []

    async def waiter():
        await event.wait()
        results.append('done')

    task = asyncio.create_task(waiter())
    # Ensure waiter is waiting
    await asyncio.sleep(0)
    assert results == []
    # Signal and verify
    event.set()
    await asyncio.sleep(0)
    assert results == ['done']
    task.cancel()


@pytest.mark.asyncio
async def test_asyncio_lock():
    """
    Test basic asyncio.Lock behavior.
    """
    lock = asyncio.Lock()
    order = []

    async def worker(name):
        async with lock:
            order.append(name)

    # Acquire lock before starting workers
    await lock.acquire()
    t1 = asyncio.create_task(worker('first'))
    t2 = asyncio.create_task(worker('second'))

    # Let tasks queue behind the lock
    await asyncio.sleep(0)
    assert order == []

    # Release and let them proceed
    lock.release()
    await asyncio.sleep(0)
    # Only one worker enters at a time; order list should have both
    assert set(order) == {'first', 'second'}


# ---------------------
# Async consumption of parser via executor
# ---------------------

@pytest.mark.asyncio
async def test_parser_consume_in_executor():
    """
    Ensure StreamingJsonParser.consume can be called in executor and remains non-blocking.
    """
    parser = StreamingJsonParser()
    data = '{"x": 42}'
    loop = asyncio.get_event_loop()
    # Call consume in executor to avoid blocking
    await loop.run_in_executor(None, parser.consume, data)
    assert parser.get() == {'x': 42}


# ---------------------
# Incremental JSON stdin test
# ---------------------
@pytest.mark.asyncio
async def test_incremental_json_from_stdin(monkeypatch):
    """
    Test reading a large JSON LLM prompt from stdin in chunks via executor,
    echoing it to stdout and parsing it incrementally.
    """
    # Build a large prompt by repeating a sentence
    prompt = "The quick brown fox jumps over the lazy dog. " * 10000
    json_obj = {"prompt": prompt}
    big_json = json.dumps(json_obj)

    # Split into manageable chunks
    chunk_size = 2048
    chunks = [big_json[i:i + chunk_size] for i in range(0, len(big_json), chunk_size)]
    chunks.append('')  # Signal EOF

    # Monkey-patch blocking sys.stdin.read to return our chunks
    it = iter(chunks)
    monkeypatch.setattr(sys.stdin, 'read', lambda n=-1: next(it))

    parser = StreamingJsonParser()
    writer = io.StringIO()
    partial_states = []
    writer_snapshots = []

    async def async_read(n):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sys.stdin.read, n)

    # Read, echo, and parse incrementally
    while True:
        data = await async_read(chunk_size)
        if not data:
            break
        writer.write(data)
        parser.consume(data)
        writer_snapshots.append(writer.getvalue())
        partial_states.append(parser.get().copy())

    # Verify the final parsed state matches our JSON object
    assert partial_states[-1] == json_obj
    # Verify stdout accumulation matches the original JSON string
    assert writer.getvalue() == big_json
    # Verify that each snapshot corresponds to concatenated chunks
    for i, snap in enumerate(writer_snapshots):
        assert snap == ''.join(chunks[:i + 1])
