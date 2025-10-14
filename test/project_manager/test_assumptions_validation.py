import pytest
import tempfile
import os
from datetime import datetime, timezone, timedelta

from task_manager.database import TaskDatabase
from task_manager.tools_lib import CaptureAssumptionValidationTool, GetTaskDetailsTool, CreateTaskTool


class TestAssumptionValidationSystem:
    """Comprehensive test suite for RA assumption validation system."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()

        db = TaskDatabase(temp_file.name)
        yield db

        db.close()
        os.unlink(temp_file.name)

    @pytest.fixture
    def validation_tool(self, temp_db):
        """Create validation tool with test database."""
        return CaptureAssumptionValidationTool(temp_db, None)

    @pytest.fixture
    def task_details_tool(self, temp_db):
        """Create task details tool with test database."""
        return GetTaskDetailsTool(temp_db, None)

    @pytest.fixture
    def create_task_tool(self, temp_db):
        """Create task creation tool with test database."""
        return CreateTaskTool(temp_db, None)

    async def get_task_details_parsed(self, task_details_tool, task_id):
        """Helper method to get properly parsed task details."""
        import json

        result = await task_details_tool.apply(str(task_id))
        result_data = json.loads(result)
        return result_data

    def create_ra_tags_with_ids(self, ra_tag_strings):
        """Helper to create RA tags with proper ID formatting for testing."""
        import hashlib

        ra_tags = []
        for tag_text in ra_tag_strings:
            # Extract type from tag text (e.g., "#COMPLETION_DRIVE_IMPL:" -> "COMPLETION_DRIVE_IMPL")
            if tag_text.startswith("#") and ":" in tag_text:
                tag_type = tag_text[1 : tag_text.index(":")]
            else:
                tag_type = "UNKNOWN"

            # Generate consistent ID for testing
            tag_id = f"ra_tag_{hashlib.md5(tag_text.encode()).hexdigest()[:8]}"

            ra_tags.append(
                {
                    "id": tag_id,
                    "type": tag_type,
                    "text": tag_text,
                    "created_at": "2025-09-11T04:00:00.000000+00:00Z",
                }
            )

        return ra_tags

    @pytest.fixture
    def test_task_with_ra_tags(self, temp_db):
        """Create a test task with RA tags for validation testing."""
        import json

        # Create project and epic
        project_id = temp_db.create_project("Test Project", "Test description")
        epic_id = temp_db.create_epic(project_id, "Test Epic", "Test epic description")

        # Create RA tags with proper formatting
        ra_tag_strings = [
            "#COMPLETION_DRIVE_IMPL: Test database connection handling",
            "#SUGGEST_ERROR_HANDLING: Validate input parameters",
            "#PATTERN_MOMENTUM: Using existing validation patterns",
            "#CONTEXT_RECONSTRUCT: Inferring expected behavior",
        ]
        ra_tags_with_ids = self.create_ra_tags_with_ids(ra_tag_strings)

        # Create task with properly formatted RA tags
        task_id = temp_db.create_task(
            epic_id,
            "Test Task",
            "Test task description",
            ra_mode="standard",
            ra_score=6,
            ra_tags=ra_tag_strings,  # Use original strings for DB storage
        )

        # Manually update the task's RA tags to include IDs by directly modifying database
        with temp_db._connection_lock:
            cursor = temp_db._connection.cursor()
            cursor.execute(
                """
                UPDATE tasks SET ra_tags = ? WHERE id = ?
            """,
                (json.dumps(ra_tags_with_ids), task_id),
            )
            temp_db._connection.commit()

        return {
            "task_id": task_id,
            "project_id": project_id,
            "epic_id": epic_id,
            "ra_tags": ra_tags_with_ids,
        }


class TestValidationCreation(TestAssumptionValidationSystem):
    """Test validation record creation scenarios."""

    @pytest.mark.asyncio
    async def test_valid_validation_creation(self, validation_tool, test_task_with_ra_tags):
        """Test successful validation creation with all required parameters."""
        task_id = test_task_with_ra_tags["task_id"]
        ra_tag_id = test_task_with_ra_tags["ra_tags"][0]["id"]

        result = await validation_tool.apply(
            task_id=str(task_id),
            ra_tag_id=ra_tag_id,
            outcome="validated",
            reason="Test validation successful",
            confidence=85,
            reviewer_agent_id="test-reviewer",
        )

        import json

        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["task_id"] == task_id
        assert result_data["ra_tag_id"] == ra_tag_id
        assert result_data["outcome"] == "validated"
        assert result_data["confidence"] == 85
        assert result_data["reviewer"] == "test-reviewer"
        assert result_data["operation"] == "created"

    @pytest.mark.asyncio
    async def test_validation_with_default_confidence(
        self, validation_tool, test_task_with_ra_tags
    ):
        """Test validation creation with auto-populated confidence based on outcome."""
        task_id = test_task_with_ra_tags["task_id"]
        ra_tags = test_task_with_ra_tags["ra_tags"]

        test_cases = [("validated", 90), ("rejected", 10), ("partial", 75)]

        for i, (outcome, expected_confidence) in enumerate(test_cases):
            ra_tag_id = ra_tags[i]["id"]

            result = await validation_tool.apply(
                task_id=str(task_id),
                ra_tag_id=ra_tag_id,
                outcome=outcome,
                reason=f"Test {outcome} validation",
                reviewer_agent_id=f"test-reviewer-{i}",
            )

            import json

            result_data = json.loads(result)

            assert result_data["success"] is True
            assert result_data["confidence"] == expected_confidence
            assert result_data["outcome"] == outcome

    @pytest.mark.asyncio
    async def test_validation_with_default_reviewer(self, validation_tool, test_task_with_ra_tags):
        """Test validation creation with auto-populated reviewer ID."""
        task_id = test_task_with_ra_tags["task_id"]
        ra_tag_id = test_task_with_ra_tags["ra_tags"][0]["id"]

        result = await validation_tool.apply(
            task_id=str(task_id),
            ra_tag_id=ra_tag_id,
            outcome="validated",
            reason="Test with default reviewer",
        )

        import json

        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["reviewer"] == "mcp-reviewer-agent"


class TestValidationErrors(TestAssumptionValidationSystem):
    """Test validation error handling scenarios."""

    @pytest.mark.asyncio
    async def test_missing_task_id(self, validation_tool):
        """Test validation fails with missing task_id."""
        result = await validation_tool.apply(
            task_id="", ra_tag_id="test_tag", outcome="validated", reason="Test reason"
        )

        import json

        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "task_id parameter is required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_missing_ra_tag_id(self, validation_tool):
        """Test validation fails with missing ra_tag_id."""
        result = await validation_tool.apply(
            task_id="1", ra_tag_id="", outcome="validated", reason="Test reason"
        )

        import json

        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "ra_tag_id parameter is required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_invalid_outcome(self, validation_tool):
        """Test validation fails with invalid outcome value."""
        result = await validation_tool.apply(
            task_id="1", ra_tag_id="test_tag", outcome="invalid_outcome", reason="Test reason"
        )

        import json

        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "outcome must be one of: validated, rejected, partial" in result_data["error"]

    @pytest.mark.asyncio
    async def test_missing_reason(self, validation_tool):
        """Test validation fails with missing reason."""
        result = await validation_tool.apply(
            task_id="1", ra_tag_id="test_tag", outcome="validated", reason=""
        )

        import json

        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "reason parameter is required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_invalid_task_id_format(self, validation_tool):
        """Test validation fails with non-numeric task_id."""
        result = await validation_tool.apply(
            task_id="not_a_number", ra_tag_id="test_tag", outcome="validated", reason="Test reason"
        )

        import json

        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "Invalid task_id format" in result_data["error"]

    @pytest.mark.asyncio
    async def test_nonexistent_task_id(self, validation_tool):
        """Test validation fails with non-existent task_id."""
        result = await validation_tool.apply(
            task_id="999", ra_tag_id="test_tag", outcome="validated", reason="Test reason"
        )

        import json

        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "Task 999 not found" in result_data["error"]

    @pytest.mark.asyncio
    async def test_invalid_ra_tag_id(self, validation_tool, test_task_with_ra_tags):
        """Test validation fails with invalid RA tag ID."""
        task_id = test_task_with_ra_tags["task_id"]

        result = await validation_tool.apply(
            task_id=str(task_id),
            ra_tag_id="invalid_tag_id",
            outcome="validated",
            reason="Test reason",
        )

        import json

        result_data = json.loads(result)

        assert result_data["success"] is False
        assert (
            f"RA tag with ID 'invalid_tag_id' not found in task {task_id}" in result_data["error"]
        )

    @pytest.mark.asyncio
    async def test_confidence_out_of_range(self, validation_tool, test_task_with_ra_tags):
        """Test validation fails with confidence outside 0-100 range."""
        task_id = test_task_with_ra_tags["task_id"]
        ra_tag_id = test_task_with_ra_tags["ra_tags"][0]["id"]

        for invalid_confidence in [-1, 101, 150]:
            result = await validation_tool.apply(
                task_id=str(task_id),
                ra_tag_id=ra_tag_id,
                outcome="validated",
                reason="Test reason",
                confidence=invalid_confidence,
            )

            import json

            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "confidence must be between 0 and 100" in result_data["error"]

    @pytest.mark.asyncio
    async def test_task_without_ra_tags(self, validation_tool, temp_db):
        """Test validation fails for task without RA tags."""
        # Create task without RA tags
        project_id = temp_db.create_project("No Tags Project", "Test")
        epic_id = temp_db.create_epic(project_id, "No Tags Epic", "Test")
        task_id = temp_db.create_task(epic_id, "No Tags Task", "Test")

        result = await validation_tool.apply(
            task_id=str(task_id), ra_tag_id="any_tag_id", outcome="validated", reason="Test reason"
        )

        import json

        result_data = json.loads(result)

        assert result_data["success"] is False
        assert f"Task {task_id} has no RA tags to validate" in result_data["error"]


class TestValidationUpdates(TestAssumptionValidationSystem):
    """Test validation update and deduplication scenarios."""

    @pytest.mark.asyncio
    async def test_duplicate_validation_within_window(
        self, validation_tool, test_task_with_ra_tags
    ):
        """Test that duplicate validations within 10-minute window update existing record."""
        task_id = test_task_with_ra_tags["task_id"]
        ra_tag_id = test_task_with_ra_tags["ra_tags"][0]["id"]
        reviewer_id = "test-reviewer"

        # Create initial validation
        result1 = await validation_tool.apply(
            task_id=str(task_id),
            ra_tag_id=ra_tag_id,
            outcome="validated",
            reason="Initial validation",
            confidence=80,
            reviewer_agent_id=reviewer_id,
        )

        import json

        result1_data = json.loads(result1)
        assert result1_data["operation"] == "created"
        initial_validation_id = result1_data["validation_id"]

        # Create duplicate validation within 10-minute window
        result2 = await validation_tool.apply(
            task_id=str(task_id),
            ra_tag_id=ra_tag_id,
            outcome="rejected",
            reason="Updated validation after review",
            confidence=90,
            reviewer_agent_id=reviewer_id,
        )

        result2_data = json.loads(result2)
        assert result2_data["operation"] == "updated"
        assert result2_data["validation_id"] == initial_validation_id
        assert result2_data["outcome"] == "rejected"
        assert result2_data["confidence"] == 90

    @pytest.mark.asyncio
    async def test_different_reviewers_create_separate_validations(
        self, validation_tool, test_task_with_ra_tags
    ):
        """Test that different reviewers can create separate validations for same RA tag."""
        task_id = test_task_with_ra_tags["task_id"]
        ra_tag_id = test_task_with_ra_tags["ra_tags"][0]["id"]

        # Create validation from first reviewer
        result1 = await validation_tool.apply(
            task_id=str(task_id),
            ra_tag_id=ra_tag_id,
            outcome="validated",
            reason="Reviewer 1 validation",
            reviewer_agent_id="reviewer-1",
        )

        # Create validation from second reviewer
        result2 = await validation_tool.apply(
            task_id=str(task_id),
            ra_tag_id=ra_tag_id,
            outcome="rejected",
            reason="Reviewer 2 validation",
            reviewer_agent_id="reviewer-2",
        )

        import json

        result1_data = json.loads(result1)
        result2_data = json.loads(result2)

        assert result1_data["operation"] == "created"
        assert result2_data["operation"] == "created"
        assert result1_data["validation_id"] != result2_data["validation_id"]
        assert result1_data["reviewer"] == "reviewer-1"
        assert result2_data["reviewer"] == "reviewer-2"


class TestValidationIntegration(TestAssumptionValidationSystem):
    """Test integration with database and task system."""

    @pytest.mark.asyncio
    async def test_validation_context_auto_population(
        self, validation_tool, test_task_with_ra_tags, temp_db
    ):
        """Test that project_id and epic_id are auto-populated from task context."""
        task_id = test_task_with_ra_tags["task_id"]
        project_id = test_task_with_ra_tags["project_id"]
        epic_id = test_task_with_ra_tags["epic_id"]
        ra_tag_id = test_task_with_ra_tags["ra_tags"][0]["id"]

        result = await validation_tool.apply(
            task_id=str(task_id),
            ra_tag_id=ra_tag_id,
            outcome="validated",
            reason="Test context population",
        )

        import json

        result_data = json.loads(result)

        # Verify validation was created successfully
        assert result_data["success"] is True
        validation_id = result_data["validation_id"]

        # Query database directly to verify context was populated
        with temp_db._connection_lock:
            cursor = temp_db._connection.cursor()
            cursor.execute(
                """
                SELECT project_id, epic_id FROM assumption_validations 
                WHERE id = ?
            """,
                (validation_id,),
            )
            result_row = cursor.fetchone()

        assert result_row is not None
        assert result_row[0] == project_id  # project_id
        assert result_row[1] == epic_id  # epic_id

    @pytest.mark.asyncio
    async def test_multiple_ra_tag_types_validation(self, validation_tool, test_task_with_ra_tags):
        """Test validation of different RA tag types."""
        task_id = test_task_with_ra_tags["task_id"]
        ra_tags = test_task_with_ra_tags["ra_tags"]

        # Expected RA tag types from test fixture
        expected_types = [
            "COMPLETION_DRIVE_IMPL",
            "SUGGEST_ERROR_HANDLING",
            "PATTERN_MOMENTUM",
            "CONTEXT_RECONSTRUCT",
        ]

        for i, ra_tag in enumerate(ra_tags):
            result = await validation_tool.apply(
                task_id=str(task_id),
                ra_tag_id=ra_tag["id"],
                outcome="validated",
                reason=f"Validation for {ra_tag['type']} tag",
                reviewer_agent_id=f"reviewer-{i}",
            )

            import json

            result_data = json.loads(result)

            assert result_data["success"] is True
            assert result_data["ra_tag_type"] == expected_types[i]

    @pytest.mark.asyncio
    async def test_validation_timestamp_format(self, validation_tool, test_task_with_ra_tags):
        """Test that validation timestamps are in correct ISO format."""
        task_id = test_task_with_ra_tags["task_id"]
        ra_tag_id = test_task_with_ra_tags["ra_tags"][0]["id"]

        before_validation = datetime.now(timezone.utc)

        result = await validation_tool.apply(
            task_id=str(task_id),
            ra_tag_id=ra_tag_id,
            outcome="validated",
            reason="Test timestamp format",
        )

        after_validation = datetime.now(timezone.utc)

        import json

        result_data = json.loads(result)

        # Parse timestamp from result
        validated_at_str = result_data["validated_at"]
        validated_at = datetime.fromisoformat(validated_at_str.replace("Z", "+00:00"))

        # Verify timestamp is within expected range
        assert before_validation <= validated_at <= after_validation

        # Verify ISO format with Z suffix
        assert validated_at_str.endswith("Z")
        assert "T" in validated_at_str
