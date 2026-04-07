"""
ACER Graph Data Models

The core data structures for the ACER ontology visualization.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum


class RelationshipStatus(Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    USER_ADDED = "user_added"


class ConfidenceLevel(Enum):
    HIGH = "high"      # ≥ 85%
    MEDIUM = "medium"  # 60-84%
    LOW = "low"        # < 60%


def get_confidence_level(confidence: float) -> ConfidenceLevel:
    """Determine confidence level from score."""
    if confidence is None:
        return ConfidenceLevel.LOW
    if confidence >= 0.85:
        return ConfidenceLevel.HIGH
    elif confidence >= 0.60:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


@dataclass
class Datapoint:
    """A single datapoint extracted from a document."""
    id: int
    aligned_datapoint: str
    impact_category: str
    impact_subcategory: str
    value: str
    unit: Optional[str] = None
    normalized_value: Optional[str] = None
    confidence: float = 1.0
    source_page: Optional[str] = None
    source_location: Optional[str] = None
    requirement_sources: list[str] = field(default_factory=list)
    status: str = "verified"
    
    @property
    def confidence_level(self) -> ConfidenceLevel:
        return get_confidence_level(self.confidence)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "alignedDatapoint": self.aligned_datapoint,
            "impactCategory": self.impact_category,
            "impactSubcategory": self.impact_subcategory,
            "value": self.value,
            "unit": self.unit,
            "normalized": self.normalized_value,
            "confidence": self.confidence,
            "sourcePage": self.source_page,
            "sourceLocation": self.source_location,
            "requirementSources": self.requirement_sources,
            "status": self.status
        }


@dataclass
class Relationship:
    """One of the 6 ACER relationships."""
    name: str
    found: bool
    value: Any = None  # str, list[Datapoint], or dict for metadata
    confidence: Optional[float] = None
    source_location: Optional[str] = None
    status: RelationshipStatus = RelationshipStatus.NOT_FOUND
    suggested: Any = None  # Suggested value if not found
    
    def __post_init__(self):
        if self.found and self.status == RelationshipStatus.NOT_FOUND:
            self.status = RelationshipStatus.FOUND
    
    @property
    def confidence_level(self) -> ConfidenceLevel:
        return get_confidence_level(self.confidence)
    
    @property
    def display_value(self) -> str:
        """Human-readable value for display."""
        if self.value is None:
            return "NOT FOUND"
        if isinstance(self.value, list):
            return f"{len(self.value)} datapoints"
        if isinstance(self.value, dict):
            return ", ".join(f"{k}: {v}" for k, v in self.value.items() if k != 'extractedAt')
        return str(self.value)
    
    def to_dict(self) -> dict:
        result = {
            "found": self.found,
            "status": self.status.value
        }
        if self.value is not None:
            if isinstance(self.value, list) and self.value and isinstance(self.value[0], Datapoint):
                result["count"] = len(self.value)
                result["averageConfidence"] = sum(d.confidence for d in self.value) / len(self.value) if self.value else 0
                result["items"] = [d.to_dict() for d in self.value]
            else:
                result["value"] = self.value
        if self.confidence is not None:
            result["confidence"] = self.confidence
        if self.suggested is not None:
            result["suggested"] = self.suggested
        if self.source_location:
            result["sourceLocation"] = self.source_location
        return result


@dataclass
class AcerGraph:
    """
    Complete ACER graph for a document.
    
    Represents all 6 relationships between a document and the ACER ontology.
    """
    document_name: str
    source_file: Optional[str] = None
    
    # The 6 relationships
    has_metadata: Optional[Relationship] = None
    has_equipment: Optional[Relationship] = None
    has_asset_type: Optional[Relationship] = None
    has_datapoint: Optional[Relationship] = None
    has_impact_category: Optional[Relationship] = None
    has_requirement_source: Optional[Relationship] = None
    
    # Processing info
    extracted_at: datetime = field(default_factory=datetime.now)
    llm_model: str = ""
    processing_time_seconds: float = 0.0
    
    # Relationship definitions (for display)
    RELATIONSHIP_NAMES = [
        "has_metadata",
        "has_equipment", 
        "has_asset_type",
        "has_datapoint",
        "has_impact_category",
        "has_requirement_source"
    ]
    
    # Display names (PascalCase)
    RELATIONSHIP_DISPLAY_NAMES = {
        "has_metadata": "hasMetadata",
        "has_equipment": "hasEquipment", 
        "has_asset_type": "hasAssetType",
        "has_datapoint": "hasDatapoint",
        "has_impact_category": "hasImpactCategory",
        "has_requirement_source": "hasRequirementSource"
    }
    
    # Descriptions for each relationship
    RELATIONSHIP_DESCRIPTIONS = {
        "hasMetadata": "Document metadata (auto-extracted)",
        "hasEquipment": "Equipment identified in the document",
        "hasAssetType": "Asset type classification",
        "hasDatapoint": "Extracted technical specifications",
        "hasImpactCategory": "Sustainability impact category",
        "hasRequirementSource": "Compliance standards referenced"
    }
    
    def get_relationship(self, name: str) -> Optional[Relationship]:
        """Get relationship by name (handles both snake_case and camelCase)."""
        # Try direct attribute first
        if hasattr(self, name):
            return getattr(self, name)
        # Try snake_case conversion
        snake_name = self._camel_to_snake(name)
        if hasattr(self, snake_name):
            return getattr(self, snake_name)
        return None
    
    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """Convert camelCase to snake_case."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def get_all_relationships(self) -> list[tuple[str, Relationship]]:
        """Get all relationships with their names."""
        result = []
        for name in self.RELATIONSHIP_NAMES:
            rel = self.get_relationship(name)
            if rel:
                result.append((name, rel))
        return result
    
    @property
    def relationships_found(self) -> int:
        """Count of relationships that were found."""
        return sum(1 for _, rel in self.get_all_relationships() if rel.found)
    
    @property
    def relationships_missing(self) -> int:
        """Count of relationships that are missing."""
        return sum(1 for _, rel in self.get_all_relationships() if not rel.found)
    
    @property
    def total_datapoints(self) -> int:
        """Total datapoints extracted."""
        if self.has_datapoint and isinstance(self.has_datapoint.value, list):
            return len(self.has_datapoint.value)
        return 0
    
    @property
    def average_confidence(self) -> float:
        """Average confidence across all relationships."""
        confidences = [rel.confidence for _, rel in self.get_all_relationships() 
                      if rel.confidence is not None]
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    @property
    def confidence_breakdown(self) -> dict:
        """Breakdown of datapoint confidence levels."""
        if not self.has_datapoint or not isinstance(self.has_datapoint.value, list):
            return {"high": 0, "medium": 0, "low": 0}
        
        items = self.has_datapoint.value
        return {
            "high": sum(1 for d in items if d.confidence_level == ConfidenceLevel.HIGH),
            "medium": sum(1 for d in items if d.confidence_level == ConfidenceLevel.MEDIUM),
            "low": sum(1 for d in items if d.confidence_level == ConfidenceLevel.LOW)
        }
    
    def to_dict(self) -> dict:
        """Export to dictionary."""
        relationships = {}
        for name, rel in self.get_all_relationships():
            display_name = self.RELATIONSHIP_DISPLAY_NAMES.get(name, name)
            relationships[display_name] = rel.to_dict()
        
        return {
            "$schema": "https://acer.build/v1/acer-graph.schema.json",
            "document": {
                "name": self.document_name,
                "sourceFile": self.source_file or self.document_name
            },
            "relationships": relationships,
            "meta": {
                "extractedAt": self.extracted_at.isoformat(),
                "llmModel": self.llm_model,
                "ontologyVersion": "0.0.1",
                "relationshipsFound": self.relationships_found,
                "relationshipsMissing": self.relationships_missing,
                "datapointsExtracted": self.total_datapoints,
                "averageConfidence": self.average_confidence
            }
        }
    
    def to_markdown(self) -> str:
        """Export to Markdown (Obsidian-ready)."""
        lines = [
            f"# {self.document_name}",
            "",
            "## ACER Relationships",
            "",
            "| Relationship | Status | Confidence | Value |",
            "|--------------|--------|------------|-------|"
        ]
        
        for name, rel in self.get_all_relationships():
            status_icon = "✓" if rel.found else "✗"
            conf_str = f"{rel.confidence:.0%}" if rel.confidence else "-"
            value = rel.display_value
            lines.append(f"| [[{name}]] | {status_icon} | {conf_str} | {value} |")
        
        # Add datapoints section if available
        if self.has_datapoint and isinstance(self.has_datapoint.value, list):
            lines.extend(["", "## Datapoints", ""])
            
            # Group by impact category
            by_category: dict = {}
            for dp in self.has_datapoint.value:
                cat = dp.impact_category
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(dp)
            
            for category, datapoints in by_category.items():
                lines.append(f"### [[{category}]]")
                lines.append("")
                lines.append("| ACER ID | Datapoint | Value | Unit | Confidence |")
                lines.append("|---------|-----------|-------|------|------------|")
                
                for dp in datapoints:
                    conf_emoji = "✓" if dp.confidence_level == ConfidenceLevel.HIGH else "⚠️"
                    lines.append(f"| #{dp.id} | [[{dp.aligned_datapoint}]] | {dp.value} | {dp.unit or '-'} | {dp.confidence:.0%} {conf_emoji} |")
                lines.append("")
        
        lines.extend([
            "---",
            "",
            f"*Generated by Building Passport Processor | ACER Visualizer v1.0*",
            f"*Extracted: {self.extracted_at.isoformat()}*"
        ])
        
        return "\n".join(lines)
