"""
Parquet streaming parser implementation.
Note: Parquet is columnar storage format, so this implements JSON parsing
with Parquet-inspired columnar processing and metadata handling.
"""
import json
from typing import Any, Dict, Optional, List, Union


class StreamingJsonParser:
    """Streaming JSON parser with Parquet-inspired columnar processing."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self.buffer = ""
        self.parsed_data = {}
        self.column_data = {}  # Parquet-style columnar storage
        self.metadata = {
            'schema': {},
            'row_groups': [],
            'total_rows': 0
        }
        self.current_row_group = []
        self.row_group_size = 1000  # Parquet-style row group size

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data incrementally using Parquet-style processing.
        
        Args:
            buffer: String chunk of JSON data to process
        """
        self.buffer += buffer
        self._parse_parquet_style()

    def _parse_parquet_style(self) -> None:
        """Parse using Parquet-inspired columnar processing."""
        # Parquet processes data in row groups and stores in columnar format

        # Extract rows from buffer
        rows = self._extract_rows_from_buffer()

        # Process rows into columnar format
        for row in rows:
            self._add_row_to_columns(row)

        # Update metadata
        self._update_parquet_metadata()

    def _extract_rows_from_buffer(self) -> List[Dict[str, Any]]:
        """Extract complete rows (JSON objects) from buffer."""
        rows = []
        current_row = ""
        brace_count = 0
        in_string = False
        escape_next = False

        for char in self.buffer:
            current_row += char

            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1

                    if brace_count == 0 and current_row.strip():
                        # Complete row found
                        try:
                            row_obj = json.loads(current_row.strip())
                            if isinstance(row_obj, dict):
                                complete_pairs = self._extract_complete_pairs_parquet(row_obj)
                                if complete_pairs:
                                    rows.append(complete_pairs)
                        except json.JSONDecodeError:
                            # Try partial parsing
                            partial_row = self._parse_partial_row(current_row.strip())
                            if partial_row:
                                rows.append(partial_row)

                        current_row = ""

        # Handle incomplete row
        if current_row.strip() and brace_count > 0:
            partial_row = self._parse_partial_row(current_row.strip())
            if partial_row:
                rows.append(partial_row)

        return rows

    def _parse_partial_row(self, row_str: str) -> Optional[Dict[str, Any]]:
        """Parse partial row using Parquet-style error recovery."""
        try:
            # Parquet-style row completion
            if '{' in row_str:
                open_braces = row_str.count('{')
                close_braces = row_str.count('}')

                if open_braces > close_braces:
                    # Complete the row
                    completed_row = row_str + '}' * (open_braces - close_braces)

                    try:
                        row_obj = json.loads(completed_row)
                        if isinstance(row_obj, dict):
                            return self._extract_complete_pairs_parquet(row_obj)
                    except json.JSONDecodeError:
                        pass

            return None

        except Exception:
            return None

    def _add_row_to_columns(self, row: Dict[str, Any]) -> None:
        """Add row data to columnar storage (Parquet-style)."""
        # Parquet stores data in columns for efficient compression and querying

        for column_name, value in row.items():
            if column_name not in self.column_data:
                self.column_data[column_name] = []

            self.column_data[column_name].append(value)

        # Add to current row group
        self.current_row_group.append(row)

        # Check if row group is full
        if len(self.current_row_group) >= self.row_group_size:
            self._finalize_row_group()

    def _finalize_row_group(self) -> None:
        """Finalize current row group (Parquet-style)."""
        if self.current_row_group:
            # Create row group metadata
            row_group_metadata = {
                'num_rows': len(self.current_row_group),
                'columns': list(set().union(*(row.keys() for row in self.current_row_group))),
                'compressed_size': len(str(self.current_row_group)),  # Simplified
                'uncompressed_size': len(str(self.current_row_group))  # Simplified
            }

            self.metadata['row_groups'].append(row_group_metadata)
            self.metadata['total_rows'] += len(self.current_row_group)

            # Update parsed data with row group data
            for row in self.current_row_group:
                self.parsed_data.update(row)

            # Clear current row group
            self.current_row_group = []

    def _update_parquet_metadata(self) -> None:
        """Update Parquet-style metadata."""
        # Update schema information
        all_columns = set()
        for row in self.current_row_group:
            all_columns.update(row.keys())

        for column in all_columns:
            if column not in self.metadata['schema']:
                # Infer column type (simplified)
                column_values = self.column_data.get(column, [])
                if column_values:
                    sample_value = column_values[-1]
                    self.metadata['schema'][column] = {
                        'type': type(sample_value).__name__,
                        'nullable': True,  # Assume nullable
                        'compression': 'SNAPPY'  # Default Parquet compression
                    }

    def _extract_complete_pairs_parquet(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs with Parquet-style validation."""
        complete_pairs = {}

        for key, value in obj.items():
            # Parquet column name validation
            if isinstance(key, str) and len(key) > 0:
                # Parquet supports various data types
                if self._is_valid_parquet_value(value):
                    complete_pairs[key] = value

        return complete_pairs

    def _is_valid_parquet_value(self, value: Any) -> bool:
        """Check if value is valid for Parquet storage."""
        # Parquet supports: boolean, int32, int64, float, double, binary, string, etc.
        if value is None:
            return True
        if isinstance(value, (str, int, float, bool)):
            return True
        if isinstance(value, list):
            # Parquet supports arrays
            return all(self._is_valid_parquet_value(item) for item in value)
        if isinstance(value, dict):
            # Parquet supports nested structures
            return all(isinstance(k, str) and self._is_valid_parquet_value(v)
                       for k, v in value.items())

        return False

    def get_columnar_data(self) -> Dict[str, List[Any]]:
        """
        Return data in Parquet-style columnar format.
        
        Returns:
            Dictionary with column names as keys and lists of values
        """
        return self.column_data.copy()

    def get_metadata(self) -> Dict[str, Any]:
        """
        Return Parquet-style metadata.
        
        Returns:
            Dictionary containing schema and row group metadata
        """
        return self.metadata.copy()

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as Python object.
        
        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        # Finalize any remaining row group
        if self.current_row_group:
            self._finalize_row_group()

        return self.parsed_data.copy()
