from openpyxl import load_workbook
from pathlib import Path
from backend.utils.type_inference import _infer_column_types
from typing import Dict, Any, Optional


class XLSXParser:
    """Parser for XLSX files using openpyxl"""

    def __init__(self):
        pass

    async def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse an XLSX file and extract column information.

        Args:
            file_path: Path to the XLSX file

        Returns:
            Dict containing columns, sample data, and metadata
        """
        # Load workbook
        workbook = load_workbook(filename=file_path, read_only=True)

        # Get the first sheet
        sheet = workbook.active

        # Extract headers (first row)
        headers = [str(cell.value) if cell.value is not None else "" for cell in next(sheet.iter_rows(min_row=1, max_row=1))]

        # Extract data rows
        data_rows = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            data_rows.append(row)

        # Get sample data (first 10 rows)
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
_xlsx_parser: Optional[XLSXParser] = None


def get_xlsx_parser() -> XLSXParser:
    """Get or create global XLSX parser instance"""
    global _xlsx_parser
    if _xlsx_parser is None:
        _xlsx_parser = XLSXParser()
    return _xlsx_parser
