from pathlib import Path
from backend.utils.type_inference import _infer_column_types
from typing import Dict, Any, Optional
from euring import EuringRecord
from datetime import datetime
from backend.services.base_parser import BaseParser
from backend.utils.unit_conversion import dms_to_decimal


class EURINGParser(BaseParser):
    """Parser for EURING files using the euring library.
    Expects .txt files with one EURING code per line."""

    def __init__(self):
        pass

    async def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a .txt containing EURING Exchange codes.
        Every new line should be its own code.

        Args:
            file_path: Path to the .txt file

        Returns:
            Dict containing columns, sample data, and metadata
        """
        content, _ = await self._read_text_file(file_path)
        return self._parse_lines(content.splitlines(), name=file_path.name)

    # Make a method so we can reuse the parsing logic for both files and raw strings (this is done for SUBMIT files, which contain EURING codes as one of their columns)
    def parse_content(self, raw: str, name: str = "input.txt") -> Dict[str, Any]:
        """
        Parse a raw string of EURING Exchange codes.
        Every new line should be its own code.

        Args:
            raw: String containing EURING codes, one per line
            name: Optional filename to use in the result

        Returns:
            Dict containing columns, sample data, and metadata
        """
        lines = raw.splitlines()
        return self._parse_lines(lines, name=name)

    def _parse_lines(self, lines: list[str], name: str) -> Dict[str, Any]:
        # Decode non-empty lines; use None as a placeholder for empty lines
        all_records = [
            EuringRecord.decode(line.strip()).to_dict() if line.strip() else None
            for line in lines
        ]

        # Pre-process records: fill derived fields BEFORE building headers so that
        # latitude/longitude (derived from geographical_coordinates) appear in seen_keys.
        for record in all_records:
            if record is None:
                continue

            # Convert coordinates from DMS to decimal and fill lat/lon if empty
            coords = dms_to_decimal(
                record["fields"]["geographical_coordinates"]["value"]
            )
            if record["fields"]["latitude"]["value"] == "":
                record["fields"]["latitude"]["value"] = coords["lat"]
            if record["fields"]["longitude"]["value"] == "":
                record["fields"]["longitude"]["value"] = coords["lon"]

            # Convert date to the correct format
            record["fields"]["date"]["value"] = datetime.strptime(
                record["fields"]["date"]["value"], "%d%m%Y"
            ).strftime("%Y-%m-%d")

        # Build headers based on all processed records to ensure we have all possible fields:
        seen_keys = {}
        for record in all_records:
            if record is None:
                continue
            for key, field in record["fields"].items():
                if field["value"] != "" and key not in seen_keys:
                    seen_keys[key] = field["name"]

        headers = list(seen_keys.values())

        # Extract the data rows:
        data_rows = []
        for row_dict in all_records:
            # Empty lines produce a row of empty strings to preserve alignment
            if row_dict is None:
                data_rows.append(tuple("" for _ in seen_keys))
                continue

            row_tuple = tuple(
                row_dict["fields"].get(key, {}).get("value", "") for key in seen_keys
            )
            data_rows.append(row_tuple)

        # Get sample data from data_rows
        sample_data = data_rows[:10]

        # Infer column types
        column_info = _infer_column_types(headers, data_rows)

        return {
            "filename": name,
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
