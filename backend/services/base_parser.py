import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any
from backend.utils.encoding import _detect_encoding


class BaseParser(ABC):
    """Abstract base class for all file parsers."""

    def _check_row_limit(self, data_rows) -> None:
        """Raise ValueError if data_rows exceeds the configured maximum."""
        from backend.config import MAX_DATA_ROWS
        if len(data_rows) > MAX_DATA_ROWS:
            raise ValueError(
                f"File exceeds the maximum of {MAX_DATA_ROWS:,} data rows"
            )

    def _read_text_file_sync(self, file_path: Path) -> tuple[str, str]:
        """Read a text file synchronously, auto-detecting encoding. Returns (content, encoding)."""
        raw = file_path.read_bytes()
        encoding = _detect_encoding(raw)
        return raw.decode(encoding), encoding

    async def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a file off the event loop and enforce the row limit.

        Runs _parse_file_sync in a thread pool so the event loop stays free
        for other requests. Subclasses only need to implement _parse_file_sync.
        """
        result = await asyncio.to_thread(self._parse_file_sync, file_path)
        self._check_row_limit(result["data_rows"])
        return result

    @abstractmethod
    def _parse_file_sync(self, file_path: Path) -> Dict[str, Any]:
        """
        Synchronous file parsing implementation. Called by parse_file in a thread.

        Must return a dict with at least:
            - filename:    str
            - total_rows:  int
            - columns:     list of ColumnInfo-compatible dicts
            - headers:     list[str]
            - data_rows:   list of rows
            - sample_data: list of rows (first 10)
        """
