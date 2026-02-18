# RingParser Application Architecture and Flow

## Overview

**RingParser** is a web application for mapping CSV/XLSX files to an XSD schema and generating valid XML output, primarily for EURING bird ringing data. It consists of a Python FastAPI backend and a vanilla JavaScript frontend.

---

## Backend (Python/FastAPI)

### Key Classes and Their Roles

- **CSVParser (`backend/services/csv_parser.py`)**
  - Parses CSV files, auto-detects encoding and delimiter.
  - Extracts headers, data rows, and delegates type inference to `type_inference.py`.
  - Returns metadata, sample data, and column info.

- **XLSXParser (`backend/services/xlsx__parser.py`)**
  - Parses XLSX files using openpyxl.
  - Extracts headers, data rows, and delegates type inference to `type_inference.py`.
  - Returns metadata, sample data, and column info.

- **XSDParser (`backend/services/xsd_parser.py`)**
  - Parses the XSD schema file.
  - Extracts field definitions, constraints, and structure.
  - Provides a structured representation for mapping and validation.

- **MappingEngine (`backend/services/mapping_engine.py`)**
  - Manages column-to-field mappings.
  - Suggests mappings using name similarity and domain-specific logic.
  - Stores and retrieves mapping configurations.

- **Validator (`backend/services/validator.py`)**
  - Validates mapped data against XSD constraints.
  - Checks types, patterns, enumerations, required fields, and more.
  - Returns detailed validation results.

- **XMLGenerator (`backend/services/xml_generator.py`)**
  - Generates XML output from mapped and validated data.
  - Builds XML structure according to the schema and mapping.
  - Saves XML files and provides previews.

- **Data Models (`backend/models/`)**
  - Pydantic models for file data, mappings, validation, and XML generation.
  - Used for API request/response validation and serialization.

- **FileHandler (`backend/utils/file_handler.py`)**
  - Handles file upload storage: validates extension and size, generates UUID filenames.
  - Provides helpers to retrieve and delete uploaded files.

- **Type Inference (`backend/utils/type_inference.py`)**
  - Detects column types (integer, decimal, date, time, string) from sample values.
  - Called by both `CSVParser` and `XLSXParser` during file parsing.

- **API Routes (`backend/api/routes.py`)**
  - Defines all 9 REST endpoints under the `/api` prefix.
  - Coordinates between `FileHandler`, parsers, `MappingEngine`, `Validator`, and `XMLGenerator`.

- **App & Config (`backend/app.py`, `backend/config.py`)**
  - `app.py`: FastAPI application setup, CORS middleware, static file serving, lifespan hooks.
  - `config.py`: Centralised path constants, file size limits, allowed extensions, and server settings.

---

### File Parsing Flow (Backend)

1. **File Upload**
   - User uploads a CSV or XLSX file via the frontend (`POST /api/file/upload`).
   - `FileHandler` validates the file type/size, generates a UUID filename, and saves it to `/data/uploads/`.
   - Returns a `file_id` used in all subsequent requests.

2. **File Parsing**
   - The frontend requests `/api/file/parse/{file_id}` with the file type.
   - The backend locates the file and uses either `CSVParser` or `XLSXParser` to extract headers, sample data, and column info.
   - The result is returned to the frontend for mapping.

3. **Schema Parsing**
   - The XSD schema is parsed by `XSDParser` to extract all possible fields, constraints, and structure.
   - This information is sent to the frontend for mapping.

4. **Mapping**
   - The user maps source columns to schema fields.
   - The backend can auto-suggest mappings using `MappingEngine`.
   - Mappings are stored and can be retrieved or updated.

5. **Validation**
   - The mapped data is validated against the schema using `Validator`.
   - Checks include type, required fields, enumerations, patterns, and more.
   - Validation results are returned to the frontend.

6. **XML Generation**
   - Once validation passes, the frontend requests XML generation.
   - `XMLGenerator` builds the XML file according to the mapping and schema.
   - The XML file is saved and a preview is provided.
   - The user can download the generated XML.

---

## Frontend (JavaScript)

### Main Responsibilities

- **file-upload.js**
  - Handles file selection, drag-and-drop, and upload.
  - Calls backend to upload and parse files.
  - Displays file info and parsing results.

- **schema-viewer.js**
  - Loads and displays the XSD schema fields and constraints.
  - Allows the user to browse and select schema fields.
  - Handles validation requests and displays results.

- **column-mapper.js**
  - Manages the mapping UI between source columns and schema fields.
  - Supports manual and auto-mapping (using backend suggestions).
  - Saves mapping configurations.

- **xml-generator.js**
  - Handles XML generation requests.
  - Displays XML previews and download options.

- **app.js**
  - Initializes the application and sets up event listeners.
  - Manages application state and coordinates between modules.

---

### Step-by-Step User Flow

1. **Upload File**
   - User selects or drags a CSV/XLSX file.
   - JS validates file type/size, uploads to backend, and triggers parsing.

2. **Parse and Display Columns**
   - JS receives parsed columns/sample data and displays them for mapping.

3. **Load Schema**
   - JS requests schema from backend and displays available fields.

4. **Map Columns**
   - User maps source columns to schema fields.
   - JS can request auto-mapping suggestions from backend.

5. **Validate Data**
   - User triggers validation.
   - JS sends mapping and file info to backend, receives validation results, and displays errors/warnings.

6. **Generate and Download XML**
   - Once validation passes, user requests XML generation.
   - JS receives XML preview and download link.

---

See [ARCHITECTURE_CLASSES_DETAIL.md](ARCHITECTURE_CLASSES_DETAIL.md) for a full breakdown of every class, method, and API endpoint.
