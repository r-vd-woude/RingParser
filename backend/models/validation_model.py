from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from backend.models.xml_model import AdvancedOverride


class ValidationSeverity(str, Enum):
    """Severity levels for validation messages"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationMessage(BaseModel):
    """Individual validation message"""
    field_path: str
    field_name: str
    severity: ValidationSeverity
    message: str
    constraint_type: Optional[str] = None
    actual_value: Optional[str] = None
    expected_value: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of validation"""
    is_valid: bool
    total_errors: int
    total_warnings: int
    messages: List[ValidationMessage] = Field(default_factory=list)
    validated_fields: int
    required_fields_missing: List[str] = Field(default_factory=list)


class ValidateDataRequest(BaseModel):
    """Request to validate mapped data"""
    file_id: str
    file_type: str
    mapping_id: str
    schema_id: Optional[str] = None
    advanced_overrides: List[AdvancedOverride] = Field(default_factory=list)
