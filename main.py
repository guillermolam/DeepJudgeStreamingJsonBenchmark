"""
Comprehensive Benchmarking System for Streaming JSON Parsers
============================================================

This script benchmarks streaming JSON parser implementations across multiple
metrics including performance, throughput, CPU usage, and network simulation.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Type

# Ensure `src/` is in sys.path so imports like `serializers.json_parser` work
sys.path.insert(0, str(Path(__file__).parent / "src"))

import argparse
import importlib
import json
import multiprocessing
import time
import traceback
import tracemalloc
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Any, Tuple
from dataclasses import dataclass

import psutil
from tqdm import tqdm

from simulation.algo_metadata import ALGORITHM_METADATA
from simulation.data_gen import generate_test_data, create_streaming_chunks
from simulation.net_sim import HTTPSimulator, TCPSimulator, TelnetSimulator
from simulation.utils import (
    Timer,
    calculate_throughput,
    calculate_amdahl_speedup,
    save_results,
)


def sanitize_output_path(
    base_path: str, user_path: str, subdir_allowed: bool = True
) -> str:
    """
    Sanitize an output path to prevent path traversal attacks.

    Args:
        base_path: Absolute base path that should contain the output (e.g., project root)
        user_path: User-provided path (relative or absolute)
        subdir_allowed: Whether subdirectories are allowed within base_path

    Returns:
        Sanitized absolute path

    Raises:
        ValueError: If the target path is outside the allowed base path
    """
    # Convert base_path to an absolute path
    base_path = os.path.abspath(base_path)

    # Handle user_path - if it's absolute, make it relative to base_path
    if os.path.isabs(user_path):
        # Strip leading path separators to make it relative
        user_path = user_path.lstrip(os.sep).lstrip(os.altsep or "")

    # Join a base path with a user path
    target_path = os.path.join(base_path, user_path)

    # Resolve symbolic links and relative path components (../, ./)
    real_target_path = os.path.realpath(target_path)

    # Check if the resolved path is within the allowed base path
    if subdir_allowed:
        # Allow subdirectories - check if base_path is a prefix of real_target_path
        try:
            os.path.relpath(real_target_path, base_path)
            # If relpath doesn't raise ValueError, the path is within base_path
            if (
                not real_target_path.startswith(base_path + os.sep)
                and real_target_path != base_path
            ):
                raise ValueError(
                    f"Target path is outside allowed base directory: {real_target_path}"
                )
        except ValueError as e:
            raise ValueError(
                f"Target path is outside allowed base directory: {real_target_path}"
            ) from e
    else:
        # Only allow files directly in base_path
        if os.path.dirname(real_target_path) != base_path:
            raise ValueError(
                f"Target path must be directly in base directory: {real_target_path}"
            )

    return real_target_path


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark execution."""

    output_dir: str = "."
    runs_per_test: int = 3
    protocols: Optional[List[str]] = None
    dataset_sizes: Optional[List[int]] = None

    def __post_init__(self):
        if self.protocols is None:
            self.protocols = ["http", "tcp", "telnet"]
        if self.dataset_sizes is None:
            self.dataset_sizes = [100, 1000, 2000]


@dataclass
class TestDataset:
    """Container for test dataset information."""

    size: int
    data: Dict[str, Any]
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
    serialize_time_ms: float = 0.0
    deserialize_time_ms: float = 0.0
    total_ser_deser_time_ms: float = 0.0
    total_with_conversions_ms: float = 0.0
    throughput_mbps: float = 0.0
    cpu_time_seconds: float = 0.0
    memory_current_bytes: int = 0
    memory_peak_bytes: int = 0
    synchronization_overhead_ms: float = 0.0
    network_latency_ms: float = 0.0
    speedup: Optional[float] = None
    efficiency: Optional[float] = None
    amdahl_theoretical_speedup: Optional[float] = None
    algorithm_name: str = ""
    time_complexity: str = "Unknown"
    space_complexity: str = "Unknown"
    overall_complexity: str = "Unknown"


class ParserDiscovery:
    BASE_PACKAGE = "serializers"
    SUBMODULES = ["raw", "solid", "anyio"]

    def discover_parsers(self) -> Dict[str, Type]:
        parsers: Dict[str, Type] = {}
        failed_parsers = []

        for sub, module_name, full_mod_path in self._iter_module_paths():
            parser_cls = self._load_parser_class(full_mod_path)
            if parser_cls is None:
                failed_parsers.append((sub, module_name, full_mod_path))
            else:
                key = f"{sub}.{module_name}"  # Ensure a unique key for each parser
                parsers[key] = parser_cls
                print(f"✓ Loaded parser: {key}")

        if failed_parsers:
            print("\n❌ The following parsers failed to load:")
            for sub, module_name, mod_path in failed_parsers:
                print(f"  - {sub}.{module_name} (module: {mod_path})")
            raise RuntimeError(
                "One or more parser modules could not be loaded. See above for details."
            )

        print(f"\nLoaded {len(parsers)} parsers successfully")
        return parsers

    def _iter_module_paths(self):
        # 🔽 Update this line
        root = Path(__file__).parent / "src" / self.BASE_PACKAGE
        for sub in self.SUBMODULES:
            pkg_dir = root / sub
            if not pkg_dir.is_dir():
                continue
            for py_file in pkg_dir.glob("*.py"):
                if py_file.name == "__init__.py":
                    continue
                module_name = py_file.stem
                # The Full module path needs to reflect the fact that src is in sys.path
                full_mod_path = f"{self.BASE_PACKAGE}.{sub}.{module_name}"
                yield sub, module_name, full_mod_path

    @staticmethod
    def _load_parser_class(full_mod_path: str) -> Optional[Type]:
        try:
            module = importlib.import_module(full_mod_path)
            cls = getattr(module, "StreamingJsonParser", None)
            if not cls:
                print(
                    f"❌ 'StreamingJsonParser' class not found in module: {full_mod_path}"
                )
            return cls
        except ImportError as e:
            print(f"❌ ImportError for {full_mod_path}: {e}")
            return None


class TestDatasetGenerator:
    """Generates test datasets for benchmarking."""

    def generate_datasets(self, sizes: List[int]) -> Dict[int, TestDataset]:
        """Generate test datasets of different sizes."""
        datasets = {}

        print("\nGenerating test datasets...")
        for size in tqdm(sizes, desc="Dataset sizes"):
            dataset = self._create_dataset(size)
            datasets[size] = dataset
            tqdm.write(
                f"  Size {size}: {dataset.size_chars:,} chars, {dataset.size_bytes:,} bytes"
            )

        return datasets

    @staticmethod
    def _create_dataset(size: int) -> TestDataset:
        """Create a single test dataset."""
        data = generate_test_data(size)
        json_str = json.dumps(data, separators=(",", ":"))
        json_bytes = json_str.encode("utf-8")
        chunks = create_streaming_chunks(json_bytes)

        return TestDataset(
            size=size,
            data=data,
            json_str=json_str,
            json_bytes=json_bytes,
            size_chars=len(json_str),
            size_bytes=len(json_bytes),
            chunks=chunks,
        )


class NetworkSimulatorFactory:
    """Factory for creating network simulators."""

    def __init__(self):
        self._simulators = {
            "http": HTTPSimulator(),
            "tcp": TCPSimulator(),
            "telnet": TelnetSimulator(),
        }

    def get_simulator(self, protocol: str):
        """Get a network simulator for the specified protocol."""
        return self._simulators.get(protocol)


class MetricsCollector:
    """Collects and manages benchmark metrics."""

    def __init__(self):
        self._process = psutil.Process()

    def start_collection(self) -> Tuple[Any, Any]:
        """Start collecting metrics."""
        tracemalloc.start()
        return self._process.cpu_times(), time.perf_counter()

    def stop_collection(self, cpu_start: Any) -> Tuple[float, int, int]:
        """Stop collecting metrics and return results."""
        cpu_end = self._process.cpu_times()
        cpu_time = (cpu_end.user - cpu_start.user) + (cpu_end.system - cpu_start.system)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return cpu_time, current, peak


class SingleRunBenchmark:
    """Handles execution of a single benchmark run."""

    def __init__(
        self,
        network_factory: NetworkSimulatorFactory,
        metrics_collector: MetricsCollector,
    ):
        self._network_factory = network_factory
        self._metrics_collector = metrics_collector

    def execute(
        self,
        parser_name: str,
        parser_class: type,
        dataset: TestDataset,
        run_number: int,
        protocol: str,
    ) -> BenchmarkMetrics:
        """Execute a single benchmark run."""
        metrics = BenchmarkMetrics(
            parser_name=parser_name,
            dataset_size=dataset.size,
            run_number=run_number,
            protocol=protocol,
            timestamp=time.time(),
        )

        try:
            self._run_benchmark(parser_class, dataset, protocol, metrics)
            metrics.success = True
        except Exception as e:
            metrics.error = str(e)
            metrics.success = False

        return metrics

    def _run_benchmark(
        self,
        parser_class: type,
        dataset: TestDataset,
        protocol: str,
        metrics: BenchmarkMetrics,
    ) -> None:
        """Execute the actual benchmark logic."""
        # Start a metrics collection
        cpu_start, _ = self._metrics_collector.start_collection()

        # Initialize parser
        parser = parser_class()

        # Simulate network transmission
        simulator = self._network_factory.get_simulator(protocol)
        transmission_result = simulator.simulate_transmission(dataset.chunks)
        transmitted_chunks = transmission_result.chunks
        metrics.network_latency_ms = transmission_result.total_latency

        # Measure serialization (parsing chunks)
        with Timer() as serialize_timer:
            for chunk in transmitted_chunks:
                parser.consume(chunk)

        # Measure deserialization (getting final result)
        with Timer() as deserialize_timer:
            result = parser.get()

        # Stop a metrics collection
        cpu_time, memory_current, memory_peak = self._metrics_collector.stop_collection(
            cpu_start
        )

        # Update metrics
        self._update_metrics(
            metrics,
            serialize_timer,
            deserialize_timer,
            cpu_time,
            memory_current,
            memory_peak,
            dataset,
            result,
        )

    @staticmethod
    def _update_metrics(
        metrics: BenchmarkMetrics,
        serialize_timer: Timer,
        deserialize_timer: Timer,
        cpu_time: float,
        memory_current: int,
        memory_peak: int,
        dataset: TestDataset,
        result: Any,
    ) -> None:
        """Update metrics with collected data_gen."""
        total_time = serialize_timer.elapsed_ms + deserialize_timer.elapsed_ms
        throughput = calculate_throughput(dataset.size_bytes, total_time)

        metrics.serialize_time_ms = serialize_timer.elapsed_ms
        metrics.deserialize_time_ms = deserialize_timer.elapsed_ms
        metrics.total_ser_deser_time_ms = total_time
        metrics.total_with_conversions_ms = total_time
        metrics.throughput_mbps = throughput
        metrics.cpu_time_seconds = cpu_time
        metrics.memory_current_bytes = memory_current
        metrics.memory_peak_bytes = memory_peak

        # Calculate result sizes
        if result:
            result_str = str(result)
            metrics.partial_serialization_chars = dataset.size_chars
            metrics.partial_serialization_bytes = dataset.size_bytes
            metrics.partial_deserialization_chars = len(result_str)
            metrics.partial_deserialization_bytes = len(result_str.encode("utf-8"))


class ParallelBenchmark:
    """Handles parallel benchmark execution for speedup calculation."""

    def execute(
        self, parser_class: type, dataset: TestDataset, max_workers: int = 4
    ) -> Dict[str, Any]:
        """Execute parallel benchmark for speedup calculation."""
        if parser_class is None:
            return {
                "parallel_time_ms": 0,
                "num_workers": 0,
                "success": False,
                "error": "parser_class cannot be None",
            }

        if not dataset.chunks:
            return {
                "parallel_time_ms": 0,
                "num_workers": 0,
                "success": False,
                "error": "dataset.chunks is empty",
            }

        num_workers = min(max_workers, multiprocessing.cpu_count())
        chunk_groups = [dataset.chunks[i::num_workers] for i in range(num_workers)]

        start_time = time.perf_counter()
        start_memory = psutil.Process().memory_info().rss

        try:
            timeout_seconds = 30  # Configurable timeout
            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                futures = [
                    executor.submit(
                        self._process_chunk_group, parser_class, chunk_group
                    )
                    for chunk_group in chunk_groups
                ]

                results = []
                for future in as_completed(futures, timeout=timeout_seconds):
                    try:
                        results.append(future.result(timeout=timeout_seconds))
                    except ValueError:
                        # Log the error but continue with other workers
                        print(
                            f"Timeout occurred while processing chunk group: {future.exception()}"
                        )
                        continue

            parallel_time = (time.perf_counter() - start_time) * 1000  # ms
            end_memory = psutil.Process().memory_info().rss

            return {
                "parallel_time_ms": parallel_time,
                "num_workers": num_workers,
                "memory_usage_mb": (end_memory - start_memory) / 1024 / 1024,
                "success": True,
            }

        except Exception as e:
            return {
                "parallel_time_ms": 0,
                "num_workers": 0,
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def _process_chunk_group(parser_class: type, chunks: List[bytes]) -> Any:
        """Process a group of chunks in parallel worker."""
        parser = parser_class()
        for chunk in chunks:
            parser.consume(chunk)
        return parser.get()


class SpeedupCalculator:
    """Calculates speedup metrics for parallel execution."""

    @staticmethod
    def calculate_speedup(
        sequential_times: List[float], parallel_result: Dict[str, Any]
    ) -> Optional[Dict[str, float]]:
        """Calculate speedup metrics."""
        if not sequential_times or not parallel_result["success"]:
            return None

        avg_sequential_time = sum(sequential_times) / len(sequential_times)
        return calculate_amdahl_speedup(
            avg_sequential_time,
            parallel_result["parallel_time_ms"],
            parallel_result["num_workers"],
        )


class BenchmarkResultsManager:
    """Manages benchmark results and metadata."""

    def __init__(self):
        self._results = []

    def add_result(self, metrics: BenchmarkMetrics) -> None:
        """Add a benchmark result."""
        # Add algorithm metadata
        algo_info = ALGORITHM_METADATA.get(metrics.parser_name, {})
        metrics.algorithm_name = algo_info.get("name", metrics.parser_name)
        metrics.time_complexity = algo_info.get("time_complexity", "Unknown")
        metrics.space_complexity = algo_info.get("space_complexity", "Unknown")
        metrics.overall_complexity = algo_info.get("overall_complexity", "Unknown")

        self._results.append(metrics)

    def update_speedup_metrics(
        self, parser_name: str, dataset_size: int, speedup_data: Dict[str, float]
    ) -> None:
        """Update speedup metrics for matching results."""
        for result in self._results:
            if (
                result.parser_name == parser_name
                and result.dataset_size == dataset_size
            ):
                result.speedup = speedup_data["speedup"]
                result.efficiency = speedup_data["efficiency"]
                result.amdahl_theoretical_speedup = speedup_data["theoretical_speedup"]

    def get_results(self) -> List[Dict[str, Any]]:
        """Get all results as dictionaries."""
        return [self._metrics_to_dict(metrics) for metrics in self._results]

    def get_sequential_times(self, parser_name: str, dataset_size: int) -> List[float]:
        """Get sequential times for a specific parser and dataset size."""
        return [
            result.total_ser_deser_time_ms
            for result in self._results
            if (
                result.parser_name == parser_name
                and result.dataset_size == dataset_size
                and result.success
            )
        ]

    @staticmethod
    def _metrics_to_dict(metrics: BenchmarkMetrics) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "parser_name": metrics.parser_name,
            "dataset_size": metrics.dataset_size,
            "run_number": metrics.run_number,
            "protocol": metrics.protocol,
            "timestamp": metrics.timestamp,
            "success": metrics.success,
            "error": metrics.error,
            "serialize_time_ms": metrics.serialize_time_ms,
            "deserialize_time_ms": metrics.deserialize_time_ms,
            "total_ser_deser_time_ms": metrics.total_ser_deser_time_ms,
            "total_with_conversions_ms": metrics.total_with_conversions_ms,
            "throughput_mbps": metrics.throughput_mbps,
            "cpu_time_seconds": metrics.cpu_time_seconds,
            "memory_current_bytes": metrics.memory_current_bytes,
            "memory_peak_bytes": metrics.memory_peak_bytes,
            "synchronization_overhead_ms": metrics.synchronization_overhead_ms,
            "network_latency_ms": metrics.network_latency_ms,
            "speedup": metrics.speedup,
            "efficiency": metrics.efficiency,
            "amdahl_theoretical_speedup": metrics.amdahl_theoretical_speedup,
            "algorithm_name": metrics.algorithm_name,
            "time_complexity": metrics.time_complexity,
            "space_complexity": metrics.space_complexity,
            "overall_complexity": metrics.overall_complexity,
        }


class BenchmarkSummaryGenerator:
    """Generates benchmark summary reports."""

    def print_summary(
        self, results: List[Dict[str, Any]], datasets: Dict[int, TestDataset]
    ) -> None:
        """Print a summary of benchmark results."""
        if not results:
            print("No results to summarize.")
            return

        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        self._print_success_rate(results)
        self._print_top_performers(results)
        self._print_average_times(results, datasets)

    @staticmethod
    def _print_success_rate(results: List[Dict[str, Any]]) -> None:
        """Print success rate statistics."""
        successful_runs = sum(1 for r in results if r["success"])
        total_runs = len(results)
        success_rate = (successful_runs / total_runs) * 100
        print(f"Success Rate: {successful_runs}/{total_runs} ({success_rate:.1f}%)")

    @staticmethod
    def _print_top_performers(results: List[Dict[str, Any]]) -> None:
        """Print top performing algorithms."""
        successful_results = [r for r in results if r["success"]]
        if not successful_results:
            return

        top_throughput = sorted(
            successful_results, key=lambda x: x.get("throughput_mbps", 0), reverse=True
        )[:5]

        print("\nTop 5 Performers (Throughput):")
        for i, result in enumerate(top_throughput, 1):
            print(
                f"  {i}. {result['algorithm_name']} "
                f"({result['dataset_size']} fields): "
                f"{result['throughput_mbps']:.2f} MB/s"
            )

    @staticmethod
    def _print_average_times(
        results: List[Dict[str, Any]], datasets: Dict[int, TestDataset]
    ) -> None:
        """Print average processing times by dataset size."""
        successful_results = [r for r in results if r["success"]]
        if not successful_results:
            return

        print("\nAverage Processing Times by Dataset Size:")
        for size in sorted(datasets.keys()):
            size_results = [r for r in successful_results if r["dataset_size"] == size]
            if size_results:
                avg_time = sum(
                    r["total_ser_deser_time_ms"] for r in size_results
                ) / len(size_results)
                print(f"  {size:,} fields: {avg_time:.2f} ms")


class StreamingParserBenchmark:
    """Main benchmarking class for streaming JSON parsers."""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.output_dir = Path(config.output_dir)

        # Initialize components
        self.parser_discovery = ParserDiscovery()
        self.dataset_generator = TestDatasetGenerator()
        self.network_factory = NetworkSimulatorFactory()
        self.metrics_collector = MetricsCollector()
        self.single_run_benchmark = SingleRunBenchmark(
            self.network_factory, self.metrics_collector
        )
        self.parallel_benchmark = ParallelBenchmark()
        self.speedup_calculator = SpeedupCalculator()
        self.results_manager = BenchmarkResultsManager()
        self.summary_generator = BenchmarkSummaryGenerator()

        # Load parsers and generate datasets
        self.parsers = self.parser_discovery.discover_parsers()
        self.test_data = self.dataset_generator.generate_datasets(config.dataset_sizes)

    def run_comprehensive_benchmark(self) -> None:
        """Run the complete benchmark suite."""
        if not self.parsers:
            print(
                "❌ No parsers found! Make sure parser files are in the current directory."
            )
            sys.exit(1)

        print("\n🚀 Starting comprehensive benchmark...")
        print(f"Parsers: {len(self.parsers)}")
        print(f"Dataset sizes: {list(self.test_data.keys())}")
        print(f"Runs per test: {self.config.runs_per_test}")
        print(f"Protocols: {', '.join(self.config.protocols)}")

        total_tests = (
            len(self.parsers)
            * len(self.test_data)
            * self.config.runs_per_test
            * len(self.config.protocols)
        )

        with tqdm(total=total_tests, desc="Running benchmarks") as pbar:
            self._execute_benchmarks(pbar)

        print(
            f"\n✅ Benchmark completed! {len(self.results_manager.get_results())} test results collected."
        )

    def _execute_benchmarks(self, pbar: tqdm) -> None:
        """Execute all benchmark combinations."""
        for parser_name, parser_class in self.parsers.items():
            for dataset_size, dataset in self.test_data.items():
                self._benchmark_parser_dataset(parser_name, parser_class, dataset, pbar)

    def _benchmark_parser_dataset(
        self, parser_name: str, parser_class: type, dataset: TestDataset, pbar: tqdm
    ) -> None:
        """Benchmark a parser with a specific dataset."""
        # Run sequential benchmarks for each protocol
        for protocol in self.config.protocols:
            for run in range(self.config.runs_per_test):
                metrics = self.single_run_benchmark.execute(
                    parser_name, parser_class, dataset, run + 1, protocol
                )
                self.results_manager.add_result(metrics)
                pbar.update(1)

        # Run parallel benchmark for speedup calculation
        self._calculate_speedup_metrics(parser_name, parser_class, dataset)

    def _calculate_speedup_metrics(
        self, parser_name: str, parser_class: type, dataset: TestDataset
    ) -> None:
        """Calculate and update speedup metrics."""
        try:
            sequential_times = self.results_manager.get_sequential_times(
                parser_name, dataset.size
            )

            if sequential_times:
                parallel_result = self.parallel_benchmark.execute(parser_class, dataset)
                if not isinstance(parallel_result, dict):
                    raise TypeError(f"Expected dict, got {type(parallel_result)}")

                speedup_data = self.speedup_calculator.calculate_speedup(
                    sequential_times, parallel_result
                )

                if speedup_data:
                    self.results_manager.update_speedup_metrics(
                        parser_name, dataset.size, speedup_data
                    )
        except Exception as e:
            print(f"Error calculating speedup metrics: {str(e)}")

    def save_results(self, format_type: str = "both") -> None:
        """Save benchmark results to files."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results = self.results_manager.get_results()

        if format_type in ["csv", "both"]:
            csv_file = self.output_dir / f"benchmark_results_{timestamp}.csv"
            save_results(results, csv_file, "csv")
            print(f"📊 Results saved to: {csv_file}")

        if format_type in ["json", "both"]:
            json_file = self.output_dir / f"benchmark_results_{timestamp}.json"
            save_results(results, json_file, "json")
            print(f"📊 Results saved to: {json_file}")

    def print_summary(self) -> None:
        """Print a summary of benchmark results."""
        results = self.results_manager.get_results()
        self.summary_generator.print_summary(results, self.test_data)


class ArgumentParser:
    """Handles command line argument parsing."""

    @staticmethod
    def parse_args() -> argparse.Namespace:
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(
            description="Comprehensive Streaming JSON Parser Benchmark",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python main.py --runs 3 --output results
  python main.py --runs 5 --format json --output /tmp/benchmarks
            """,
        )

        parser.add_argument(
            "--runs",
            "-r",
            type=int,
            default=3,
            help="Number of runs per test (default: 3)",
        )

        parser.add_argument(
            "--output",
            "-o",
            type=str,
            default=".",
            help="Output directory for results (default: current directory)",
        )

        parser.add_argument(
            "--format",
            "-f",
            choices=["csv", "json", "both"],
            default="both",
            help="Output format (default: both)",
        )

        parser.add_argument(
            "--quiet", "-q", action="store_true", help="Suppress progress output"
        )

        return parser.parse_args()


def main():
    """Main entry point for the benchmark runner."""
    arg_parser = ArgumentParser()
    args = arg_parser.parse_args()

    # Define the allowed base directory (project root)
    project_root = str(Path(__file__).parent.absolute())

    try:
        # Sanitize and validate the output directory passed as argument
        sanitized_output_path = sanitize_output_path(
            base_path=project_root, user_path=args.output, subdir_allowed=True
        )

        # Create output directory if it doesn't exist
        if not sanitized_output_path:
            Path(sanitized_output_path).mkdir(parents=True, exist_ok=True)

        print(f"📁 Using sanitized output directory: {sanitized_output_path}")

    except ValueError as e:
        print(f"❌ Invalid output directory: {e}")
        sys.exit(1)

    try:
        # Initialize and run benchmark
        config = BenchmarkConfig(
            output_dir=str(sanitized_output_path), runs_per_test=args.runs
        )

        benchmark = StreamingParserBenchmark(config)
        benchmark.run_comprehensive_benchmark()
        benchmark.save_results(args.format)

        if not args.quiet:
            benchmark.print_summary()

        print("\n🎉 Benchmark completed successfully!")

    except KeyboardInterrupt:
        print("\n⚠️  Benchmark interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
