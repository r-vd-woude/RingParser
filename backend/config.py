import os
from pathlib import Path
from dotenv import load_dotenv
from backend.services.parser_registry import supported_extensions

# Load a .env file if present (no-op when the file is absent, e.g. in Docker
# where env vars are injected directly by the runtime).
load_dotenv()


# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
FORMAT_DIR = DATA_DIR / "format"

# File upload settings
MAX_UPLOAD_SIZE = int(
    float(os.getenv("MAX_UPLOAD_SIZE", "10")) * 1024 * 1024
)  # env var in MB, default 10
MAX_UPLOAD_SIZE_SCHEMA = int(
    float(os.getenv("MAX_UPLOAD_SIZE_SCHEMA", "256")) * 1024
)  # env var in KB, default 256

# Derived from the parser registry — add new parsers there, not here
ALLOWED_EXTENSIONS = supported_extensions()

# Server settings
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# XML generation settings
XML_CHUNK_SIZE = int(os.getenv("XML_CHUNK_SIZE", "1000"))  # Max rows per XML file
MAX_DATA_ROWS = int(
    os.getenv("MAX_DATA_ROWS", "10000")
)  # Max data rows accepted from any uploaded file

# File retention — oldest files are deleted once this limit is exceeded (FIFO)
MAX_RETAINED_FILES = int(os.getenv("MAX_RETAINED_FILES", "50"))

# API limiter settings
UPLOAD_LIMIT = os.getenv("UPLOAD_LIMIT", "5/minute")
DOWNLOAD_LIMIT = os.getenv("DOWNLOAD_LIMIT", "5/minute")
MAPPING_LIMIT = os.getenv("MAPPING_LIMIT", "100/minute")

# Fields hardcoded in the XML generator — maps field name to its default value.
# Add new fields here; both the generator and validator derive their behaviour from this.
# These can be overridden by an "advanced overrides".
HARDCODED_FIELD_NAMES: dict[str, str | None] = {
    "Modus": "Insert",
    "EURINGCodeIdentifier": "4",
    "ReportingDate": "set_to_today",
}

# Settings for CORS
# CORS_ORIGINS accepts a comma-separated list
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
CORS_CREDENTIALS = os.getenv("CORS_CREDENTIALS", "true").lower() in ("true", "1", "yes")
CORS_METHODS = os.getenv("CORS_METHODS", "GET,POST").split(",")  # only methods the API actually uses
CORS_HEADERS = os.getenv("CORS_HEADERS", "Content-Type").split(",")  # only headers the API actually needs

# Domain-specific synonyms for (bird ringing data)
SYNONYMS = {
    ("catch", "capture"): 0.85,
    ("sex", "gender"): 0.8,
    ("species", "bird"): 0.7,
    ("date", "day"): 0.7,
    ("time", "hour"): 0.7,
}

# Check common domain-specific abbreviations
ABBREVIATIONS = {
    "lat": "latitude",
    "lon": "longitude",
    "lng": "longitude",
    "long": "longitude",
    "dt": "date",
    "tm": "time",
    "addr": "address",
    "desc": "description",
    "qty": "quantity",
    "amt": "amount",
    "num": "number",
    "id": "identifier",
    "coord": "coordinate",
    "loc": "location",
}
