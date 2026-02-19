from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class AdvancedOverride(BaseModel):
    """Override for a hardcoded field in the XML generator.

    Exactly one of static_value or source_column should be set.
    """
    field_name: str
    static_value: Optional[str] = None
    source_column: Optional[str] = None


class GenerateXMLRequest(BaseModel):
    """Request to generate XML output"""
    file_id: str
    file_type: str
    mapping_id: str
    schema_id: Optional[str] = None
    advanced_overrides: List[AdvancedOverride] = []


class GenerateXMLResponse(BaseModel):
    """Response after generating XML"""
    xml_id: str
    filename: str
    preview: str  # First 50 lines of XML (from first file if zipped)
    total_rows: int
    total_files: int
    file_size: int
    message: str
    created_at: datetime = Field(default_factory=datetime.now)
