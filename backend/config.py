from pathlib import Path
from backend.services.parser_registry import supported_extensions

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
FORMAT_DIR = DATA_DIR / "format"

# File upload settings
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

# Derived from the parser registry — add new parsers there, not here
ALLOWED_EXTENSIONS = supported_extensions()

# Server settings
HOST = "127.0.0.1"
PORT = 8000
DEBUG = True

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# XML generation settings
XML_CHUNK_SIZE = 1000  # Max rows per XML file (XSD maxOccurs limit)

# File retention — oldest files are deleted once this limit is exceeded (FIFO)
MAX_RETAINED_FILES = 50

# Fields hardcoded in the XML generator — maps field name to its default value.
# Add new fields here; both the generator and validator derive their behaviour from this.
HARDCODED_FIELD_NAMES: dict[str, str] = {
    "Modus": "Insert",
    "EURINGCodeIdentifier": "4",
}
