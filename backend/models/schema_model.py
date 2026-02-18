from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class FieldType(str, Enum):
    """XSD field types"""
    STRING = "string"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    DECIMAL = "decimal"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ENUM = "enum"
    COMPLEX = "complex"


class ConstraintType(str, Enum):
    """Types of constraints"""
    ENUMERATION = "enumeration"
    PATTERN = "pattern"
    MIN_LENGTH = "minLength"
    MAX_LENGTH = "maxLength"
    MIN_INCLUSIVE = "minInclusive"
    MAX_INCLUSIVE = "maxInclusive"
    MIN_EXCLUSIVE = "minExclusive"
    MAX_EXCLUSIVE = "maxExclusive"
    TOTAL_DIGITS = "totalDigits"
    FRACTION_DIGITS = "fractionDigits"


class Constraint(BaseModel):
    """Represents a validation constraint on a field"""
    type: ConstraintType
    value: Union[str, int, float, List[str]]
    description: Optional[str] = None


class ChoiceOption(BaseModel):
    """Represents one option in an xs:choice"""
    name: str
    path: str
    fields: List['SchemaField'] = Field(default_factory=list)
    description: Optional[str] = None


class SchemaField(BaseModel):
    """Represents a field in the XSD schema"""
    name: str
    path: str  # Full path like "MyBulk.Capture.Species"
    type: FieldType
    base_type: Optional[str] = None  # XSD type name like "tpSpecies"
    required: bool = False
    min_occurs: int = 0
    max_occurs: Optional[int] = 1
    default_value: Optional[str] = None
    nillable: bool = False
    constraints: List[Constraint] = Field(default_factory=list)
    description: Optional[str] = None

    # For complex types
    children: List['SchemaField'] = Field(default_factory=list)

    # For choice elements
    is_choice: bool = False
    choice_options: List[ChoiceOption] = Field(default_factory=list)


class XSDSchema(BaseModel):
    """Represents the complete parsed XSD schema"""
    root_element: str
    version: Optional[str] = None
    fields: List[SchemaField]= Field(default_factory=list)
    simple_types: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    complex_types: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    total_fields: int = 0
    required_fields: int = 0


# Allow forward references
SchemaField.model_rebuild()
ChoiceOption.model_rebuild()
