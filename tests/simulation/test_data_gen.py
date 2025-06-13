import json

import pytest

from simulation.data_gen import (
    generate_test_data,
    create_streaming_chunks,
    generate_mixed_complexity_data,
    validate_generated_data
)


class TestDataGen:
    @pytest.mark.parametrize("num_fields", [1, 10, 100, 1000])
    def test_generate_test_data(self, num_fields: int):
        """Test generating JSON data with various field counts."""
        data = generate_test_data(num_fields)

        # Basic type and structure checks
        assert isinstance(data, dict)
        assert "_metadata" in data
        assert data["_metadata"]["target_fields"] == num_fields
        assert data["_metadata"]["total_fields"] > 0

        # Verify JSON serialization
        json_str = json.dumps(data)
        assert len(json_str) > 0

        # Verify data can be parsed back
        parsed_data = json.loads(json_str)
        assert parsed_data == data

        # Verify metadata fields
        assert "generated_at" in data["_metadata"]
        assert "generator_version" in data["_metadata"]
        assert "test_run_id" in data["_metadata"]

    def test_create_streaming_chunks(self):
        """Test creating streaming chunks with various configurations."""
        test_data = {"field_1": "test_value", "field_2": 123, "nested": {"a": 1, "b": 2}}
        json_bytes = json.dumps(test_data).encode('utf-8')

        # Test with auto-sized chunks
        chunks = create_streaming_chunks(json_bytes)
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(chunk, bytes) for chunk in chunks)

        # Verify chunk reassembly
        reassembled = b''.join(chunks)
        assert reassembled == json_bytes

        # Test with custom chunk size
        chunk_size = 5
        custom_chunks = create_streaming_chunks(json_bytes, chunk_size=chunk_size)
        assert all(len(chunk) <= chunk_size for chunk in custom_chunks)

        # Test with chunk size larger than data
        large_chunks = create_streaming_chunks(json_bytes, chunk_size=len(json_bytes) * 2)
        assert len(large_chunks) == 1

    def test_generate_mixed_complexity_data(self):
        """Test generating mixed complexity data."""
        num_fields = 100
        data = generate_mixed_complexity_data(num_fields)

        assert isinstance(data, dict)
        assert "_metadata" in data
        assert data["_metadata"]["target_fields"] == num_fields

        # Verify all expected sections exist
        expected_sections = [
            "simple_fields",
            "arrays",
            "nested_objects",
            "mixed_arrays",
            "deep_nesting"
        ]

        for section in expected_sections:
            assert section in data
            assert isinstance(data[section], dict)
            assert len(data[section]) > 0

    @pytest.mark.parametrize("num_fields", [0, -1, -100])
    def test_edge_cases(self, num_fields: int):
        """Test edge cases like zero or negative field counts."""
        data = generate_test_data(num_fields)
        assert isinstance(data, dict)
        assert "_metadata" in data
        assert data["_metadata"]["target_fields"] == num_fields

        # Should still be valid JSON
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        assert parsed == data

    def test_deterministic_output(self):
        """Test that the same seed produces the same output."""
        num_fields = 50

        # Generate data twice with the same parameters
        data1 = generate_test_data(num_fields)
        data2 = generate_test_data(num_fields)

        # Should be identical
        assert data1 == data2

        # Different field count should produce different output
        data3 = generate_test_data(num_fields + 1)
        assert data1 != data3

    @pytest.mark.parametrize("input_fields,expected_fields,tolerance", [
        (100, 100, True),
        (100, 90, True),  # Within 10% tolerance
        (100, 110, True),  # Within 10% tolerance
        (100, 89, False),  # Outside tolerance
        (100, 111, False),  # Outside tolerance
        (10, 9, True),  # Small number of fields
        (1, 1, True),  # Minimum fields
        (0, 0, True),  # Zero fields
    ])
    def test_validate_generated_data(self, input_fields: int, expected_fields: int, tolerance: bool):
        """Test validation of generated data with various field counts."""
        data = generate_test_data(input_fields)
        is_valid = validate_generated_data(data, expected_fields)

        if tolerance:
            assert is_valid is True
        else:
            assert is_valid is False
