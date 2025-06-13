#!/usr/bin/env python3
"""
Comprehensive Benchmarking System for Streaming JSON Parsers
============================================================

This script benchmarks 12 streaming JSON parser implementations across multiple
metrics including performance, throughput, CPU usage, and network simulation.
"""

import argparse
import importlib
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

from .algo_metadata import ALGORITHM_METADATA
from .data_gen import generate_test_data, create_streaming_chunks
from .net_sim import HTTPSimulator, TCPSimulator, TelnetSimulator
from .utils import Timer, calculate_throughput, calculate_amdahl_speedup, save_results


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs."""
    output_dir: str = "."
    runs_per_test: int = 3
    dataset_sizes: Optional[List[int]] = None
    protocols: Optional[List[str]] = None

    def __post_init__(self):
        if self.dataset_sizes is None:
            self.dataset_sizes = [100, 1500, 10000]
        if self.protocols is None:
            self.protocols = ['http', 'tcp', 'telnet']


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
        """Convert metrics to dictionary."""
        return {
            'parser_name': self.parser_name,
            'dataset_size': self.dataset_size,
            'run_number': self.run_number,
            'protocol': self.protocol,
            'timestamp': self.timestamp,
            'success': self.success,
            'error': self.error,
            'serialize_time_ms': self.serialize_time_ms,
            'deserialize_time_ms': self.deserialize_time_ms,
            'total_ser_deser_time_ms': self.total_ser_deser_time_ms,
            'throughput_mbps': self.throughput_mbps,
            'cpu_time_seconds': self.cpu_time_seconds,
            'memory_current_bytes': self.memory_current_bytes,
            'memory_peak_bytes': self.memory_peak_bytes,
            'network_latency_ms': self.network_latency_ms
        }


class ParserProtocol(Protocol):
    """Protocol for streaming JSON parsers."""

    def consume(self, buffer: str) -> None: ...

    def get(self) -> Any: ...


class NetworkSimulatorFactory:
    """Factory for creating network simulators."""

    @staticmethod
    def create_simulator(protocol: str):
        """Create appropriate network simulator."""
        simulators = {
            'http': HTTPSimulator,
            'tcp': TCPSimulator,
            'telnet': TelnetSimulator
        }

        simulator_class = simulators.get(protocol)
        if not simulator_class:
            raise ValueError(f"Unknown protocol: {protocol}")

        return simulator_class()


class ParserLoader:
    """Responsible for discovering and loading parser implementations."""

    PARSER_FILES = [
        'bson_parser', 'cbor_parser', 'flatbuffers_parser', 'json_parser',
        'marshall_parser', 'msgpack_parser', 'parquet_parser',
        'pickle_binary_mono_parser', 'pickle_binary_multi_parser',
        'protobuf_parser', 'reactivex_parser', 'ultrajson_parser'
    ]

    def load_parsers(self) -> Dict[str, type]:
        """Dynamically discover and load all parser implementations."""
        parsers = {}

        for parser_name in self.PARSER_FILES:
            parser_class = self._load_single_parser(parser_name)
            if parser_class:
                parsers[parser_name] = parser_class
                print(f"✓ Loaded parser: {parser_name}")
            else:
                print(f"✗ Failed to load parser: {parser_name}")

        print(f"\nLoaded {len(parsers)} parsers successfully")
        return parsers

    @staticmethod
    def _load_single_parser(parser_name: str) -> Optional[type]:
        """Load a single parser implementation."""
        try:
            module = importlib.import_module(parser_name)
            if hasattr(module, 'StreamingJsonParser'):
                return module.StreamingJsonParser
            else:
                print(f"✗ No StreamingJsonParser class found in {parser_name}")
                return None
        except Exception as e:
            print(f"✗ Failed to load {parser_name}: {e}")
            return None


class TestDataGenerator:
    """Responsible for generating test datasets."""

    def generate_datasets(self, sizes: List[int]) -> Dict[int, TestDataset]:
        """Generate test datasets of different sizes."""
        datasets = {}

        print("\nGenerating test datasets...")
        for size in tqdm(sizes, desc="Dataset sizes"):
            dataset = self._generate_single_dataset(size)
            datasets[size] = dataset
            print(f"  Size {size}: {dataset.size_chars:,} chars, {dataset.size_bytes:,} bytes")

        return datasets

    @staticmethod
    def _generate_single_dataset(size: int) -> TestDataset:
        """Generate a single test dataset."""
        data = generate_test_data(size)
        json_str = json.dumps(data, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')

        return TestDataset(
            data=data,
            json_str=json_str,
            json_bytes=json_bytes,
            size_chars=len(json_str),
            size_bytes=len(json_bytes),
            chunks=create_streaming_chunks(json_bytes)
        )


class MetricsCollector:
    """Responsible for collecting performance metrics."""

    def collect_metrics(self, parser_name: str, parser_class: type,
                        dataset: TestDataset, run_number: int,
                        protocol: str) -> BenchmarkMetrics:
        """Collect comprehensive metrics for a single benchmark run."""

        metrics = BenchmarkMetrics(
            parser_name=parser_name,
            dataset_size=len(dataset.data) if hasattr(dataset.data, '__len__') else 0,
            run_number=run_number,
            protocol=protocol,
            timestamp=time.time()
        )

        try:
            self._run_benchmark(parser_class, dataset, protocol, metrics)
            metrics.success = True
        except Exception as e:
            metrics.error = str(e)
            metrics.success = False

        return metrics

    def _run_benchmark(self, parser_class: type, dataset: TestDataset,
                       protocol: str, metrics: BenchmarkMetrics) -> None:
        """Run the actual benchmark and collect metrics."""
        # Start monitoring
        tracemalloc.start()
        process = psutil.Process()
        cpu_start = process.cpu_times()

        # Initialize parser
        parser = parser_class()

        # Simulate network transmission
        simulator = NetworkSimulatorFactory.create_simulator(protocol)
        transmission_result = simulator.simulate_transmission(dataset.chunks)

        # Measure serialization
        with Timer() as serialize_timer:
            for chunk in transmission_result.chunks:
                parser.consume(chunk)

        # Measure deserialization
        with Timer() as deserialize_timer:
            parser.get()

        # Calculate final metrics
        self._calculate_final_metrics(
            metrics, serialize_timer, deserialize_timer,
            dataset, process, cpu_start,
            transmission_result.total_latency
        )

        tracemalloc.stop()

    @staticmethod
    def _calculate_final_metrics(metrics: BenchmarkMetrics,
                                 serialize_timer: Timer, deserialize_timer: Timer,
                                 dataset: TestDataset,
                                 process: psutil.Process, cpu_start,
                                 network_latency: float) -> None:
        """Calculate and update final metrics."""
        # CPU time
        cpu_end = process.cpu_times()
        cpu_time = (cpu_end.user - cpu_start.user) + (cpu_end.system - cpu_start.system)

        # Memory usage
        current, peak = tracemalloc.get_traced_memory()

        # Time and throughput
        total_time = serialize_timer.elapsed_ms + deserialize_timer.elapsed_ms
        throughput = calculate_throughput(dataset.size_bytes, total_time)

        # Update metrics
        metrics.serialize_time_ms = serialize_timer.elapsed_ms
        metrics.deserialize_time_ms = deserialize_timer.elapsed_ms
        metrics.total_ser_deser_time_ms = total_time
        metrics.throughput_mbps = throughput
        metrics.cpu_time_seconds = cpu_time
        metrics.memory_current_bytes = current
        metrics.memory_peak_bytes = peak
        metrics.network_latency_ms = network_latency


class ParallelBenchmarkRunner:
    """Handles parallel benchmark execution for speedup calculations."""

    def run_parallel_benchmark(self, parser_class: type,
                               dataset: TestDataset) -> Dict[str, Any]:
        """Run parallel benchmark for speedup calculation."""
        num_workers = min(4, multiprocessing.cpu_count())
        chunk_groups = [dataset.chunks[i::num_workers] for i in range(num_workers)]

        start_time = time.perf_counter()

        try:
            results = self._execute_parallel_processing(parser_class, chunk_groups, num_workers)
            parallel_time = (time.perf_counter() - start_time) * 1000  # ms

            return {
                'parallel_time_ms': parallel_time,
                'num_workers': num_workers,
                'success': True,
                'results': results
            }
        except Exception as e:
            return {
                'parallel_time_ms': 0,
                'num_workers': 0,
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def _execute_parallel_processing(parser_class: type,
                                     chunk_groups: List[List[bytes]],
                                     num_workers: int) -> List[Any]:
        """Execute parallel processing of chunk groups."""
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for chunk_group in chunk_groups:
                future = executor.submit(_process_chunk_group, parser_class, chunk_group)
                futures.append(future)

            results = []
            for future in as_completed(futures):
                results.append(future.result())

            return results


class BenchmarkResultsManager:
    """Manages benchmark results and reporting."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.results: List[Dict[str, Any]] = []

    def add_result(self, metrics: BenchmarkMetrics, algo_info: Dict[str, Any]) -> None:
        """Add a benchmark result with algorithm metadata."""
        result = metrics.to_dict()
        result.update({
            'algorithm_name': algo_info.get('name', metrics.parser_name),
            'time_complexity': algo_info.get('time_complexity', 'Unknown'),
            'space_complexity': algo_info.get('space_complexity', 'Unknown'),
            'overall_complexity': algo_info.get('overall_complexity', 'Unknown')
        })
        self.results.append(result)

    def update_speedup_metrics(self, parser_name: str, dataset_size: int,
                               speedup_info: Dict[str, float]) -> None:
        """Update results with speedup information."""
        for result in self.results:
            if (result['parser_name'] == parser_name and
                    result['dataset_size'] == dataset_size):
                result.update({
                    'speedup': speedup_info['speedup'],
                    'efficiency': speedup_info['efficiency'],
                    'amdahl_theoretical_speedup': speedup_info['theoretical_speedup']
                })

    def save_results(self, format_type: str = 'both') -> None:
        """Save benchmark results to files."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        if format_type in ['csv', 'both']:
            csv_file = self.output_dir / f"benchmark_results_{timestamp}.csv"
            save_results(self.results, csv_file, 'csv')
            print(f"📊 Results saved to: {csv_file}")

        if format_type in ['json', 'both']:
            json_file = self.output_dir / f"benchmark_results_{timestamp}.json"
            save_results(self.results, json_file, 'json')
            print(f"📊 Results saved to: {json_file}")

    def print_summary(self, dataset_sizes: List[int]) -> None:
        """Print a summary of benchmark results."""
        if not self.results:
            print("No results to summarize.")
            return

        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        self._print_success_rate()
        self._print_top_performers()
        self._print_average_times(dataset_sizes)

    def _print_success_rate(self) -> None:
        """Print success rate statistics."""
        successful_runs = sum(1 for r in self.results if r['success'])
        total_runs = len(self.results)
        success_rate = (successful_runs / total_runs) * 100

        print(f"Success Rate: {successful_runs}/{total_runs} ({success_rate:.1f}%)")

    def _print_top_performers(self) -> None:
        """Print top performing parsers by throughput."""
        successful_results = [r for r in self.results if r['success']]
        if not successful_results:
            return

        top_throughput = sorted(
            successful_results,
            key=lambda x: x.get('throughput_mbps', 0),
            reverse=True
        )[:5]

        print("\nTop 5 Performers (Throughput):")
        for i, result in enumerate(top_throughput, 1):
            print(f"  {i}. {result['algorithm_name']} "
                  f"({result['dataset_size']} fields): "
                  f"{result['throughput_mbps']:.2f} MB/s")

    def _print_average_times(self, dataset_sizes: List[int]) -> None:
        """Print average processing times by dataset size."""
        successful_results = [r for r in self.results if r['success']]
        if not successful_results:
            return

        print("\nAverage Processing Times by Dataset Size:")
        for size in sorted(dataset_sizes):
            size_results = [r for r in successful_results if r['dataset_size'] == size]
            if size_results:
                avg_time = sum(r['total_ser_deser_time_ms'] for r in size_results) / len(size_results)
                print(f"  {size:,} fields: {avg_time:.2f} ms")


class StreamingParserBenchmark:
    """Main benchmarking orchestrator following SOLID principles."""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.parser_loader = ParserLoader()
        self.data_generator = TestDataGenerator()
        self.metrics_collector = MetricsCollector()
        self.parallel_runner = ParallelBenchmarkRunner()
        self.results_manager = BenchmarkResultsManager(Path(config.output_dir))

        # Load components
        self.parsers = self.parser_loader.load_parsers()
        self.test_data = self.data_generator.generate_datasets(config.dataset_sizes)

    def run_comprehensive_benchmark(self) -> None:
        """Run the complete benchmark suite."""
        if not self.parsers:
            raise RuntimeError("No parsers loaded")

        total_tests = self._calculate_total_tests()
        print("\n 🚀 Starting comprehensive benchmark...")
        print(f"Parsers: {len(self.parsers)}")
        print(f"Dataset sizes: {self.config.dataset_sizes}")
        print(f"Runs per test: {self.config.runs_per_test}")
        print(f"Protocols: {self.config.protocols}")

        with tqdm(total=total_tests, desc="Running benchmarks") as pbar:
            self._run_all_benchmarks(pbar)

        print(f"\n✅ Benchmark completed! {len(self.results_manager.results)} test results collected.")

    def _calculate_total_tests(self) -> int:
        """Calculate total number of tests to run."""
        return (len(self.parsers) * len(self.test_data) *
                self.config.runs_per_test * len(self.config.protocols))

    def _run_all_benchmarks(self, pbar: tqdm) -> None:
        """Run all benchmark combinations."""
        for parser_name, parser_class in self.parsers.items():
            self._run_parser_benchmarks(parser_name, parser_class, pbar)

    def _run_parser_benchmarks(self, parser_name: str, parser_class: type, pbar: tqdm) -> None:
        """Run benchmarks for a single parser."""
        algo_info = ALGORITHM_METADATA.get(parser_name, {})

        for dataset_size, dataset in self.test_data.items():
            sequential_times = self._run_sequential_benchmarks(
                parser_name, parser_class, dataset, algo_info, pbar
            )

            if sequential_times:
                self._run_speedup_analysis(
                    parser_name, parser_class, dataset_size, dataset, sequential_times
                )

    def _run_sequential_benchmarks(self, parser_name: str, parser_class: type,
                                   dataset: TestDataset, algo_info: Dict[str, Any],
                                   pbar: tqdm) -> List[float]:
        """Run sequential benchmarks for all protocols."""
        sequential_times = []

        for protocol in self.config.protocols:
            for run in range(self.config.runs_per_test):
                metrics = self.metrics_collector.collect_metrics(
                    parser_name, parser_class, dataset, run + 1, protocol
                )

                self.results_manager.add_result(metrics, algo_info)

                if metrics.success:
                    sequential_times.append(metrics.total_ser_deser_time_ms)

                pbar.update(1)

        return sequential_times

    def _run_speedup_analysis(self, parser_name: str, parser_class: type,
                              dataset_size: int, dataset: TestDataset,
                              sequential_times: List[float]) -> None:
        """Run parallel benchmark and calculate speedup."""
        avg_sequential_time = sum(sequential_times) / len(sequential_times)
        parallel_result = self.parallel_runner.run_parallel_benchmark(parser_class, dataset)

        if parallel_result['success']:
            speedup = calculate_amdahl_speedup(
                avg_sequential_time,
                parallel_result['parallel_time_ms'],
                parallel_result['num_workers']
            )

            self.results_manager.update_speedup_metrics(parser_name, dataset_size, speedup)


def _process_chunk_group(parser_class: type, chunks: List[bytes]) -> Any:
    """Process a group of chunks in parallel worker."""
    parser = parser_class()
    for chunk in chunks:
        parser.consume(chunk)
    return parser.get()


def _sanitize_output_dir(output_arg: str) -> Path:
    """Sanitize the user-provided output directory argument.

    Resolves the provided path, forbidding path traversal attempts that
    escape the current working directory. If a path outside the current
    working directory is requested, a ``ValueError`` is raised.

    Parameters
    ----------
    output_arg: str
        The raw ``--output/-o`` argument value.

    Returns
    -------
    Path
        A safe, absolute ``Path`` inside the current working directory.
    """
    base_dir = Path.cwd().resolve()
    candidate = Path(output_arg).expanduser()

    # Resolve relative paths against the base directory so that
    # "../foo" cannot escape : resolve() collapses any ".." segments.
    resolved = (candidate if candidate.is_absolute() else base_dir / candidate).resolve()

    try:
        # ``relative_to`` raises ``ValueError`` if *resolved* is not within *base_dir*.
        resolved.relative_to(base_dir)
    except ValueError:
        raise ValueError("Invalid output directory: Path traversal detected") from None

    return resolved


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Streaming JSON Parser Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python benchmark_runner.py --runs 3 --output results
  python benchmark_runner.py --runs 5 --format json --output /tmp/benchmarks
        """
    )

    parser.add_argument(
        '--runs', '-r',
        type=int,
        default=3,
        help='Number of runs per test (default: 3)'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        default='.',
        help='Output directory for results (default: current directory)'
    )

    parser.add_argument(
        '--format', '-f',
        choices=['csv', 'json', 'both'],
        default='both',
        help='Output format (default: both)'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress progress output'
    )

    return parser


def main():
    """Main entry point for the benchmark runner."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    output_dir = _sanitize_output_dir(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Create configuration
        config = BenchmarkConfig(
            output_dir=str(output_dir),
            runs_per_test=args.runs
        )

        # Initialize and run benchmark
        benchmark = StreamingParserBenchmark(config)

        if len(benchmark.parsers) == 0:
            print("❌ No parsers found! Make sure parser files are in the current directory.")
            sys.exit(1)

        # Run the benchmark
        benchmark.run_comprehensive_benchmark()

        # Save results
        benchmark.results_manager.save_results(args.format)

        # Print summary
        if not args.quiet:
            benchmark.results_manager.print_summary(config.dataset_sizes)

        print("🎉 Benchmark completed successfully!")

    except KeyboardInterrupt:
        print("\n⚠️  Benchmark interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
