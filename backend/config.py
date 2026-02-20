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
MAX_UPLOAD_SIZE_SCHEMA = 252 * 1024  # 252KB

# Derived from the parser registry — add new parsers there, not here
ALLOWED_EXTENSIONS = supported_extensions()

# Server settings
HOST = "127.0.0.1"
PORT = 8000
DEBUG = False

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# XML generation settings
XML_CHUNK_SIZE = 1000  # Max rows per XML file
MAX_DATA_ROWS = 10_000  # Max data rows accepted from any uploaded file

# File retention — oldest files are deleted once this limit is exceeded (FIFO)
MAX_RETAINED_FILES = 50

# API limiter settings
UPLOAD_LIMIT = "5/minute"  # Limit to 5 uploads per minute per IP
DOWNLOAD_LIMIT = "5/minute"  # Limit to 20 downloads per minute per IP
MAPPING_LIMIT = "100/minute"  # Limit to 100 mapping requests per minute per IP

# Fields hardcoded in the XML generator — maps field name to its default value.
# Add new fields here; both the generator and validator derive their behaviour from this.
# These can be overridden by an "advanced overrides".
HARDCODED_FIELD_NAMES: dict[str, str | None] = {
    "Modus": "Insert",
    "EURINGCodeIdentifier": "4",
    "ReportingDate": "set_to_today",
}

# Settings for CORS
CORS_ORIGINS = [
    "*"
]  # Allow requests from any origin (for local development; restrict in production)
CORS_CREDENTIALS = True  # Allow cookies and credentials in requests
CORS_METHODS = ["*"]  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
CORS_HEADERS = ["*"]  # Allow all custom headers

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
