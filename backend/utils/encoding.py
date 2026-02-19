import csv
import chardet


def _detect_encoding(raw_content: bytes) -> str:
    """Detect file encoding using chardet"""
    result = chardet.detect(raw_content)
    encoding = result.get("encoding", "utf-8")

    # Fallback to utf-8 if detection failed
    if encoding is None:
        encoding = "utf-8"

    # Handle common encoding variations
    if encoding.lower() in ["ascii", "us-ascii"]:
        encoding = "utf-8"

    return encoding


def _detect_delimiter(content: str, delimiter_candidates: list | None = None) -> str:
    """
    Detect CSV delimiter by analyzing the first few lines.

    Args:
        content: CSV file content as string
        delimiter_candidates: List of delimiter characters to consider

    Returns:
        Detected delimiter character
    """
    if delimiter_candidates is None:
        delimiter_candidates = [",", ";", "\t", "|"]

    # Get first few lines for analysis
    lines = content.split("\n")[:5]
    sample = "\n".join(lines)

    # Try csv.Sniffer
    try:
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(
            sample, delimiters="".join(delimiter_candidates)
        ).delimiter
        return delimiter
    except Exception:
        pass

    # Fallback: Count occurrences of each delimiter in first line
    if lines:
        first_line = lines[0]
        delimiter_counts = {d: first_line.count(d) for d in delimiter_candidates}

        # Find delimiter with maximum count (and count > 0)
        max_delimiter = max(delimiter_counts.items(), key=lambda x: x[1])
        if max_delimiter[1] > 0:
            return max_delimiter[0]

    # Default to comma
    return ","
