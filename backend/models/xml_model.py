from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class GenerateXMLRequest(BaseModel):
    """Request to generate XML output"""
    file_id: str
    file_type: str
    mapping_id: str
    schema_id: Optional[str] = None


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
