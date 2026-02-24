# RingParser - parsing a variety of files to XML 

A web application for mapping files to an XML Schema (XSD) and generating valid XML output based on the selected Schema.

## Features

- Upload files
- Parse an XML Schema and display fields with constraints
- Map source columns to target XSD fields interactively
- Validate mapped data against XSD constraints
- Generate valid XML output conforming to schema

## Supported files

Currently it supports .csv, xlsx, xls, EURING and Submit.CR-Birding-EURING files ([see registry](backend/services/parser_registry.py)).

## Configuration

Settings related to configuration can be set in [config.py](backend/config.py).
Currently, these settings are limited, but might be extended in the future.

## Tech Stack

- **Backend**: Python
- **Frontend**: Vanilla JavaScript + HTML/CSS

## Project Structure

```
RingParser/
├── backend/          # FastAPI backend
│   ├── api/          # API routes
│   ├── services/     # Business logic
│   ├── models/       # Data models
│   └── utils/        # Utilities
├── frontend/         # Web interface
│   ├── css/          # Stylesheets
│   └── js/           # JavaScript
├── data/             # Data files
│   ├── format/       # XML Schemas
│   ├── uploads/      # Uploaded files
│   └── outputs/      # Generated XML
└── tests/            # Test files
```

## Setup

### Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) (package manager)

### Installation

1. Create virtual environment:

```bash
cd backend
uv venv .venv
```

2. Activate virtual environment:

- Windows: `.venv\Scripts\activate`
- Linux/Mac: `source .venv/bin/activate`

3. Install dependencies:

```bash
uv pip install -r requirements.txt
```

## Running the application natively

From the project root directory:

```bash
python run.py
```

The application will start on http://localhost:8000

- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- API Base URL: http://localhost:8000/api

## Building and running the container image

### Building

Build the image using `docker/podman build -t ringparser:latest .`

### Run

`docker/podman run -d \
 --name ringparser \
 -p 8000:8000 \
 -v ./data/uploads:/app/data/uploads \
 -v ./data/outputs:/app/data/outputs \
 ringparser:latest`

Or use the included compose file:

`docker compose up -d`

### Docker environmental parameters

The following environmental variables can be passed to the Docker image:

#### Upload and download restrictions

- MAX_UPLOAD_SIZE: numeric,the maximum allowed upload size of file to be parsed,in MB (default: 10MB)
- MAX_UPLOAD_SIZE_SCHEMA: numeric maximum allowed upload size of a custom schema, in KB (default: 256KB)
- XML_CHUNK_SIZE: integer, maximum number of records in a generated XML file (default: 1000)
- MAX_DATA_ROWS: integer, maximum amount of rows allowed in the uploaded files to be parsed, used to prevent XLSX/XML zip bombing (default: 10.000)
- MAX_RETAINED_FILES: how many uploads and downloads should be kept, removing oldest first (default: 50)

#### Network and debug settings

- HOST: string, interface to which we bind the application
- PORT: string, port to which the application is bound
- DEBUG: string, enable debug, true or false (default: false)

#### API limits

- UPLOAD_LIMIT: string, API limit for uploading files (default: "5/minute")
- DOWNLOAD_LIMIT: string, API limit for downloading files (default: "5/minute")
- MAPPING_LIMIT: string, API limit for how many mapping actions users are allowed to do (default: "100/minute")

#### CORS settings

- CORS_ORIGINS: string, what domains are allowed to talk to the API from a browser (default: \* = all) set to your domain
- CORS_CREDENTIALS: string, allow credentials and cookies (default: true)
- CORS_METHODS: list, what API methods are allowed (default: "GET,POST")
- CORS_HEADERS: string, you can add custom headers here (default: "Content-Type")

## Supported files

Currently supported files can be found in [parser_registry.py](/backend/services/parser_registry.py).

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/schema/parse` - Parse XSD schema
- `POST /api/file/upload` - Upload file
- `POST /api/file/parse` - Parse uploaded file
- `POST /api/mapping/create` - Create column mapping
- `POST /api/mapping/suggest` - Auto-suggest mappings
- `POST /api/mapping/validate` - Validate data
- `POST /api/xml/generate` - Generate XML output
- `GET /api/xml/download/{id}` - Download generated XML

## Development

### Testing the XSD Parser

```bash
# Test health endpoint
curl http://localhost:8000/api/health

# Test schema parsing
curl -X POST http://localhost:8000/api/schema/parse
```

### Project Configuration

Configuration settings are in [config.py](backend/config.py):

## XSD Schema

The application uses the "Griel bulkupload XSD schema" [bulkimportnew.xsd.xml](data/format/griel_bulkupload.xml).

Data needs to be entered in the EURING standard format [EURING2000 Exchange Code](https://euring.org/files/documents/E2020ExchangeCodeV202.pdf)

## Contributing

This project is in active development.
Pull requests are appreciated.

Adding parsers for other file types can be done following the examples in [xlsx_parser.py](backend/services/xlsx_parser.py) and [csv_parser.py](backend/services/csv_parser.py).

The class for the new parsing service should at least contain the following:

- A method called _parse_file_ that returns a dictonary containing:
  - "filename": str
  - "total_rows": int
  - "columns": Any (usually a list or dict with column/type info)
  - "sample_data": list (first 10 rows)
  - "data_rows": list (all rows except header)
  - "headers": list (column names)

A function to infer column types is available [\_infer_column_type](backend/utils/type_inference.py).

You then will need to add your file type and parser in registry routes [parser_registry.py](backend/services/parser_registry.py).

Update the index accordingly to reflect that a new file type can be uploaded [index.html](frontend/index.html).

## License

This project is licensed under the GNU General Public License v3.0.  
See the [LICENSE](LICENSE) file for the full text.
