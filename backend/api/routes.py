from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Path as FastAPIPath,
    Body,
)
from fastapi.responses import FileResponse
from typing import List, Optional

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
    MappingSuggestionsResponse,
)
from backend.models.validation_model import ValidateDataRequest, ValidationResult
from backend.models.xml_model import GenerateXMLRequest, GenerateXMLResponse
from backend.utils.file_handler import FileHandler
from backend.config import OUTPUT_DIR, FORMAT_DIR, XSD_SCHEMA_PATH

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Ring Parser API is running"}


@router.get("/parsers")
async def list_parsers():
    """Return the file extensions supported by registered parsers."""
    return {"supported_extensions": sorted(supported_extensions())}


def _resolve_schema_path(schema_id: Optional[str]) -> Path:
    """Resolve a schema_id (filename) to a full path, defaulting to the built-in schema."""
    if schema_id:
        path = FORMAT_DIR / schema_id
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Schema '{schema_id}' not found")
        return path
    return XSD_SCHEMA_PATH


@router.get("/schema/list")
async def list_schemas():
    """Return all available XSD schema files from the format directory."""
    schemas = []
    for f in sorted(FORMAT_DIR.iterdir()):
        if f.is_file() and f.suffix in (".xsd", ".xml"):
            schemas.append({"id": f.name, "name": f.stem, "size": f.stat().st_size})
    return {"schemas": schemas}


@router.post("/schema/upload")
async def upload_schema(file: UploadFile = File(...)):
    """Upload a custom XSD schema file to the format directory."""
    if not file.filename or not (file.filename.endswith(".xsd") or file.filename.endswith(".xml")):
        raise HTTPException(status_code=400, detail="Only .xsd or .xml files are accepted")
    dest = FORMAT_DIR / file.filename
    content = await file.read()
    dest.write_bytes(content)
    return {"id": file.filename, "name": Path(file.filename).stem, "size": len(content)}


@router.post("/schema/parse", response_model=XSDSchema)
async def parse_schema(schema_id: Optional[str] = Body(None, embed=True)):
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


@router.post("/file/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a CSV or XLSX file for processing.

    Args:
        file: Uploaded file (CSV or XLSX)

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
async def parse_file(
    file_id: str = FastAPIPath(..., description="ID of uploaded file"),
    file_type: str = Body(..., embed=True, description="File type: CSV or XLSX"),
):
    """
    Parse uploaded file and extract columns/fields.

    Args:
        file_id: ID of the uploaded file
        file_type: Type of file

    Returns:
        Union[CSVParseResult, XLSXParseResult]: Parsed file data
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
async def create_mapping(request: CreateMappingRequest, schema_id: Optional[str] = Body(None, embed=True)):
    """
    Create or update column mapping configuration.

    Args:
        request: Mapping configuration request

    Returns:
        CreateMappingResponse with mapping ID and statistics
    """
    try:
        mapping_engine = get_mapping_engine()

        # Create/update mapping
        config = mapping_engine.create_mapping(
            file_id=request.file_id,
            file_type=request.file_type,
            mappings=request.mappings,
        )

        # Get schema to calculate required fields stats
        parser = get_parser(_resolve_schema_path(schema_id))
        schema = parser.parse()

        # Count required fields that are mapped
        mapped_paths = {m.target_path for m in request.mappings}
        required_fields_total = schema.required_fields

        # This is a simplified count - in production, traverse schema properly
        required_fields_mapped = len(
            [
                m
                for m in request.mappings
                if any(f.path == m.target_path and f.required for f in schema.fields)
            ]
        )

        return CreateMappingResponse(
            mapping_id=config.mapping_id,
            message="Mapping configuration saved successfully",
            total_mappings=len(request.mappings),
            required_fields_mapped=required_fields_mapped,
            required_fields_total=required_fields_total,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating mapping: {str(e)}")


@router.post("/mapping/suggest", response_model=MappingSuggestionsResponse)
async def suggest_mapping(
    source_columns: List[str] = Body(
        ..., embed=True, description="Source column names"
    ),
    threshold: float = Body(
        0.5, embed=True, description="Minimum confidence threshold (0.0-1.0)"
    ),
    schema_id: Optional[str] = Body(None, embed=True),
):
    """
    Auto-suggest column mappings based on field names similarity.

    Args:
        source_columns: List of source column names
        threshold: Minimum confidence threshold for suggestions

    Returns:
        MappingSuggestionsResponse with suggested mappings
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
async def validate_mapping(request: ValidateDataRequest):
    """
    Validate mapped data against XSD constraints.

    Args:
        request: Validation request with file_id, file_type, and mapping_id

    Returns:
        ValidationResult with validation messages and statistics
    """
    try:
        # Get file path
        file_path = FileHandler.get_upload_path(request.file_id, request.file_type)
        if not file_path:
            raise HTTPException(
                status_code=404, detail=f"File not found with ID: {request.file_id}"
            )

        # Parse file to get data
        file_data = await get_file_parser(request.file_type).parse_file(file_path)
        data_rows = file_data["data_rows"]
        headers = file_data["headers"]

        # Get mapping configuration
        mapping_engine = get_mapping_engine()
        mapping_config = mapping_engine.get_mapping(request.mapping_id)
        if not mapping_config:
            raise HTTPException(
                status_code=404,
                detail=f"Mapping not found with ID: {request.mapping_id}",
            )

        # Get schema
        parser = get_parser(_resolve_schema_path(request.schema_id))
        schema = parser.parse()

        # Validate
        validator = get_validator()
        result = validator.validate_data(
            data_rows=data_rows,
            headers=headers,
            mapping_config=mapping_config,
            schema=schema,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating data: {str(e)}")


@router.post("/xml/generate", response_model=GenerateXMLResponse)
async def generate_xml(request: GenerateXMLRequest):
    """
    Generate XML output from mapping configuration and source data.

    Args:
        request: XML generation request with file_id, file_type, and mapping_id

    Returns:
        GenerateXMLResponse with XML ID, preview, and statistics
    """
    try:
        # Get file path
        file_path = FileHandler.get_upload_path(request.file_id, request.file_type)
        if not file_path:
            raise HTTPException(
                status_code=404, detail=f"File not found with ID: {request.file_id}"
            )

        # Parse file to get data
        file_data = await get_file_parser(request.file_type).parse_file(file_path)
        data_rows = file_data["data_rows"]
        headers = file_data["headers"]
        total_rows = file_data["total_rows"]

        # Get mapping configuration
        mapping_engine = get_mapping_engine()
        mapping_config = mapping_engine.get_mapping(request.mapping_id)
        if not mapping_config:
            raise HTTPException(
                status_code=404,
                detail=f"Mapping not found with ID: {request.mapping_id}",
            )

        # Get schema
        parser = get_parser(_resolve_schema_path(request.schema_id))
        schema = parser.parse()

        # Generate XML
        xml_generator = get_xml_generator()
        xml_id, output_path, total_files = xml_generator.generate_xml(
            data_rows=data_rows,
            headers=headers,
            mapping_config=mapping_config,
            schema=schema,
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
async def download_xml(
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
