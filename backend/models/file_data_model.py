from typing import List, Dict
from pydantic import BaseModel, Field


class ColumnInfo(BaseModel):
    """Information about a CSV column"""

    name: str
    index: int
    type: str
    sample_values: List[str] = Field(default_factory=list)


class ElementPathInfo(BaseModel):
    """Information about an XML element path"""

    path: str
    name: str
    type: str
    has_text: bool
    has_attributes: bool
    attributes: List[str] = Field(default_factory=list)


class RepeatingElementInfo(BaseModel):
    """Information about repeating XML elements"""

    path: str
    count: int
    name: str


class CSVParseResult(BaseModel):
    """Result of CSV file parsing"""

    filename: str
    encoding: str
    delimiter: str
    total_rows: int
    columns: List[ColumnInfo]
    sample_data: List[List[str]] = Field(default_factory=list)
    headers: List[str]


class XLSXParseResult(BaseModel):
    """Result of XLSX file parsing"""

    filename: str
    total_rows: int
    columns: List[ColumnInfo]
    sample_data: List = Field(default_factory=list)
    headers: List[str]


class FileUploadResponse(BaseModel):
    """Response after file upload"""

    file_id: str
    filename: str
    file_type: str  # "csv" or "xml"
    file_size: int
    upload_path: str
    message: str
