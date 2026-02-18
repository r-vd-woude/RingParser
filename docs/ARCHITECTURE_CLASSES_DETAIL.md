# RingParser: Detailed Class and Flow Documentation

## Backend Classes and Their Usage

### 1. CSVParser (`backend/services/csv_parser.py`)

- **Purpose:** Parses CSV files, auto-detects encoding and delimiter, extracts headers and data rows. Column type inference is delegated to `type_inference.py`.
- **Key Methods:**
  - `parse_file(file_path: Path)`: Reads the file, detects encoding/delimiter, parses rows, calls `_infer_column_types()`, and returns metadata and sample data.
  - `_detect_encoding(raw_content: bytes)`: Uses chardet to detect file encoding.
  - `_detect_delimiter(content: str)`: Uses csv.Sniffer and heuristics to detect delimiter (tries comma, semicolon, tab, pipe).
- **Usage:**
  - Instantiated via `get_csv_parser()` singleton accessor.
  - Used in API routes to parse uploaded CSV files and return structured data for mapping and validation.

### 2. XLSXParser (`backend/services/xlsx__parser.py`)

- **Purpose:** Parses XLSX files using openpyxl, extracts headers and data rows. Column type inference is delegated to `type_inference.py`.
- **Key Methods:**
  - `parse_file(file_path: Path)`: Loads the active workbook sheet, extracts headers from row 1 and data from row 2 onwards, calls `_infer_column_types()`, returns metadata and sample data.
- **Usage:**
  - Instantiated via `get_xlsx_parser()` singleton accessor.
  - Used in API routes to parse uploaded XLSX files for mapping and validation.

### 3. XSDParser (`backend/services/xsd_parser.py`)

- **Purpose:** Parses the XSD schema file, extracts field definitions, constraints, and structure.
- **Key Methods:**
  - `parse()`: Loads and parses the XSD, extracts simple/complex types, root element, and fields.
  - `_extract_simple_types`, `_extract_complex_types`, `_parse_element`, `_create_field_from_element`, etc.: Internal helpers for schema parsing.
- **Usage:**
  - Instantiated via `get_parser()` singleton accessor.
  - Used to provide schema structure for mapping, validation, and XML generation.

### 4. MappingEngine (`backend/services/mapping_engine.py`)

- **Purpose:** Manages column-to-field mappings, suggests mappings using name similarity and domain-specific logic.
- **Key Methods:**
  - `create_mapping(file_id, file_type, mappings)`: Creates or updates a mapping configuration.
  - `get_mapping(mapping_id)`: Retrieves a mapping configuration by ID.
  - `suggest_mappings(source_columns, schema, threshold)`: Suggests mappings based on similarity.
- **Usage:**
  - Instantiated via `get_mapping_engine()` singleton accessor.
  - Used in API routes for mapping creation, retrieval, and auto-suggestion.

### 5. Validator (`backend/services/validator.py`)

- **Purpose:** Validates mapped data against XSD constraints (type, required, pattern, enumeration, etc.).
- **Key Methods:**
  - `validate_data(data_rows, headers, mapping_config, schema)`: Validates data rows using mapping and schema, returns validation results.
  - Internal helpers for type and constraint validation.
- **Usage:**
  - Instantiated via `get_validator()` singleton accessor.
  - Used in API routes to validate mapped data before XML generation.

### 6. XMLGenerator (`backend/services/xml_generator.py`)

- **Purpose:** Generates XML output from mapped and validated data.
- **Key Methods:**
  - `generate_xml(data_rows, headers, mapping_config, schema)`: Builds XML structure, saves file, returns XML ID and path.
  - `get_xml_preview(file_path, lines)`: Returns a preview of the generated XML.
- **Usage:**
  - Instantiated via `get_xml_generator()` singleton accessor.
  - Used in API routes to generate and preview XML output.

### 7. Data Models (`backend/models/`)

- **Purpose:** Define Pydantic models for file data, mappings, validation, and XML generation.
- **Key models:**
  - `schema_model.py`: `FieldType`, `ConstraintType`, `Constraint`, `ChoiceOption`, `SchemaField`, `XSDSchema`
  - `mapping_model.py`: `FieldMapping`, `MappingConfiguration`, `MappingSuggestion`, `CreateMappingRequest`, `CreateMappingResponse`
  - `validation_model.py`: `ValidationSeverity`, `ValidationMessage`, `ValidationResult`, `ValidateDataRequest`
  - `xml_model.py`: `GenerateXMLRequest`, `GenerateXMLResponse`
  - `file_data_model.py`: `ColumnInfo`, `CSVParseResult`, `XLSXParseResult`, `FileUploadResponse`
- **Usage:**
  - Used for API request/response validation and serialization throughout the backend.

### 8. FileHandler (`backend/utils/file_handler.py`)

- **Purpose:** Handles all file upload storage and retrieval. All methods are static.
- **Key Methods:**
  - `save_upload_file(file)`: Validates extension (`.csv`, `.xlsx`, `.xls`) and size (10 MB max), generates a UUID-based filename, writes the file asynchronously via aiofiles, returns `(file_id, file_path)`.
  - `get_upload_path(file_id)`: Returns the `Path` to a previously uploaded file.
  - `delete_upload(file_id)`: Deletes an uploaded file from disk.
  - `get_file_type(file_id)`: Returns the file extension for a given file_id.
- **Usage:**
  - Called from `POST /api/file/upload` to persist the incoming upload before parsing.

### 9. Type Inference (`backend/utils/type_inference.py`)

- **Purpose:** Detects column data types from sample values. Used by both `CSVParser` and `XLSXParser`.
- **Key Functions:**
  - `_infer_column_types(headers, rows)`: Samples up to the first 20 rows per column and returns a list of column info dicts with `name`, `index`, `type`, and `sample_values`.
  - `_infer_type(values)`: Checks in order: integer → decimal → date → time → string.
  - `_is_integer()`, `_is_decimal()`, `_is_date()`, `_is_time()`: Individual type checkers. Uses `dateutil.parser` for flexible date/time detection. Handles the EURING special value `"----"` for missing time.

### 10. App & Config (`backend/app.py`, `backend/config.py`)

- **`backend/app.py`** — FastAPI application entry point:
  - Creates the FastAPI app instance with a `lifespan` context manager (startup/shutdown hooks).
  - Adds CORS middleware (all origins permitted for local development).
  - Mounts API routes with `/api` prefix.
  - Serves the `frontend/` directory as static files at the root path.

- **`backend/config.py`** — Centralised configuration:
  - Path constants: `BASE_DIR`, `DATA_DIR`, `UPLOAD_DIR`, `OUTPUT_DIR`, `FORMAT_DIR`, `XSD_SCHEMA_PATH`.
  - File limits: `MAX_UPLOAD_SIZE` (10 MB), `ALLOWED_EXTENSIONS` (`{".csv", ".xlsx", ".xls"}`).
  - Server settings: `HOST` (`127.0.0.1`), `PORT` (`8000`), `DEBUG` (`True`).
  - Auto-creates `UPLOAD_DIR` and `OUTPUT_DIR` on import.

### 11. API Routes (`backend/api/routes.py`)

All endpoints are mounted under `/api`. Each endpoint handles its own error responses.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check — returns `{status, message}` |
| POST | `/schema/parse` | Parse XSD schema → `XSDSchema` |
| POST | `/file/upload` | Upload CSV/XLSX file → `FileUploadResponse` |
| POST | `/file/parse/{file_id}` | Parse uploaded file → `CSVParseResult \| XLSXParseResult` |
| POST | `/mapping/create` | Create/update mapping config → `CreateMappingResponse` |
| POST | `/mapping/suggest` | Auto-suggest mappings → `MappingSuggestionsResponse` |
| POST | `/mapping/validate` | Validate mapped data → `ValidationResult` |
| POST | `/xml/generate` | Generate XML → `GenerateXMLResponse` |
| GET | `/xml/download/{xml_id}` | Download generated XML file |

---

## Backend File Parsing and Processing Flow

1. **File Upload**
   - User uploads a file via the frontend.
   - File is saved to `/data/uploads/`.

2. **File Parsing**
   - API route `/api/file/parse/{file_id}` is called with file type.
   - Uses `get_csv_parser()` or `get_xlsx_parser()` to parse the file.
   - Returns headers, sample data, and column info to the frontend.

3. **Schema Parsing**
   - `get_parser()` is used to parse the XSD schema.
   - Extracts all fields, constraints, and structure for mapping and validation.

4. **Mapping**
   - User maps columns to schema fields via the frontend.
   - Backend uses `MappingEngine` to store and suggest mappings.

5. **Validation**
   - `Validator` checks mapped data against schema constraints.
   - Returns detailed validation results to the frontend.

6. **XML Generation**
   - `XMLGenerator` builds XML from validated data and mapping.
   - XML file is saved and previewed; user can download it.

---

## Frontend JavaScript Modules and Their Roles

- **file-upload.js**: Handles file selection, drag-and-drop, upload, and parsing. Calls backend and displays file info.
- **schema-viewer.js**: Loads and displays schema fields/constraints. Handles validation requests and displays results.
- **column-mapper.js**: Manages mapping UI, supports auto-mapping, and saves mapping configurations.
- **xml-generator.js**: Handles XML generation requests, previews, and downloads.
- **app.js**: Initializes the app, sets up event listeners, and manages state.

---

## Example Usage Flow (End-to-End)

1. User uploads a CSV/XLSX file (handled by file-upload.js, sent to backend).
2. Backend parses file (CSVParser/XLSXParser), returns columns/sample data.
3. Frontend loads XSD schema (schema-viewer.js), displays fields.
4. User maps columns to schema fields (column-mapper.js, MappingEngine for suggestions).
5. User validates mapping (schema-viewer.js, Validator backend).
6. If valid, user generates XML (xml-generator.js, XMLGenerator backend).
7. User previews/downloads XML output.

---

For further details on any class, function, or flow, let me know!
