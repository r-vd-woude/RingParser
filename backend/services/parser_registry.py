from backend.services.base_parser import BaseParser
from backend.services.csv_parser import CSVParser
from backend.services.submit_parser import SUBMITParser
from backend.services.xlsx_parser import XLSXParser
from backend.services.euring_parser import EURINGParser

# Add new parsers here — the rest of the application picks them up automatically
PARSER_REGISTRY: dict[str, type[BaseParser]] = {
    "csv": CSVParser,
    "xlsx": XLSXParser,
    "xls": XLSXParser,
    "txt": EURINGParser,
    "submit": SUBMITParser,
}


def get_file_parser(file_extension: str) -> BaseParser:
    """Return an instantiated parser for the given extension, e.g. 'csv' or 'xlsx'."""
    ext = file_extension.lower().lstrip(".")
    parser_cls = PARSER_REGISTRY.get(ext)
    if not parser_cls:
        raise ValueError(
            f"Unsupported file type: '{ext}'. Supported: {', '.join(PARSER_REGISTRY)}"
        )
    return parser_cls()


def supported_extensions() -> set[str]:
    """Return file extensions accepted by registered parsers, e.g. {'.csv', '.xlsx'}."""
    return {f".{ext}" for ext in PARSER_REGISTRY}
