import xmlschema
from lxml import etree
from pathlib import Path
from typing import List, Optional, Tuple
import os

from backend.models.schema_model import (
    XSDSchema,
    SchemaField,
    FieldType,
    Constraint,
    ConstraintType,
    ChoiceOption,
)


class XSDParser:
    """Parser for XSD schema files"""

    def __init__(self, schema_path: Path):
        self.schema_path = schema_path
        self.schema = None
        self.simple_types = {}
        self.complex_types = {}
        self._complex_type_nodes = {}  # lxml nodes, not serialized
        self.xs_namespace = "{http://www.w3.org/2001/XMLSchema}"
        self._cached_xsdschema: Optional[XSDSchema] = None
        self._cached_mtime: Optional[float] = None

    def parse(self) -> XSDSchema:
        """Parse the XSD schema and return structured representation, with caching."""

        mtime = os.path.getmtime(self.schema_path)
        if self._cached_xsdschema is not None and self._cached_mtime == mtime:
            return self._cached_xsdschema

        # Load schema with xmlschema for validation capabilities
        self.schema = xmlschema.XMLSchema(str(self.schema_path))

        # Also parse with lxml for detailed structure extraction
        # Make sure to disable external entity loading for security
        _safe_parser = etree.XMLParser(
            resolve_entities=False, no_network=True, load_dtd=False
        )
        tree = etree.parse(str(self.schema_path), _safe_parser)
        root = tree.getroot()

        # Extract simple types (enumerations, patterns, etc.)
        self._extract_simple_types(root)

        # Extract complex types
        self._extract_complex_types(root)

        # Find root element
        root_element_node = root.find(f".//{self.xs_namespace}element[@name]")
        root_element_name = (
            root_element_node.get("name") if root_element_node is not None else "MyBulk"
        )

        # Parse fields from root element
        fields = self._parse_element(root_element_node, root_element_name)

        # Count statistics
        total_fields, required_fields = self._count_fields(fields)

        xsdschema = XSDSchema(
            root_element=root_element_name,
            version=root.get("version"),
            fields=fields,
            simple_types=self.simple_types,
            complex_types=self.complex_types,
            total_fields=total_fields,
            required_fields=required_fields,
        )
        self._cached_xsdschema = xsdschema
        self._cached_mtime = mtime
        return xsdschema

    def _extract_simple_types(self, root):
        """Extract all simple type definitions"""
        simple_types = root.findall(f".//{self.xs_namespace}simpleType[@name]")

        for st in simple_types:
            type_name = st.get("name")
            type_info = {"base": None, "constraints": []}

            # Find restriction base
            restriction = st.find(f".//{self.xs_namespace}restriction")
            if restriction is not None:
                type_info["base"] = self._strip_namespace(restriction.get("base", ""))

                # Extract constraints
                type_info["constraints"] = self._extract_constraints(restriction)

            self.simple_types[type_name] = type_info

    def _extract_complex_types(self, root):
        """Extract all complex type definitions"""
        complex_types = root.findall(f".//{self.xs_namespace}complexType[@name]")

        for ct in complex_types:
            type_name = ct.get("name")
            self.complex_types[type_name] = {"structure": "complex"}
            self._complex_type_nodes[type_name] = ct

    def _extract_constraints(self, restriction_node) -> List[Constraint]:
        """Extract constraints from a restriction node"""
        constraints = []

        # Enumeration values
        enumerations = restriction_node.findall(f"./{self.xs_namespace}enumeration")
        if enumerations:
            enum_values = [enum.get("value") for enum in enumerations]
            constraints.append(
                Constraint(
                    type=ConstraintType.ENUMERATION,
                    value=enum_values,
                    description=f"{len(enum_values)} allowed values",
                )
            )

        # Pattern
        pattern = restriction_node.find(f"./{self.xs_namespace}pattern")
        if pattern is not None:
            constraints.append(
                Constraint(
                    type=ConstraintType.PATTERN,
                    value=pattern.get("value"),
                    description="Must match regex pattern",
                )
            )

        # Length constraints
        min_length = restriction_node.find(f"./{self.xs_namespace}minLength")
        if min_length is not None:
            constraints.append(
                Constraint(
                    type=ConstraintType.MIN_LENGTH,
                    value=int(min_length.get("value")),
                    description=f"Minimum length: {min_length.get('value')}",
                )
            )

        max_length = restriction_node.find(f"./{self.xs_namespace}maxLength")
        if max_length is not None:
            constraints.append(
                Constraint(
                    type=ConstraintType.MAX_LENGTH,
                    value=int(max_length.get("value")),
                    description=f"Maximum length: {max_length.get('value')}",
                )
            )

        # Numeric range constraints
        min_inclusive = restriction_node.find(f"./{self.xs_namespace}minInclusive")
        if min_inclusive is not None:
            val = min_inclusive.get("value")
            constraints.append(
                Constraint(
                    type=ConstraintType.MIN_INCLUSIVE,
                    value=float(val) if "." in val else int(val),
                    description=f"Minimum value: {val} (inclusive)",
                )
            )

        max_inclusive = restriction_node.find(f"./{self.xs_namespace}maxInclusive")
        if max_inclusive is not None:
            val = max_inclusive.get("value")
            constraints.append(
                Constraint(
                    type=ConstraintType.MAX_INCLUSIVE,
                    value=float(val) if "." in val else int(val),
                    description=f"Maximum value: {val} (inclusive)",
                )
            )

        min_exclusive = restriction_node.find(f"./{self.xs_namespace}minExclusive")
        if min_exclusive is not None:
            val = min_exclusive.get("value")
            constraints.append(
                Constraint(
                    type=ConstraintType.MIN_EXCLUSIVE,
                    value=float(val) if "." in val else int(val),
                    description=f"Minimum value: {val} (exclusive)",
                )
            )

        max_exclusive = restriction_node.find(f"./{self.xs_namespace}maxExclusive")
        if max_exclusive is not None:
            val = max_exclusive.get("value")
            constraints.append(
                Constraint(
                    type=ConstraintType.MAX_EXCLUSIVE,
                    value=float(val) if "." in val else int(val),
                    description=f"Maximum value: {val} (exclusive)",
                )
            )

        # Decimal precision constraints
        total_digits = restriction_node.find(f"./{self.xs_namespace}totalDigits")
        if total_digits is not None:
            constraints.append(
                Constraint(
                    type=ConstraintType.TOTAL_DIGITS,
                    value=int(total_digits.get("value")),
                    description=f"Total digits: {total_digits.get('value')}",
                )
            )

        fraction_digits = restriction_node.find(f"./{self.xs_namespace}fractionDigits")
        if fraction_digits is not None:
            constraints.append(
                Constraint(
                    type=ConstraintType.FRACTION_DIGITS,
                    value=int(fraction_digits.get("value")),
                    description=f"Fraction digits: {fraction_digits.get('value')}",
                )
            )

        return constraints

    def _parse_element(self, element_node, parent_path: str = "") -> List[SchemaField]:
        """Parse an element and its children recursively"""
        if element_node is None:
            return []

        fields = []

        # Check for complexType
        complex_type = element_node.find(f"./{self.xs_namespace}complexType")
        if complex_type is not None:
            # Check for sequence (direct child only, not recursive)
            sequence = complex_type.find(f"./{self.xs_namespace}sequence")
            if sequence is not None:
                for child in sequence.findall(f"./{self.xs_namespace}element"):
                    field = self._create_field_from_element(child, parent_path)
                    if field:
                        fields.append(field)

            # Check for choice (direct child only, not recursive)
            choice = complex_type.find(f"./{self.xs_namespace}choice")
            if choice is not None:
                field = self._create_choice_field(choice, parent_path)
                if field:
                    fields.append(field)

        return fields

    def _create_field_from_element(
        self, element_node, parent_path: str
    ) -> Optional[SchemaField]:
        """Create a SchemaField from an element node"""
        name = element_node.get("name")
        if not name:
            return None

        # Build full path
        path = f"{parent_path}.{name}" if parent_path else name

        # Get attributes
        type_attr = element_node.get("type")
        min_occurs = int(element_node.get("minOccurs", "1"))
        max_occurs_str = element_node.get("maxOccurs", "1")
        max_occurs = None if max_occurs_str == "unbounded" else int(max_occurs_str)
        default_value = element_node.get("default")
        nillable = element_node.get("nillable", "false").lower() == "true"

        # Determine if required
        required = min_occurs > 0

        # Determine field type and constraints
        field_type, base_type, constraints = self._determine_field_type(type_attr)

        # Check for nested complex type
        children = []
        complex_type = element_node.find(f"./{self.xs_namespace}complexType")
        if complex_type is not None:
            field_type = FieldType.COMPLEX
            children = self._parse_element(element_node, path)
        elif type_attr:
            type_name_ref = self._strip_namespace(type_attr)
            if type_name_ref in self._complex_type_nodes:
                node = self._complex_type_nodes[type_name_ref]
                if node is not None:
                    sequence = node.find(f"./{self.xs_namespace}sequence")
                    if sequence is not None:
                        for child_el in sequence.findall(
                            f"./{self.xs_namespace}element"
                        ):
                            child_field = self._create_field_from_element(
                                child_el, path
                            )
                            if child_field:
                                children.append(child_field)

        return SchemaField(
            name=name,
            path=path,
            type=field_type,
            base_type=base_type,
            required=required,
            min_occurs=min_occurs,
            max_occurs=max_occurs,
            default_value=default_value,
            nillable=nillable,
            constraints=constraints,
            children=children,
        )

    def _create_choice_field(
        self, choice_node, parent_path: str
    ) -> Optional[SchemaField]:
        """Create a choice field with multiple options"""
        # Choice itself doesn't have a name, we'll use parent's name or "Choice"
        choice_name = "Executor"  # This is specific to the schema structure

        path = f"{parent_path}.{choice_name}" if parent_path else choice_name

        # Parse each choice option
        options = []
        for element in choice_node.findall(f"./{self.xs_namespace}element"):
            option_name = element.get("name")
            option_path = f"{path}.{option_name}"

            # Parse fields for this option
            option_fields = []
            complex_type = element.find(f"./{self.xs_namespace}complexType")
            if complex_type is not None:
                sequence = complex_type.find(f"./{self.xs_namespace}sequence")
                if sequence is not None:
                    for child in sequence.findall(f"./{self.xs_namespace}element"):
                        field = self._create_field_from_element(child, option_path)
                        if field:
                            option_fields.append(field)
            else:
                # Simple type choice option
                field = self._create_field_from_element(element, path)
                if field:
                    option_fields = [field]

            options.append(
                ChoiceOption(name=option_name, path=option_path, fields=option_fields)
            )

        return SchemaField(
            name=choice_name,
            path=path,
            type=FieldType.COMPLEX,
            required=True,  # Choices are usually required
            is_choice=True,
            choice_options=options,
        )

    def _determine_field_type(
        self, type_attr: Optional[str]
    ) -> Tuple[FieldType, Optional[str], List[Constraint]]:
        """Determine field type and constraints from type attribute"""
        if not type_attr:
            return FieldType.STRING, None, []

        # Strip namespace prefix
        type_name = self._strip_namespace(type_attr)

        # Check if it's a custom simple type
        if type_name in self.simple_types:
            type_info = self.simple_types[type_name]
            base_type = type_info.get("base", "string")
            constraints = type_info.get("constraints", [])

            # Map XSD base type to our FieldType
            if base_type == "date":
                field_type = FieldType.DATE
            elif base_type == "time":
                field_type = FieldType.TIME
            elif base_type == "dateTime":
                field_type = FieldType.DATETIME
            elif base_type == "decimal":
                field_type = FieldType.DECIMAL
            elif base_type in [
                "integer",
                "int",
                "positiveInteger",
                "nonNegativeInteger",
            ]:
                field_type = FieldType.INTEGER
            elif base_type == "boolean":
                field_type = FieldType.BOOLEAN
            elif "string" in base_type:
                # Check if it has enumeration constraint
                has_enum = any(
                    c.type == ConstraintType.ENUMERATION for c in constraints
                )
                field_type = FieldType.ENUM if has_enum else FieldType.STRING
            else:
                field_type = FieldType.STRING

            return field_type, type_name, constraints

        # Check if it's a custom complex type
        if type_name in self.complex_types:
            return FieldType.COMPLEX, type_name, []

        # Standard XSD types
        if type_name == "date":
            return FieldType.DATE, None, []
        elif type_name == "time":
            return FieldType.TIME, None, []
        elif type_name == "dateTime":
            return FieldType.DATETIME, None, []
        elif type_name == "decimal":
            return FieldType.DECIMAL, None, []
        elif type_name in ["integer", "int", "positiveInteger", "nonNegativeInteger"]:
            return FieldType.INTEGER, None, []
        elif type_name == "boolean":
            return FieldType.BOOLEAN, None, []
        else:
            return FieldType.STRING, None, []

    def _strip_namespace(self, type_name: str) -> str:
        """Remove namespace prefix from type name"""
        if ":" in type_name:
            return type_name.split(":")[-1]
        return type_name.replace(self.xs_namespace, "")

    def _count_fields(
        self, fields: List[SchemaField], total: int = 0, required: int = 0
    ) -> Tuple[int, int]:
        """Recursively count total and required fields"""
        for field in fields:
            total += 1
            if field.required:
                required += 1
            if field.children:
                total, required = self._count_fields(field.children, total, required)
            if field.is_choice:
                for option in field.choice_options:
                    total, required = self._count_fields(option.fields, total, required)
        return total, required


# Per-path parser cache
_parser_cache: dict[Path, XSDParser] = {}


def get_parser(schema_path: Path) -> XSDParser:
    """Get or create a parser instance, cached per schema path."""
    if schema_path not in _parser_cache:
        _parser_cache[schema_path] = XSDParser(schema_path)
    return _parser_cache[schema_path]
