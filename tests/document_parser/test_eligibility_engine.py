"""Tests for eligibility engine."""

import pytest

from app.document_parser.eligibility_engine import (
    EWS_THRESHOLD,
    LIG_THRESHOLD,
    MIG_THRESHOLD,
    EligibilityEngine,
)


class TestEligibilityDetermination:
    """Test eligibility determination."""

    def setup_method(self):
        """Setup test fixtures."""
        self.engine = EligibilityEngine()

    def test_ews_eligibility(self):
        """Test EWS category determination."""
        result = self.engine.determine_eligibility(250000)
        assert result.category == "EWS"
        assert result.isEligible is True
        assert "PMAY-EWS" in result.eligibleSchemes

    def test_ews_threshold_boundary(self):
        """Test EWS threshold boundary."""
        result = self.engine.determine_eligibility(300000)
        assert result.category == "EWS"
        assert result.isEligible is True

    def test_lig_eligibility(self):
        """Test LIG category determination."""
        result = self.engine.determine_eligibility(450000)
        assert result.category == "LIG"
        assert result.isEligible is True
        assert "PMAY-LIG" in result.eligibleSchemes

    def test_lig_threshold_boundary(self):
        """Test LIG threshold boundary."""
        result = self.engine.determine_eligibility(600000)
        assert result.category == "LIG"
        assert result.isEligible is True

    def test_mig_eligibility(self):
        """Test MIG category determination."""
        result = self.engine.determine_eligibility(1200000)
        assert result.category == "MIG"
        assert result.isEligible is True
        assert "PMAY-MIG" in result.eligibleSchemes

    def test_not_eligible(self):
        """Test not eligible category."""
        result = self.engine.determine_eligibility(2000000)
        assert result.category == "Not Eligible"
        assert result.isEligible is False
        assert len(result.eligibleSchemes) == 0

    def test_large_family_ews(self):
        """Test large family EWS benefits."""
        result = self.engine.determine_eligibility(250000, family_count=5)
        assert result.category == "EWS"
        assert "Large Family EWS Subsidy" in result.eligibleSchemes

    def test_validate_ews(self):
        """Test EWS validation."""
        assert self.engine.validate_ews_eligibility(250000) is True
        assert self.engine.validate_ews_eligibility(300000) is True
        assert self.engine.validate_ews_eligibility(350000) is False

    def test_validate_lig(self):
        """Test LIG validation."""
        assert self.engine.validate_lig_eligibility(450000) is True
        assert self.engine.validate_lig_eligibility(600000) is True
        assert self.engine.validate_lig_eligibility(700000) is False

    def test_pmay_eligibility(self):
        """Test PMAY eligibility validation."""
        assert self.engine.validate_pmay_eligibility(250000, 4, False) is True
        assert self.engine.validate_pmay_eligibility(2000000, 4, False) is False
        assert self.engine.validate_pmay_eligibility(250000, 4, True) is False
        assert self.engine.validate_pmay_eligibility(250000, 0, False) is False


class TestEligibilityReasons:
    """Test eligibility reason generation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.engine = EligibilityEngine()

    def test_ews_reason(self):
        """Test EWS reason message."""
        result = self.engine.determine_eligibility(250000)
        assert "EWS" in result.reason
        assert "250,000" in result.reason

    def test_not_eligible_reason(self):
        """Test not eligible reason message."""
        result = self.engine.determine_eligibility(2000000)
        assert "Not eligible" in result.reason
        assert "exceeds" in result.reason
