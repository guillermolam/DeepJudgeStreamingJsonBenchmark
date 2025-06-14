"""
Data Generator for Streaming JSON Parser Benchmarks
===================================================

Generates deterministic JSON test data_gen with varying complexity levels for
benchmarking streaming JSON parser implementations. This module provides
the core data_gen generation functionality used by the benchmarking system.

Key Features:
- Deterministic data_gen generation with configurable complexity
- Support for nested objects, arrays, and mixed data_gen types
- Streaming chunk generation for network simulation
- Data validation and metadata generation

This is a production module used by the benchmarking system, not a test file.
For testing this module, see tests/simulation/test_data_gen.py
"""
from __future__ import annotations

import json
import random
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Tuple


class DataType(Enum):
    """Enumeration of supported data_gen types."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    NULL = "null"
    ARRAY = "array"
    OBJECT = "object"


class GeneratorConfig:
    """Configuration constants for data_gen generation."""

    DEFAULT_STRING_VALUES = [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit",
        "The quick brown fox jumps over the lazy dog",
        "Streaming JSON parser performance benchmark test data_gen",
        "Artificial intelligence and machine learning algorithms",
        "Distributed systems and microservices architecture",
        "Real-time data_gen processing and analytics pipeline",
        "Cloud computing infrastructure and scalability",
        "Database optimization and query performance tuning",
        "Network protocols and communication standards",
        "Software engineering best practices and methodologies"
    ]

    NESTED_OBJECT_PROBABILITY = 0.3
    ARRAY_PROBABILITY = 0.2
    MIN_FIELDS_FOR_NESTED = 50
    MIN_FIELDS_FOR_ARRAY = 10
    NESTED_SIZE_RANGE = (5, 20)
    ARRAY_SIZE_RANGE = (3, 15)
    TOLERANCE_PERCENTAGE = 0.1


class ValueGenerator:
    """Pure functions for generating different types of values."""

    def __init__(self, string_values: List[str]):
        self._string_values = string_values

    def generate_string(self) -> str:
        """Generate a random string value."""
        return random.choice(self._string_values)

    @staticmethod
    def generate_number() -> int | float:
        """Generate a random number (int or float)."""
        if random.random() < 0.5:
            return random.randint(-1000000, 1000000)
        return round(random.uniform(-1000.0, 1000.0), 4)

    @staticmethod
    def generate_boolean() -> bool:
        """Generate a random boolean value."""
        return random.random() < 0.5

    def generate_array_element(self) -> Any:
        """Generate a random array element."""
        return random.choice([
            self.generate_string(),
            random.randint(1, 1000),
            self.generate_boolean()
        ])

    def generate_simple_object(self, item_index: int) -> Dict[str, Any]:
        """Generate a simple object for array elements."""
        return {
            f"item_{item_index}_prop": self.generate_string(),
            f"item_{item_index}_value": random.randint(1, 100)
        }


class FieldCounter:
    """Manages field counting for data_gen generation."""

    def __init__(self, target_fields: int):
        self._target_fields = target_fields
        self._fields_created = 0

    @property
    def target_fields(self) -> int:
        """Get target number of fields."""
        return self._target_fields

    @property
    def fields_created(self) -> int:
        """Get number of fields created so far."""
        return self._fields_created

    @property
    def remaining_fields(self) -> int:
        """Get the number of remaining fields to create."""
        return self._target_fields - self._fields_created

    def increment(self, count: int = 1) -> None:
        """Increment the field counter."""
        self._fields_created += count

    def has_remaining_fields(self) -> bool:
        """Check if there are remaining fields to create."""
        return self._fields_created < self._target_fields


class MetadataGenerator:
    """Generates metadata for test data_gen."""

    @staticmethod
    def generate_metadata(fields_created: int, target_fields: int) -> Dict[str, Any]:
        """Generate metadata for the test data_gen."""
        return {
            "generated_at": datetime.now().isoformat(),
            "total_fields": fields_created,
            "target_fields": target_fields,
            "generator_version": "1.0.0",
            "test_run_id": f"test_{target_fields}_{random.randint(1000, 9999)}"
        }


class NestedObjectGenerator:
    """Handles generation of nested objects."""

    def __init__(self, value_generator: ValueGenerator, field_counter: FieldCounter):
        self._value_generator = value_generator
        self._field_counter = field_counter

    def create_nested_object(self, depth: int = 0, max_depth: int = 3) -> Dict[str, Any]:
        """Create a nested object with specified depth constraints."""
        if depth >= max_depth or not self._field_counter.has_remaining_fields():
            return {}

        obj = {}
        nested_fields = min(
            random.randint(2, 8),
            self._field_counter.remaining_fields
        )

        for i in range(nested_fields):
            if not self._field_counter.has_remaining_fields():
                break

            key = f"nested_field_{depth}_{i}"
            obj[key] = self._generate_nested_field_value(depth, max_depth)
            self._field_counter.increment()

        return obj

    def _generate_nested_field_value(self, depth: int, max_depth: int) -> Any:
        """Generate a value for a nested field."""
        data_type = random.choice([
            DataType.STRING, DataType.NUMBER, DataType.BOOLEAN,
            DataType.ARRAY, DataType.OBJECT
        ])

        if data_type == DataType.STRING:
            return self._value_generator.generate_string()
        elif data_type == DataType.NUMBER:
            return self._value_generator.generate_number()
        elif data_type == DataType.BOOLEAN:
            return self._value_generator.generate_boolean()
        elif data_type == DataType.ARRAY:
            return self._create_nested_array()
        elif data_type == DataType.OBJECT and depth < max_depth - 1:
            return self.create_nested_object(depth + 1, max_depth)
        else:
            return self._value_generator.generate_string()

    def _create_nested_array(self) -> List[Any]:
        """Create an array for nested objects."""
        array_size = random.randint(1, 10)
        return [self._value_generator.generate_array_element() for _ in range(array_size)]


class ArrayGenerator:
    """Handles generation of arrays."""

    def __init__(self, value_generator: ValueGenerator):
        self._value_generator = value_generator

    def create_array(self, size_range: Tuple[int, int]) -> List[Any]:
        """Create an array with elements of various types."""
        array_size = random.randint(*size_range)
        array = []

        for i in range(array_size):
            element_type = random.choice([
                DataType.STRING, DataType.NUMBER, DataType.BOOLEAN, DataType.OBJECT
            ])

            if element_type == DataType.STRING:
                array.append(self._value_generator.generate_string())
            elif element_type == DataType.NUMBER:
                array.append(_generate_array_number())
            elif element_type == DataType.BOOLEAN:
                array.append(self._value_generator.generate_boolean())
            elif element_type == DataType.OBJECT:
                array.append(self._value_generator.generate_simple_object(i))

        return array


def _generate_array_number() -> int | float:
    """Generate a number specifically for arrays."""
    if random.random() < 0.5:
        return random.randint(1, 10000)
    return round(random.uniform(0.1, 999.9), 3)


class SimpleFieldGenerator:
    """Handles generation of simple fields."""

    def __init__(self, value_generator: ValueGenerator):
        self._value_generator = value_generator

    def create_simple_field(self) -> Any:
        """Create a simple field value."""
        field_type = random.choice([
            DataType.STRING, DataType.NUMBER, DataType.BOOLEAN, DataType.NULL
        ])

        if field_type == DataType.STRING:
            return self._value_generator.generate_string()
        elif field_type == DataType.NUMBER:
            return self._generate_simple_number()
        elif field_type == DataType.BOOLEAN:
            return self._value_generator.generate_boolean()
        elif field_type == DataType.NULL:
            return None
        return None

    @staticmethod
    def _generate_simple_number() -> int | float:
        """Generate a number for simple fields."""
        if random.random() < 0.5:
            return random.randint(-999999, 999999)
        return round(random.uniform(-999.99, 999.99), 4)


class DataGenerator:
    """Main data_gen generator orchestrating the creation of test data_gen."""

    def __init__(self, num_fields: int, config: GeneratorConfig):
        self._validate_input(num_fields)
        self._field_counter = FieldCounter(num_fields)
        self._config = config
        self._value_generator = ValueGenerator(config.DEFAULT_STRING_VALUES)
        self._nested_generator = NestedObjectGenerator(self._value_generator, self._field_counter)
        self._array_generator = ArrayGenerator(self._value_generator)
        self._simple_generator = SimpleFieldGenerator(self._value_generator)
        self._metadata_generator = MetadataGenerator()

    @staticmethod
    def _validate_input(num_fields: int) -> None:
        """Validate input parameters."""
        if not isinstance(num_fields, int):
            raise TypeError(f"num_fields must be an integer, got {type(num_fields).__name__}")
        if num_fields <= 0:
            raise ValueError(f"num_fields must be a positive integer, got {num_fields}")

    def generate(self) -> Dict[str, Any]:
        """Generate test data_gen with the specified number of fields."""
        random.seed(42 + self._field_counter.target_fields)
        data_generated = {}

        while self._field_counter.has_remaining_fields():
            field_name = f"field_{self._field_counter.fields_created}"
            field_value = self._create_field_value()
            data_generated[field_name] = field_value

        data_generated["_metadata"] = self._metadata_generator.generate_metadata(
            self._field_counter.fields_created,
            self._field_counter.target_fields
        )

        return data_generated

    def _create_field_value(self) -> Any:
        """Create a field value based on remaining fields and probabilities."""
        remaining = self._field_counter.remaining_fields

        if self._should_create_nested_object(remaining):
            return self._create_nested_object_field()
        elif self._should_create_array(remaining):
            return self._create_array_field()
        else:
            return self._create_simple_field()

    def _should_create_nested_object(self, remaining_fields: int) -> bool:
        """Determine if a nested object should be created."""
        return (remaining_fields > self._config.MIN_FIELDS_FOR_NESTED and
                random.random() < self._config.NESTED_OBJECT_PROBABILITY)

    def _should_create_array(self, remaining_fields: int) -> bool:
        """Determine if an array should be created."""
        return (remaining_fields > self._config.MIN_FIELDS_FOR_ARRAY and
                random.random() < self._config.ARRAY_PROBABILITY)

    def _create_nested_object_field(self) -> Dict[str, Any]:
        """Create a nested object field."""
        nested_data = self._nested_generator.create_nested_object(0, 3)
        if not isinstance(nested_data, dict) or not nested_data:
            self._field_counter.increment()
        return nested_data

    def _create_array_field(self) -> List[Any]:
        """Create an array field."""
        array_data = self._array_generator.create_array(self._config.ARRAY_SIZE_RANGE)
        self._field_counter.increment()
        return array_data

    def _create_simple_field(self) -> Any:
        """Create a simple field."""
        field_value = self._simple_generator.create_simple_field()
        self._field_counter.increment()
        return field_value


class ChunkSizeCalculator:
    """Calculates optimal chunk sizes for streaming."""

    @staticmethod
    def calculate_chunk_size(data_size: int) -> int:
        """Calculate optimal chunk size based on data_gen size."""
        if data_size < 1000:
            return 50
        elif data_size < 10000:
            return 200
        elif data_size < 100000:
            return 1024
        else:
            return 4096


class StreamingChunkGenerator:
    """Generates streaming chunks from JSON data_gen."""

    def __init__(self, chunk_calculator: ChunkSizeCalculator):
        self._chunk_calculator = chunk_calculator

    def create_chunks(self, json_bytes_chunk: bytes, chunk_size: int = None) -> List[bytes]:
        """Split JSON bytes into chunks for streaming simulation."""
        if chunk_size is None:
            chunk_size = self._chunk_calculator.calculate_chunk_size(len(json_bytes_chunk))

        return [json_bytes_chunk[i:i + chunk_size]
                for i in range(0, len(json_bytes_chunk), chunk_size)]


class MixedComplexityDataGenerator:
    """Generates data_gen with mixed complexity patterns."""

    def __init__(self, config: GeneratorConfig):
        self._config = config
        self._value_generator = ValueGenerator(config.DEFAULT_STRING_VALUES)

    def generate(self, num_fields: int) -> Dict[str, Any]:
        """Generate JSON data_gen with mixed complexity patterns."""
        random.seed(42 + num_fields)

        json_data = {
            "simple_fields": {},
            "arrays": {},
            "nested_objects": {},
            "mixed_arrays": {},
            "deep_nesting": {}
        }

        fields_per_section = num_fields // 5

        self._populate_simple_fields(json_data["simple_fields"], fields_per_section)
        self._populate_arrays(json_data["arrays"], fields_per_section)
        self._populate_nested_objects(json_data["nested_objects"], fields_per_section)
        self._populate_mixed_arrays(json_data["mixed_arrays"], fields_per_section)
        self._populate_deep_nesting(json_data["deep_nesting"], num_fields - (fields_per_section * 4))

        return json_data

    @staticmethod
    def _populate_simple_fields(section: Dict[str, Any], count: int) -> None:
        """Populate a simple fields section."""
        for i in range(count):
            section[f"simple_{i}"] = random.choice([
                f"Simple string value {i}",
                random.randint(1, 1000000),
                random.choice([True, False]),
                None
            ])

    @staticmethod
    def _populate_arrays(section: Dict[str, Any], count: int) -> None:
        """Populate an arrays section."""
        for i in range(count):
            array_size = random.randint(5, 20)
            section[f"array_{i}"] = [random.randint(1, 1000) for _ in range(array_size)]

    @staticmethod
    def _populate_nested_objects(section: Dict[str, Any], count: int) -> None:
        """Populate a nested objects section."""
        for i in range(count):
            section[f"nested_{i}"] = {
                "level_1": {
                    "level_2": {
                        "value": f"Deep value {i}",
                        "number": random.randint(1, 1000)
                    }
                }
            }

    @staticmethod
    def _populate_mixed_arrays(section: Dict[str, Any], count: int) -> None:
        """Populate a mixed arrays section."""
        for i in range(count):
            section[f"mixed_{i}"] = [
                {"id": j, "value": f"Item {j}"}
                for j in range(random.randint(3, 10))
            ]

    @staticmethod
    def _populate_deep_nesting(section: Dict[str, Any], count: int) -> None:
        """Populate a deep nesting section."""
        current_level = section
        for i in range(count):
            current_level[f"level_{i}"] = {
                "data_gen": f"Level {i} data_gen",
                "next": {}
            }
            current_level = current_level[f"level_{i}"]["next"]


class DataValidator:
    """Validates generated data_gen against requirements."""

    def __init__(self, config: GeneratorConfig):
        self._config = config

    def validate(self, data_gen: Dict[str, Any], expected_fields: int) -> bool:
        """Validate that generated data_gen meets requirements."""
        actual_fields = self._count_fields(data_gen)
        tolerance = max(1, int(expected_fields * self._config.TOLERANCE_PERCENTAGE))
        return abs(actual_fields - expected_fields) <= tolerance

    def _count_fields(self, obj: Any) -> int:
        """Recursively count fields in a data_gen structure."""
        if isinstance(obj, dict):
            count = len(obj)
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    count += self._count_fields(value)
            return count
        elif isinstance(obj, list):
            count = 0
            for item in obj:
                if isinstance(item, (dict, list)):
                    count += self._count_fields(item)
            return count
        return 0


# Public API functions
def generate_test_data(num_fields: int) -> Dict[str, Any]:
    """
    Generate a JSON structure with the specified number of fields.

    Args:
        num_fields: Target number of fields in the generated JSON

    Returns:
        Dictionary representing the JSON structure
    """
    config = GeneratorConfig()
    generator = DataGenerator(num_fields, config)
    return generator.generate()


def create_streaming_chunks(json_bytes_chunk: bytes, chunk_size: int = None) -> List[bytes]:
    """
    Split JSON bytes into chunks for streaming simulation.

    Args:
        json_bytes_chunk: The JSON data_gen as bytes
        chunk_size: Size of each chunk (auto-calculated if None)

    Returns:
        List of byte chunks
    """
    chunk_calculator = ChunkSizeCalculator()
    chunk_generator = StreamingChunkGenerator(chunk_calculator)
    return chunk_generator.create_chunks(json_bytes_chunk, chunk_size)


def generate_mixed_complexity_data(num_fields: int) -> Dict[str, Any]:
    """
    Generate JSON data_gen with mixed complexity patterns.

    Args:
        num_fields: Target number of fields

    Returns:
        Dictionary with mixed complexity patterns
    """
    config = GeneratorConfig()
    generator = MixedComplexityDataGenerator(config)
    return generator.generate(num_fields)


def validate_generated_data(val_data_gen: Dict[str, Any], expected_fields: int) -> bool:
    """
    Validate that generated data_gen meets requirements.

    Args:
        val_data_gen: Generated data_gen dictionary
        expected_fields: Expected number of fields

    Returns:
        True if validation passes
    """
    config = GeneratorConfig()
    validator = DataValidator(config)
    return validator.validate(val_data_gen, expected_fields)


if __name__ == "__main__":
    """
    Demo script showing data_gen generator capabilities.

    This is a demonstration of the data_gen generator functionality.
    For comprehensive testing, run the test suite: pytest tests/simulation/test_data_gen.py
    """
    print("Data Generator Demo")
    print("=" * 50)
    print("This demonstrates the data_gen generation capabilities.")
    print("For comprehensive testing, run: pytest tests/simulation/test_data_gen.py")
    print()

    # Demo with a small dataset
    demo_size = 100
    print(f"Generating demo dataset with {demo_size} fields...")

    data = generate_test_data(demo_size)
    json_str = json.dumps(data, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')
    chunks = create_streaming_chunks(json_bytes)

    print(f"✓ Generated {len(json_str):,} characters")
    print(f"✓ Created {len(chunks)} streaming chunks")
    print(f"✓ Validation: {'PASS' if validate_generated_data(data, demo_size) else 'FAIL'}")
    print("\nDemo completed! Use this module in your benchmarking applications.")