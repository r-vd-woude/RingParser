import re
from datetime import datetime


# ---------------------------------------------------------------------------
# Date normalisation
# ---------------------------------------------------------------------------

# Common date formats tried in order. Day-first formats are listed before
# month-first because this tool is primarily used in a European bird-ringing
# context. Each format that includes a time component has the time stripped
# from the result.
_DATE_FORMATS = [
    "%Y-%m-%d",            # already correct — fast path
    "%Y/%m/%d",
    "%Y-%m-%dT%H:%M:%S",   # ISO 8601 with time
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%m/%d/%Y",            # US format — lower priority to avoid DD/MM ambiguity
    "%d %b %Y",            # 15 Jan 2023
    "%d %B %Y",            # 15 January 2023
    "%B %d, %Y",           # January 15, 2023
    "%b %d, %Y",           # Jan 15, 2023
]


def normalize_date(value: str, output_format: str = "ISO") -> str:
    """
    Parse a date string in any common format and return it in the requested
    output format. Strips any time component.

    output_format:
      "ISO"      → YYYY-MM-DD  (default, required by xs:date)
      "DDMMYYYY" → DDMMYYYY    (EURING bulk-upload format)

    Returns the original value unchanged if no format matches.
    """
    v = value.strip()
    if not v:
        return v
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(v, fmt)
            if output_format == "DDMMYYYY":
                return dt.strftime("%d%m%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value


# ---------------------------------------------------------------------------
# Coordinate normalisation
# ---------------------------------------------------------------------------

# Matches the most common DMS notations, e.g.:
#   52°30'15.5"N   52°30'15.5"   52d30m15.5sN   N52°30'15.5"
# The direction letter may appear before or after the numeric part.
_DMS_RE = re.compile(
    r"^\s*"
    r"(?P<dir_pre>[NSEWnsew])?\s*"          # optional leading direction
    r"(?P<deg>\d{1,3})[°d]\s*"             # degrees + separator
    r"(?P<min>\d{1,2})['\u2019m]\s*"       # minutes + separator
    r"(?P<sec>\d{1,2}(?:[.,]\d+)?)[\"s]?\s*"  # seconds (decimal optional)
    r"(?P<dir_post>[NSEWnsew])?"            # optional trailing direction
    r"\s*$",
    re.IGNORECASE,
)


def normalize_coordinate(value: str) -> str:
    """
    Normalise a latitude or longitude value to a plain decimal-degree string.

    Handles:
      - Already-decimal values (returned unchanged)
      - Decimal with a trailing direction letter: "52.5 N" → "-52.5" for S/W
      - DMS strings with degree/minute/second symbols: "52°30'15.5\"N"

    Returns the original value unchanged if no format is recognised.
    """
    v = value.strip()
    if not v:
        return v

    # Already a plain decimal number?
    try:
        float(v)
        return v
    except ValueError:
        pass

    # Decimal with a trailing (or leading) direction letter: "52.5 N"
    decimal_dir = re.match(
        r"^([NSEWnsew])?\s*([+-]?\d+(?:\.\d+)?)\s*([NSEWnsew])?$", v
    )
    if decimal_dir:
        direction = (decimal_dir.group(1) or decimal_dir.group(3) or "").upper()
        num = float(decimal_dir.group(2))
        if direction in ("S", "W"):
            num = -num
        return str(round(num, 6))

    # DMS with symbols
    m = _DMS_RE.match(v)
    if m:
        decimal = (
            float(m.group("deg"))
            + float(m.group("min")) / 60
            + float(m.group("sec").replace(",", ".")) / 3600
        )
        direction = (m.group("dir_pre") or m.group("dir_post") or "").upper()
        if direction in ("S", "W"):
            decimal = -decimal
        return str(round(decimal, 6))

    return value


# ---------------------------------------------------------------------------
# EURING fixed-width DMS decoder (used by euring_parser only)
# ---------------------------------------------------------------------------

def dms_to_decimal(degrees_str: str) -> float:
    sign_lat = degrees_str[0]
    sign_long = degrees_str[7]
    lat = (
        int(degrees_str[1:3])
        + int(degrees_str[3:5]) / 60
        + int(degrees_str[5:7]) / 3600
    )
    lon = (
        int(degrees_str[8:11])
        + int(degrees_str[11:13]) / 60
        + int(degrees_str[13:15]) / 3600
    )

    if sign_lat == "-":
        lat = -lat
    if sign_long == "-":
        lon = -lon

    return {"lat": lat, "lon": lon}


def strip_empty_fields(record: dict) -> dict:
    filtered_fields = {}
    for key, field in record["fields"].items():
        if field["value"] != "":
            filtered_fields[key] = field
    record["fields"] = filtered_fields
    return record
