from pydantic import BaseModel, Field
from datetime import datetime


class PipelineResponse(BaseModel):
    """Response from the single-call pipeline endpoint."""
    xml_id: str
    download_url: str   # e.g. /api/xml/download/{xml_id}
    file_id: str
    mapping_id: str
    filename: str
    total_rows: int
    total_files: int
    file_size: int
    preview: str        # First 50 lines of the generated XML
    message: str
    created_at: datetime = Field(default_factory=datetime.now)
