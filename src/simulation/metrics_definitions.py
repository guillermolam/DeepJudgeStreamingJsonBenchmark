from dataclasses import dataclass
from typing import List, Optional

@dataclass
class PerformanceCategory:
    """Represents a performance category for analysis."""
    metric_key: str
    display_name: str
    lower_is_better: bool = True

class PerformanceCategoryManager:
    """Manages performance categories for analysis."""

    def __init__(self):
        self._categories = [
            PerformanceCategory('serialize_time_ms', 'Serialization Speed', True),
            PerformanceCategory('deserialize_time_ms', 'Deserialization Speed', True),
            PerformanceCategory('throughput_mbps', 'Throughput (MB/s)', False),
            PerformanceCategory('memory_peak_bytes', 'Memory Efficiency', True),
            PerformanceCategory('cpu_time_seconds', 'CPU Efficiency', True),
            PerformanceCategory('dataset_size', 'Data Size', True),
            PerformanceCategory('total_ser_deser_time_ms', 'Total Processing Time', True)
        ]

    def get_categories(self) -> List[PerformanceCategory]:
        """Get all performance categories."""
        return self._categories

    def get_category_by_key(self, key: str) -> Optional[PerformanceCategory]:
        """Get category by metric key."""
        return next((cat for cat in self._categories if cat.metric_key == key), None)
