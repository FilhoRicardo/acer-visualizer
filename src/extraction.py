"""Mock PDF extraction module for ACER Visualizer.

In production, this would integrate with a real PDF parsing pipeline
(e.g., Azure Document Intelligence, LlamaIndex, or custom OCR).
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class ExtractedMetadata:
    """Auto-extracted document metadata."""
    filename: str
    file_size_kb: float
    page_count: Optional[int] = None
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    author: Optional[str] = None


@dataclass
class EquipmentInfo:
    """Identified equipment details."""
    name: str
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None


@dataclass
class Datapoint:
    """Extracted data point from document."""
    aligned_datapoint: str
    value: str
    unit: str
    normalized_value: Optional[str] = None
    confidence: float = 0.5
    source_page: Optional[str] = None
    source_location: Optional[str] = None


@dataclass
class RequirementSource:
    """Compliance or requirement standard referenced."""
    standard_name: str
    standard_code: Optional[str] = None
    requirement_text: Optional[str] = None
    page_reference: Optional[str] = None


def extract_from_text(filename: str, text: str) -> dict:
    """Mock extraction from document text.
    
    In production: use Azure Document Intelligence, LlamaIndex,
    or custom NLP pipeline.
    """
    metadata = ExtractedMetadata(
        filename=filename,
        file_size_kb=len(text.encode()) / 1024,
        page_count=max(1, len(text) // 3000)
    )
    
    # Extract equipment name (mock: look for capitalized terms)
    equipment = None
    if match := re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Model|Unit|RTU|AC|Unitary)', text):
        equipment = EquipmentInfo(
            name=match.group(0),
            manufacturer="Extracted from document"
        )
    
    # Extract datapoints (mock patterns)
    datapoints = []
    
    # Capacity patterns
    for match in re.finditer(r'Capacity[:\s]+(\d+(?:\.\d+)?)\s*(tons?|MBH|BTU|kW|kBtu)', text, re.I):
        value = match.group(1)
        unit = match.group(2)
        datapoints.append(Datapoint(
            aligned_datapoint="Cooling Capacity",
            value=value,
            unit=unit,
            normalized_value=None,
            confidence=0.92,
            source_page="1",
            source_location="Specifications"
        ))
    
    # Efficiency patterns
    for match in re.finditer(r'(?:EER|IEER|SEER)[:\s]+(\d+(?:\.\d+)?)', text, re.I):
        datapoints.append(Datapoint(
            aligned_datapoint="Energy Efficiency Ratio",
            value=match.group(1),
            unit="",
            confidence=0.95,
            source_page="1",
            source_location="Ratings"
        ))
    
    # Flow rate patterns
    for match in re.finditer(r'(\d+(?:,\d{3})*)\s*(CFM|cfm|L/s|L/s)', text):
        datapoints.append(Datapoint(
            aligned_datapoint="Airflow Rate",
            value=match.group(1),
            unit=match.group(2),
            confidence=0.88,
            source_page="2",
            source_location="Performance"
        ))
    
    # Weight patterns
    for match in re.finditer(r'(\d+(?:,\d{3})*)\s*(lbs?|kg)', text, re.I):
        datapoints.append(Datapoint(
            aligned_datapoint="Unit Weight",
            value=match.group(1),
            unit=match.group(2),
            confidence=0.85,
            source_page="2",
            source_location="Physical Specs"
        ))
    
    # Extract requirements
    requirements = []
    for match in re.finditer(r'(ASHRAE|LEED|Energy Star|OSHA|IECC)[^\.]*', text, re.I):
        requirements.append(RequirementSource(
            standard_name=match.group(1),
            requirement_text=match.group(0)[:100]
        ))
    
    return {
        "metadata": metadata,
        "equipment": equipment,
        "datapoints": datapoints,
        "requirements": requirements
    }
