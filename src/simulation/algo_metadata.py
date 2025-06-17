"""
Algorithm Metadata for Streaming JSON Parser Benchmarks
=======================================================

Contains complexity analysis and metadata for each parser implementation.
"""

import importlib
from typing import Dict, Any, Optional

from .parser_loader import LOADED_PARSERS


class MetadataCollector:
    """Dynamically collects and manages algorithm metadata."""

    def __init__(self):
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load metadata from all available parser modules."""
        for parser_name, parser_class in LOADED_PARSERS.items():
            try:
                module = importlib.import_module(parser_class.__module__)
                if hasattr(module, "get_metadata"):
                    self._metadata[parser_name] = module.get_metadata()
            except (ImportError, AttributeError) as e:
                print(f"Could not load metadata for {parser_name}: {e}")

    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Get all collected metadata."""
        return self._metadata

    def get_metadata(self, parser_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific parser."""
        return self._metadata.get(parser_name)


# Initialize the metadata collector
METADATA_COLLECTOR = MetadataCollector()
ALGORITHM_METADATA = METADATA_COLLECTOR.get_all_metadata()


def get_algorithm_info(parser_algorythm_name: str) -> Dict[str, Any]:
    """
    Get algorithm metadata for a specific parser.

    Args:
        parser_algorythm_name: Name of the parser

    Returns:
        Dictionary containing algorithm metadata
    """
    return ALGORITHM_METADATA.get(parser_algorythm_name, {
        'name': parser_algorythm_name.replace('_', ' ').title(),
        'time_complexity': 'Unknown',
        'space_complexity': 'Unknown',
        'overall_complexity': 'Unknown',
        'description': 'No metadata available',
        'strengths': [],
        'weaknesses': [],
        'best_use_case': 'Unknown'
    })


def get_complexity_score(complexity_str: str) -> int:
    """
    Convert complexity notation to numeric score for comparison.
    Lower scores indicate better complexity.

    Args:
        complexity_str: Complexity notation (e.g., 'O(1)', 'O(n)', 'O(n log n)')

    Returns:
        Numeric score for comparison
    """
    complexity_scores = {
        'O(1)': 1,
        'O(log n)': 2,
        'O(n)': 3,
        'O(n log n)': 4,
        'O(n²)': 5,
        'O(n^2)': 5,
        'O(2^n)': 6,
        'Unknown': 999
    }

    # Clean up the complexity string
    clean_complexity = complexity_str.strip().split(' ')[0]

    return complexity_scores.get(clean_complexity, 999)


def _determine_winner(score1: int, score2: int, parser1: str, parser2: str) -> str:
    """
    Determine the winner based on scores.

    Args:
        score1: Score for parser1
        score2: Score for parser2
        parser1: Name of first parser
        parser2: Name of second parser

    Returns:
        Winner name or 'tie'
    """
    if score1 < score2:
        return parser1
    elif score2 < score1:
        return parser2
    else:
        return 'tie'


def compare_algorithms(parser1: str, parser2: str) -> Dict[str, Any]:
    """
    Compare two algorithms based on their metadata.

    Args:
        parser1: Name of first parser
        parser2: Name of second parser

    Returns:
        Comparison results
    """

    info1 = get_algorithm_info(parser1)
    info2 = get_algorithm_info(parser2)

    time_score1 = get_complexity_score(info1['time_complexity'])
    time_score2 = get_complexity_score(info2['time_complexity'])

    space_score1 = get_complexity_score(info1['space_complexity'])
    space_score2 = get_complexity_score(info2['space_complexity'])

    time_winner = _determine_winner(time_score1, time_score2, parser1, parser2)
    space_winner = _determine_winner(space_score1, space_score2, parser1, parser2)
    overall_winner = _determine_winner(
        time_score1 + space_score1,
        time_score2 + space_score2,
        parser1,
        parser2
    )

    return {
        'parser1': {
            'name': info1['name'],
            'time_complexity': info1['time_complexity'],
            'space_complexity': info1['space_complexity'],
            'time_score': time_score1,
            'space_score': space_score1
        },
        'parser2': {
            'name': info2['name'],
            'time_complexity': info2['time_complexity'],
            'space_complexity': info2['space_complexity'],
            'time_score': time_score2,
            'space_score': space_score2
        },
        'comparison': {
            'time_winner': time_winner,
            'space_winner': space_winner,
            'overall_winner': overall_winner
        }
    }


def generate_algorithm_report() -> str:
    """
    Generate a comprehensive report of all algorithms.

    Returns:
        Formatted report string
    """

    report = ["Algorithm Complexity Analysis Report", "=" * 50, ""]

    # Sort algorithms by time complexity
    sorted_algos = sorted(
        ALGORITHM_METADATA.items(),
        key=lambda x: get_complexity_score(x[1]['time_complexity'])
    )

    for _, algo_info in sorted_algos:
        report.append("Algorithm: " + algo_info['name'])
        report.append("  Time Complexity: " + algo_info['time_complexity'])
        report.append("  Space Complexity: " + algo_info['space_complexity'])
        report.append("  Overall: " + algo_info['overall_complexity'])
        report.append("  Description: " + algo_info['description'])
        report.append("  Best Use Case: " + algo_info['best_use_case'])
        report.append("")

    return "\n".join(report)
