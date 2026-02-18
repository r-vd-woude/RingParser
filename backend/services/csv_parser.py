import csv
import io
from typing import Dict, Any, Optional
from pathlib import Path
import chardet
from backend.utils.type_inference import _infer_column_types


class CSVParser:
    """Parser for CSV files with automatic delimiter and encoding detection"""

    def __init__(self):
        self.delimiter_candidates = [",", ";", "\t", "|"]

    async def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a CSV file and extract column information.

        Args:
            file_path: Path to the CSV file

        Returns:
            Dict containing columns, sample data, and metadata
        """
        # Read file content as bytes
        with open(file_path, "rb") as f:
            raw_content = f.read()

        # Detect encoding
        encoding = self._detect_encoding(raw_content)

        # Decode content
        content = raw_content.decode(encoding)

        # Detect delimiter
        delimiter = self._detect_delimiter(content)

        # Parse CSV
        csv_reader = csv.reader(io.StringIO(content), delimiter=delimiter)

        # Read all rows
        rows = list(csv_reader)

        if not rows:
            raise ValueError("CSV file is empty")

        # Extract headers (first row)
        headers = rows[0]

        # Extract data rows
        data_rows = rows[1:]

        # Get sample data (first 10 rows)
        sample_data = data_rows[:10]

        # Infer column types
        column_info = _infer_column_types(headers, data_rows)

        return {
            "filename": file_path.name,
            "encoding": encoding,
            "delimiter": delimiter,
            "total_rows": len(data_rows),
            "columns": column_info,
            "sample_data": sample_data,
            "data_rows": data_rows,
            "headers": headers,
        }

    def _detect_encoding(self, raw_content: bytes) -> str:
        """Detect file encoding using chardet"""
        result = chardet.detect(raw_content)
        encoding = result.get("encoding", "utf-8")

        # Fallback to utf-8 if detection failed
        if encoding is None:
            encoding = "utf-8"

        # Handle common encoding variations
        if encoding.lower() in ["ascii", "us-ascii"]:
            encoding = "utf-8"

        return encoding

    def _detect_delimiter(self, content: str) -> str:
        """
        Detect CSV delimiter by analyzing the first few lines.

        Args:
            content: CSV file content as string

        Returns:
            Detected delimiter character
        """
        # Get first few lines for analysis
        lines = content.split("\n")[:5]
        sample = "\n".join(lines)

        # Try csv.Sniffer
        try:
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(
                sample, delimiters="".join(self.delimiter_candidates)
            ).delimiter
            return delimiter
        except Exception:
            pass

        # Fallback: Count occurrences of each delimiter in first line
        if lines:
            first_line = lines[0]
            delimiter_counts = {
                d: first_line.count(d) for d in self.delimiter_candidates
            }

            # Find delimiter with maximum count (and count > 0)
            max_delimiter = max(delimiter_counts.items(), key=lambda x: x[1])
            if max_delimiter[1] > 0:
                return max_delimiter[0]

        # Default to comma
        return ","


# Global parser instance
_csv_parser: Optional[CSVParser] = None


def get_csv_parser() -> CSVParser:
    """Get or create global CSV parser instance"""
    global _csv_parser
    if _csv_parser is None:
        _csv_parser = CSVParser()
    return _csv_parser
