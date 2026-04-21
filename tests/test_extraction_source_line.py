"""Tests for extraction.py mock data — verifies source_line is present in mock datapoints."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.extraction import extract_from_text, Datapoint


class TestMockExtractionSourceLine:
    """Test that the mock extraction pipeline populates source_line."""

    def test_capacity_datapoint_has_source_line(self):
        """Mock extraction for Cooling Capacity must include source_line."""
        text = "Cooling Capacity: 12.5 tons"
        result = extract_from_text("test.pdf", text)
        datapoints = result["datapoints"]

        capacity_dps = [dp for dp in datapoints if dp.aligned_datapoint == "Cooling Capacity"]
        assert len(capacity_dps) >= 1, f"Expected at least 1 Cooling Capacity datapoint, got {len(capacity_dps)}"

        dp = capacity_dps[0]
        assert dp.source_line is not None, (
            "Cooling Capacity datapoint must have source_line set. "
            "Found: source_page={}, source_line={}".format(dp.source_page, dp.source_line)
        )
        assert isinstance(dp.source_line, int), (
            f"source_line must be int, got {type(dp.source_line).__name__}: {dp.source_line}"
        )

    def test_eer_datapoint_has_source_line(self):
        """Mock extraction for EER must include source_line."""
        text = "EER: 10.5"
        result = extract_from_text("test.pdf", text)
        datapoints = result["datapoints"]

        eer_dps = [dp for dp in datapoints if dp.aligned_datapoint == "Energy Efficiency Ratio"]
        assert len(eer_dps) >= 1, f"Expected at least 1 EER datapoint, got {len(eer_dps)}"

        dp = eer_dps[0]
        assert dp.source_line is not None, (
            "EER datapoint must have source_line set. "
            "Found: source_page={}, source_line={}".format(dp.source_page, dp.source_line)
        )
        assert isinstance(dp.source_line, int)

    def test_source_line_is_not_zero(self):
        """source_line must be a positive integer, not 0 or negative."""
        text = "Capacity: 5.0 tons EER: 12.0"
        result = extract_from_text("test.pdf", text)
        for dp in result["datapoints"]:
            if dp.source_line is not None:
                assert dp.source_line > 0, (
                    f"source_line must be positive, got {dp.source_line} for {dp.aligned_datapoint}"
                )

    def test_source_page_is_preserved(self):
        """source_page must be set alongside source_line."""
        text = "Cooling Capacity: 8.0 tons"
        result = extract_from_text("test.pdf", text)
        datapoints = result["datapoints"]

        assert len(datapoints) >= 1
        dp = datapoints[0]
        assert dp.source_page is not None, "source_page must be set"
        assert dp.source_location is not None, "source_location should be set too"
