import uuid
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher
from datetime import datetime
import re

from backend.models.mapping_model import (
    MappingConfiguration,
    FieldMapping,
    MappingSuggestion,
)
from backend.models.schema_model import XSDSchema, SchemaField

from backend.config import SYNONYMS, ABBREVIATIONS


class MappingEngine:
    """Engine for managing column-to-field mappings"""

    def __init__(self):
        # In-memory storage for mappings (in production, use database)
        self.mappings: Dict[str, MappingConfiguration] = {}

    def create_mapping(
        self, file_id: str, file_type: str, mappings: List[FieldMapping]
    ) -> MappingConfiguration:
        """
        Create or update a mapping configuration.

        Args:
            file_id: ID of the uploaded file
            file_type: Type of file (csv or xlsx)
            mappings: List of field mappings

        Returns:
            MappingConfiguration object
        """
        # Check if mapping already exists for this file
        mapping_id = self._get_mapping_id_by_file(file_id)

        if mapping_id:
            # Update existing mapping
            config = self.mappings[mapping_id]
            config.mappings = mappings
            config.updated_at = datetime.now()
        else:
            # Create new mapping
            mapping_id = str(uuid.uuid4())
            config = MappingConfiguration(
                mapping_id=mapping_id,
                file_id=file_id,
                file_type=file_type,
                mappings=mappings,
            )
            self.mappings[mapping_id] = config

        return config

    def get_mapping(self, mapping_id: str) -> Optional[MappingConfiguration]:
        """Get mapping configuration by ID"""
        return self.mappings.get(mapping_id)

    def suggest_mappings(
        self, source_columns: List[str], schema: XSDSchema, threshold: float = 0.5
    ) -> List[MappingSuggestion]:
        """
        Auto-suggest mappings based on field name similarity.

        Args:
            source_columns: List of source column names
            schema: Target XSD schema
            threshold: Minimum confidence threshold (0.0 - 1.0)

        Returns:
            List of mapping suggestions
        """
        suggestions = []

        # Flatten schema fields for easier matching
        target_fields = self._flatten_schema_fields(schema.fields)

        for source_col in source_columns:
            best_match = None
            best_score = 0.0
            best_reason = ""

            for target_field in target_fields:
                # Skip complex types (we want leaf fields)
                if target_field["is_complex"]:
                    continue

                # Calculate similarity score
                score, reason = self._calculate_similarity(
                    source_col, target_field["name"], target_field["path"]
                )

                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = target_field
                    best_reason = reason

            # Add suggestion if good match found
            if best_match:
                suggestions.append(
                    MappingSuggestion(
                        source_column=source_col,
                        target_path=best_match["path"],
                        target_name=best_match["name"],
                        confidence=best_score,
                        reason=best_reason,
                    )
                )

        # Sort by confidence (highest first)
        suggestions.sort(key=lambda x: x.confidence, reverse=True)

        return suggestions

    def _flatten_schema_fields(
        self, fields: List[SchemaField], parent_path: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Flatten schema fields into a list for easier matching.

        Args:
            fields: Schema fields to flatten
            parent_path: Parent path prefix

        Returns:
            List of flattened field dictionaries
        """
        flattened = []

        for field in fields:
            field_dict = {
                "name": field.name,
                "path": field.path,
                "type": field.type,
                "required": field.required,
                "is_complex": len(field.children) > 0 or field.is_choice,
            }

            flattened.append(field_dict)

            # Recursively flatten children
            if field.children:
                flattened.extend(
                    self._flatten_schema_fields(field.children, field.path)
                )

            # Flatten choice options
            if field.is_choice and field.choice_options:
                for option in field.choice_options:
                    if option.fields:
                        flattened.extend(
                            self._flatten_schema_fields(option.fields, option.path)
                        )

        return flattened

    def _calculate_similarity(
        self, source: str, target_name: str, target_path: str
    ) -> tuple[float, str]:
        """
        Calculate similarity score between source and target field names.

        Args:
            source: Source column name
            target_name: Target field name
            target_path: Target field full path

        Returns:
            Tuple of (similarity_score, reason)
        """
        # Normalize names for comparison
        source_norm = self._normalize_name(source)
        target_norm = self._normalize_name(target_name)

        # Exact match (case-insensitive)
        if source_norm == target_norm:
            return 1.0, "Exact name match"

        # Check if source contains target or vice versa
        if source_norm in target_norm:
            return 0.9, f"Source '{source}' contained in target '{target_name}'"
        if target_norm in source_norm:
            return 0.9, f"Target '{target_name}' contained in source '{source}'"

        # Calculate string similarity using SequenceMatcher
        similarity = SequenceMatcher(None, source_norm, target_norm).ratio()

        # Boost score for common abbreviations
        abbreviation_score = self._check_abbreviation(source, target_name)
        if abbreviation_score > similarity:
            return abbreviation_score, f"Potential abbreviation match"

        # Check for semantic matches (domain-specific)
        semantic_score = self._check_semantic_match(source, target_name)
        if semantic_score > similarity:
            return semantic_score, f"Semantic match"

        if similarity >= 0.5:
            return similarity, f"Name similarity: {similarity:.0%}"

        return similarity, "Low similarity"

    def _normalize_name(self, name: str) -> str:
        """Normalize field name for comparison"""
        # Convert to lowercase
        name = name.lower()

        # Remove common separators
        name = re.sub(r"[_\-\s.]+", "", name)

        # Remove common prefixes/suffixes
        name = re.sub(r"^(fld|col|field|column)", "", name)
        name = re.sub(r"(id|code|value)$", "", name)

        return name

    def _check_abbreviation(self, source: str, target: str) -> float:
        """Check if source might be an abbreviation of target"""
        source_norm = source.lower().replace("_", "").replace("-", "")
        target_norm = target.lower()

        # Check if source matches first letters of target words
        target_words = re.findall(r"[A-Z][a-z]*", target) or [target]
        if target_words:
            abbreviation = "".join(word[0].lower() for word in target_words)
            if source_norm == abbreviation:
                return 0.85

        # Load abbreviations from config
        abbreviations = ABBREVIATIONS

        source_lower = source_norm.lower()
        target_lower = target_norm.lower()

        if (
            source_lower in abbreviations
            and abbreviations[source_lower] in target_lower
        ):
            return 0.85

        return 0.0

    def _check_semantic_match(self, source: str, target: str) -> float:
        """Check for semantic/domain-specific matches"""

        # Load synonyms from config
        synonyms = SYNONYMS

        source_norm = self._normalize_name(source)
        target_norm = self._normalize_name(target)

        for (word1, word2), score in synonyms.items():
            if (word1 in source_norm and word2 in target_norm) or (
                word2 in source_norm and word1 in target_norm
            ):
                return score

        return 0.0

    def _get_mapping_id_by_file(self, file_id: str) -> Optional[str]:
        """Find mapping ID by file ID"""
        for mapping_id, config in self.mappings.items():
            if config.file_id == file_id:
                return mapping_id
        return None


# Global mapping engine instance
_mapping_engine: Optional[MappingEngine] = None


def get_mapping_engine() -> MappingEngine:
    """Get or create global mapping engine instance"""
    global _mapping_engine
    if _mapping_engine is None:
        _mapping_engine = MappingEngine()
    return _mapping_engine
