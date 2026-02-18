# Ring Parser - CSV/XML to XSD Mapper

A web application for mapping CSV/XML files to XSD schema and generating valid XML output for EURING bird ringing data format.

## Features

- Upload CSV or XML files
- Parse XSD schema and display fields with constraints
- Map source columns to target XSD fields interactively
- Validate mapped data against XSD constraints
- Generate valid XML output conforming to schema

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: Vanilla JavaScript + HTML/CSS
- **Data Processing**: lxml, xmlschema, pandas
- **Deployment**: Local (localhost)

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
│   ├── format/       # XSD schema
│   ├── uploads/      # Uploaded files
│   └── outputs/      # Generated XML
└── tests/            # Test files
```

## Setup

### Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) (modern Python package/dependency manager)

### Installation

1. Create virtual environment:

```bash
cd backend
python -m venv venv
```

2. Activate virtual environment:

- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

3. Install dependencies:

```bash
uv pip install -r backend/requirements.lock
```

## Running the Application

From the project root directory:

```bash
python run.py
```

The application will start on http://localhost:8000

- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- API Base URL: http://localhost:8000/api

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/schema/parse` - Parse XSD schema
- `POST /api/file/upload` - Upload CSV/XML file (Phase 2)
- `POST /api/file/parse` - Parse uploaded file (Phase 2)
- `POST /api/mapping/create` - Create column mapping (Phase 3)
- `POST /api/mapping/suggest` - Auto-suggest mappings (Phase 3)
- `POST /api/mapping/validate` - Validate data (Phase 4)
- `POST /api/xml/generate` - Generate XML output (Phase 5)
- `GET /api/xml/download/{id}` - Download generated XML (Phase 5)

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

The application uses the "Griel bulkupload XSD schema" [bulkimportnew.xsd.xml](data/format/bulkimportnew.xsd.xml).

Data needs to be entered in the EURING standard format [EURING2000 Exchange Code](https://euring.org/files/documents/E2020ExchangeCodeV202.pdf)

## License

Project for EURING BirdRinging Data Format

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
