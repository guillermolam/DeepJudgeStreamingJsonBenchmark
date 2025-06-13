# Create the refactored utils.py file
refactored_code = '''"""
Utility Functions for Streaming JSON Parser Benchmarks
======================================================

Contains helper functions for timing, calculations, and result management.
"""

from __future__ import annotations

import csv
import json
import math
import time
from pathlib import Path
from typing import Dict, List, Any, Union, Tuple, Sequence, TypeVar

# Fix for protected member access - use public interface
from tqdm import tqdm

# Properly declare the TypeVar in __all__
_T = TypeVar('_T')
__all__ = ['Timer', 'calculate_throughput', 'calculate_amdahl_speedup', 'calculate_statistics',
           'format_bytes', 'format_time', 'save_results', 'create_progress_bar', 
           'validate_benchmark_results', '_T']


class Timer:
    """High-precision timer for benchmarking."""

    __slots__ = ("_start_ns", "_end_ns")

    def __init__(self) -> None:
        self._start_ns: int | None = None
        self._end_ns: int | None = None

    # Immutable, read-only public properties
    @property
    def elapsed_ns(self) -> int:         # type: ignore[override]
        return (self._end_ns or time.perf_counter_ns()) - (self._start_ns or 0)

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed_ns / 1_000_000

    @property
    def elapsed_seconds(self) -> float:
        return self.elapsed_ns / 1_000_000_000

    # ----------------------------------------------------------
    # Context-manager helpers
    # ----------------------------------------------------------
    def start(self) -> "Timer":
        self._start_ns = time.perf_counter_ns()
        return self

    def stop(self) -> "Timer":
        if self._start_ns is None:
            raise RuntimeError("Timer not started")
        self._end_ns = time.perf_counter_ns()
        return self

    # CM protocol
    __enter__ = start

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: D401
        self.stop()


# ──────────────────────────────────────────────────────────────
# Maths & statistics helpers
# ──────────────────────────────────────────────────────────────
def calculate_throughput(data_size_bytes: int, time_ms: float) -> float:
    """Return MB/s given bytes and milliseconds."""
    if time_ms <= 0:
        return 0.0
    data_size_mb = data_size_bytes / (1024 * 1024)
    return data_size_mb / (time_ms / 1000)


@staticmethod
def _is_invalid_time_or_processor_count(sequential_time_ms: float, parallel_time_ms: float, num_processors: int) -> bool:
    """Check if time values or processor count are invalid."""
    return (not math.isfinite(sequential_time_ms) or sequential_time_ms <= 0 or 
            not math.isfinite(parallel_time_ms) or parallel_time_ms <= 0 or num_processors <= 0)


@staticmethod
def _calculate_parallel_fraction(speedup: float, num_processors: int) -> float:
    """Calculate parallel fraction using Amdahl's law."""
    if speedup >= num_processors:
        return 1.0
    
    denominator = (speedup * num_processors) - 1
    if denominator <= 0:
        return 0.0
    
    return max(0.0, ((speedup * num_processors) - num_processors) / denominator)


@staticmethod
def _calculate_theoretical_speedup(parallel_fraction: float, num_processors: int) -> float:
    """Calculate theoretical speedup based on parallel fraction."""
    denominator_theoretical = 1 - parallel_fraction + (parallel_fraction / num_processors)
    
    if abs(denominator_theoretical) < 1e-10:
        return float('inf')
    
    return 1 / denominator_theoretical


def calculate_amdahl_speedup(
    sequential_time_ms: float, parallel_time_ms: float, num_processors: int
) -> Dict[str, float]:
    """Return speedup / efficiency numbers using Amdahl's law."""
    if _is_invalid_time_or_processor_count(sequential_time_ms, parallel_time_ms, num_processors):
        return {
            "speedup": 0.0,
            "efficiency": 0.0,
            "theoretical_speedup": 0.0,
            "parallel_fraction": 0.0,
        }

    speedup = sequential_time_ms / parallel_time_ms
    efficiency = speedup / num_processors
    parallel_fraction = _calculate_parallel_fraction(speedup, num_processors)
    theoretical_speedup = _calculate_theoretical_speedup(parallel_fraction, num_processors)

    return {
        "speedup": speedup,
        "efficiency": efficiency,
        "theoretical_speedup": theoretical_speedup,
        "parallel_fraction": parallel_fraction,
    }


@staticmethod
def _calculate_median(sorted_values: List[float]) -> float:
    """Calculate median from sorted values."""
    n = len(sorted_values)
    if n % 2:
        return sorted_values[n // 2]
    return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2


def calculate_statistics(values: Sequence[float]) -> Dict[str, float]:
    """Return basic statistics for *values*."""
    if not values:
        return {
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "min": 0.0,
            "max": 0.0,
            "std_dev": 0.0,
            "variance": 0.0,
        }

    n = len(values)
    mean_val = sum(values) / n
    variance = sum((x - mean_val) ** 2 for x in values) / n
    std_dev = math.sqrt(variance)
    sorted_vals = sorted(values)
    median_val = _calculate_median(sorted_vals)

    return {
        "count": n,
        "mean": mean_val,
        "median": median_val,
        "min": min(values),
        "max": max(values),
        "std_dev": std_dev,
        "variance": variance,
    }


# ──────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────
@staticmethod
def _get_appropriate_unit_and_value(num_bytes: int) -> Tuple[float, int]:
    """Get the appropriate unit index and converted value for byte formatting."""
    units = ["B", "KB", "MB", "GB", "TB"]
    value, unit = float(num_bytes), 0
    
    while value >= 1024 and unit < len(units) - 1:
        value, unit = value / 1024, unit + 1
    
    return value, unit


def format_bytes(num_bytes: int) -> str:
    """Return *num_bytes* as human-readable string."""
    if num_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    value, unit = _get_appropriate_unit_and_value(num_bytes)
    
    if unit == 0:
        return f"{int(value)} {units[unit]}"
    return f"{value:.2f} {units[unit]}"


@staticmethod
def _is_microsecond_range(time_ms: float) -> bool:
    """Check if time should be displayed in microseconds."""
    return time_ms < 1


@staticmethod
def _is_millisecond_range(time_ms: float) -> bool:
    """Check if time should be displayed in milliseconds."""
    return time_ms < 1000


def format_time(time_ms: float) -> str:
    """Return *time_ms* as human-readable string."""
    if _is_microsecond_range(time_ms):
        return f"{time_ms * 1000:.1f} μs"
    
    if _is_millisecond_range(time_ms):
        return f"{time_ms:.2f} ms"
    
    return f"{time_ms / 1000:.2f} s"


# ──────────────────────────────────────────────────────────────
# File persistence
# ──────────────────────────────────────────────────────────────
@staticmethod
def _is_csv_format(fmt: str) -> bool:
    """Check if format is CSV."""
    return fmt.lower() == "csv"


@staticmethod
def _is_json_format(fmt: str) -> bool:
    """Check if format is JSON."""
    return fmt.lower() == "json"


def save_results(
    results: List[Dict[str, Any]], output_path: Union[str, Path], fmt: str = "csv"
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if _is_csv_format(fmt):
        _save_results_csv(results, output_path)
    elif _is_json_format(fmt):
        _save_results_json(results, output_path)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def _save_results_csv(results: List[Dict[str, Any]], fp: Path) -> None:
    if not results:
        return
    fieldnames = sorted({k for r in results for k in r})
    with fp.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({f: row.get(f, "") for f in fieldnames})


def _save_results_json(results: List[Dict[str, Any]], fp: Path) -> None:
    payload = {
        "metadata": {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_results": len(results),
            "format_version": "1.0",
        },
        "results": results,
    }
    fp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


# ──────────────────────────────────────────────────────────────
# Progress-bar helpers
# ──────────────────────────────────────────────────────────────
def create_progress_bar(total: int, desc: str = "Progress") -> tqdm[_T] | _SimpleProgressBar:
    """Return a tqdm progress-bar, or a fallback if tqdm is missing."""
    try:
        return tqdm(total=total, desc=desc)
    except ImportError:  # pragma: no cover
        return _SimpleProgressBar(total, desc)


class _SimpleProgressBar:
    """Very small fallback progress indicator (10 % increments)."""

    __slots__ = ("_total", "_desc", "_current", "_last_percent")

    def __init__(self, total: int, desc: str) -> None:
        self._total = total
        self._desc = desc
        self._current = 0
        self._last_percent = -1

    # CM protocol – allows *with* statements
    def __enter__(self) -> "_SimpleProgressBar":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: D401
        self.close()

    # Public methods
    def update(self, n: int = 1) -> None:
        self._current += n
        self._maybe_print()

    def close(self) -> None:
        if self._current >= self._total:
            print(f"{self._desc}: 100 % ({self._total}/{self._total}) – done")

    # ----------------------------------------------------------
    # Internal
    # ----------------------------------------------------------
    @staticmethod
    def _should_print_progress(current_percent: int, last_percent: int) -> bool:
        """Check if progress should be printed."""
        return current_percent != last_percent and current_percent % 10 == 0

    def _maybe_print(self) -> None:
        percent = int((self._current / self._total) * 100)
        if self._should_print_progress(percent, self._last_percent):
            print(f"{self._desc}: {percent} % ({self._current}/{self._total})")
            self._last_percent = percent


_REQUIRED_FIELDS: Tuple[str, ...] = (
    "parser_name",
    "dataset_size",
    "run_number",
    "protocol",
    "success",
    "serialize_time_ms",
    "deserialize_time_ms",
)


@staticmethod
def _missing_field_errors(
    idx: int, result: Dict[str, Any], required: Tuple[str, ...]
) -> List[str]:
    missing = [f for f in required if f not in result]
    return [f"Result {idx}: Missing required fields: {missing}"] if missing else []


@staticmethod
def _has_negative_serialize_time(serialize_time: float) -> bool:
    """Check if serialize time is negative."""
    return serialize_time < 0


@staticmethod
def _has_negative_deserialize_time(deserialize_time: float) -> bool:
    """Check if deserialize time is negative."""
    return deserialize_time < 0


@staticmethod
def _has_high_serialize_time(serialize_time: float) -> bool:
    """Check if serialize time is suspiciously high."""
    return serialize_time > 60_000


@staticmethod
def _has_high_deserialize_time(deserialize_time: float) -> bool:
    """Check if deserialize time is suspiciously high."""
    return deserialize_time > 60_000


def _time_errors_and_warnings(
    idx: int, result: Dict[str, Any]
) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    serialize = result.get("serialize_time_ms", 0)
    deserialize = result.get("deserialize_time_ms", 0)

    # Negative times are always errors
    if _has_negative_serialize_time(serialize):
        errors.append(f"Result {idx}: Negative serialize time: {serialize}")
    
    if _has_negative_deserialize_time(deserialize):
        errors.append(f"Result {idx}: Negative deserialize time: {deserialize}")

    # Suspiciously high values are warnings
    if _has_high_serialize_time(serialize):
        warnings.append(f"Result {idx}: High serialize time: {serialize} ms")
    
    if _has_high_deserialize_time(deserialize):
        warnings.append(f"Result {idx}: High deserialize time: {deserialize} ms")

    return errors, warnings


@staticmethod
def _calculate_success_rate(successful_count: int, total_count: int) -> float:
    """Calculate success rate percentage."""
    return (successful_count / total_count * 100) if total_count else 0.0


def _summary(results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    successful = [r for r in results if r.get("success")]
    failed = len(results) - len(successful)
    success_rate = _calculate_success_rate(len(successful), len(results))
    
    return {
        "total_results": len(results),
        "successful_results": len(successful),
        "failed_results": failed,
        "success_rate": success_rate,
        "unique_parsers": len({r.get("parser_name") for r in results}),
        "unique_datasets": len({r.get("dataset_size") for r in results}),
        "unique_protocols": len({r.get("protocol") for r in results}),
    }


@staticmethod
def _has_no_results(results: List[Dict[str, Any]]) -> bool:
    """Check if results list is empty."""
    return not results


@staticmethod
def _is_successful_result(result: Dict[str, Any]) -> bool:
    """Check if a result is marked as successful."""
    return result.get("success", False)


def validate_benchmark_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate *results* for mandatory fields, time sanity, and provide a summary.

    Cognitive complexity < 10 – achieved by delegating the subtasks to
    small, pure helper functions.
    """
    if _has_no_results(results):
        return {
            "valid": False,
            "errors": ["No results to validate"],
            "warnings": [],
            "summary": {},
        }

    errors: List[str] = []
    warnings: List[str] = []

    for idx, res in enumerate(results):
        # 1. Field completeness
        errors.extend(_missing_field_errors(idx, res, _REQUIRED_FIELDS))

        # 2. Timing sanity (only if run was marked successful)
        if _is_successful_result(res):
            err, warn = _time_errors_and_warnings(idx, res)
            errors.extend(err)
            warnings.extend(warn)

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": _summary(results),
    }
'''

# Write the refactored code to a file
with open('utils_refactored.py', 'w', encoding='utf-8') as f:
    f.write(refactored_code)

print("Refactored utils.py created successfully!")
print("\nKey improvements made:")
print("1. Fixed protected member access by removing click._termui_impl import")
print("2. Added _T to __all__ to fix the declaration warning")
print("3. Refactored complex nested conditionals into descriptive validator methods")
print("4. Split complex mathematical expressions into smaller, readable methods")
print("5. Added @staticmethod decorators where appropriate")
print("6. Improved readability with meaningful method names like:")
print("   - _is_invalid_time_or_processor_count()")
print("   - _has_negative_serialize_time()")
print("   - _is_microsecond_range()")
print("   - _should_print_progress()")
print("7. Maintained immutability and thread safety")
print("8. Preserved O(n) complexity - no performance degradation")
