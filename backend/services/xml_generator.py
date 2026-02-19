import uuid
import zipfile
from datetime import date
from typing import List, Dict, Any, Optional
from pathlib import Path
from lxml import etree

from backend.models.mapping_model import MappingConfiguration
from backend.models.schema_model import XSDSchema
from backend.config import OUTPUT_DIR, XML_CHUNK_SIZE, HARDCODED_FIELD_NAMES
from backend.utils.file_handler import prune_directory
from backend.utils.ring_number import format_ring_number


class XMLGenerator:
    """Generator for XML output from mapped data"""

    def __init__(self):
        self.namespace = "http://www.w3.org/2001/XMLSchema"

    def generate_xml(
        self,
        data_rows: List[List[str]],
        headers: List[str],
        mapping_config: MappingConfiguration,
        schema: XSDSchema,
        advanced_overrides: Optional[List[Any]] = None,
    ) -> tuple[str, Path, int]:
        """
        Generate XML output from mapped data. Automatically splits into chunks
        of 1000 rows (the XSD maxOccurs limit) and zips them if needed.

        Args:
            data_rows: List of data rows
            headers: Column headers
            mapping_config: Mapping configuration
            schema: XSD schema

        Returns:
            Tuple of (xml_id, file_path, total_files)
        """
        column_to_target = {
            m.source_column: m.target_path for m in mapping_config.mappings
        }

        chunks = [
            data_rows[i : i + XML_CHUNK_SIZE]
            for i in range(0, len(data_rows), XML_CHUNK_SIZE)
        ]

        xml_id = str(uuid.uuid4())

        if len(chunks) == 1:
            file_path = self._generate_chunk(
                chunks[0], headers, column_to_target, xml_id, advanced_overrides
            )
            prune_directory(OUTPUT_DIR)
            return xml_id, file_path, 1

        # Multiple chunks — generate each then zip
        temp_paths = []
        for i, chunk in enumerate(chunks):
            temp_id = str(uuid.uuid4())
            temp_path = self._generate_chunk(
                chunk, headers, column_to_target, temp_id, advanced_overrides
            )
            temp_paths.append(temp_path)

        zip_path = OUTPUT_DIR / f"{xml_id}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, path in enumerate(temp_paths):
                zf.write(path, f"part_{i + 1:03d}.xml")
                path.unlink()

        prune_directory(OUTPUT_DIR)
        return xml_id, zip_path, len(chunks)

    def _generate_chunk(
        self,
        data_rows: List[List[str]],
        headers: List[str],
        column_to_target: Dict[str, str],
        chunk_id: str,
        advanced_overrides: Optional[List[Any]] = None,
    ) -> Path:
        """Generate a single XML file from a chunk of rows."""
        root = etree.Element("MyBulk")
        # Build header index once per chunk so every row can do O(1) lookups
        header_idx = {h: i for i, h in enumerate(headers)}
        override_map = {o.field_name: o for o in (advanced_overrides or [])}

        for row in data_rows:
            capture = self._create_capture_element(
                row, headers, column_to_target, header_idx, override_map
            )
            root.append(capture)

        xml_str = etree.tostring(
            root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
        ).decode("utf-8")

        file_path = OUTPUT_DIR / f"{chunk_id}.xml"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(xml_str)

        return file_path

    def _create_capture_element(
        self,
        row: List[str],
        headers: List[str],
        column_to_target: Dict[str, str],
        header_idx: Dict[str, int],
        override_map: Dict[str, Any],
    ) -> etree.Element:
        """Create a Capture element from a data row"""
        capture = etree.Element("Capture")

        def resolve(field_name: str, default: str) -> str:
            ov = override_map.get(field_name)
            if ov is None:
                return default
            if ov.source_column and ov.source_column in header_idx:
                v = str(row[header_idx[ov.source_column]]).strip()
                return v if v else default
            if ov.static_value is not None:
                return ov.static_value
            return default

        for field_name, default_value in HARDCODED_FIELD_NAMES.items():
            if default_value == "set_to_today":
                default_value = date.today().strftime("%Y-%m-%d")
            etree.SubElement(capture, field_name).text = resolve(
                field_name, default_value
            )

        field_data = {}
        for col_idx, header in enumerate(headers):
            if header not in column_to_target:
                continue

            target_path = column_to_target[header]

            col_override = override_map.get(target_path)
            if col_override is not None and col_override.static_value is not None:
                value = col_override.static_value
            else:
                raw = row[col_idx] if col_idx < len(row) else None
                value = str(raw).strip() if raw is not None else ""
                if not value:
                    continue

            if target_path.endswith("RingNumber"):
                value = format_ring_number(value)

            field_data[target_path] = value

        for target_path, value in sorted(field_data.items()):
            self._add_field_to_element(capture, target_path, value)

        return capture

    def _add_field_to_element(
        self, parent: etree.Element, target_path: str, value: str
    ):
        """Add a field to the XML element hierarchy"""
        parts = target_path.split(".")

        if parts[0] == "MyBulk":
            parts = parts[1:]
        if parts[0] == "Capture":
            parts = parts[1:]

        if len(parts) == 1:
            field_elem = etree.SubElement(parent, parts[0])
            field_elem.text = value
        else:
            self._add_nested_field(parent, parts, value)

    def _add_nested_field(self, parent: etree.Element, parts: List[str], value: str):
        """Add a nested field to the XML hierarchy"""
        current = parent
        for part in parts[:-1]:
            child = current.find(part)
            if child is None:
                child = etree.SubElement(current, part)
            current = child

        field_elem = etree.SubElement(current, parts[-1])
        field_elem.text = value

    def get_xml_preview(self, file_path: Path, lines: int = 50) -> str:
        """Get preview of output file (first N lines). Handles both .xml and .zip."""
        if file_path.suffix == ".zip":
            with zipfile.ZipFile(file_path, "r") as zf:
                first_entry = sorted(zf.namelist())[0]
                content = zf.read(first_entry).decode("utf-8")
            preview_lines = content.splitlines()[:lines]
            return "\n".join(preview_lines)

        with open(file_path, "r", encoding="utf-8") as f:
            preview_lines = []
            for i, line in enumerate(f):
                if i >= lines:
                    break
                preview_lines.append(line.rstrip())
            return "\n".join(preview_lines)


# Global generator instance
_xml_generator: Optional[XMLGenerator] = None


def get_xml_generator() -> XMLGenerator:
    """Get or create global XML generator instance"""
    global _xml_generator
    if _xml_generator is None:
        _xml_generator = XMLGenerator()
    return _xml_generator
