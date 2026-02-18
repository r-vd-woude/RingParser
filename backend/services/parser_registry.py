from backend.services.csv_parser import CSVParser
from backend.services.xlsx_parser import XLSXParser
from backend.services.euring_parser import EURINGParser

# Add new parsers here — the rest of the application picks them up automatically
PARSER_REGISTRY: dict[str, type] = {
    "csv": CSVParser,
    "xlsx": XLSXParser,
    "xls": XLSXParser,
    "txt": EURINGParser,
}


def get_file_parser(file_extension: str):
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
