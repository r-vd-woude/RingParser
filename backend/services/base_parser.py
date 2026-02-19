from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any
import aiofiles

from backend.utils.encoding import _detect_encoding


class BaseParser(ABC):
    """Abstract base class for all file parsers."""

    async def _read_text_file(self, file_path: Path) -> tuple[str, str]:
        """Read a text file, auto-detecting encoding. Returns (content, encoding)."""
        async with aiofiles.open(file_path, "rb") as f:
            raw = await f.read()
        encoding = _detect_encoding(raw)
        return raw.decode(encoding), encoding

    @abstractmethod
    async def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a file and return its contents in a standard structure.

        All parsers must return a dict with at least:
            - filename:   str
            - total_rows: int
            - columns:    list of ColumnInfo-compatible dicts
            - headers:    list[str]
            - data_rows:  list of rows
            - sample_data: list of rows (first 10)
        """
