"""
Sample ACER Graph - Carrier 40RUS 060-8 Rooftop Unit

This is the sample data that demonstrates the ACER Visualizer.
In production, this would be generated from PDF extraction.
"""
from datetime import datetime
from models.acer_graph import (
    AcerGraph, Relationship, Datapoint, 
    RelationshipStatus, ConfidenceLevel
)


def create_carrier_rtu_graph() -> AcerGraph:
    """Create sample ACER graph for Carrier 40RUS 060-8."""
    
    # Create datapoints
    datapoints = [
        # Energy - Primary metrics
        Datapoint(
            id=80,
            aligned_datapoint="Primary Energy Demand (PED)",
            impact_category="Climate Health",
            impact_subcategory="Energy",
            value="175,000",
            unit="BTU/h",
            normalized_value="51.3 kW",
            confidence=0.94,
            source_page="1",
            source_location="Technical Specifications Table",
            requirement_sources=["EU Tax", "LEED v4"]
        ),
        Datapoint(
            id=143,
            aligned_datapoint="Effective Rated Output",
            impact_category="Climate Health",
            impact_subcategory="Energy",
            value="160,000",
            unit="BTU/h",
            normalized_value="46.9 kW",
            confidence=0.92,
            source_page="1",
            source_location="Technical Specifications Table",
            requirement_sources=["EU Tax"]
        ),
        Datapoint(
            id=127,
            aligned_datapoint="Energy Efficiency Class",
            impact_category="Climate Health",
            impact_subcategory="Energy",
            value="EER 11.5",
            confidence=0.89,
            source_page="3",
            source_location="Performance Data"
        ),
        Datapoint(
            id=152,
            aligned_datapoint="COP",
            impact_category="Climate Health",
            impact_subcategory="Energy",
            value="3.8",
            confidence=0.96,
            source_page="3",
            source_location="Performance Data",
            requirement_sources=["EU Tax", "ASHRAE 90.1"]
        ),
        Datapoint(
            id=155,
            aligned_datapoint="Airflow Rate",
            impact_category="Climate Health",
            impact_subcategory="Energy",
            value="2,000",
            unit="CFM",
            normalized_value="944 L/s",
            confidence=0.93,
            source_page="2",
            source_location="Specifications"
        ),
        
        # Greenhouse Gas Emissions
        Datapoint(
            id=92,
            aligned_datapoint="Refrigerant Type",
            impact_category="Climate Health",
            impact_subcategory="Greenhouse Gas Emissions",
            value="R-410A",
            confidence=0.98,
            source_page="2",
            source_location="Refrigerant Specifications",
            requirement_sources=["F-Gas Regulation"]
        ),
        Datapoint(
            id=88,
            aligned_datapoint="Global Warming Potential (GWP)",
            impact_category="Climate Health",
            impact_subcategory="Greenhouse Gas Emissions",
            value="2,088",
            unit="kg CO₂e",
            confidence=0.87,
            source_page="2",
            source_location="Environmental Data"
        ),
        
        # Physical Characteristics
        Datapoint(
            id=160,
            aligned_datapoint="Dimensions (L×W×H)",
            impact_category="Asset Integrity",
            impact_subcategory="Physical Characteristics",
            value="72×48×42",
            unit="in",
            confidence=0.98,
            source_page="2",
            source_location="Physical Specifications"
        ),
        Datapoint(
            id=163,
            aligned_datapoint="Operating Weight",
            impact_category="Asset Integrity",
            impact_subcategory="Physical Characteristics",
            value="850",
            unit="lbs",
            normalized_value="386 kg",
            confidence=0.97,
            source_page="2",
            source_location="Physical Specifications"
        ),
        
        # Element Resilience
        Datapoint(
            id=48,
            aligned_datapoint="Expected Asset Lifetime",
            impact_category="Asset Integrity",
            impact_subcategory="Element Resilience",
            value="25",
            unit="years",
            confidence=0.72,  # Lower confidence - may need verification
            source_page="4",
            source_location="Warranty Information"
        ),
        Datapoint(
            id=54,
            aligned_datapoint="Warranty Period",
            impact_category="Asset Integrity",
            impact_subcategory="Element Resilience",
            value="5",
            unit="years",
            confidence=0.95,
            source_page="4",
            source_location="Warranty Information"
        ),
        
        # Additional specs
        Datapoint(
            id=131,
            aligned_datapoint="Voltage/Frequency",
            impact_category="Human Health",
            impact_subcategory="Safety",
            value="208/230V",
            unit="3-phase",
            confidence=0.99,
            source_page="2",
            source_location="Electrical Specifications"
        ),
        Datapoint(
            id=130,
            aligned_datapoint="Safety Certification",
            impact_category="Human Health",
            impact_subcategory="Safety",
            value="UL, ETL",
            confidence=0.98,
            source_page="1",
            source_location="Certifications"
        ),
    ]
    
    # Create the graph
    graph = AcerGraph(
        document_name="Carrier 40RUS 060-8",
        source_file="carrier-40rus-datasheet.pdf",
        extracted_at=datetime.now(),
        llm_model="claude-3-5-sonnet-20241022",
        processing_time_seconds=3.8,
        
        has_metadata=Relationship(
            name="hasMetadata",
            found=True,
            value={
                "pageCount": 8,
                "fileSize": "2.4MB",
                "extractedAt": datetime.now().isoformat(),
                "llmModel": "claude-3-5-sonnet-20241022"
            },
            confidence=1.0,
            status=RelationshipStatus.FOUND
        ),
        
        has_equipment=Relationship(
            name="hasEquipment",
            found=True,
            value="Carrier 40RUS 060-8",
            confidence=0.98,
            status=RelationshipStatus.FOUND,
            source_location="Page 1, Product Name"
        ),
        
        has_asset_type=Relationship(
            name="hasAssetType",
            found=True,
            value="Rooftop Unit",
            confidence=0.95,
            status=RelationshipStatus.FOUND,
            source_location="Page 1, Product Category"
        ),
        
        has_datapoint=Relationship(
            name="hasDatapoint",
            found=True,
            value=datapoints,
            confidence=0.89,  # Average
            status=RelationshipStatus.FOUND
        ),
        
        has_impact_category=Relationship(
            name="hasImpactCategory",
            found=False,
            confidence=None,
            status=RelationshipStatus.NOT_FOUND,
            suggested="Climate Health"
        ),
        
        has_requirement_source=Relationship(
            name="hasRequirementSource",
            found=False,
            confidence=None,
            status=RelationshipStatus.NOT_FOUND,
            suggested=["EU Tax", "LEED v4"]
        )
    )
    
    return graph


def create_simple_example_graph() -> AcerGraph:
    """Create a simpler example for testing."""
    
    datapoints = [
        Datapoint(
            id=80,
            aligned_datapoint="Primary Energy Demand (PED)",
            impact_category="Climate Health",
            impact_subcategory="Energy",
            value="175,000",
            unit="BTU/h",
            confidence=0.94
        ),
        Datapoint(
            id=152,
            aligned_datapoint="COP",
            impact_category="Climate Health",
            impact_subcategory="Energy",
            value="3.8",
            confidence=0.96
        ),
        Datapoint(
            id=48,
            aligned_datapoint="Expected Asset Lifetime",
            impact_category="Asset Integrity",
            impact_subcategory="Element Resilience",
            value="25",
            unit="years",
            confidence=0.72
        ),
    ]
    
    return AcerGraph(
        document_name="Simple Example Equipment",
        source_file="simple-example.pdf",
        extracted_at=datetime.now(),
        llm_model="demo",
        processing_time_seconds=1.0,
        
        has_metadata=Relationship(
            name="hasMetadata",
            found=True,
            value={"pageCount": 2},
            confidence=1.0,
            status=RelationshipStatus.FOUND
        ),
        
        has_equipment=Relationship(
            name="hasEquipment",
            found=True,
            value="Demo Equipment 1000",
            confidence=0.95,
            status=RelationshipStatus.FOUND
        ),
        
        has_asset_type=Relationship(
            name="hasAssetType",
            found=True,
            value="HVAC Unit",
            confidence=0.92,
            status=RelationshipStatus.FOUND
        ),
        
        has_datapoint=Relationship(
            name="hasDatapoint",
            found=True,
            value=datapoints,
            confidence=0.87,
            status=RelationshipStatus.FOUND
        ),
        
        has_impact_category=Relationship(
            name="hasImpactCategory",
            found=True,
            value="Climate Health",
            confidence=0.85,
            status=RelationshipStatus.USER_ADDED,
            source_location="User selected"
        ),
        
        has_requirement_source=Relationship(
            name="hasRequirementSource",
            found=True,
            value=["EU Tax", "LEED v4"],
            confidence=0.90,
            status=RelationshipStatus.USER_ADDED,
            source_location="User selected"
        )
    )
