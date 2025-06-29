"""Asynchronous wrapper around the solid parquet_parser using AnyIO."""

from __future__ import annotations

from typing import Any, Dict
from serializers.anyio import AnyioWrapper
from serializers.solid import parquet_parser as solid


def get_metadata():
    """Returns metadata for the anyio Parquet parser."""
    return {
        'name': 'anyio Parquet Parser',
        'time_complexity': 'O(n log n)',
        'space_complexity': 'O(n)',
        'overall_complexity': 'O(n log n) time, O(n) space',
        'description': 'Parquet-style streaming parser with anyio for async operations.',
        'strengths': ['Asynchronous', 'Columnar storage efficiency'],
        'weaknesses': ['Complex implementation', 'Dependency on anyio'],
        'best_use_case': 'High-performance async applications requiring Parquet support.'
    }


class StreamingJsonParser(AnyioWrapper):
    """AnyIO version of :class:`solid.StreamingJsonParser`."""

    def __init__(self) -> None:
        super().__init__(solid.StreamingJsonParser)

    def get_columnar_data(self) -> Dict[str, Any]:
        return self._parser.get_columnar_data()


def check_solution(tests=None):
    from .. import run_module_tests
    import sys
    return run_module_tests(sys.modules[__name__], tests)
