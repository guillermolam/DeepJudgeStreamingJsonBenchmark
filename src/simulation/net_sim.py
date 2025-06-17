"""
Network Protocol Simulators for Streaming JSON Parser Benchmarks
================================================================

Simulates HTTP, TCP, and Telnet transmission characteristics.
"""

import random
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class TransmissionResult:
    """Result of network transmission simulation."""

    chunks: List[bytes]
    total_latency: float
    overhead_bytes: int
    protocol_info: Dict[str, Any]


class NetworkSimulator:
    """Base class for network protocol simulators."""

    def __init__(self, base_latency_ms: float = 1.0, jitter_ms: float = 0.5):
        self.base_latency_ms = base_latency_ms
        self.jitter_ms = jitter_ms
        random.seed(42)  # deterministic for benchmarking

    def _add_latency(self) -> float:
        """Add simulated network latency."""
        latency = self.base_latency_ms + random.uniform(-self.jitter_ms, self.jitter_ms)
        return max(0.1, latency)  # ensure minimum latency

    def simulate_transmission(self, chunks: List[bytes]) -> TransmissionResult:
        """Simulate the transmission of byte chunks."""
        raise NotImplementedError("Must be implemented by subclasses")


class HTTPSimulator(NetworkSimulator):
    """Simulates HTTP transmission with headers and chunked encoding."""

    def __init__(self, base_latency_ms: float = 2.0, jitter_ms: float = 1.0):
        super().__init__(base_latency_ms, jitter_ms)
        self.http_version = "HTTP/1.1"
        self.connection_overhead = 150  # bytes for headers

    def _create_http_headers(self, content_length: int) -> bytes:
        headers = [
            f"{self.http_version} 200 OK",
            "Content-Type: application/json; charset=utf-8",
            f"Content-Length: {content_length}",
            "Transfer-Encoding: chunked",
            "Connection: keep-alive",
            "Cache-Control: no-cache",
            "Server: StreamingParser-Benchmark/1.0",
            "",  # blank line end
            "",
        ]
        return "\r\n".join(headers).encode("utf-8")

    @staticmethod
    def _create_chunk_header(chunk_size: int) -> bytes:
        return f"{chunk_size:x}\r\n".encode("utf-8")

    @staticmethod
    def _create_chunk_footer() -> bytes:
        return b"\r\n"

    def simulate_transmission(self, chunks: List[bytes]) -> TransmissionResult:
        total_content = sum(len(c) for c in chunks)
        transmitted = []
        total_latency = 0.0
        overhead = 0

        headers = self._create_http_headers(total_content)
        transmitted.append(headers)
        overhead += len(headers)
        total_latency += self._add_latency()

        for chunk in chunks:
            header = self._create_chunk_header(len(chunk))
            transmitted.append(header)
            overhead += len(header)

            transmitted.append(chunk)

            footer = self._create_chunk_footer()
            transmitted.append(footer)
            overhead += len(footer)

            total_latency += self._add_latency()

        final_chunk = b"0\r\n\r\n"
        transmitted.append(final_chunk)
        overhead += len(final_chunk)
        total_latency += self._add_latency()

        info = {
            "protocol": "HTTP",
            "version": self.http_version,
            "encoding": "chunked",
            "total_chunks": len(chunks),
            "header_size": len(headers),
            "chunk_overhead_per_chunk": 6,
        }

        return TransmissionResult(transmitted, total_latency, overhead, info)


class TCPSimulator(NetworkSimulator):
    """Simulates TCP with packet headers and ACKs."""

    def __init__(self, base_latency_ms: float = 0.5, jitter_ms: float = 0.2):
        super().__init__(base_latency_ms, jitter_ms)
        self.mtu = 1500
        self.tcp_header = 20
        self.ip_header = 20
        self.ack_every = 2

    def _create_ack_packet(self, ack_num: int) -> Dict[str, Any]:
        return {
            "ack": ack_num,
            "data": b"",
            "tcp_header": b"A" * self.tcp_header,
            "ip_header": b"I" * self.ip_header,
            "size": self.tcp_header + self.ip_header,
        }

    def simulate_transmission(self, chunks: List[bytes]) -> TransmissionResult:
        data_stream = b"".join(chunks)
        transmitted = []
        total_latency = 0.0
        overhead = 0
        packet_count = 0
        seq = 0

        max_data = self.mtu - self.tcp_header - self.ip_header

        for i in range(0, len(data_stream), max_data):
            piece = data_stream[i : i + max_data]
            transmitted.append(piece)
            overhead += self.tcp_header + self.ip_header
            total_latency += self._add_latency()
            seq += len(piece)
            packet_count += 1

            if packet_count % self.ack_every == 0:
                ack = self._create_ack_packet(seq)
                overhead += ack["size"]
                total_latency += self._add_latency()

        if packet_count % self.ack_every != 0:
            ack = self._create_ack_packet(seq)
            overhead += ack["size"]
            total_latency += self._add_latency()

        info = {
            "protocol": "TCP",
            "mtu": self.mtu,
            "packets": packet_count,
            "tcp_hdr": self.tcp_header,
            "ip_hdr": self.ip_header,
            "acks": (packet_count + self.ack_every - 1) // self.ack_every,
        }

        return TransmissionResult(transmitted, total_latency, overhead, info)


class TelnetSimulator(NetworkSimulator):
    """Simulates Telnet, sending character-by-character with optional echo."""

    def __init__(self, base_latency_ms: float = 5.0, jitter_ms: float = 2.0):
        super().__init__(base_latency_ms, jitter_ms)
        self.echo = True
        self.buffer_size = 1

    @staticmethod
    def _cmd(cmd: str) -> bytes:
        codes = {
            "WILL_ECHO": b"\xff\xfb\x01",
            "DO_SGA": b"\xff\xfd\x03",
        }
        return codes.get(cmd, b"")

    def simulate_transmission(self, chunks: List[bytes]) -> TransmissionResult:
        transmitted = []
        total_latency = 0.0
        overhead = 0

        for c in ("WILL_ECHO", "DO_SGA"):
            cmd = self._cmd(c)
            if cmd:
                transmitted.append(cmd)
                overhead += len(cmd)
                total_latency += self._add_latency()

        data_stream = b"".join(chunks)

        for b in data_stream:
            byte = bytes([b])
            transmitted.append(byte)
            total_latency += self._add_latency()

            if self.echo:
                transmitted.append(byte)
                overhead += 1
                total_latency += self._add_latency()

        info = {
            "protocol": "Telnet",
            "echo_enabled": self.echo,
            "buffer_size": self.buffer_size,
        }

        return TransmissionResult(transmitted, total_latency, overhead, info)
