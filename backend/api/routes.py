import asyncio
import json
import xmlschema

from fastapi import (
    APIRouter,
    Request,
    UploadFile,
    File,
    Form,
    HTTPException,
    Path as FastAPIPath,
    Body,
)
from fastapi.responses import FileResponse
from typing import List, Optional
from pathlib import Path
import uuid as uuid

from backend.services.xsd_parser import get_parser
from backend.services.parser_registry import get_file_parser, supported_extensions
from backend.services.mapping_engine import get_mapping_engine
from backend.services.validator import get_validator
from backend.services.xml_generator import get_xml_generator
from backend.models.schema_model import XSDSchema
from backend.models.file_data_model import FileUploadResponse
from backend.models.mapping_model import (
    CreateMappingRequest,
    CreateMappingResponse,
    FieldMapping,
    MappingSuggestionsResponse,
    MappingExportData,
    MappingExportEntry,
    ImportMappingRequest,
)
from backend.models.validation_model import ValidateDataRequest, ValidationResult
from backend.models.xml_model import (
    AdvancedOverride,
    GenerateXMLRequest,
    GenerateXMLResponse,
)
from backend.models.pipeline_model import PipelineResponse
from backend.utils.file_handler import FileHandler
from backend.config import (
    OUTPUT_DIR,
    FORMAT_DIR,
    MAX_UPLOAD_SIZE_SCHEMA,
    UPLOAD_LIMIT,
    DOWNLOAD_LIMIT,
    MAPPING_LIMIT,
    PARSE_LIMIT,
    INFO_LIMIT,
)
from backend.limiter import limiter

router = APIRouter()


@router.get("/health")
@limiter.limit(INFO_LIMIT)
async def health_check(
    request: Request,
):
    """Health check endpoint"""
    return {"status": "healthy", "message": "Ring Parser API is running"}


@router.get("/parsers")
@limiter.limit(INFO_LIMIT)
async def list_parsers(
    request: Request,
):
    """Return the file extensions supported by registered parsers."""
    return {"supported_extensions": sorted(supported_extensions())}


def _resolve_schema_path(schema_id: Optional[str]) -> Path:
    """Resolve a schema_id (filename) to a full path, defaulting to the first available schema."""
    if schema_id:
        path = FORMAT_DIR / schema_id
        if not path.exists():
            raise HTTPException(
                status_code=404, detail=f"Schema '{schema_id}' not found"
            )
        return path
    for f in sorted(FORMAT_DIR.iterdir()):
        if f.is_file() and f.suffix in (".xsd", ".xml"):
            return f
    raise HTTPException(status_code=404, detail="No schema files available")


@router.get("/schema/list")
@limiter.limit(INFO_LIMIT)
async def list_schemas(
    request: Request,
):
    """Return all available XSD schema files from the format directory."""
    schemas = []
    for f in sorted(FORMAT_DIR.iterdir()):
        if f.is_file() and f.suffix in (".xsd", ".xml"):
            schemas.append({"id": f.name, "name": f.stem, "size": f.stat().st_size})
    return {"schemas": schemas}


@router.post("/schema/upload")
@limiter.limit(UPLOAD_LIMIT)
async def upload_schema(request: Request, file: UploadFile = File(...)):
    """Upload a custom XSD schema file to the format directory."""
    if not file.filename or not (
        file.filename.endswith(".xsd") or file.filename.endswith(".xml")
    ):
        raise HTTPException(
            status_code=400, detail="Only .xsd or .xml files are accepted"
        )
    if "/" in file.filename or "\\" in file.filename:
        raise HTTPException(
            status_code=400, detail="Filename must not contain path separators"
        )
    safe_name = Path(file.filename).name
    dest = FORMAT_DIR / safe_name
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_SCHEMA:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE_SCHEMA / 1024:.0f}KB",
        )
    dest.write_bytes(content)
    try:
        xmlschema.XMLSchema(str(dest))
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400, detail=f"Invalid or unreadable schema file: {e}"
        )
    return {"id": file.filename, "name": Path(file.filename).stem, "size": len(content)}


@router.post("/schema/parse", response_model=XSDSchema)
@limiter.limit(PARSE_LIMIT)
async def parse_schema(
    request: Request, schema_id: Optional[str] = Body(None, embed=True)
):
    """
    Parse the XSD schema file and return structured representation.

    Returns:
        XSDSchema: Complete schema structure with fields, types, and constraints
    """
    try:
        schema_path = _resolve_schema_path(schema_id)
        parser = get_parser(schema_path)
        schema = parser.parse()
        return schema
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error parsing XSD schema: {str(e)}"
        )


def _collect_leaf_fields(fields, result, include_biometrics: bool):
    """Recursively collect leaf (non-complex) schema fields.

    Mirrors the frontend ``getLeafFields`` logic:
    - Skips the ``ProjectIDRingerNumber`` choice option (only ActingUserProjectID is used).
    - Optionally excludes Biometrics fields.
    """
    for field in fields:
        is_complex = bool(field.children) or field.is_choice
        if not is_complex:
            if not include_biometrics and "Biometrics" in field.path:
                pass  # skip
            else:
                result.append(
                    {
                        "name": field.name,
                        "path": field.path,
                        "required": field.required,
                    }
                )
        if field.children:
            _collect_leaf_fields(field.children, result, include_biometrics)
        if field.is_choice and field.choice_options:
            for option in field.choice_options:
                if option.name == "ProjectIDRingerNumber":
                    continue
                if option.fields:
                    _collect_leaf_fields(option.fields, result, include_biometrics)


@router.get("/schema/leaf-fields")
@limiter.limit(INFO_LIMIT)
async def get_leaf_fields(
    request: Request,
    schema_id: Optional[str] = None,
    include_biometrics: bool = False,
):
    """Return a flat list of leaf (non-complex) XSD fields.

    Useful for R scripts that need to know which fields exist and which are
    required without having to traverse the full nested schema tree.

    Query params:
    - ``schema_id``: filename of the schema (defaults to first available).
    - ``include_biometrics``: include Biometrics fields (default ``false``).
    """
    try:
        schema_path = _resolve_schema_path(schema_id)
        parser = get_parser(schema_path)
        schema = parser.parse()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing schema: {str(e)}")

    fields: list = []
    _collect_leaf_fields(schema.fields, fields, include_biometrics)
    return {
        "schema_id": schema_id or schema_path.name,
        "fields": fields,
        "total": len(fields),
    }


@router.post("/file/upload", response_model=FileUploadResponse)
@limiter.limit(UPLOAD_LIMIT)
async def upload_file(request: Request, file: UploadFile = File(...)):
    """
    Upload a supported file for processing.

    Args:
        file: Uploaded file

    Returns:
        FileUploadResponse with file information and upload ID
    """
    try:
        # Save the uploaded file
        file_id, file_path = await FileHandler.save_upload_file(file)

        # Get file info
        file_type = FileHandler.get_file_type(file.filename or "")
        file_size = file_path.stat().st_size

        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename or "unknown",
            file_type=file_type,
            file_size=file_size,
            upload_path=str(file_path),
            message=f"File uploaded successfully with ID: {file_id}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@router.post("/file/parse/{file_id}")
@limiter.limit(PARSE_LIMIT)
async def parse_file(
    request: Request,
    file_id: str = FastAPIPath(..., description="ID of uploaded file"),
    file_type: str = Body(..., embed=True, description="File type: CSV or XLSX"),
):
    """
    Parse uploaded file and extract columns/fields.

    Args:
        file_id: ID of the uploaded file
        file_type: Type of file

    Returns:
        Parsed file data
    """
    try:
        # Get file path
        file_path = FileHandler.get_upload_path(file_id, file_type)
        if not file_path:
            raise HTTPException(
                status_code=404, detail=f"File not found with ID: {file_id}"
            )

        # Parse using the registry — no if/elif needed when adding new parsers
        parser = get_file_parser(file_type)
        return await parser.parse_file(file_path)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing file: {str(e)}")


@router.post("/mapping/create", response_model=CreateMappingResponse)
@limiter.limit(MAPPING_LIMIT)
async def create_mapping(request: Request, body: CreateMappingRequest):
    """
    Create or update column mapping configuration.

    Args:
        request: Mapping configuration request

    Returns:
        CreateMappingResponse with mapping ID and statistics
    """
    try:
        mapping_engine = get_mapping_engine()

        # Create/update mapping — this must always succeed
        config = mapping_engine.create_mapping(
            file_id=body.file_id,
            file_type=body.file_type,
            mappings=body.mappings,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating mapping: {str(e)}")

    # Schema stats are optional — a parsing failure must not prevent returning mapping_id
    required_fields_total = 0
    required_fields_mapped = 0
    try:
        parser = get_parser(_resolve_schema_path(body.schema_id))
        schema = parser.parse()
        required_fields_total = schema.required_fields
        required_fields_mapped = len(
            [
                m
                for m in body.mappings
                if any(f.path == m.target_path and f.required for f in schema.fields)
            ]
        )
    except Exception:
        pass  # stats failure is non-fatal

    return CreateMappingResponse(
        mapping_id=config.mapping_id,
        message="Mapping configuration saved successfully",
        total_mappings=len(body.mappings),
        required_fields_mapped=required_fields_mapped,
        required_fields_total=required_fields_total,
    )


@router.post("/mapping/suggest", response_model=MappingSuggestionsResponse)
@limiter.limit(MAPPING_LIMIT)
async def suggest_mapping(
    request: Request,
    source_columns: List[str] = Body(
        ..., embed=True, description="Source column names"
    ),
    threshold: float = Body(
        0.5, embed=True, description="Minimum confidence threshold (0.0-1.0)"
    ),
    schema_id: Optional[str] = Body(None, embed=True),
    exclude_biometrics: bool = Body(
        True,
        embed=True,
        description="Exclude Biometrics fields from suggestions (default true). "
        "Users opt in to biometric mapping manually.",
    ),
):
    """
    Auto-suggest column mappings based on field name similarity.

    ``ProjectIDRingerNumber`` fields are always excluded (only
    ``ActingUserProjectID`` is used). Biometrics fields are excluded by default
    and must be opted in via ``exclude_biometrics=false``.
    """
    try:
        # Get schema
        parser = get_parser(_resolve_schema_path(schema_id))
        schema = parser.parse()

        # Get mapping engine and generate suggestions
        mapping_engine = get_mapping_engine()
        suggestions = mapping_engine.suggest_mappings(
            source_columns=source_columns, schema=schema, threshold=threshold
        )

        # Apply server-side filters so callers (frontend and R scripts) get
        # the same clean list without needing their own post-processing.
        if exclude_biometrics:
            suggestions = [s for s in suggestions if "Biometrics" not in s.target_path]

        # Count high confidence suggestions
        high_confidence = len([s for s in suggestions if s.confidence >= 0.8])

        return MappingSuggestionsResponse(
            suggestions=suggestions,
            total_suggestions=len(suggestions),
            high_confidence_count=high_confidence,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating suggestions: {str(e)}"
        )


@router.post("/mapping/validate", response_model=ValidationResult)
@limiter.limit(MAPPING_LIMIT)
async def validate_mapping(request: Request, body: ValidateDataRequest):
    """
    Validate mapped data against XSD constraints.

    Args:
        request: Validation request with file_id, file_type, and mapping_id

    Returns:
        ValidationResult with validation messages and statistics
    """
    try:
        # Get file path
        file_path = FileHandler.get_upload_path(body.file_id, body.file_type)
        if not file_path:
            raise HTTPException(
                status_code=404, detail=f"File not found with ID: {body.file_id}"
            )

        # Parse file to get data
        file_data = await get_file_parser(body.file_type).parse_file(file_path)
        data_rows = file_data["data_rows"]
        headers = file_data["headers"]

        # Get mapping configuration
        mapping_engine = get_mapping_engine()
        mapping_config = mapping_engine.get_mapping(body.mapping_id)
        if not mapping_config:
            raise HTTPException(
                status_code=404,
                detail=f"Mapping not found with ID: {body.mapping_id}",
            )

        # Get schema
        parser = get_parser(_resolve_schema_path(body.schema_id))
        schema = parser.parse()

        # Validate (pass overrides so required-field check accounts for them)
        validator = get_validator()
        result = await asyncio.to_thread(
            validator.validate_data,
            data_rows,
            headers,
            mapping_config,
            schema,
            body.advanced_overrides or None,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating data: {str(e)}")


@router.get("/mapping/{mapping_id}/export", response_model=MappingExportData)
@limiter.limit(DOWNLOAD_LIMIT)
async def export_mapping(
    request: Request,
    mapping_id: str = FastAPIPath(..., description="ID of the saved mapping to export"),
):
    """Export a saved mapping configuration as portable JSON.

    The response can be saved to a ``.json`` file and later passed to
    ``POST /api/mapping/import`` or the browser *Load mapping* button.
    """
    engine = get_mapping_engine()
    config = engine.get_mapping(mapping_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Mapping not found: {mapping_id}")

    mappings = {
        m.target_path: MappingExportEntry(
            source_column=m.source_column,
            target_name=m.target_name,
        )
        for m in config.mappings
    }
    return MappingExportData(mappings=mappings)


@router.post("/mapping/import", response_model=CreateMappingResponse)
@limiter.limit(UPLOAD_LIMIT)
async def import_mapping(request: Request, body: ImportMappingRequest):
    """Import a previously exported mapping JSON and associate it with an uploaded file.

    Typical R-script usage::

        mapping_json <- jsonlite::read_json("my_mapping.json")
        httr::POST(".../api/mapping/import",
                   body = list(file_id = file_id,
                               file_type = "csv",
                               mapping = mapping_json),
                   encode = "json")
    """
    field_mappings = [
        FieldMapping(
            source_column=entry.source_column,
            target_path=target_path,
            target_name=entry.target_name,
            confidence=1.0,
        )
        for target_path, entry in body.mapping.mappings.items()
        if "ProjectIDRingerNumber" not in target_path
    ]

    try:
        engine = get_mapping_engine()
        config = engine.create_mapping(
            file_id=body.file_id,
            file_type=body.file_type,
            mappings=field_mappings,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error importing mapping: {str(e)}"
        )

    return CreateMappingResponse(
        mapping_id=config.mapping_id,
        message="Mapping imported successfully",
        total_mappings=len(field_mappings),
        required_fields_mapped=0,
        required_fields_total=0,
    )


@router.post("/pipeline/run", response_model=PipelineResponse)
@limiter.limit(PARSE_LIMIT)
async def run_pipeline(
    request: Request,
    file: UploadFile = File(..., description="Data file to process (CSV, XLSX, etc.)"),
    schema_id: Optional[str] = Form(
        None, description="Schema filename (defaults to first available)"
    ),
    mapping_json: Optional[str] = Form(
        None,
        description="JSON string of a previously exported mapping "
        "(same format as GET /api/mapping/{id}/export). "
        "If omitted, mappings are auto-suggested from column names.",
    ),
    date_format: str = Form(
        "ISO", description="Date output format: 'ISO' (YYYY-MM-DD) or 'DDMMYYYY'"
    ),
    advanced_overrides_json: Optional[str] = Form(
        None,
        description="JSON array of overrides, e.g. "
        '[{"field_name":"Modus","static_value":"Insert"}]',
    ),
    threshold: float = Form(
        0.5, description="Minimum confidence for auto-mapping (0.0–1.0)"
    ),
    exclude_biometrics: bool = Form(
        True, description="Exclude Biometrics fields from auto-mapping"
    ),
):
    """Run the full pipeline in a single request: upload → parse → map → generate XML.

    Typical R-script usage::

        library(httr)
        res <- POST(
          "http://localhost:8000/api/pipeline/run",
          body = list(
            file               = upload_file("rings.csv"),
            schema_id          = "griel_bulkupload.xml",
            mapping_json       = readLines("my_mapping.json", warn = FALSE),
            date_format        = "ISO"
          ),
          encode = "multipart"
        )
        xml_id <- content(res)$xml_id
        GET(paste0("http://localhost:8000/api/xml/download/", xml_id),
            write_disk("output.xml"))
    """
    try:
        # 1. Save uploaded file
        file_id, file_path = await FileHandler.save_upload_file(file)
        file_type = FileHandler.get_file_type(file.filename or "")

        # 2. Parse file
        file_parser = get_file_parser(file_type)
        file_data = await file_parser.parse_file(file_path)
        data_rows = file_data["data_rows"]
        headers = file_data["headers"]
        total_rows = file_data["total_rows"]

        # 3. Resolve schema (prefer explicit param, then schema_id inside mapping_json)
        effective_schema_id = schema_id
        if not effective_schema_id and mapping_json:
            try:
                mj = json.loads(mapping_json)
                effective_schema_id = mj.get("schema_id")
            except Exception:
                pass
        schema_path = _resolve_schema_path(effective_schema_id)
        xsd_parser = get_parser(schema_path)
        schema = xsd_parser.parse()

        # 4. Build mapping — from provided JSON or auto-suggest
        engine = get_mapping_engine()
        if mapping_json:
            mj = json.loads(mapping_json)
            field_mappings = [
                FieldMapping(
                    source_column=v["source_column"],
                    target_path=k,
                    target_name=v.get("target_name", k.split(".")[-1]),
                    confidence=1.0,
                )
                for k, v in mj.get("mappings", {}).items()
                if "ProjectIDRingerNumber" not in k
                and (not exclude_biometrics or "Biometrics" not in k)
            ]
        else:
            suggestions = engine.suggest_mappings(
                source_columns=headers,
                schema=schema,
                threshold=threshold,
            )
            field_mappings = [
                FieldMapping(
                    source_column=s.source_column,
                    target_path=s.target_path,
                    target_name=s.target_name,
                    confidence=s.confidence,
                )
                for s in suggestions
                if "ProjectIDRingerNumber" not in s.target_path
                and (not exclude_biometrics or "Biometrics" not in s.target_path)
            ]

        mapping_config = engine.create_mapping(
            file_id=file_id,
            file_type=file_type,
            mappings=field_mappings,
        )

        # 5. Parse advanced overrides
        overrides: List[AdvancedOverride] = []
        if advanced_overrides_json:
            try:
                raw = json.loads(advanced_overrides_json)
                overrides = [AdvancedOverride(**item) for item in raw]
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"Invalid advanced_overrides_json: {e}"
                )

        # 6. Generate XML
        xml_gen = get_xml_generator()
        xml_id, output_path, total_files = await asyncio.to_thread(
            xml_gen.generate_xml,
            data_rows,
            headers,
            mapping_config,
            schema,
            overrides,
            date_format,
        )

        preview = xml_gen.get_xml_preview(output_path, lines=50)
        file_size = output_path.stat().st_size

        return PipelineResponse(
            xml_id=xml_id,
            download_url=f"/api/xml/download/{xml_id}",
            file_id=file_id,
            mapping_id=mapping_config.mapping_id,
            filename=output_path.name,
            total_rows=total_rows,
            total_files=total_files,
            file_size=file_size,
            preview=preview,
            message=f"Pipeline completed: {total_files} file(s) containing {total_rows} Capture elements",
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@router.post("/xml/generate", response_model=GenerateXMLResponse)
@limiter.limit(UPLOAD_LIMIT)
async def generate_xml(request: Request, body: GenerateXMLRequest):
    """
    Generate XML output from mapping configuration and source data.

    Args:
        request: XML generation request with file_id, file_type, and mapping_id

    Returns:
        GenerateXMLResponse with XML ID, preview, and statistics
    """
    try:
        # Get file path
        file_path = FileHandler.get_upload_path(body.file_id, body.file_type)
        if not file_path:
            raise HTTPException(
                status_code=404, detail=f"File not found with ID: {body.file_id}"
            )

        # Parse file to get data
        file_data = await get_file_parser(body.file_type).parse_file(file_path)
        data_rows = file_data["data_rows"]
        headers = file_data["headers"]
        total_rows = file_data["total_rows"]

        # Get mapping configuration
        mapping_engine = get_mapping_engine()
        mapping_config = mapping_engine.get_mapping(body.mapping_id)
        if not mapping_config:
            raise HTTPException(
                status_code=404,
                detail=f"Mapping not found with ID: {body.mapping_id}",
            )

        # Get schema
        parser = get_parser(_resolve_schema_path(body.schema_id))
        schema = parser.parse()

        # Generate XML
        xml_generator = get_xml_generator()
        xml_id, output_path, total_files = await asyncio.to_thread(
            xml_generator.generate_xml,
            data_rows,
            headers,
            mapping_config,
            schema,
            body.advanced_overrides,
            body.date_format,
        )

        # Get preview
        preview = xml_generator.get_xml_preview(output_path, lines=50)

        # Get file size
        file_size = output_path.stat().st_size

        message = f"XML generated successfully: {total_files} file(s) containing {total_rows} Capture elements"

        return GenerateXMLResponse(
            xml_id=xml_id,
            filename=output_path.name,
            preview=preview,
            total_rows=total_rows,
            total_files=total_files,
            file_size=file_size,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating XML: {str(e)}")


@router.get("/xml/download/{xml_id}")
@limiter.limit(DOWNLOAD_LIMIT)
async def download_xml(
    request: Request,
    xml_id: str = FastAPIPath(..., description="ID of generated XML"),
):
    """
    Download generated XML file.

    Args:
        xml_id: ID of the generated XML file

    Returns:
        FileResponse with XML file
    """
    try:
        uuid.UUID(xml_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid XML ID")

    try:
        zip_file = OUTPUT_DIR / f"{xml_id}.zip"
        xml_file = OUTPUT_DIR / f"{xml_id}.xml"

        if zip_file.exists():
            return FileResponse(
                path=str(zip_file),
                media_type="application/zip",
                filename=f"bird_ringing_data_{xml_id}.zip",
            )
        elif xml_file.exists():
            return FileResponse(
                path=str(xml_file),
                media_type="application/xml",
                filename=f"bird_ringing_data_{xml_id}.xml",
            )
        else:
            raise HTTPException(
                status_code=404, detail=f"XML file not found with ID: {xml_id}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading XML: {str(e)}")
