import random
from datetime import datetime
from typing import Dict, Any, List

# ---------------------------------------------------------
# Configurations
# ---------------------------------------------------------
DEFAULT_STRING_VALUES = [
    "Alpha",
    "Beta",
    "Gamma",
    "Delta",
    "Epsilon",
    "Zeta",
    "Eta",
    "Theta",
    "Iota",
    "Kappa",
]


# ---------------------------------------------------------
# DataGenerator: produces only strings or nested dicts
# ---------------------------------------------------------
class DataGenerator:
    def __init__(self, num_fields: int):
        if not isinstance(num_fields, int) or num_fields <= 0:
            raise ValueError(f"num_fields must be positive integer, got {num_fields}")
        self.target_fields = num_fields
        self.generated = 0
        random.seed(42 + num_fields)

    def generate(self) -> Dict[str, Any]:
        output = {}
        while self.generated < self.target_fields:
            key = f"field_{self.generated}"
            if random.random() < 0.3 and self.generated <= self.target_fields - 2:
                # generate nested object with up to 2 nested entries
                nested = {
                    f"{key}_nested_{i}": random.choice(DEFAULT_STRING_VALUES)
                    for i in range(1 + random.randint(1, 2))
                }
                output[key] = nested
            else:
                output[key] = random.choice(DEFAULT_STRING_VALUES)
            self.generated += 1

        output["_metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "target_fields": self.target_fields,
            "total_fields": self.generated,
            "generator_version": "1.0.0",
            "test_run_id": f"test_{self.target_fields}_{random.randint(1000,9999)}",
        }
        return output


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------
def generate_test_data(num_fields: int) -> Dict[str, Any]:
    return DataGenerator(num_fields).generate()


def create_streaming_chunks(json_bytes: bytes, chunk_size: int = None) -> List[bytes]:
    if chunk_size is None:
        chunk_size = max(1, len(json_bytes) // 10)
    return [
        json_bytes[i : i + chunk_size] for i in range(0, len(json_bytes), chunk_size)
    ]


def validate_generated_data(data: Dict[str, Any], expected_fields: int) -> bool:
    actual = data["_metadata"]["total_fields"]
    tol = max(1, int(expected_fields * 0.1))
    return abs(actual - expected_fields) <= tol


def generate_mixed_complexity_data(num_fields: int) -> Dict[str, Any]:
    # Not used by benchmark/test suite—optional
    return {}
