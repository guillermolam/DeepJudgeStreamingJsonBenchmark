"""
Network Protocol Simulators for Streaming JSON Parser Benchmarks
================================================================

Simulates HTTP, TCP, and Telnet transmission characteristics.
"""

import random
import time
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
        random.seed(42)  # Deterministic for benchmarking

    def _add_latency(self) -> float:
        """Add simulated network latency."""
        latency = self.base_latency_ms + random.uniform(-self.jitter_ms, self.jitter_ms)
        return max(0.1, latency)  # Minimum 0.1 ms latency

    def simulate_transmission(self, chunks: List[bytes]) -> TransmissionResult:
        """Simulate the transmission of data_gen chunks."""
        raise NotImplementedError("Subclasses must implement simulate_transmission")


class HTTPSimulator(NetworkSimulator):
    """Simulates HTTP transmission with headers and chunked encoding."""

    def __init__(self, base_latency_ms: float = 2.0, jitter_ms: float = 1.0):
        super().__init__(base_latency_ms, jitter_ms)
        self.http_version = "HTTP/1.1"
        self.connection_overhead = 150  # bytes for headers

    def _create_http_headers(self, content_length: int) -> bytes:
        """Create HTTP response headers."""
        headers = [
            f"{self.http_version} 200 OK",
            "Content-Type: application/json; charset=utf-8",
            f"Content-Length: {content_length}",
            "Transfer-Encoding: chunked",
            "Connection: keep-alive",
            "Cache-Control: no-cache",
            "Server: StreamingParser-Benchmark/1.0",
            "",  # Empty line to end headers
            ""
        ]
        return "\r\n".join(headers).encode('utf-8')

    @staticmethod
    def _create_chunk_header(chunk_size: int) -> bytes:
        """Create HTTP chunk size header."""
        return f"{chunk_size:x}\r\n".encode('utf-8')

    @staticmethod
    def _create_chunk_footer() -> bytes:
        """Create HTTP chunk footer."""
        return b"\r\n"

    def simulate_transmission(self, chunks: List[bytes]) -> TransmissionResult:
        """Simulate HTTP chunked transfer encoding."""

        total_content_length = sum(len(chunk) for chunk in chunks)
        transmitted_chunks = []
        total_latency = 0.0
        overhead_bytes = 0

        # Add HTTP headers (sent first)
        headers = self._create_http_headers(total_content_length)
        transmitted_chunks.append(headers)
        overhead_bytes += len(headers)
        total_latency += self._add_latency()

        # Process each chunk with HTTP chunked encoding
        for chunk in chunks:
            # Add chunk size header
            chunk_header = self._create_chunk_header(len(chunk))
            transmitted_chunks.append(chunk_header)
            overhead_bytes += len(chunk_header)

            # Add actual chunk data_gen
            transmitted_chunks.append(chunk)

            # Add chunk footer
            chunk_footer = self._create_chunk_footer()
            transmitted_chunks.append(chunk_footer)
            overhead_bytes += len(chunk_footer)

            # Simulate network latency for this chunk
            total_latency += self._add_latency()

        # Add final chunk (size 0) to end chunked encoding
        final_chunk = b"0\r\n\r\n"
        transmitted_chunks.append(final_chunk)
        overhead_bytes += len(final_chunk)
        total_latency += self._add_latency()

        protocol_info = {
            'protocol': 'HTTP',
            'version': self.http_version,
            'encoding': 'chunked',
            'total_chunks': len(chunks),
            'header_size': len(headers),
            'chunk_overhead_per_chunk': 6,  # Average overhead per chunk
        }

        result = TransmissionResult(
            chunks=transmitted_chunks,
            total_latency=total_latency,
            overhead_bytes=overhead_bytes,
            protocol_info=protocol_info
        )

        # Add latency info to result for access
        result.total_latency = total_latency

        return result


class TCPSimulator(NetworkSimulator):
    """Simulates TCP transmission with packet overhead and acknowledgments."""

    def __init__(self, base_latency_ms: float = 0.5, jitter_ms: float = 0.2):
        super().__init__(base_latency_ms, jitter_ms)
        self.mtu = 1500  # Maximum Transmission Unit
        self.tcp_header_size = 20  # TCP header size in bytes
        self.ip_header_size = 20  # IP header size in bytes
        self.ack_frequency = 2  # Send ACK every 2 packets

    def _create_tcp_packet(self, data: bytes, seq_num: int) -> Dict[str, Any]:
        """Create a TCP packet with headers."""
        return {
            'sequence_number': seq_num,
            'data_gen': data,
            'tcp_header': b'T' * self.tcp_header_size,  # Simulated TCP header
            'ip_header': b'I' * self.ip_header_size,  # Simulated IP header
            'total_size': len(data) + self.tcp_header_size + self.ip_header_size
        }

    def _create_ack_packet(self, ack_num: int) -> Dict[str, Any]:
        """Create a TCP ACK packet."""
        return {
            'ack_number': ack_num,
            'data_gen': b'',
            'tcp_header': b'A' * self.tcp_header_size,
            'ip_header': b'I' * self.ip_header_size,
            'total_size': self.tcp_header_size + self.ip_header_size,
            'is_ack': True
        }

    def simulate_transmission(self, chunks: List[bytes]) -> TransmissionResult:
        """Simulate TCP transmission with packet segmentation."""

        transmitted_chunks = []
        total_latency = 0.0
        overhead_bytes = 0
        seq_num = 1000  # Starting sequence number
        packet_count = 0

        # Combine all chunks into a single data_gen stream
        data_stream = b''.join(chunks)

        # Split data_gen into TCP packets based on MTU
        max_data_per_packet = self.mtu - self.tcp_header_size - self.ip_header_size

        for i in range(0, len(data_stream), max_data_per_packet):
            packet_data = data_stream[i:i + max_data_per_packet]

            # Create a TCP packet
            packet = self._create_tcp_packet(packet_data, seq_num)

            # Add packet data_gen to transmitted chunks
            transmitted_chunks.append(packet['data_gen'])

            # Track overhead
            overhead_bytes += self.tcp_header_size + self.ip_header_size

            # Simulate transmission latency
            total_latency += self._add_latency()

            # Update sequence number
            seq_num += len(packet_data)
            packet_count += 1

            # Simulate ACK packets
            if packet_count % self.ack_frequency == 0:
                ack_packet = self._create_ack_packet(seq_num)
                overhead_bytes += ack_packet['total_size']
                total_latency += self._add_latency()  # ACK latency

        # Final ACK
        if packet_count % self.ack_frequency != 0:
            ack_packet = self._create_ack_packet(seq_num)
            overhead_bytes += ack_packet['total_size']
            total_latency += self._add_latency()

        protocol_info = {
            'protocol': 'TCP',
            'mtu': self.mtu,
            'total_packets': packet_count,
            'tcp_header_size': self.tcp_header_size,
            'ip_header_size': self.ip_header_size,
            'ack_packets': (packet_count + self.ack_frequency - 1) // self.ack_frequency,
            'total_overhead_per_packet': self.tcp_header_size + self.ip_header_size
        }

        result = TransmissionResult(
            chunks=transmitted_chunks,
            total_latency=total_latency,
            overhead_bytes=overhead_bytes,
            protocol_info=protocol_info
        )

        result.total_latency = total_latency
        return result


class TelnetSimulator(NetworkSimulator):
    """Simulates Telnet transmission with character-by-character echo."""

    def __init__(self, base_latency_ms: float = 5.0, jitter_ms: float = 2.0):
        super().__init__(base_latency_ms, jitter_ms)
        self.echo_enabled = True
        self.line_mode = False  # Character mode by default
        self.buffer_size = 1  # Send one character at a time

    @staticmethod
    def _create_telnet_command(command: str) -> bytes:
        """Create Telnet protocol command."""
        # Telnet commands start with IAC (255)
        commands = {
            'WILL_ECHO': b'\xff\xfb\x01',  # IAC WILL ECHO
            'WONT_ECHO': b'\xff\xfc\x01',  # IAC WONT ECHO
            'DO_SUPPRESS_GA': b'\xff\xfd\x03',  # IAC DO SUPPRESS-GO-AHEAD
            'WILL_SGA': b'\xff\xfb\x03'  # IAC WILL SUPPRESS-GO-AHEAD
        }
        return commands.get(command, b'')

    def simulate_transmission(self, chunks: List[bytes]) -> TransmissionResult:
        """Simulate Telnet character-by-character transmission."""

        transmitted_chunks = []
        total_latency = 0.0
        overhead_bytes = 0

        # Send initial Telnet negotiation
        negotiation_commands = [
            self._create_telnet_command('WILL_ECHO'),
            self._create_telnet_command('DO_SUPPRESS_GA'),
            self._create_telnet_command('WILL_SGA')
        ]

        for cmd in negotiation_commands:
            if cmd:
                transmitted_chunks.append(cmd)
                overhead_bytes += len(cmd)
                total_latency += self._add_latency()

        # Combine all chunks into a single data_gen stream
        data_stream = b''.join(chunks)

        # Simulate character-by-character transmission
        char_count = 0
        for i in range(0, len(data_stream), self.buffer_size):
            char_data = data_stream[i:i + self.buffer_size]

            # Send character
            transmitted_chunks.append(char_data)
            total_latency += self._add_latency()

            # Simulate echo if enabled
            if self.echo_enabled:
                # Echo back the character (overhead)
                echo_data = char_data  # Echo the same character
                transmitted_chunks.append(echo_data)
                overhead_bytes += len(echo_data)
                total_latency += self._add_latency()

            char_count += len(char_data)

            # Add extra latency for special characters
            if char_data in [b'\n', b'\r', b'\r\n']:
                total_latency += self._add_latency() * 0.5  # Extra processing time

        protocol_info = {
            'protocol': 'Telnet',
            'echo_enabled': self.echo_enabled,
            'line_mode': self.line_mode,
            'buffer_size': self.buffer_size,
            'total_characters': char_count,
            'negotiation_overhead': sum(len(cmd) for cmd in negotiation_commands),
            'echo_overhead': overhead_bytes
        }

        result = TransmissionResult(
            chunks=transmitted_chunks,
            total_latency=total_latency,
            overhead_bytes=overhead_bytes,
            protocol_info=protocol_info
        )

        result.total_latency = total_latency
        return result


def benchmark_network_simulators():
    """Benchmark the network simulators themselves."""

    print("Benchmarking Network Simulators")
    print("=" * 40)

    # Test data_gen
    test_data = b"Hello, World! " * 100  # 1400 bytes
    chunks = [test_data[i:i + 100] for i in range(0, len(test_data), 100)]

    simulators = {
        'HTTP': HTTPSimulator(),
        'TCP': TCPSimulator(),
        'Telnet': TelnetSimulator()
    }

    for name, simulator in simulators.items():
        start_time = time.perf_counter()
        result = simulator.simulate_transmission(chunks)
        end_time = time.perf_counter()

        simulation_time = (end_time - start_time) * 1000  # ms

        print(f"\n{name} Simulator:")
        print(f"  Simulation time: {simulation_time:.2f} ms")
        print(f"  Network latency: {result.total_latency:.2f} ms")
        print(f"  Overhead bytes: {result.overhead_bytes}")
        print(f"  Output chunks: {len(result.chunks)}")
        print(f"  Protocol info: {result.protocol_info}")


if __name__ == "__main__":
    benchmark_network_simulators()
