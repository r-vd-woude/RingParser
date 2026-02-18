from pathlib import Path
from backend.utils.type_inference import _infer_column_types
from typing import Dict, Any, Optional
from euring import EuringRecord


class EURINGParser:
    """Parser for EURING files using euring"""

    def _init_(self):
        pass

    async def parse_file(self, file_path: Path) -> Dict(str, Any):
        """
        Parse a .txt containing EURING Exchange codes.
        Every new line should be its own code.

        Args:
            file_path: Path to the .txt file

        Returns:
            Dict containing columns, sample data, and metadata
        """

        # Read the file:
        with open(file_path, "r", encoding="utf-8") as file:
            euring_codes = file.readlines()

        # Get the first record out of the file to extract headers
        first_record = EuringRecord.decode(euring_codes[0].strip()).to_dict()
        headers = [v["name"] for v in first_record["fields"].values()]

        # Extract the data rows:
        data_rows = []
        for line in euring_codes:
            row_dict = EuringRecord.decode(line.strip()).to_dict()
            row_tuple = tuple(v["value"] for v in row_dict["fields"].values())
            data_rows.append(row_tuple)

        # Get sample data from data_rows
        sample_data = data_rows[:10]

        # Infer column types
        column_info = _infer_column_types(headers, data_rows)

        return {
            "filename": file_path.name,
            "total_rows": len(data_rows),
            "columns": column_info,
            "sample_data": sample_data,
            "data_rows": data_rows,
            "headers": headers,
        }


# Global parser instance
_euring_parser: Optional[EURINGParser] = None


def get_euring_parser() -> EURINGParser:
    """Get or create global XLSX parser instance"""
    global _euring_parser
    if _euring_parser is None:
        _euring_parser = EURINGParser()
    return _euring_parser
