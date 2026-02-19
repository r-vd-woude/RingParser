from typing import List, Dict
from pydantic import BaseModel, Field


class ColumnInfo(BaseModel):
    """Information about a CSV column"""

    name: str
    index: int
    type: str
    sample_values: List[str] = Field(default_factory=list)


class FileUploadResponse(BaseModel):
    """Response after file upload"""

    file_id: str
    filename: str
    file_type: str  # "csv" or "xml"
    file_size: int
    upload_path: str
    message: str
