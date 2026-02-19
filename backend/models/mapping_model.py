from typing import List, Optional
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
