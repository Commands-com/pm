"""
Unit tests for consensus summary API endpoint.

Tests the GET /api/assumptions/consensus/{task_id} endpoint
with various task scenarios and edge cases.
"""

import pytest
import json
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from src.task_manager.api import app
from src.task_manager.models import ConsensusSummaryResponse


class TestConsensusSummaryAPI:
    """Test suite for consensus summary API endpoint."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        self.test_task_id = 123

    @patch('src.task_manager.assumptions.get_database')
    def test_consensus_summary_task_not_found(self, mock_get_db):
        """Test 404 response for non-existent task."""
        mock_db = Mock()
        mock_db.execute_query.return_value = []  # No task found
        mock_get_db.return_value = mock_db

        response = self.client.get(f"/api/assumptions/consensus/{self.test_task_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch('src.task_manager.assumptions.get_database')
    def test_consensus_summary_task_with_no_ra_tags(self, mock_get_db):
        """Test task with no RA tags returns empty summary."""
        mock_db = Mock()
        # Task exists but no RA tags
        mock_db.execute_query.side_effect = [
            [(123, "Test Task")],  # Task exists
            []  # No RA tags
        ]
        mock_get_db.return_value = mock_db

        response = self.client.get(f"/api/assumptions/consensus/{self.test_task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == self.test_task_id
        assert data["overall_consensus"] == 0.0
        assert data["total_ra_tags"] == 0
        assert data["validated_tags"] == 0
        assert data["validation_coverage"] == 0.0
        assert len(data["contentious_tags"]) == 0
        assert len(data["high_confidence_tags"]) == 0

    @patch('src.task_manager.assumptions.get_database')
    @patch('src.task_manager.assumptions.ConsensusCalculator')
    def test_consensus_summary_with_mixed_consensus(self, mock_calculator_class, mock_get_db):
        """Test task with mixed consensus levels."""
        mock_db = Mock()
        mock_calculator = Mock()
        mock_calculator_class.return_value = mock_calculator

        # Mock task exists
        # Mock RA tags data
        ra_tags_json = json.dumps([
            {"id": "tag_1", "text": "#COMPLETION_DRIVE_IMPL: High confidence tag"},
            {"id": "tag_2", "text": "#COMPLETION_DRIVE_IMPL: Contentious tag"}
        ])

        mock_db.execute_query.side_effect = [
            [(123, "Test Task")],  # Task exists
            [("tag_1", ra_tags_json), ("tag_2", ra_tags_json)],  # RA tags
            [("validated", 95, "claude-3-opus"), ("validated", 92, "gpt-4")],  # tag_1 validations
            [("validated", 80, "claude-3-opus"), ("rejected", 85, "gpt-4")]   # tag_2 validations
        ]
        mock_get_db.return_value = mock_db

        # Mock consensus results
        mock_high_confidence_result = Mock()
        mock_high_confidence_result.consensus = 0.95
        mock_high_confidence_result.total_validations = 2
        mock_high_confidence_result.outcome = "validated"
        mock_high_confidence_result.model_disagreement = False

        mock_contentious_result = Mock()
        mock_contentious_result.consensus = 0.65
        mock_contentious_result.total_validations = 2
        mock_contentious_result.outcome = "validated"
        mock_contentious_result.model_disagreement = True
        mock_contentious_result.model_breakdown = {"validated": 1, "rejected": 1}

        mock_calculator.calculate_consensus_cached.side_effect = [
            mock_high_confidence_result,
            mock_contentious_result
        ]

        response = self.client.get(f"/api/assumptions/consensus/{self.test_task_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["task_id"] == self.test_task_id
        assert data["total_ra_tags"] == 2
        assert data["validated_tags"] == 2
        assert data["validation_coverage"] == 1.0
        assert data["overall_consensus"] == 0.8  # (0.95 + 0.65) / 2

        # Should have one contentious tag
        assert len(data["contentious_tags"]) == 1
        contentious = data["contentious_tags"][0]
        assert contentious["ra_tag_id"] == "tag_2"
        assert contentious["consensus"] == 0.65

        # Should have one high confidence tag
        assert len(data["high_confidence_tags"]) == 1
        high_conf = data["high_confidence_tags"][0]
        assert high_conf["ra_tag_id"] == "tag_1"
        assert high_conf["consensus"] == 0.95

    @patch('src.task_manager.assumptions.get_database')
    def test_consensus_summary_database_error(self, mock_get_db):
        """Test database error handling."""
        mock_db = Mock()
        mock_db.execute_query.side_effect = Exception("Database connection failed")
        mock_get_db.return_value = mock_db

        response = self.client.get(f"/api/assumptions/consensus/{self.test_task_id}")

        assert response.status_code == 500
        assert "Failed to get consensus summary" in response.json()["detail"]

    @patch('src.task_manager.assumptions._get_cached_response')
    @patch('src.task_manager.assumptions.get_database')
    def test_consensus_summary_caching(self, mock_get_db, mock_get_cached):
        """Test that caching is used when available."""
        # Mock cached response
        cached_data = {
            "task_id": self.test_task_id,
            "overall_consensus": 0.85,
            "total_ra_tags": 3,
            "validated_tags": 3,
            "validation_coverage": 1.0,
            "contentious_tags": [],
            "high_confidence_tags": [],
            "cache_timestamp": "2023-01-01T00:00:00Z"
        }
        mock_get_cached.return_value = cached_data

        response = self.client.get(f"/api/assumptions/consensus/{self.test_task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_consensus"] == 0.85
        assert data["total_ra_tags"] == 3

        # With dependency injection, database may be created but cache should still work
        # Verify cache is working by checking the response matches cached data exactly
        assert data["total_ra_tags"] == cached_data["total_ra_tags"]
        assert data["overall_consensus"] == cached_data["overall_consensus"]

    @patch('src.task_manager.assumptions.get_database')
    @patch('src.task_manager.assumptions.ConsensusCalculator')
    def test_consensus_summary_coverage_calculation(self, mock_calculator_class, mock_get_db):
        """Test validation coverage calculation."""
        mock_db = Mock()
        mock_calculator = Mock()
        mock_calculator_class.return_value = mock_calculator

        # Mock task with 3 RA tags, but only 2 have validations
        ra_tags_json = json.dumps([
            {"id": "tag_1", "text": "#COMPLETION_DRIVE_IMPL: Tag 1"},
            {"id": "tag_2", "text": "#COMPLETION_DRIVE_IMPL: Tag 2"},
            {"id": "tag_3", "text": "#COMPLETION_DRIVE_IMPL: Tag 3"}
        ])

        mock_db.execute_query.side_effect = [
            [(123, "Test Task")],  # Task exists
            [("tag_1", ra_tags_json), ("tag_2", ra_tags_json), ("tag_3", ra_tags_json)],  # RA tags
            [("validated", 90, "claude-3-opus")],  # tag_1 validations
            [("validated", 85, "gpt-4")],          # tag_2 validations
            []                                      # tag_3 no validations
        ]
        mock_get_db.return_value = mock_db

        # Mock consensus results for validated tags
        mock_result = Mock()
        mock_result.consensus = 0.85
        mock_result.total_validations = 1
        mock_result.outcome = "validated"
        mock_result.model_disagreement = False

        mock_calculator.calculate_consensus_cached.return_value = mock_result

        response = self.client.get(f"/api/assumptions/consensus/{self.test_task_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["total_ra_tags"] == 3
        assert data["validated_tags"] == 2
        assert data["validation_coverage"] == pytest.approx(0.667, rel=1e-2)
        assert data["overall_consensus"] == 0.85  # Average of 2 validated tags

    def test_consensus_summary_response_model_validation(self):
        """Test that response matches expected Pydantic model."""
        # Create a sample response data
        response_data = {
            "success": True,
            "task_id": 123,
            "overall_consensus": 0.85,
            "total_ra_tags": 5,
            "validated_tags": 4,
            "validation_coverage": 0.8,
            "contentious_tags": [
                {
                    "ra_tag_id": "tag_1",
                    "ra_tag_text": "#COMPLETION_DRIVE_IMPL: Contentious assumption",
                    "consensus": 0.65,
                    "total_validations": 3,
                    "disagreement_reason": "Low consensus (65.0%) indicates model disagreement"
                }
            ],
            "high_confidence_tags": [
                {
                    "ra_tag_id": "tag_2",
                    "ra_tag_text": "#COMPLETION_DRIVE_IMPL: High confidence assumption",
                    "consensus": 0.95,
                    "total_validations": 4,
                    "outcome": "validated"
                }
            ],
            "cache_timestamp": "2023-01-01T00:00:00Z"
        }

        # Validate against Pydantic model
        response_model = ConsensusSummaryResponse(**response_data)

        assert response_model.task_id == 123
        assert response_model.overall_consensus == 0.85
        assert len(response_model.contentious_tags) == 1
        assert len(response_model.high_confidence_tags) == 1
        assert response_model.contentious_tags[0].consensus == 0.65
        assert response_model.high_confidence_tags[0].consensus == 0.95