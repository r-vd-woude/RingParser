import os
from pathlib import Path
from backend.services.parser_registry import supported_extensions

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
FORMAT_DIR = DATA_DIR / "format"

# XSD Schema file
XSD_SCHEMA_PATH = FORMAT_DIR / "bulkimportnew.xsd.xml"

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

# Fields hardcoded in the XML generator — filled in automatically, never require user mapping
HARDCODED_FIELD_NAMES = {"Modus", "EURINGCodeIdentifier"}
