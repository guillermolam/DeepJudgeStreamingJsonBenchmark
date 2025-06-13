"""
Algorithm Metadata for Streaming JSON Parser Benchmarks
=======================================================

Contains complexity analysis and metadata for each parser implementation.
"""

from typing import Dict, Any

ALGORITHM_METADATA: Dict[str, Dict[str, Any]] = {

    'json_parser': {
        'name': 'Standard JSON Parser',
        'time_complexity': 'O(n)',
        'space_complexity': 'O(n)',
        'overall_complexity': 'O(n) time, O(n) space',
        'description': 'Standard Python json module with streaming buffer',
        'strengths': ['Simple implementation', 'Reliable', 'Built-in'],
        'weaknesses': ['Not optimized for streaming', 'Memory overhead'],
        'best_use_case': 'General purpose JSON parsing'
    },

    'ultrajson_parser': {
        'name': 'UltraJSON Parser',
        'time_complexity': 'O(n)',
        'space_complexity': 'O(n)',
        'overall_complexity': 'O(n) time, O(n) space - optimized C implementation',
        'description': 'Ultra-fast JSON encoder/decoder with C extensions',
        'strengths': ['Very fast', 'C implementation', 'Drop-in replacement'],
        'weaknesses': ['External dependency', 'Less flexible'],
        'best_use_case': 'High-performance JSON processing'
    },

    'msgpack_parser': {
        'name': 'MessagePack Parser',
        'time_complexity': 'O(n)',
        'space_complexity': 'O(n)',
        'overall_complexity': 'O(n) time, O(n) space - binary format efficiency',
        'description': 'Binary serialization format, more compact than JSON',
        'strengths': ['Compact binary format', 'Fast', 'Cross-language'],
        'weaknesses': ['Not human-readable', 'Format conversion overhead'],
        'best_use_case': 'Network protocols, data storage'
    },

    'pickle_binary_mono_parser': {
        'name': 'Pickle Binary (Single-threaded)',
        'time_complexity': 'O(n)',
        'space_complexity': 'O(n)',
        'overall_complexity': 'O(n) time, O(n) space - Python object serialization',
        'description': 'Python pickle protocol for object serialization',
        'strengths': ['Native Python objects', 'Preserves types'],
        'weaknesses': ['Python-specific', 'Security concerns', 'Larger size'],
        'best_use_case': 'Python-to-Python communication'
    },

    'pickle_binary_multi_parser': {
        'name': 'Pickle Binary (Multi-threaded)',
        'time_complexity': 'O(n/p)',
        'space_complexity': 'O(n)',
        'overall_complexity': 'O(n/p) time, O(n) space where p = processors',
        'description': 'Multi-threaded pickle with parallel processing',
        'strengths': ['Parallel processing', 'Better CPU utilization'],
        'weaknesses': ['Threading overhead', 'Complex synchronization'],
        'best_use_case': 'Large datasets with multiple CPU cores'
    },

    'bson_parser': {
        'name': 'BSON Parser',
        'time_complexity': 'O(n)',
        'space_complexity': 'O(n)',
        'overall_complexity': 'O(n) time, O(n) space - binary JSON with types',
        'description': 'Binary JSON format used by MongoDB',
        'strengths': ['Type preservation', 'Efficient for databases', 'Binary format'],
        'weaknesses': ['Larger than JSON', 'MongoDB-specific'],
        'best_use_case': 'Database storage and retrieval'
    },

    'cbor_parser': {
        'name': 'CBOR Parser',
        'time_complexity': 'O(n)',
        'space_complexity': 'O(n)',
        'overall_complexity': 'O(n) time, O(n) space - RFC 7049 binary format',
        'description': 'Concise Binary Object Representation (RFC 7049)',
        'strengths': ['Standardized', 'Compact', 'Self-describing'],
        'weaknesses': ['Less common', 'Conversion overhead'],
        'best_use_case': 'IoT devices, constrained environments'
    },

    'protobuf_parser': {
        'name': 'Protocol Buffers Parser',
        'time_complexity': 'O(n)',
        'space_complexity': 'O(n)',
        'overall_complexity': 'O(n) time, O(n) space - schema-based binary',
        'description': 'Google Protocol Buffers with schema definition',
        'strengths': ['Very compact', 'Schema evolution', 'Cross-language'],
        'weaknesses': ['Requires schema', 'Complex setup'],
        'best_use_case': 'Microservices, API communication'
    },

    'flatbuffers_parser': {
        'name': 'FlatBuffers Parser',
        'time_complexity': 'O(1)',
        'space_complexity': 'O(n)',
        'overall_complexity': 'O(1) access time, O(n) space - zero-copy',
        'description': 'Zero-copy serialization with direct memory access',
        'strengths': ['Zero-copy', 'Constant access time', 'Memory efficient'],
        'weaknesses': ['Complex schema', 'Write-once limitation'],
        'best_use_case': 'Game engines, real-time systems'
    },

    'parquet_parser': {
        'name': 'Apache Parquet Parser',
        'time_complexity': 'O(n log n)',
        'space_complexity': 'O(n)',
        'overall_complexity': 'O(n log n) time, O(n) space - columnar storage',
        'description': 'Columnar storage format optimized for analytics',
        'strengths': ['Excellent compression', 'Columnar efficiency', 'Analytics optimized'],
        'weaknesses': ['Complex format', 'Not streaming-friendly', 'Overhead'],
        'best_use_case': 'Data analytics, batch processing'
    },

    'marshall_parser': {
        'name': 'Python Marshal Parser',
        'time_complexity': 'O(n)',
        'space_complexity': 'O(n)',
        'overall_complexity': 'O(n) time, O(n) space - Python bytecode format',
        'description': 'Python marshal module for bytecode serialization',
        'strengths': ['Fast for Python objects', 'Compact'],
        'weaknesses': ['Python version dependent', 'Limited compatibility'],
        'best_use_case': 'Python bytecode, internal serialization'
    },

    'reactivex_parser': {
        'name': 'ReactiveX Streaming Parser',
        'time_complexity': 'O(n)',
        'space_complexity': 'O(1)',
        'overall_complexity': 'O(n) time, O(1) space - reactive streaming',
        'description': 'Reactive Extensions for streaming data processing',
        'strengths': ['True streaming', 'Constant memory', 'Reactive patterns'],
        'weaknesses': ['Complex programming model', 'Learning curve'],
        'best_use_case': 'Real-time streaming, event processing'
    }
}


def get_algorithm_info(parser_name: str) -> Dict[str, Any]:
    """
    Get algorithm metadata for a specific parser.

    Args:
        parser_name: Name of the parser

    Returns:
        Dictionary containing algorithm metadata
    """
    return ALGORITHM_METADATA.get(parser_name, {
        'name': parser_name.replace('_', ' ').title(),
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

    for parser_name, info in sorted_algos:
        report.append("Algorithm: " + info['name'])
        report.append("  Time Complexity: " + info['time_complexity'])
        report.append("  Space Complexity: " + info['space_complexity'])
        report.append("  Overall: " + info['overall_complexity'])
        report.append("  Description: " + info['description'])
        report.append("  Best Use Case: " + info['best_use_case'])
        report.append("")

    return "\n".join(report)


if __name__ == "__main__":
    """Test the algorithm metadata module."""

    print("Algorithm Metadata Test")
    print("=" * 30)

    # Test getting info for each parser
    for parser_name in ALGORITHM_METADATA.keys():
        info = get_algorithm_info(parser_name)
        print("\n" + parser_name + ":")
        print("  Name: " + info['name'])
        print("  Time: " + info['time_complexity'])
        print("  Space: " + info['space_complexity'])

    # Test comparison
    print("\n" + "=" * 30)
    print("Algorithm Comparison Test")
    print("=" * 30)

    comparison = compare_algorithms('flatbuffers_parser', 'json_parser')
    print("\nComparing FlatBuffers vs JSON:")
    print("Time winner: " + comparison['comparison']['time_winner'])
    print("Space winner: " + comparison['comparison']['space_winner'])
    print("Overall winner: " + comparison['comparison']['overall_winner'])

    # Generate a full report
    print("\n" + "=" * 50)
    print(generate_algorithm_report())
