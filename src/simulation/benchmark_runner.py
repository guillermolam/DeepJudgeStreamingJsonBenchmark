#!/usr/bin/env python3
"""
Comprehensive Benchmarking System for Streaming JSON Parsers
============================================================

This script benchmarks streaming JSON parser implementations across multiple
metrics including performance, throughput, CPU usage, and network simulation.
"""

import argparse
import json
import multiprocessing
import sys
import time
import traceback
import tracemalloc
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional, Protocol

import psutil
from tqdm import tqdm

# ✅ Import centralized parser list
from parser_loader import LOADED_PARSERS
from .algo_metadata import ALGORITHM_METADATA
from .data_gen import generate_test_data, create_streaming_chunks
from .net_sim import HTTPSimulator, TCPSimulator, TelnetSimulator
from .utils import Timer, calculate_throughput, calculate_amdahl_speedup, save_results


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs."""

    output_dir: str = "tests/.benchmarks"
    runs_per_test: int = 3
    dataset_sizes: Optional[List[int]] = None
    protocols: Optional[List[str]] = None

    def __post_init__(self):
        if self.dataset_sizes is None:
            self.dataset_sizes = [100, 1500, 10000]
        if self.protocols is None:
            self.protocols = ["http", "tcp", "telnet"]


@dataclass
class TestDataset:
    """Container for test dataset information."""

    data: Any
    json_str: str
    json_bytes: bytes
    size_chars: int
    size_bytes: int
    chunks: List[bytes]


@dataclass
class BenchmarkMetrics:
    """Container for benchmark metrics."""

    parser_name: str
    dataset_size: int
    run_number: int
    protocol: str
    timestamp: float
    success: bool = False
    error: Optional[str] = None
    serialize_time_ms: float = 0
    deserialize_time_ms: float = 0
    total_ser_deser_time_ms: float = 0
    throughput_mbps: float = 0
    cpu_time_seconds: float = 0
    memory_current_bytes: int = 0
    memory_peak_bytes: int = 0
    network_latency_ms: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parser_name": self.parser_name,
            "dataset_size": self.dataset_size,
            "run_number": self.run_number,
            "protocol": self.protocol,
            "timestamp": self.timestamp,
            "success": self.success,
            "error": self.error,
            "serialize_time_ms": self.serialize_time_ms,
            "deserialize_time_ms": self.deserialize_time_ms,
            "total_ser_deser_time_ms": self.total_ser_deser_time_ms,
            "throughput_mbps": self.throughput_mbps,
            "cpu_time_seconds": self.cpu_time_seconds,
            "memory_current_bytes": self.memory_current_bytes,
            "memory_peak_bytes": self.memory_peak_bytes,
            "network_latency_ms": self.network_latency_ms,
        }


class ParserProtocol(Protocol):
    """Protocol for streaming JSON parsers."""

    def consume(self, buffer: str) -> None: ...
    def get(self) -> Any: ...


class NetworkSimulatorFactory:
    """Factory for creating network simulators."""

    @staticmethod
    def create_simulator(protocol: str):
        mapping = {
            "http": HTTPSimulator,
            "tcp": TCPSimulator,
            "telnet": TelnetSimulator,
        }
        if protocol not in mapping:
            raise ValueError(f"Unknown protocol: {protocol}")
        return mapping[protocol]()


class TestDataGenerator:
    """Generates datasets of various sizes."""

    def generate_datasets(self, sizes: List[int]) -> Dict[int, TestDataset]:
        results = {}
        print("\nGenerating test datasets...")
        for size in tqdm(sizes, desc="Dataset sizes"):
            data = generate_test_data(size)
            json_str = json.dumps(data, separators=(",", ":"))
            json_bytes = json_str.encode("utf-8")
            results[size] = TestDataset(
                data=data,
                json_str=json_str,
                json_bytes=json_bytes,
                size_chars=len(json_str),
                size_bytes=len(json_bytes),
                chunks=create_streaming_chunks(json_bytes),
            )
            print(f"  Size {size}: {len(json_str):,} chars, {len(json_bytes):,} bytes")
        return results


class MetricsCollector:
    """Collects performance and memory metrics for benchmark runs."""

    def collect_metrics(
        self,
        parser_name: str,
        parser_class: type,
        dataset: TestDataset,
        run_number: int,
        protocol: str,
    ) -> BenchmarkMetrics:
        metrics = BenchmarkMetrics(
            parser_name=parser_name,
            dataset_size=len(dataset.data) if hasattr(dataset.data, "__len__") else 0,
            run_number=run_number,
            protocol=protocol,
            timestamp=time.time(),
        )
        try:
            self._run(parser_class, dataset, protocol, metrics)
            metrics.success = True
        except Exception as e:
            metrics.error = str(e)
            metrics.success = False
        return metrics

    def _run(
        self,
        parser_class: type,
        dataset: TestDataset,
        protocol: str,
        metrics: BenchmarkMetrics,
    ):
        tracemalloc.start()
        process = psutil.Process()
        cpu_start = process.cpu_times()

        parser = parser_class()
        simulator = NetworkSimulatorFactory.create_simulator(protocol)
        transmission = simulator.simulate_transmission(dataset.chunks)

        with Timer() as st:
            for chunk in transmission.chunks:
                parser.consume(chunk)

        with Timer() as dt:
            parser.get()

        cpu_end = process.cpu_times()
        cpu_time = (cpu_end.user - cpu_start.user) + (cpu_end.system - cpu_start.system)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        total = st.elapsed_ms + dt.elapsed_ms
        throughput = calculate_throughput(dataset.size_bytes, total)

        metrics.serialize_time_ms = st.elapsed_ms
        metrics.deserialize_time_ms = dt.elapsed_ms
        metrics.total_ser_deser_time_ms = total
        metrics.throughput_mbps = throughput
        metrics.cpu_time_seconds = cpu_time
        metrics.memory_current_bytes = current
        metrics.memory_peak_bytes = peak
        metrics.network_latency_ms = transmission.total_latency


class ParallelBenchmarkRunner:
    """Runs parsers in parallel to measure speedup."""

    def run_parallel_benchmark(
        self, parser_class: type, dataset: TestDataset
    ) -> Dict[str, Any]:
        num_workers = min(4, multiprocessing.cpu_count())
        chunk_groups = [dataset.chunks[i::num_workers] for i in range(num_workers)]
        start = time.perf_counter()

        try:
            results = []
            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                futures = [
                    executor.submit(_process_chunk_group, parser_class, group)
                    for group in chunk_groups
                ]
                for future in as_completed(futures):
                    results.append(future.result())

            elapsed = (time.perf_counter() - start) * 1000
            return {
                "parallel_time_ms": elapsed,
                "num_workers": num_workers,
                "success": True,
            }
        except Exception as e:
            return {
                "parallel_time_ms": 0,
                "num_workers": 0,
                "success": False,
                "error": str(e),
            }


class BenchmarkResultsManager:
    """Stores, aggregates, saves, and prints benchmark results."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.results: List[Dict[str, Any]] = []

    def add_result(self, m: BenchmarkMetrics):
        base = m.to_dict()
        algo = ALGORITHM_METADATA.get(m.parser_name, {})
        base.update(
            {
                "algorithm_name": algo.get("name", m.parser_name),
                "time_complexity": algo.get("time_complexity", "Unknown"),
                "space_complexity": algo.get("space_complexity", "Unknown"),
                "overall_complexity": algo.get("overall_complexity", "Unknown"),
            }
        )
        self.results.append(base)

    def update_speedup_metrics(
        self, parser_name: str, dataset_size: int, speedup: Dict[str, float]
    ):
        for r in self.results:
            if r["parser_name"] == parser_name and r["dataset_size"] == dataset_size:
                r.update(
                    {
                        "speedup": speedup["speedup"],
                        "efficiency": speedup["efficiency"],
                        "amdahl_theoretical_speedup": speedup["theoretical_speedup"],
                    }
                )

    def save_results(self, fmt: str = "both"):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        if fmt in ("csv", "both"):
            csv_file = self.output_dir / f"benchmark_results_{timestamp}.csv"
            save_results(self.results, csv_file, "csv")
            print(f"📊 Results saved to: {csv_file}")
        if fmt in ("json", "both"):
            json_file = self.output_dir / f"benchmark_results_{timestamp}.json"
            save_results(self.results, json_file, "json")
            print(f"📊 Results saved to: {json_file}")

    def print_summary(self, dataset_sizes: List[int]):
        if not self.results:
            print("No results to summarize.")
            return

        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        ok = [r for r in self.results if r["success"]]
        print(
            f"Success Rate: {len(ok)}/{len(self.results)} ({len(ok)/len(self.results)*100:.1f}%)"
        )

        top = sorted(ok, key=lambda x: x.get("throughput_mbps", 0), reverse=True)[:5]
        print("\nTop 5 Performers (Throughput):")
        for i, r in enumerate(top, 1):
            print(
                f"  {i}. {r['algorithm_name']} ({r['dataset_size']} fields): {r['throughput_mbps']:.2f} MB/s"
            )

        print("\nAverage Processing Times by Dataset Size:")
        for size in sorted(dataset_sizes):
            grp = [r for r in ok if r["dataset_size"] == size]
            if grp:
                print(
                    f"  {size:,} fields: {sum(r['total_ser_deser_time_ms'] for r in grp)/len(grp):.2f} ms"
                )


class StreamingParserBenchmark:
    """Main orchestrator."""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.data_generator = TestDataGenerator()
        self.metrics = MetricsCollector()
        self.parallel = ParallelBenchmarkRunner()
        self.results = BenchmarkResultsManager(Path(config.output_dir))

        self.parsers = LOADED_PARSERS
        if not self.parsers:
            raise RuntimeError("No parsers loaded")
        self.test_data = self.data_generator.generate_datasets(config.dataset_sizes)

    def run_comprehensive_benchmark(self):
        total = (
            len(self.parsers)
            * len(self.test_data)
            * self.config.runs_per_test
            * len(self.config.protocols)
        )
        print(f"\n🚀 Starting benchmark with {len(self.parsers)} parsers...")
        with tqdm(total=total, desc="Running benchmarks") as pbar:
            for pname, pcls in self.parsers.items():
                for size, ds in self.test_data.items():
                    seq_times = []
                    for protocol in self.config.protocols:
                        for run in range(self.config.runs_per_test):
                            m = self.metrics.collect_metrics(
                                pname, pcls, ds, run + 1, protocol
                            )
                            self.results.add_result(m)
                            if m.success:
                                seq_times.append(m.total_ser_deser_time_ms)
                            pbar.update(1)
                    if seq_times:
                        avg_seq = sum(seq_times) / len(seq_times)
                        par = self.parallel.run_parallel_benchmark(pcls, ds)
                        if par["success"]:
                            speedup = calculate_amdahl_speedup(
                                avg_seq, par["parallel_time_ms"], par["num_workers"]
                            )
                            self.results.update_speedup_metrics(pname, size, speedup)

        print(
            f"\n✅ Benchmark completed! Collected {len(self.results.results)} results."
        )


# Parallel worker function
def _process_chunk_group(parser_class: type, group: List[bytes]):
    parser = parser_class()
    for chunk in group:
        parser.consume(chunk)
    return parser.get()


def create_arg_parser():
    p = argparse.ArgumentParser(description="Streaming JSON Parser Benchmark")
    p.add_argument("--runs", "-r", type=int, default=3)
    p.add_argument("--output", "-o", default="tests/.benchmarks")
    p.add_argument("--format", "-f", choices=["csv", "json", "both"], default="both")
    p.add_argument("--quiet", "-q", action="store_true")
    return p


def sanitize_output_dir(out: str) -> Path:
    base = Path.cwd().resolve()
    candidate = Path(out).expanduser()
    resolved = (candidate if candidate.is_absolute() else base / candidate).resolve()
    if not resolved.is_relative_to(base):
        raise ValueError("Invalid output directory: Path traversal detected")
    return resolved


def main():
    args = create_arg_parser().parse_args()
    out = sanitize_output_dir(args.output)
    out.mkdir(parents=True, exist_ok=True)

    cfg = BenchmarkConfig(output_dir=str(out), runs_per_test=args.runs)

    try:
        bench = StreamingParserBenchmark(cfg)
        bench.run_comprehensive_benchmark()
        bench.results.save_results(args.format)
        if not args.quiet:
            bench.results.print_summary(cfg.dataset_sizes)
        print("🎉 Completed successfully!")
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
