import csv
import io
from pathlib import Path
from backend.utils.encoding import _detect_delimiter
from backend.utils.type_inference import _infer_column_types
from backend.services.base_parser import BaseParser
from backend.services.euring_parser import EURINGParser
from typing import Dict, Any, Optional


class SUBMITParser(BaseParser):
    """Parser for SUBMIT files, which are similar to CSV but with EURING codes as one of their columns."""

    def _parse_file_sync(self, file_path: Path) -> Dict[str, Any]:
        content, encoding = self._read_text_file_sync(file_path)
        return self._parse_string(content, name=file_path.name, encoding=encoding)

    def _parse_string(self, content: str, name: str, encoding: str) -> Dict[str, Any]:
        delimiter = _detect_delimiter(content, delimiter_candidates=[",", ";", "\t"])
        csv_reader = csv.reader(io.StringIO(content), delimiter=delimiter)
        rows = list(csv_reader)

        if not rows:
            raise ValueError("SUBMIT file is empty")

        headers = [h.strip() for h in rows[0]]
        data_rows = rows[1:]

        # Find the euring2020 column index
        if "euring2020" not in headers:
            raise ValueError("Column 'euring2020' not found in SUBMIT file")

        euring_index = headers.index("euring2020")

        # Extract all values from that column, joined as one string (one code per line)
        euring_raw = "\n".join(row[euring_index] for row in data_rows)

        # Parse the EURING codes
        euring_result = EURINGParser().parse_content(euring_raw, name=name)

        # Merge EURING columns back into the rows
        merged_headers = headers + euring_result["headers"]
        merged_rows = [
            tuple(csv_row) + tuple(euring_row)
            for csv_row, euring_row in zip(data_rows, euring_result["data_rows"])
        ]

        sample_data = merged_rows[:10]
        column_info = _infer_column_types(merged_headers, merged_rows)

        return {
            "filename": name,
            "encoding": encoding,
            "delimiter": delimiter,
            "total_rows": len(merged_rows),
            "columns": column_info,
            "sample_data": sample_data,
            "data_rows": merged_rows,
            "headers": merged_headers,
        }


# Global parser instance
_submit_parser: Optional[SUBMITParser] = None


def get_submit_parser() -> SUBMITParser:
    """Get or create global SUBMIT parser instance"""
    global _submit_parser
    if _submit_parser is None:
        _submit_parser = SUBMITParser()
    return _submit_parser
