from typing import List, Dict, Any
from dateutil import parser


def _infer_column_types(
    headers: List[str], data_rows: List[List[str]]
) -> List[Dict[str, Any]]:
    """
    Infer data types for each column.

    Args:
        headers: Column headers
        data_rows: Data rows

    Returns:
        List of column information dictionaries
    """
    column_info = []
    for i, header in enumerate(headers):
        # Collect sample values for this column
        sample_values = []
        for row in data_rows[:20]:  # Sample first 20 rows
            if i < len(row) and row[i] is not None:
                value = str(row[i]).strip()
                if value:  # Ignore empty values
                    sample_values.append(value)

        # Infer type
        inferred_type = _infer_type(sample_values)

        # Get sample values (first 3 non-empty)
        display_samples = [v for v in sample_values[:3]]

        column_info.append(
            {
                "name": header,
                "index": i,
                "type": inferred_type,
                "sample_values": display_samples,
            }
        )
    return column_info


def _infer_type(values: List[str]) -> str:
    """
    Infer data type from sample values.

    Args:
        values: Sample values

    Returns:
        Inferred type name
    """
    if not values:
        return "string"

    # Check for integers
    try:
        all_int = all(_is_integer(v) for v in values)
        if all_int:
            return "integer"
    except Exception:
        pass

    # Check for decimals/floats
    try:
        all_decimal = all(_is_decimal(v) for v in values)
        if all_decimal:
            return "decimal"
    except Exception:
        pass

    # Check for dates
    try:
        all_date = all(_is_date(v) for v in values)
        if all_date:
            return "date"
    except Exception:
        pass

    # Check for times
    try:
        all_time = all(_is_time(v) for v in values)
        if all_time:
            return "time"
    except Exception:
        pass

    # Default to string
    return "string"


def _is_integer(value: str) -> bool:
    """Check if value is an integer"""
    try:
        int(value)
        return True
    except ValueError:
        return False


def _is_decimal(value: str) -> bool:
    """Check if value is a decimal number"""
    try:
        float(value)
        return "." in value or "e" in value.lower()
    except ValueError:
        return False


def _is_date(value: str) -> bool:
    """Check if value looks like a date using flexible parsing"""
    try:
        dt = parser.parse(value, fuzzy=False)
        # Accept only if the parsed value has a date component (not just a time)
        if dt.date() != dt.min.date():
            return True
    except Exception:
        pass
    return False


def _is_time(value: str) -> bool:
    """Check if value looks like a time using flexible parsing"""
    if value == "----":
        return True

    try:
        dt = parser.parse(value)
        # Accept only if the parsed value has a time component (not just a date)
        if dt.time() != dt.min.time():
            return True
    except Exception:
        pass
    return False
