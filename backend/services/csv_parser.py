import csv
import io
from typing import Dict, Any, Optional
from pathlib import Path
from backend.utils.type_inference import _infer_column_types
from backend.utils.encoding import _detect_delimiter
from backend.services.base_parser import BaseParser


class CSVParser(BaseParser):
    """Parser for CSV files with automatic delimiter and encoding detection"""

    async def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a CSV file and extract column information.

        Args:
            file_path: Path to the CSV file

        Returns:
            Dict containing columns, sample data, and metadata
        """
        content, encoding = await self._read_text_file(file_path)
        return self._parse_string(content, name=file_path.name, encoding=encoding)

    def _parse_string(self, content: str, name: str, encoding: str) -> Dict[str, Any]:
        delimiter = _detect_delimiter(content)
        csv_reader = csv.reader(io.StringIO(content), delimiter=delimiter)
        rows = list(csv_reader)

        if not rows:
            raise ValueError("CSV file is empty")

        headers = rows[0]
        data_rows = rows[1:]
        sample_data = data_rows[:10]
        column_info = _infer_column_types(headers, data_rows)

        return {
            "filename": name,
            "encoding": encoding,
            "delimiter": delimiter,
            "total_rows": len(data_rows),
            "columns": column_info,
            "sample_data": sample_data,
            "data_rows": data_rows,
            "headers": headers,
        }


# Global parser instance
_csv_parser: Optional[CSVParser] = None


def get_csv_parser() -> CSVParser:
    """Get or create global CSV parser instance"""
    global _csv_parser
    if _csv_parser is None:
        _csv_parser = CSVParser()
    return _csv_parser
