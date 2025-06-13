"""
Utility Functions for Streaming JSON Parser Benchmarks
======================================================

Contains helper functions for timing, calculations, and result management.
"""

import csv
import json
import math
import time
from pathlib import Path
from typing import Dict, List, Any, Union

from click._termui_impl import ProgressBar


class Timer:
    """High-precision timer for benchmarking."""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed_ns = 0
        self.elapsed_ms = 0.0
        self.elapsed_seconds = 0.0

    def start(self):
        """Start the timer."""
        self.start_time = time.perf_counter_ns()
        return self

    def stop(self):
        """Stop the timer and calculate elapsed time."""
        if self.start_time is None:
            raise RuntimeError("Timer not started")

        self.end_time = time.perf_counter_ns()
        self.elapsed_ns = self.end_time - self.start_time
        self.elapsed_ms = self.elapsed_ns / 1_000_000
        self.elapsed_seconds = self.elapsed_ns / 1_000_000_000
        return self

    def __enter__(self):
        """Context manager entry."""
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def reset(self):
        """Reset the timer."""
        self.start_time = None
        self.end_time = None
        self.elapsed_ns = 0
        self.elapsed_ms = 0.0
        self.elapsed_seconds = 0.0


def calculate_throughput(data_size_bytes: int, time_ms: float) -> float:
    """
    Calculate throughput in MB/s.

    Args:
        data_size_bytes: Size of data in bytes
        time_ms: Time taken in milliseconds

    Returns:
        Throughput in MB/s
    """
    if time_ms <= 0:
        return 0.0

    # Convert to MB/s
    data_size_mb = data_size_bytes / (1024 * 1024)
    time_seconds = time_ms / 1000

    return data_size_mb / time_seconds


def calculate_amdahl_speedup(sequential_time_ms: float, parallel_time_ms: float,
                             num_processors: int) -> Dict[str, float]:
    """
    Calculate speedup and efficiency using Amdahl's Law.

    Args:
        sequential_time_ms: Time for sequential execution
        parallel_time_ms: Time for parallel execution
        num_processors: Number of processors used

    Returns:
        Dictionary with speedup metrics
    """

    if sequential_time_ms <= 0 or parallel_time_ms <= 0:
        return {
            'speedup': 0.0,
            'efficiency': 0.0,
            'theoretical_speedup': 0.0,
            'parallel_fraction': 0.0
        }

    # Actual speedup
    actual_speedup = sequential_time_ms / parallel_time_ms

    # Efficiency (speedup per processor)
    efficiency = actual_speedup / num_processors

    # Estimate a parallel fraction (assuming some overhead)
    # This is a simplified estimation
    if actual_speedup >= num_processors:
        parallel_fraction = 1.0
    else:
        # Solve Amdahl's equation: S = 1 / (1 - p + p/n)
        # Where S = speedup, p = parallel fraction, n = processors
        # Rearranging: p = (S * n - n) / (S * n - 1)
        if actual_speedup * num_processors - 1 > 0:
            parallel_fraction = (actual_speedup * num_processors - num_processors) / (
                        actual_speedup * num_processors - 1)
        else:
            parallel_fraction = 0.0

    # Theoretical maximum speedup with this parallel fraction
    theoretical_speedup = 1 / (1 - parallel_fraction + parallel_fraction / num_processors)

    return {
        'speedup': actual_speedup,
        'efficiency': efficiency,
        'theoretical_speedup': theoretical_speedup,
        'parallel_fraction': max(0.0, min(1.0, parallel_fraction))
    }


def calculate_statistics(values: List[float]) -> Dict[str, float]:
    """
    Calculate basic statistics for a list of values.

    Args:
        values: List of numeric values

    Returns:
        Dictionary with statistical measures
    """

    if not values:
        return {
            'count': 0,
            'mean': 0.0,
            'median': 0.0,
            'min': 0.0,
            'max': 0.0,
            'std_dev': 0.0,
            'variance': 0.0
        }

    sorted_values = sorted(values)
    n = len(values)

    # Basic measures
    mean = sum(values) / n
    median = sorted_values[n // 2] if n % 2 == 1 else (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
    min_val = min(values)
    max_val = max(values)

    # Variance and standard deviation
    variance = sum((x - mean) ** 2 for x in values) / n
    std_dev = math.sqrt(variance)

    return {
        'count': n,
        'mean': mean,
        'median': median,
        'min': min_val,
        'max': max_val,
        'std_dev': std_dev,
        'variance': variance
    }


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes in human-readable format.

    Args:
        bytes_value: Number of bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """

    if bytes_value == 0:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0

    value = float(bytes_value)
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(value)} {units[unit_index]}"
    else:
        return f"{value:.2f} {units[unit_index]}"


def format_time(time_ms: float) -> str:
    """
    Format time in human-readable format.

    Args:
        time_ms: Time in milliseconds

    Returns:
        Formatted string (e.g., "1.5 s", "250 ms")
    """

    if time_ms < 1:
        return f"{time_ms * 1000:.1f} μs"
    elif time_ms < 1000:
        return f"{time_ms:.2f} ms"
    else:
        return f"{time_ms / 1000:.2f} s"


def save_results(results: List[Dict[str, Any]], output_path: Union[str, Path],
                 format_type: str = 'csv'):
    """
    Save benchmark results to file.

    Args:
        results: List of result dictionaries
        output_path: Path to output file
        format_type: Format type ('csv' or 'json')
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format_type.lower() == 'csv':
        save_results_csv(results, output_path)
    elif format_type.lower() == 'json':
        save_results_json(results, output_path)
    else:
        raise ValueError(f"Unsupported format type: {format_type}")


def save_results_csv(results: List[Dict[str, Any]], output_path: Path):
    """Save results to CSV file."""

    if not results:
        return

    # Get all possible field names
    all_fields = set()
    for result in results:
        all_fields.update(result.keys())

    # Sort fields for consistent output
    fieldnames = sorted(all_fields)

    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            # Fill missing fields with empty strings
            row = {field: result.get(field, '') for field in fieldnames}
            writer.writerow(row)


def save_results_json(results: List[Dict[str, Any]], output_path: Path):
    """Save results to JSON file."""

    output_data = {
        'metadata': {
            'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_results': len(results),
            'format_version': '1.0'
        },
        'results': results
    }

    with open(output_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(output_data, jsonfile, indent=2, default=str)


def create_progress_bar(total: int, description: str = "Progress") -> 'ProgressBar':
    """
    Create a simple progress bar.

    Args:
        total: Total number of items
        description: Description for the progress bar

    Returns:
        ProgressBar instance
    """

    try:
        from tqdm import tqdm
        return tqdm(total=total, desc=description)
    except ImportError:
        # Fallback to simple progress indicator
        return SimpleProgressBar(total, description)


class SimpleProgressBar:
    """Simple progress bar fallback when tqdm is not available."""

    def __init__(self, total: int, description: str = "Progress"):
        self.total = total
        self.description = description
        self.current = 0
        self.last_percent = -1

    def update(self, n: int = 1):
        """Update progress by n steps."""
        self.current += n
        percent = int((self.current / self.total) * 100)

        if percent != self.last_percent and percent % 10 == 0:
            print(f"{self.description}: {percent}% ({self.current}/{self.total})")
            self.last_percent = percent

    def close(self):
        """Close the progress bar."""
        if self.current >= self.total:
            print(f"{self.description}: 100% ({self.total}/{self.total}) - Complete!")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def validate_benchmark_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate benchmark results for consistency and completeness.

    Args:
        results: List of benchmark results

    Returns:
        Validation report
    """

    if not results:
        return {
            'valid': False,
            'errors': ['No results to validate'],
            'warnings': [],
            'summary': {}
        }

    errors = []
    warnings = []

    # Required fields
    required_fields = [
        'parser_name', 'dataset_size', 'run_number', 'protocol',
        'success', 'serialize_time_ms', 'deserialize_time_ms'
    ]

    # Check for required fields
    for i, result in enumerate(results):
        missing_fields = [field for field in required_fields if field not in result]
        if missing_fields:
            errors.append(f"Result {i}: Missing required fields: {missing_fields}")

    # Check for reasonable values
    for i, result in enumerate(results):
        if result.get('success', False):
            # Check timing values
            serialize_time = result.get('serialize_time_ms', 0)
            deserialize_time = result.get('deserialize_time_ms', 0)

            if serialize_time < 0:
                errors.append(f"Result {i}: Negative serialize time: {serialize_time}")
            if deserialize_time < 0:
                errors.append(f"Result {i}: Negative deserialize time: {deserialize_time}")

            # Check for suspiciously high values
            if serialize_time > 60000:  # 1 minute
                warnings.append(f"Result {i}: Very high serialize time: {serialize_time} ms")
            if deserialize_time > 60000:
                warnings.append(f"Result {i}: Very high deserialize time: {deserialize_time} ms")

    # Summary statistics
    successful_results = [r for r in results if r.get('success', False)]
    failed_results = [r for r in results if not r.get('success', False)]

    summary = {
        'total_results': len(results),
        'successful_results': len(successful_results),
        'failed_results': len(failed_results),
        'success_rate': len(successful_results) / len(results) * 100 if results else 0,
        'unique_parsers': len(set(r.get('parser_name', '') for r in results)),
        'unique_datasets': len(set(r.get('dataset_size', 0) for r in results)),
        'unique_protocols': len(set(r.get('protocol', '') for r in results))
    }

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'summary': summary
    }


if __name__ == "__main__":
    """Test the utility functions."""

    print("Testing Utility Functions")
    print("=" * 30)

    # Test Timer
    print("\nTesting Timer:")
    with Timer() as timer:
        time.sleep(0.1)
    print(f"Elapsed: {timer.elapsed_ms:.2f} ms")

    # Test throughput calculation
    print("\nTesting Throughput Calculation:")
    throughput = calculate_throughput(1024 * 1024, 1000)  # 1MB in 1 second
    print(f"Throughput: {throughput:.2f} MB/s")

    # Test Amdahl's Law calculation
    print("\nTesting Amdahl's Law:")
    speedup_info = calculate_amdahl_speedup(1000, 300, 4)
    print(f"Speedup: {speedup_info['speedup']:.2f}")
    print(f"Efficiency: {speedup_info['efficiency']:.2f}")

    # Test statistics
    print("\nTesting Statistics:")
    values = [10, 20, 30, 40, 50]
    stats = calculate_statistics(values)
    print(f"Mean: {stats['mean']:.2f}")
    print(f"Std Dev: {stats['std_dev']:.2f}")

    # Test formatting
    print("\nTesting Formatting:")
    print(f"Bytes: {format_bytes(1536)}")
    print(f"Time: {format_time(1500)}")

    print("\nUtility functions test completed!")
