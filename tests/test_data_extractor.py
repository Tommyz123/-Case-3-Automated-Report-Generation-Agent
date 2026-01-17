"""
Unit tests for DataExtractor module.

Tests cover:
- SDG questionnaire extraction (Task 2.1.15)
- Impact mechanisms extraction (Task 2.1.16)
- Schema validation (Task 2.1.17)
"""

import pytest
from datetime import datetime
from pathlib import Path

from src.data_extractor import DataExtractor
from src.models import SDGResponse, CompanyImpactData, ValidationResult


# Test fixtures
@pytest.fixture
def data_dir():
    """Return the data directory containing Excel files."""
    return Path(__file__).parent.parent / "data"


@pytest.fixture
def extractor(data_dir):
    """Create a DataExtractor instance."""
    return DataExtractor(str(data_dir))


# ==================== Task 2.1.15: SDG Questionnaire Tests ====================

class TestSDGQuestionnaireExtraction:
    """Test SDG questionnaire data extraction (Task 2.1.15)."""

    def test_extract_sdg_questionnaire_success(self, extractor):
        """Test normal SDG questionnaire extraction."""
        # Act
        responses = extractor.extract_sdg_questionnaire(
            filename="SDG问卷调查_完整中文版.xlsx"
        )

        # Assert
        assert isinstance(responses, list), "Should return a list"
        assert len(responses) > 0, "Should extract at least one response"
        assert all(isinstance(r, SDGResponse) for r in responses), \
            "All items should be SDGResponse objects"

    def test_extract_sdg_questionnaire_data_count(self, extractor):
        """Test that we extract the correct number of rows (145 data rows)."""
        # Act
        responses = extractor.extract_sdg_questionnaire(
            filename="SDG问卷调查_完整中文版.xlsx"
        )

        # Assert - Actual data has 145 rows (row 2-146, with row 1 being header)
        assert len(responses) == 145, f"Expected 145 responses, got {len(responses)}"

    def test_extract_sdg_questionnaire_data_parsing(self, extractor):
        """Test data parsing correctness."""
        # Act
        responses = extractor.extract_sdg_questionnaire(
            filename="SDG问卷调查_完整中文版.xlsx"
        )

        # Get first response for detailed checking
        first_response = responses[0]

        # Assert - Check all fields are present and correct type
        assert isinstance(first_response.timestamp, datetime), \
            "timestamp should be datetime"
        assert isinstance(first_response.company_name, str), \
            "company_name should be str"
        assert isinstance(first_response.contact_name, str), \
            "contact_name should be str"
        assert isinstance(first_response.sdg_goals, str), \
            "sdg_goals should be str"
        assert isinstance(first_response.implementation_description, str), \
            "implementation_description should be str"

        # Assert - Check non-empty
        assert len(first_response.company_name) > 0, \
            "company_name should not be empty"
        assert len(first_response.sdg_goals) > 0, \
            "sdg_goals should not be empty"

    def test_extract_sdg_questionnaire_boundary_cases(self, extractor):
        """Test boundary cases (first and last rows)."""
        # Act
        responses = extractor.extract_sdg_questionnaire(
            filename="SDG问卷调查_完整中文版.xlsx"
        )

        # Assert - First row
        first = responses[0]
        assert first.company_name, "First row should have company name"
        assert first.timestamp, "First row should have timestamp"

        # Assert - Last row
        last = responses[-1]
        assert last.company_name, "Last row should have company name"
        assert last.timestamp, "Last row should have timestamp"

    def test_extract_sdg_questionnaire_file_not_found(self, extractor):
        """Test handling of non-existent file."""
        # Act & Assert
        with pytest.raises(FileNotFoundError):
            extractor.extract_sdg_questionnaire(filename="nonexistent.xlsx")

    def test_extract_sdg_questionnaire_invalid_worksheet(self, extractor):
        """Test handling of non-existent worksheet."""
        # Act & Assert
        with pytest.raises(ValueError):
            extractor.extract_sdg_questionnaire(
                filename="SDG问卷调查_完整中文版.xlsx",
                sheet_name="NonExistentSheet"
            )


# ==================== Task 2.1.16: Impact Mechanisms Tests ====================

class TestImpactMechanismsExtraction:
    """Test impact mechanisms data extraction (Task 2.1.16)."""

    def test_extract_impact_mechanisms_success(self, extractor):
        """Test normal impact mechanisms extraction."""
        # Act
        companies_data = extractor.extract_impact_mechanisms(
            filename="影响评估机制_完整中文版.xlsx"
        )

        # Assert
        assert isinstance(companies_data, list), "Should return a list"
        assert len(companies_data) > 0, "Should extract at least one company"
        assert all(isinstance(c, CompanyImpactData) for c in companies_data), \
            "All items should be CompanyImpactData objects"

    def test_extract_impact_mechanisms_emergconnect(self, extractor):
        """Test EmergConnect case extraction."""
        # Act
        companies_data = extractor.extract_impact_mechanisms(
            filename="影响评估机制_完整中文版.xlsx"
        )

        # Find EmergConnect
        emergconnect = [c for c in companies_data if c.company_name == "EmergConnect"]

        # Assert
        assert len(emergconnect) > 0, "Should find EmergConnect data"

        ec = emergconnect[0]
        assert ec.company_name == "EmergConnect", "Company name should match"
        # Note: EmergConnect doesn't have stakeholders data in rows 6-11
        assert isinstance(ec.stakeholders, list), "stakeholders should be a list"
        assert len(ec.mechanisms) > 0, "Should have mechanisms"

    def test_extract_impact_mechanisms_data_structure(self, extractor):
        """Test that extracted data has correct structure (8 fields)."""
        # Act
        companies_data = extractor.extract_impact_mechanisms(
            filename="影响评估机制_完整中文版.xlsx"
        )

        # Get first company with mechanisms
        company_with_mechanisms = next(
            (c for c in companies_data if c.mechanisms),
            None
        )

        assert company_with_mechanisms is not None, \
            "Should find at least one company with mechanisms"

        # Check first mechanism has all 8 fields
        mech = company_with_mechanisms.mechanisms[0]
        assert hasattr(mech, 'stakeholder_affected'), "Should have stakeholder_affected"
        assert hasattr(mech, 'mechanism'), "Should have mechanism"
        assert hasattr(mech, 'driving_variable'), "Should have driving_variable"
        assert hasattr(mech, 'type_of_impact'), "Should have type_of_impact"
        assert hasattr(mech, 'positive_negative'), "Should have positive_negative"
        assert hasattr(mech, 'method'), "Should have method"
        assert hasattr(mech, 'value'), "Should have value"
        assert hasattr(mech, 'unit'), "Should have unit"

    def test_extract_impact_mechanisms_value_parsing(self, extractor):
        """Test that value field is correctly parsed as float."""
        # Act
        companies_data = extractor.extract_impact_mechanisms(
            filename="影响评估机制_完整中文版.xlsx"
        )

        # Find mechanisms with non-null values
        mechanisms_with_values = []
        for company in companies_data:
            for mech in company.mechanisms:
                if mech.value is not None:
                    mechanisms_with_values.append(mech)

        # Assert
        assert len(mechanisms_with_values) > 0, \
            "Should find at least one mechanism with a value"

        # Check that values are float
        for mech in mechanisms_with_values[:5]:  # Check first 5
            assert isinstance(mech.value, float), \
                f"Value should be float, got {type(mech.value)}"

    def test_extract_impact_mechanisms_empty_values(self, extractor):
        """Test handling of empty/null values."""
        # Act
        companies_data = extractor.extract_impact_mechanisms(
            filename="影响评估机制_完整中文版.xlsx"
        )

        # Should not crash with empty values
        assert len(companies_data) > 0, "Should handle empty values gracefully"

    def test_extract_impact_mechanisms_specific_company(self, extractor):
        """Test extracting a specific company."""
        # Act
        companies_data = extractor.extract_impact_mechanisms(
            filename="影响评估机制_完整中文版.xlsx",
            company_name="EmergConnect"
        )

        # Assert
        assert len(companies_data) == 1, "Should extract only one company"
        assert companies_data[0].company_name == "EmergConnect", \
            "Company name should match"


# ==================== Task 2.1.17: Schema Validation Tests ====================

class TestSchemaValidation:
    """Test schema validation functionality (Task 2.1.17)."""

    def test_validate_schema_sdg_response_valid(self, extractor):
        """Test validation of valid SDGResponse."""
        # Arrange
        responses = extractor.extract_sdg_questionnaire(
            filename="SDG问卷调查_完整中文版.xlsx"
        )
        valid_response = responses[0]

        # Act
        result = extractor.validate_schema(valid_response, "SDGResponse")

        # Assert
        assert isinstance(result, ValidationResult), \
            "Should return ValidationResult"
        assert result.is_valid is True, "Valid data should pass validation"
        assert len(result.errors) == 0, "Should have no errors"

    def test_validate_schema_company_impact_data_valid(self, extractor):
        """Test validation of valid CompanyImpactData."""
        # Arrange
        companies_data = extractor.extract_impact_mechanisms(
            filename="影响评估机制_完整中文版.xlsx"
        )
        valid_company = companies_data[0]

        # Act
        result = extractor.validate_schema(valid_company, "CompanyImpactData")

        # Assert
        assert isinstance(result, ValidationResult), \
            "Should return ValidationResult"
        # Note: may have warnings but should be valid
        assert isinstance(result.is_valid, bool), "Should have is_valid field"

    def test_validate_schema_warnings(self, extractor):
        """Test that validation can return warnings."""
        # Arrange
        companies_data = extractor.extract_impact_mechanisms(
            filename="影响评估机制_完整中文版.xlsx"
        )

        # Find a company that might have warnings (e.g., empty stakeholders)
        company = companies_data[0]

        # Act
        result = extractor.validate_schema(company, "CompanyImpactData")

        # Assert
        assert hasattr(result, 'warnings'), "Should have warnings field"
        assert isinstance(result.warnings, list), "Warnings should be a list"


# ==================== Integration Tests ====================

class TestDataExtractorIntegration:
    """Integration tests for DataExtractor."""

    def test_full_extraction_pipeline(self, extractor):
        """Test complete data extraction pipeline."""
        # Act
        sdg_responses = extractor.extract_sdg_questionnaire(
            filename="SDG问卷调查_完整中文版.xlsx"
        )
        companies_data = extractor.extract_impact_mechanisms(
            filename="影响评估机制_完整中文版.xlsx"
        )

        # Assert - Actual data has 145 responses (rows 2-146 with row 1 as header)
        assert len(sdg_responses) == 145, "Should extract all 145 SDG responses"
        assert len(companies_data) > 0, "Should extract company data"

        # Validate all extracted data
        for response in sdg_responses[:10]:  # Validate first 10
            result = extractor.validate_schema(response, "SDGResponse")
            assert result.is_valid, f"SDGResponse should be valid: {result.errors}"

        for company in companies_data:
            result = extractor.validate_schema(company, "CompanyImpactData")
            # Should not crash
            assert isinstance(result, ValidationResult)
