import asyncio
from openpyxl import load_workbook
from pathlib import Path
from backend.utils.type_inference import _infer_column_types
from typing import Dict, Any, Optional
from backend.services.base_parser import BaseParser


class XLSXParser(BaseParser):
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
        workbook = await asyncio.to_thread(load_workbook, filename=file_path, read_only=True)
        return self._parse_workbook(workbook, name=file_path.name)

    def parse_content(self, raw: bytes, name: str = "input.xlsx") -> Dict[str, Any]:
        """
        Parse raw XLSX bytes and extract column information.

        Args:
            raw: Bytes containing XLSX content
            name: Optional filename to use in the result

        Returns:
            Dict containing columns, sample data, and metadata
        """
        import io
        workbook = load_workbook(filename=io.BytesIO(raw), read_only=True)
        return self._parse_workbook(workbook, name=name)

    def _parse_workbook(self, workbook, name: str) -> Dict[str, Any]:
        sheet = workbook.active
        headers = [str(cell.value) if cell.value is not None else "" for cell in next(sheet.iter_rows(min_row=1, max_row=1))]

        data_rows = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            data_rows.append(row)

        sample_data = data_rows[:10]
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
_xlsx_parser: Optional[XLSXParser] = None


def get_xlsx_parser() -> XLSXParser:
    """Get or create global XLSX parser instance"""
    global _xlsx_parser
    if _xlsx_parser is None:
        _xlsx_parser = XLSXParser()
    return _xlsx_parser
