from typing import List, Dict, Any, Optional
import re
from datetime import datetime, date, time
from decimal import Decimal, InvalidOperation

from backend.models.validation_model import (
    ValidationResult,
    ValidationMessage,
    ValidationSeverity,
)
from backend.models.schema_model import XSDSchema, SchemaField, ConstraintType
from backend.models.mapping_model import MappingConfiguration
from backend.config import HARDCODED_FIELD_NAMES
from backend.utils.ring_number import format_ring_number


class Validator:
    """Validator for data against XSD schema constraints"""

    def __init__(self):
        pass

    def validate_data(
        self,
        data_rows: List[List[str]],
        headers: List[str],
        mapping_config: MappingConfiguration,
        schema: XSDSchema,
    ) -> ValidationResult:
        """
        Validate data rows against XSD schema using mapping configuration.

        Args:
            data_rows: List of data rows (from CSV or XML)
            headers: Column headers
            mapping_config: Mapping configuration
            schema: XSD schema

        Returns:
            ValidationResult with validation messages
        """
        messages = []
        validated_fields = 0

        # Create mapping lookup: column_name -> target_path
        column_to_target = {
            m.source_column: m.target_path for m in mapping_config.mappings
        }

        # Build field lookup: path -> SchemaField
        field_lookup = self._build_field_lookup(schema.fields)

        # Check required fields are mapped
        required_fields_missing = self._check_required_fields(
            mapping_config, schema.fields
        )

        # Validate each row
        for row_idx, row in enumerate(
            data_rows[:10], start=1
        ):  # Validate first 10 rows
            # Validate each mapped column
            for col_idx, header in enumerate(headers):
                if header not in column_to_target:
                    continue  # Skip unmapped columns

                target_path = column_to_target[header]
                target_field = field_lookup.get(target_path)

                if not target_field:
                    continue

                # Get cell value
                raw = row[col_idx] if col_idx < len(row) else None
                value = str(raw).strip() if raw is not None else ""

                # Format ring number before validation
                if target_path.endswith("RingNumber"):
                    value = format_ring_number(value)

                # Skip empty values for optional fields
                if not value and not target_field.required:
                    continue

                # Validate required fields
                if not value and target_field.required:
                    messages.append(
                        ValidationMessage(
                            field_path=target_path,
                            field_name=target_field.name,
                            severity=ValidationSeverity.ERROR,
                            message=f"Required field is empty (row {row_idx})",
                            constraint_type="required",
                            actual_value=value,
                        )
                    )
                    continue

                # Validate data type
                type_messages = self._validate_type(value, target_field, row_idx)
                messages.extend(type_messages)

                # Validate constraints
                constraint_messages = self._validate_constraints(
                    value, target_field, row_idx
                )
                messages.extend(constraint_messages)

                validated_fields += 1

        # Count errors and warnings
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]

        return ValidationResult(
            is_valid=len(errors) == 0,
            total_errors=len(errors),
            total_warnings=len(warnings),
            messages=messages,
            validated_fields=validated_fields,
            required_fields_missing=required_fields_missing,
        )

    def _build_field_lookup(
        self, fields: List[SchemaField], lookup: Optional[Dict[str, SchemaField]] = None
    ) -> Dict[str, SchemaField]:
        """Build a lookup dictionary of path -> SchemaField"""
        if lookup is None:
            lookup = {}

        for field in fields:
            lookup[field.path] = field

            if field.children:
                self._build_field_lookup(field.children, lookup)

            if field.is_choice and field.choice_options:
                for option in field.choice_options:
                    if option.fields:
                        self._build_field_lookup(option.fields, lookup)

        return lookup

    def _check_required_fields(
        self, mapping_config: MappingConfiguration, fields: List[SchemaField]
    ) -> List[str]:
        """Check which required fields are not mapped"""
        mapped_paths = {m.target_path for m in mapping_config.mappings}
        required_fields = []

        def check_fields(schema_fields):
            for field in schema_fields:
                if field.required and field.path not in mapped_paths:
                    # Skip complex types and fields that are hardcoded in the generator
                    if not field.children and not field.is_choice:
                        if field.name not in HARDCODED_FIELD_NAMES:
                            required_fields.append(field.path)

                if field.children:
                    check_fields(field.children)

        check_fields(fields)
        return required_fields

    def _validate_type(
        self, value: str, field: SchemaField, row_idx: int
    ) -> List[ValidationMessage]:
        """Validate data type"""
        messages = []

        if field.type == "date":
            if not self._is_valid_date(value):
                messages.append(
                    ValidationMessage(
                        field_path=field.path,
                        field_name=field.name,
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid date format (row {row_idx})",
                        constraint_type="type",
                        actual_value=value,
                        expected_value="YYYY-MM-DD",
                    )
                )

        elif field.type == "time":
            if not self._is_valid_time(value):
                messages.append(
                    ValidationMessage(
                        field_path=field.path,
                        field_name=field.name,
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid time format (row {row_idx})",
                        constraint_type="type",
                        actual_value=value,
                        expected_value="HH:MM:SS or special format",
                    )
                )

        elif field.type == "decimal":
            if not self._is_valid_decimal(value):
                messages.append(
                    ValidationMessage(
                        field_path=field.path,
                        field_name=field.name,
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid decimal number (row {row_idx})",
                        constraint_type="type",
                        actual_value=value,
                        expected_value="Decimal number",
                    )
                )

        elif field.type == "integer":
            if not self._is_valid_integer(value):
                messages.append(
                    ValidationMessage(
                        field_path=field.path,
                        field_name=field.name,
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid integer (row {row_idx})",
                        constraint_type="type",
                        actual_value=value,
                        expected_value="Integer number",
                    )
                )

        return messages

    def _validate_constraints(
        self, value: str, field: SchemaField, row_idx: int
    ) -> List[ValidationMessage]:
        """Validate field constraints"""
        messages = []

        for constraint in field.constraints:
            if constraint.type == ConstraintType.ENUMERATION:
                if value not in constraint.value:
                    allowed = constraint.value
                    if len(allowed) > 20:
                        allowed_str = (
                            ", ".join(str(v) for v in allowed[:20])
                            + f", … ({len(allowed)} total)"
                        )
                    else:
                        allowed_str = ", ".join(str(v) for v in allowed)
                    messages.append(
                        ValidationMessage(
                            field_path=field.path,
                            field_name=field.name,
                            severity=ValidationSeverity.ERROR,
                            message=f"Value not in allowed list (row {row_idx})",
                            constraint_type="enumeration",
                            actual_value=value,
                            expected_value=f"Allowed: {allowed_str}",
                        )
                    )

            elif constraint.type == ConstraintType.PATTERN:
                pattern = constraint.value
                if not re.match(f"^{pattern}$", value):
                    messages.append(
                        ValidationMessage(
                            field_path=field.path,
                            field_name=field.name,
                            severity=ValidationSeverity.ERROR,
                            message=f"Value does not match required pattern (row {row_idx})",
                            constraint_type="pattern",
                            actual_value=value,
                            expected_value=f"Pattern: {pattern[:50]}",
                        )
                    )

            elif constraint.type == ConstraintType.MIN_LENGTH:
                if len(value) < constraint.value:
                    messages.append(
                        ValidationMessage(
                            field_path=field.path,
                            field_name=field.name,
                            severity=ValidationSeverity.ERROR,
                            message=f"Value too short (row {row_idx})",
                            constraint_type="minLength",
                            actual_value=f"{len(value)} chars",
                            expected_value=f"At least {constraint.value} chars",
                        )
                    )

            elif constraint.type == ConstraintType.MAX_LENGTH:
                if len(value) > constraint.value:
                    messages.append(
                        ValidationMessage(
                            field_path=field.path,
                            field_name=field.name,
                            severity=ValidationSeverity.ERROR,
                            message=f"Value too long (row {row_idx})",
                            constraint_type="maxLength",
                            actual_value=f"{len(value)} chars",
                            expected_value=f"At most {constraint.value} chars",
                        )
                    )

            elif constraint.type == ConstraintType.MIN_INCLUSIVE:
                try:
                    num_value = float(value)
                    if num_value < constraint.value:
                        messages.append(
                            ValidationMessage(
                                field_path=field.path,
                                field_name=field.name,
                                severity=ValidationSeverity.ERROR,
                                message=f"Value below minimum (row {row_idx})",
                                constraint_type="minInclusive",
                                actual_value=value,
                                expected_value=f">= {constraint.value}",
                            )
                        )
                except ValueError:
                    pass

            elif constraint.type == ConstraintType.MAX_INCLUSIVE:
                try:
                    num_value = float(value)
                    if num_value > constraint.value:
                        messages.append(
                            ValidationMessage(
                                field_path=field.path,
                                field_name=field.name,
                                severity=ValidationSeverity.ERROR,
                                message=f"Value above maximum (row {row_idx})",
                                constraint_type="maxInclusive",
                                actual_value=value,
                                expected_value=f"<= {constraint.value}",
                            )
                        )
                except ValueError:
                    pass

        return messages

    def _is_valid_date(self, value: str) -> bool:
        """Check if value is a valid date"""
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _is_valid_time(self, value: str) -> bool:
        """Check if value is a valid time"""
        # EURING time format can be: HHMM, HH:MM:SS
        if re.match(r"^[-]{4}$", value):
            return True
        if re.match(r"^\d{4}$", value):
            return True
        if re.match(r"^\d{2}:\d{2}(:\d{2})?$", value):
            return True
        return False

    def _is_valid_decimal(self, value: str) -> bool:
        """Check if value is a valid decimal"""
        try:
            Decimal(value)
            return True
        except (ValueError, InvalidOperation):
            return False

    def _is_valid_integer(self, value: str) -> bool:
        """Check if value is a valid integer"""
        try:
            int(value)
            return True
        except ValueError:
            return False


# Global validator instance
_validator: Optional[Validator] = None


def get_validator() -> Validator:
    """Get or create global validator instance"""
    global _validator
    if _validator is None:
        _validator = Validator()
    return _validator
