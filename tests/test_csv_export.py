"""Tests for CSV export functionality."""
import pytest
from src.models.acer_graph import AcerGraph, Relationship, Datapoint, RelationshipStatus


class TestDatapointSourceFields:
    """Unit tests for Datapoint source fields."""

    def test_datapoint_source_line_is_optional_int(self):
        """source_line must be Optional[int], not a string."""
        dp = Datapoint(
            id=1,
            aligned_datapoint="Cooling Capacity",
            impact_category="Energy Performance",
            impact_subcategory="Capacity",
            value="12.5",
            unit="kW",
            source_page="3",
            source_line=42,
            source_location="Specifications Table",
        )
        assert dp.source_line == 42
        assert isinstance(dp.source_line, int)

    def test_datapoint_source_line_none(self):
        """source_line can be None when unknown."""
        dp = Datapoint(
            id=1,
            aligned_datapoint="Efficiency Ratio",
            impact_category="Energy Performance",
            impact_subcategory="Efficiency Rating",
            value="10.5",
            source_page="2",
            source_line=None,
        )
        assert dp.source_line is None

    def test_datapoint_to_dict_includes_source_line(self):
        """to_dict() must include sourceLine field."""
        dp = Datapoint(
            id=1,
            aligned_datapoint="Cooling Capacity",
            impact_category="Energy Performance",
            impact_subcategory="Capacity",
            value="12.5",
            source_page="3",
            source_line=17,
            source_location="Specs",
        )
        d = dp.to_dict()
        assert "sourceLine" in d
        assert d["sourceLine"] == 17

    def test_datapoint_to_dict_source_line_none(self):
        """to_dict() includes sourceLine as None when not set."""
        dp = Datapoint(
            id=1,
            aligned_datapoint="Efficiency Ratio",
            impact_category="Energy Performance",
            impact_subcategory="Efficiency Rating",
            value="10.5",
        )
        d = dp.to_dict()
        assert "sourceLine" in d
        assert d["sourceLine"] is None


class TestAcerGraphToCsv:
    """Tests for AcerGraph.to_csv()."""

    def _graph_with_datapoints(self) -> AcerGraph:
        """Build a graph with two datapoints for CSV export tests."""
        dp1 = Datapoint(
            id=1,
            aligned_datapoint="Cooling Capacity",
            impact_category="Energy Performance",
            impact_subcategory="Capacity",
            value="12.5",
            unit="kW",
            confidence=0.92,
            source_page="1",
            source_line=14,
            source_location="Specifications",
        )
        dp2 = Datapoint(
            id=2,
            aligned_datapoint="Energy Efficiency Ratio",
            impact_category="Energy Performance",
            impact_subcategory="Efficiency Rating",
            value="10.2",
            unit="",
            confidence=0.95,
            source_page="1",
            source_line=18,
            source_location="Ratings Table",
        )
        graph = AcerGraph(document_name="RTU-SpecSheet.pdf")
        graph.has_datapoint = Relationship(
            name="has_datapoint",
            found=True,
            value=[dp1, dp2],
            status=RelationshipStatus.FOUND,
        )
        return graph

    def test_csv_returns_string(self):
        """to_csv() must return a string."""
        graph = self._graph_with_datapoints()
        result = graph.to_csv()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_csv_header_row(self):
        """CSV must contain all required column headers."""
        graph = self._graph_with_datapoints()
        result = graph.to_csv()
        header = result.splitlines()[0]
        assert "Datapoint ID" in header
        assert "Aligned Datapoint" in header
        assert "Value" in header
        assert "Unit" in header
        assert "Impact Category" in header
        assert "Impact Subcategory" in header
        assert "Confidence" in header
        assert "Source Page" in header
        assert "Source Line" in header
        assert "Source Location" in header
        assert "Status" in header

    def test_csv_source_line_column_has_int_value(self):
        """Source Line column must contain integer values, not empty strings for known lines."""
        graph = self._graph_with_datapoints()
        result = graph.to_csv()
        lines = result.splitlines()
        # Line 1 is header, line 2 is first datapoint
        data_row = lines[1]
        cols = data_row.split(",")
        # Source Line is column index 8 (0-indexed: ID=0, Aligned=1, Value=2, Unit=3,
        # ImpactCat=4, ImpactSub=5, Confidence=6, SourcePage=7, SourceLine=8)
        source_line_col = cols[8].strip('"')
        assert source_line_col == "14", f"Expected '14' but got '{source_line_col}'"
        assert source_line_col.isdigit(), f"Source line must be numeric, got: {source_line_col}"

    def test_csv_source_line_empty_when_none(self):
        """Source Line column must be empty string when source_line is None."""
        dp = Datapoint(
            id=99,
            aligned_datapoint="Airflow Rate",
            impact_category="Energy Performance",
            impact_subcategory="Airflow",
            value="400",
            unit="CFM",
            source_page="2",
            source_line=None,
        )
        graph = AcerGraph(document_name="test.pdf")
        graph.has_datapoint = Relationship(
            name="has_datapoint",
            found=True,
            value=[dp],
            status=RelationshipStatus.FOUND,
        )
        result = graph.to_csv()
        data_row = result.splitlines()[1]
        # Find the Source Line column (8th, 0-indexed)
        cols = data_row.split(",")
        source_line_col = cols[8].strip('"')
        assert source_line_col == "", f"Expected empty string for None source_line, got: '{source_line_col}'"

    def test_csv_row_count_matches_datapoints(self):
        """CSV must have one data row per datapoint."""
        graph = self._graph_with_datapoints()
        result = graph.to_csv()
        lines = result.splitlines()
        # 1 header + 2 datapoints = 3 lines
        assert len(lines) == 3, f"Expected 3 lines (header + 2 data), got {len(lines)}: {lines}"

    def test_csv_confidence_is_percentage_string(self):
        """Confidence column must be a percentage string like '92.0%'."""
        graph = self._graph_with_datapoints()
        result = graph.to_csv()
        data_row = result.splitlines()[1]
        cols = data_row.split(",")
        confidence_col = cols[6].strip('"')
        assert "%" in confidence_col
        assert confidence_col.replace("%", "").replace(".", "").isdigit()

    def test_csv_no_datapoints_returns_header_only(self):
        """to_csv() on a graph with no datapoints returns header only."""
        graph = AcerGraph(document_name="empty.pdf")
        graph.has_datapoint = Relationship(
            name="has_datapoint",
            found=True,
            value=[],
            status=RelationshipStatus.FOUND,
        )
        result = graph.to_csv()
        lines = result.splitlines()
        assert len(lines) == 1  # header only
        assert "Datapoint ID" in lines[0]
