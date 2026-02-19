import re


def format_ring_number(value: str) -> str:
    """Format a ring number to exactly 10 characters with dot padding.

    The alphabetical prefix is uppercased; dots fill the middle; the numeric
    suffix is right-aligned.  If the combined length already reaches 10 or the
    value does not match the expected pattern it is returned unchanged so that
    the validator can catch it.

    Examples:
        '81928'  -> '.....81928'
        'ab976'  -> 'AB.....976'
    """
    value = value.strip()
    match = re.match(r"^([A-Za-z]*)(\d+)$", value)
    if not match:
        return value  # Non-conforming value – leave it for validation to report

    prefix = match.group(1).upper()
    suffix = match.group(2)
    total_len = len(prefix) + len(suffix)

    if total_len >= 10:
        return prefix + suffix  # Already at or beyond target length

    dots = "." * (10 - total_len)
    return prefix + dots + suffix
