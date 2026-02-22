from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class FieldMapping(BaseModel):
    """Mapping between source column and target XSD field"""
    source_column: str
    source_index: Optional[int] = None
    target_path: str
    target_name: str
    confidence: Optional[float] = None  # For auto-suggestions (0.0 - 1.0)
    transformation: Optional[str] = None  # Future: data transformation rules


class MappingConfiguration(BaseModel):
    """Complete mapping configuration"""
    mapping_id: str
    file_id: str
    file_type: str  # csv or xml
    mappings: List[FieldMapping] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class MappingSuggestion(BaseModel):
    """Auto-suggested mapping"""
    source_column: str
    target_path: str
    target_name: str
    confidence: float
    reason: str  # Why this mapping was suggested


class MappingSuggestionsResponse(BaseModel):
    """Response containing mapping suggestions"""
    suggestions: List[MappingSuggestion]
    total_suggestions: int
    high_confidence_count: int  # confidence >= 0.8


class CreateMappingRequest(BaseModel):
    """Request to create/update mapping"""
    file_id: str
    file_type: str
    mappings: List[FieldMapping]
    schema_id: Optional[str] = None


class CreateMappingResponse(BaseModel):
    """Response after creating/updating mapping"""
    mapping_id: str
    message: str
    total_mappings: int
    required_fields_mapped: int
    required_fields_total: int


# ---------------------------------------------------------------------------
# Mapping export / import
# ---------------------------------------------------------------------------

class MappingExportEntry(BaseModel):
    """A single field entry in the portable export format."""
    source_column: str
    target_name: str


class MappingExportData(BaseModel):
    """Portable mapping export format — matches what the browser Save Mapping button produces.

    ``mappings`` keys are XSD target paths, e.g.
    ``"MyBulk.Capture.Species": {"source_column": "Species", "target_name": "Species"}``
    """
    schema_id: Optional[str] = None
    mappings: Dict[str, MappingExportEntry]


class ImportMappingRequest(BaseModel):
    """Request to import a previously exported mapping and associate it with an uploaded file."""
    file_id: str
    file_type: str
    mapping: MappingExportData
