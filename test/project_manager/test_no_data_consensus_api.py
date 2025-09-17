import json
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from src.task_manager.api import app


@patch('src.task_manager.api.get_database')
@patch('src.task_manager.assumptions.get_database')
def test_multi_model_no_data_agreement_level_no_data(mock_get_db_assumptions, mock_get_db_api):
    """Test multi-model API returns NO_DATA agreement level when no validations exist."""
    client = TestClient(app)

    # Mock database responses
    mock_db = Mock()

    # Task exists with RA tag
    task_id = 123
    ra_tag_id = "ra_tag_test_no_data"

    # Mock database connection and cursor
    mock_cursor = Mock()
    mock_connection = Mock()
    mock_connection.cursor.return_value = mock_cursor
    mock_db._connection = mock_connection
    mock_db._connection_lock = Mock()
    mock_db._connection_lock.__enter__ = Mock(return_value=None)
    mock_db._connection_lock.__exit__ = Mock(return_value=None)

    # Mock cursor.fetchone() and cursor.fetchall() responses
    mock_cursor.fetchone.return_value = (
        task_id,
        "Test Task",
        json.dumps([{
            "id": ra_tag_id,
            "type": "implementation:assumption",
            "text": "#TEST: tag"
        }])
    )
    mock_cursor.fetchall.return_value = []  # No validations exist

    mock_get_db_assumptions.return_value = mock_db
    mock_get_db_api.return_value = mock_db

    # Call API
    response = client.get(f"/api/assumptions/multi-model/{task_id}/{ra_tag_id}")

    assert response.status_code == 200
    data = response.json()

    # Verify NO_DATA agreement level when no validations exist
    assert data["consensus"]["agreement_level"] == "no_data"
    assert data["model_count"] == 0
    assert data["validations"] == []
