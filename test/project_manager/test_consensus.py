"""
Unit tests for multi-model consensus calculation engine.

Tests the ConsensusCalculator class with various input combinations,
edge cases, and performance requirements.
"""

import pytest
from typing import List
from src.task_manager.consensus import ConsensusCalculator, ValidationInput
from src.task_manager.models import ConsensusResult, AgreementLevel


class TestConsensusCalculator:
    """Test suite for ConsensusCalculator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = ConsensusCalculator()

    def test_single_validation(self):
        """Test consensus calculation with single validation."""
        validations = [
            ValidationInput(
                validator_id="claude-3-5-sonnet-20241022",
                outcome="validated",
                confidence=85
            )
        ]

        result = self.calculator.calculate_consensus(validations)

        assert result.consensus == 1.0
        assert result.outcome == "validated"
        assert result.agreement_level == AgreementLevel.UNANIMOUS
        assert result.model_disagreement is False
        assert result.total_validations == 1
        assert result.weighted_confidence == 0.85

    def test_unanimous_agreement(self):
        """Test consensus with all models agreeing."""
        validations = [
            ValidationInput("claude-3-5-sonnet", "validated", 90),
            ValidationInput("gpt-4", "validated", 85),
            ValidationInput("gemini-pro", "validated", 88)
        ]

        result = self.calculator.calculate_consensus(validations)

        assert result.consensus == 1.0
        assert result.outcome == "validated"
        assert result.agreement_level == AgreementLevel.UNANIMOUS
        assert result.model_disagreement is False
        assert result.model_breakdown["validated"] == 3

    def test_mixed_outcomes_moderate_consensus(self):
        """Test consensus with mixed outcomes resulting in moderate agreement."""
        validations = [
            ValidationInput("claude-3-5-sonnet", "validated", 80),
            ValidationInput("gpt-4", "validated", 75),
            ValidationInput("gemini-pro", "rejected", 70)
        ]

        result = self.calculator.calculate_consensus(validations)

        # Should be between 0.5-0.74 for moderate
        assert 0.5 <= result.consensus < 0.75
        assert result.outcome == "validated"  # Majority
        assert result.agreement_level == AgreementLevel.MODERATE
        assert result.model_disagreement is True  # <75%

    def test_perfect_tie_handling(self):
        """Test handling of perfect ties between outcomes."""
        validations = [
            ValidationInput("claude-3-5-sonnet", "validated", 80),
            ValidationInput("gpt-4", "rejected", 80)
        ]

        result = self.calculator.calculate_consensus(validations)

        # Should default to partial for ties
        assert result.outcome == "partial"
        assert result.model_disagreement is True

    def test_weighted_calculation_different_models(self):
        """Test that different model weights affect consensus calculation."""
        # High-weight model says validated, low-weight says rejected
        validations = [
            ValidationInput("claude-3-5-sonnet", "validated", 90),  # weight 1.0
            ValidationInput("unknown-model", "rejected", 90)        # weight 0.7
        ]

        result = self.calculator.calculate_consensus(validations)

        # Claude should have more influence due to higher weight
        assert result.consensus > 0.5
        assert result.outcome == "validated"

    def test_confidence_weighting(self):
        """Test that confidence levels affect consensus calculation."""
        validations = [
            ValidationInput("claude-3-5-sonnet", "validated", 95),  # High confidence
            ValidationInput("gpt-4", "rejected", 30)               # Low confidence
        ]

        result = self.calculator.calculate_consensus(validations)

        # High confidence validation should dominate
        assert result.consensus > 0.7
        assert result.outcome == "validated"

    def test_agreement_level_classification(self):
        """Test proper classification of agreement levels."""
        # Test weak agreement (<50%)
        validations_weak = [
            ValidationInput("model1", "rejected", 90),
            ValidationInput("model2", "validated", 30)
        ]
        result_weak = self.calculator.calculate_consensus(validations_weak)
        assert result_weak.agreement_level == AgreementLevel.WEAK

        # Test strong agreement (75-89%)
        validations_strong = [
            ValidationInput("model1", "validated", 90),
            ValidationInput("model2", "validated", 85),
            ValidationInput("model3", "partial", 80)
        ]
        result_strong = self.calculator.calculate_consensus(validations_strong)
        assert result_strong.agreement_level in [AgreementLevel.STRONG, AgreementLevel.UNANIMOUS]

    def test_model_breakdown_accuracy(self):
        """Test that model breakdown counts are accurate."""
        validations = [
            ValidationInput("model1", "validated", 80),
            ValidationInput("model2", "validated", 85),
            ValidationInput("model3", "rejected", 75),
            ValidationInput("model4", "partial", 70)
        ]

        result = self.calculator.calculate_consensus(validations)

        assert result.model_breakdown["validated"] == 2
        assert result.model_breakdown["rejected"] == 1
        assert result.model_breakdown["partial"] == 1
        assert result.total_validations == 4

    def test_empty_validations_error(self):
        """Test that empty validations list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot calculate consensus with empty validations"):
            self.calculator.calculate_consensus([])

    def test_invalid_outcome_error(self):
        """Test that invalid outcomes raise ValueError."""
        validations = [
            ValidationInput("model1", "invalid_outcome", 80)
        ]

        with pytest.raises(ValueError, match="Invalid outcome"):
            self.calculator.calculate_consensus(validations)

    def test_invalid_confidence_error(self):
        """Test that invalid confidence values raise ValueError."""
        validations = [
            ValidationInput("model1", "validated", 150)  # >100
        ]

        with pytest.raises(ValueError, match="Invalid confidence"):
            self.calculator.calculate_consensus(validations)

        validations = [
            ValidationInput("model1", "validated", -10)  # <0
        ]

        with pytest.raises(ValueError, match="Invalid confidence"):
            self.calculator.calculate_consensus(validations)

    def test_custom_model_weights(self):
        """Test calculator with custom model weights."""
        custom_weights = {
            "super-model": 2.0,
            "weak-model": 0.1,
            "default": 0.5
        }

        calculator = ConsensusCalculator(model_weights=custom_weights)

        validations = [
            ValidationInput("super-model", "validated", 80),
            ValidationInput("weak-model", "rejected", 80)
        ]

        result = calculator.calculate_consensus(validations)

        # Super model should dominate due to much higher weight
        assert result.consensus > 0.8
        assert result.outcome == "validated"

    def test_performance_large_dataset(self):
        """Test performance with large validation dataset."""
        import time

        # Create 100 validations
        validations = []
        for i in range(100):
            model_id = f"model-{i % 10}"
            outcome = ["validated", "rejected", "partial"][i % 3]
            confidence = 70 + (i % 30)
            validations.append(ValidationInput(model_id, outcome, confidence))

        start_time = time.time()
        result = self.calculator.calculate_consensus(validations)
        end_time = time.time()

        # Should complete in under 100ms as per requirements
        processing_time = (end_time - start_time) * 1000
        assert processing_time < 100, f"Processing took {processing_time:.2f}ms, expected <100ms"

        # Verify result is valid
        assert 0.0 <= result.consensus <= 1.0
        assert result.total_validations == 100
        assert result.outcome in ["validated", "rejected", "partial"]

    def test_edge_case_zero_confidence(self):
        """Test handling of zero confidence validations."""
        validations = [
            ValidationInput("model1", "validated", 0),
            ValidationInput("model2", "rejected", 90)
        ]

        result = self.calculator.calculate_consensus(validations)

        # Zero confidence should have minimal impact
        assert result.consensus < 0.1
        assert result.outcome == "rejected"

    def test_edge_case_all_partial(self):
        """Test handling when all validations are partial."""
        validations = [
            ValidationInput("model1", "partial", 80),
            ValidationInput("model2", "partial", 85),
            ValidationInput("model3", "partial", 75)
        ]

        result = self.calculator.calculate_consensus(validations)

        assert result.consensus == 0.5  # Partial = 0.5 score
        assert result.outcome == "partial"
        assert result.model_breakdown["partial"] == 3

    def test_model_weight_extraction(self):
        """Test model weight extraction from validator IDs."""
        # Test known model extraction
        weight1 = self.calculator._get_model_weight("claude-3-5-sonnet-20241022")
        assert weight1 == 1.0

        weight2 = self.calculator._get_model_weight("gpt-3.5-turbo-16k")
        assert weight2 == 0.8

        # Test unknown model defaults
        weight3 = self.calculator._get_model_weight("unknown-model-v1")
        assert weight3 == 0.7

    def test_disagreement_detection(self):
        """Test model disagreement detection logic."""
        # Strong disagreement case
        validations_disagree = [
            ValidationInput("model1", "validated", 90),
            ValidationInput("model2", "rejected", 90)
        ]
        result_disagree = self.calculator.calculate_consensus(validations_disagree)
        assert result_disagree.model_disagreement is True

        # Strong agreement case
        validations_agree = [
            ValidationInput("model1", "validated", 90),
            ValidationInput("model2", "validated", 85),
            ValidationInput("model3", "validated", 88)
        ]
        result_agree = self.calculator.calculate_consensus(validations_agree)
        assert result_agree.model_disagreement is False

    def test_weighted_confidence_calculation(self):
        """Test weighted confidence calculation accuracy."""
        validations = [
            ValidationInput("claude-3-5-sonnet", "validated", 90),  # weight 1.0
            ValidationInput("gpt-3.5-turbo", "validated", 60)      # weight 0.8
        ]

        result = self.calculator.calculate_consensus(validations)

        # Expected: (1.0 * 0.9 + 0.8 * 0.6) / (1.0 + 0.8) = 1.38 / 1.8 = 0.767
        expected_confidence = (1.0 * 0.9 + 0.8 * 0.6) / (1.0 + 0.8)
        assert abs(result.weighted_confidence - expected_confidence) < 0.01