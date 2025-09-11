"""
Tests for RA tag normalization utility functions.

Covers all supported RA tag prefixes, edge cases, error handling, and performance requirements.
Tests ensure consistent pattern recognition and canonical type extraction from free-form RA tag text.
"""

import pytest
import json
from src.task_manager.ra_tag_utils import (
    normalize_ra_tag,
    extract_tag_category,
    get_tag_subcategory,
    parse_ra_tag_list,
    get_category_stats,
    RA_TAG_MAPPINGS
)


class TestNormalizeRaTag:
    """Tests for normalize_ra_tag() function with comprehensive coverage."""
    
    def test_completion_drive_tags(self):
        """Test normalization of COMPLETION_DRIVE_* tags."""
        test_cases = [
            ("#COMPLETION_DRIVE_IMPL: Database connection handling", "implementation:assumption"),
            ("#COMPLETION_DRIVE_INTEGRATION: Email service provider selection", "integration:assumption"),
            ("#COMPLETION_DRIVE_UI: Connection status indicator for WebSocket", "ui:assumption"),
            ("#COMPLETION_DRIVE_ARCHITECTURE: Global state management", "architecture:assumption"),
            ("#COMPLETION_DRIVE_WEBSOCKET: WebSocket connection with backoff", "websocket:assumption"),
            ("#COMPLETION_DRIVE_PERFORMANCE: Loading states for better UX", "performance:assumption"),
        ]
        
        for ra_tag, expected_type in test_cases:
            normalized_type, original_text = normalize_ra_tag(ra_tag)
            assert normalized_type == expected_type
            assert original_text == ra_tag
            
    def test_suggest_tags(self):
        """Test normalization of SUGGEST_* tags."""
        test_cases = [
            ("#SUGGEST_ERROR_HANDLING: Input validation needed", "error-handling:suggestion"),
            ("#SUGGEST_EDGE_CASE: Handle empty response arrays", "edge-case:suggestion"), 
            ("#SUGGEST_VALIDATION: Input sanitization for SQL injection", "validation:suggestion"),
            ("#SUGGEST_CLEANUP: Resource cleanup feels necessary", "cleanup:suggestion"),
            ("#SUGGEST_DEFENSIVE: Defensive programming seems prudent", "defensive:suggestion"),
            ("#SUGGEST_PERFORMANCE: Task payloads under 10KB", "performance:suggestion"),
            ("#SUGGEST_ACCESSIBILITY: Add focus indicators for keyboard nav", "accessibility:suggestion"),
        ]
        
        for ra_tag, expected_type in test_cases:
            normalized_type, original_text = normalize_ra_tag(ra_tag)
            assert normalized_type == expected_type
            assert original_text == ra_tag
            
    def test_context_tags(self):
        """Test normalization of CONTEXT_* tags."""
        test_cases = [
            ("#CONTEXT_DEGRADED: Unclear on authentication requirements", "context:degraded"),
            ("#CONTEXT_RECONSTRUCT: Filling in error handling patterns", "context:reconstruct"),
        ]
        
        for ra_tag, expected_type in test_cases:
            normalized_type, original_text = normalize_ra_tag(ra_tag)
            assert normalized_type == expected_type
            assert original_text == ra_tag
            
    def test_pattern_tags(self):
        """Test normalization of pattern detection tags."""
        test_cases = [
            ("#CARGO_CULT: Added loading state because other forms have it", "pattern:cargo-cult"),
            ("#PATTERN_MOMENTUM: Following existing controller structure", "pattern:momentum"),
            ("#ASSOCIATIVE_GENERATION: Features that feel needed", "pattern:associative"),
            ("#PATTERN_CONFLICT: Multiple valid database patterns available", "pattern:conflict"),
            ("#TRAINING_CONTRADICTION: Different contexts suggest opposing", "pattern:contradiction"),
        ]
        
        for ra_tag, expected_type in test_cases:
            normalized_type, original_text = normalize_ra_tag(ra_tag)
            assert normalized_type == expected_type
            assert original_text == ra_tag
            
    def test_generic_completion_drive(self):
        """Test generic COMPLETION_DRIVE tag without suffix."""
        normalized_type, original_text = normalize_ra_tag("#COMPLETION_DRIVE: General completion assumption")
        assert normalized_type == "completion-drive:general"
        assert original_text == "#COMPLETION_DRIVE: General completion assumption"
        
    def test_path_decision_tags(self):
        """Test PATH_DECISION tags from RA planning."""
        normalized_type, original_text = normalize_ra_tag("#PATH_DECISION: Normalization granularity choice")
        assert normalized_type == "planning:path-decision"
        assert original_text == "#PATH_DECISION: Normalization granularity choice"
        
    def test_case_insensitive_matching(self):
        """Test that tag matching is case-insensitive."""
        test_cases = [
            ("#suggest_error_handling: lowercase prefix", "error-handling:suggestion"),
            ("#Suggest_Error_Handling: mixed case prefix", "error-handling:suggestion"),
            ("#SUGGEST_ERROR_HANDLING: uppercase prefix", "error-handling:suggestion"),
        ]
        
        for ra_tag, expected_type in test_cases:
            normalized_type, original_text = normalize_ra_tag(ra_tag)
            assert normalized_type == expected_type
            assert original_text == ra_tag
            
    def test_unknown_tags(self):
        """Test handling of unknown/unrecognized tag prefixes."""
        test_cases = [
            "#UNKNOWN_TAG: Some description",
            "#CUSTOM_PREFIX: Custom implementation detail",
            "#NEW_PATTERN: Newly invented tag type",
        ]
        
        for ra_tag in test_cases:
            normalized_type, original_text = normalize_ra_tag(ra_tag)
            assert normalized_type == "unknown:other"
            assert original_text == ra_tag
            
    def test_malformed_tags(self):
        """Test handling of malformed tag formats."""
        test_cases = [
            "MISSING_HASH: No hash prefix",
            "# SPACE_AFTER_HASH: Space after hash",
            "#: Empty prefix",
            "#123_NUMERIC: Starts with number",
            "#SPECIAL-CHAR: Has hyphen in prefix",
        ]
        
        for ra_tag in test_cases:
            normalized_type, original_text = normalize_ra_tag(ra_tag)
            assert normalized_type == "unknown:other"
            assert original_text == ra_tag
            
    def test_edge_cases(self):
        """Test edge case inputs."""
        # Empty string
        normalized_type, original_text = normalize_ra_tag("")
        assert normalized_type == "unknown:other"
        assert original_text == ""
        
        # None input
        normalized_type, original_text = normalize_ra_tag(None)
        assert normalized_type == "unknown:other"
        assert original_text == ""
        
        # Non-string input
        normalized_type, original_text = normalize_ra_tag(123)
        assert normalized_type == "unknown:other"
        assert original_text == "123"
        
        # Whitespace only
        normalized_type, original_text = normalize_ra_tag("   ")
        assert normalized_type == "unknown:other"
        assert original_text == "   "
        
        # Just hash
        normalized_type, original_text = normalize_ra_tag("#")
        assert normalized_type == "unknown:other"
        assert original_text == "#"
        
    def test_tags_without_description(self):
        """Test tags that have prefix but no colon/description."""
        test_cases = [
            ("#SUGGEST_ERROR_HANDLING", "error-handling:suggestion"),
            ("#COMPLETION_DRIVE_IMPL", "implementation:assumption"),
            ("#PATTERN_MOMENTUM", "pattern:momentum"),
        ]
        
        for ra_tag, expected_type in test_cases:
            normalized_type, original_text = normalize_ra_tag(ra_tag)
            assert normalized_type == expected_type
            assert original_text == ra_tag
            
    def test_tags_with_complex_descriptions(self):
        """Test tags with complex, multi-line, or special character descriptions."""
        test_cases = [
            ("#SUGGEST_ERROR_HANDLING: Handle API timeouts, network failures, and malformed JSON responses",
             "error-handling:suggestion"),
            ("#COMPLETION_DRIVE_IMPL: Database connection pool with retry logic (max 3 attempts)",
             "implementation:assumption"),
            ("#PATTERN_MOMENTUM: Using React hooks pattern similar to UserProfile component",
             "pattern:momentum"),
        ]
        
        for ra_tag, expected_type in test_cases:
            normalized_type, original_text = normalize_ra_tag(ra_tag)
            assert normalized_type == expected_type
            assert original_text == ra_tag
            
    def test_preserve_exact_original_text(self):
        """Test that original text is preserved exactly, including whitespace."""
        test_cases = [
            "  #SUGGEST_ERROR_HANDLING: Input validation  ",
            "#COMPLETION_DRIVE_IMPL:     Extra spaces in description",
            "#PATTERN_MOMENTUM:\tTab character in description",
        ]
        
        for ra_tag in test_cases:
            normalized_type, original_text = normalize_ra_tag(ra_tag)
            assert original_text == ra_tag  # Exact preservation
            assert normalized_type != "unknown:other"  # Should still parse correctly


class TestExtractTagCategory:
    """Tests for extract_tag_category() function."""
    
    def test_category_extraction(self):
        """Test extraction of primary categories from tag prefixes."""
        test_cases = [
            ("SUGGEST_ERROR_HANDLING", "error-handling"),
            ("COMPLETION_DRIVE_IMPL", "implementation"),
            ("CONTEXT_DEGRADED", "context"),
            ("PATTERN_MOMENTUM", "pattern"),
            ("CARGO_CULT", "pattern"),
        ]
        
        for prefix, expected_category in test_cases:
            category = extract_tag_category(prefix)
            assert category == expected_category
            
    def test_unknown_prefix_category(self):
        """Test category extraction for unknown prefixes."""
        category = extract_tag_category("UNKNOWN_PREFIX")
        assert category == "unknown"
        
    def test_edge_cases_category(self):
        """Test category extraction edge cases."""
        assert extract_tag_category("") == "unknown"
        assert extract_tag_category(None) == "unknown"
        assert extract_tag_category(123) == "unknown"


class TestGetTagSubcategory:
    """Tests for get_tag_subcategory() function."""
    
    def test_subcategory_extraction(self):
        """Test extraction of subcategories from tag prefixes."""
        test_cases = [
            ("SUGGEST_ERROR_HANDLING", "suggestion"),
            ("COMPLETION_DRIVE_IMPL", "assumption"),
            ("CONTEXT_DEGRADED", "degraded"),
            ("PATTERN_MOMENTUM", "momentum"),
            ("CARGO_CULT", "cargo-cult"),
        ]
        
        for prefix, expected_subcategory in test_cases:
            subcategory = get_tag_subcategory(prefix)
            assert subcategory == expected_subcategory
            
    def test_unknown_prefix_subcategory(self):
        """Test subcategory extraction for unknown prefixes."""
        subcategory = get_tag_subcategory("UNKNOWN_PREFIX")
        assert subcategory == "other"
        
    def test_edge_cases_subcategory(self):
        """Test subcategory extraction edge cases."""
        assert get_tag_subcategory("") == "other"
        assert get_tag_subcategory(None) == "other"
        assert get_tag_subcategory(123) == "other"


class TestParseRaTagList:
    """Tests for parse_ra_tag_list() function."""
    
    def test_valid_json_parsing(self):
        """Test parsing valid JSON arrays of RA tags."""
        json_string = '["#SUGGEST_ERROR_HANDLING: Input validation", "#COMPLETION_DRIVE_IMPL: DB logic"]'
        result = parse_ra_tag_list(json_string)
        
        assert len(result) == 2
        assert result[0] == ("error-handling:suggestion", "#SUGGEST_ERROR_HANDLING: Input validation")
        assert result[1] == ("implementation:assumption", "#COMPLETION_DRIVE_IMPL: DB logic")
        
    def test_empty_json_array(self):
        """Test parsing empty JSON array."""
        result = parse_ra_tag_list('[]')
        assert result == []
        
    def test_invalid_json(self):
        """Test handling of invalid JSON strings."""
        invalid_cases = [
            '["unclosed array"',
            'not json at all',
            '{"wrong": "type"}',
            'null',
        ]
        
        for invalid_json in invalid_cases:
            result = parse_ra_tag_list(invalid_json)
            assert result == []
            
    def test_mixed_valid_invalid_tags(self):
        """Test parsing JSON with mix of valid tags and invalid entries."""
        json_string = '["#SUGGEST_ERROR_HANDLING: Valid tag", 123, "#COMPLETION_DRIVE_IMPL: Another valid", null]'
        result = parse_ra_tag_list(json_string)
        
        # Should only include the valid string tags
        assert len(result) == 2
        assert result[0] == ("error-handling:suggestion", "#SUGGEST_ERROR_HANDLING: Valid tag")
        assert result[1] == ("implementation:assumption", "#COMPLETION_DRIVE_IMPL: Another valid")
        
    def test_edge_cases_json_parsing(self):
        """Test edge cases for JSON parsing."""
        assert parse_ra_tag_list("") == []
        assert parse_ra_tag_list(None) == []
        assert parse_ra_tag_list(123) == []


class TestGetCategoryStats:
    """Tests for get_category_stats() function."""
    
    def test_category_counting(self):
        """Test counting categories from normalized tags."""
        normalized_tags = [
            ("error-handling:suggestion", "#SUGGEST_ERROR_HANDLING: desc1"),
            ("implementation:assumption", "#COMPLETION_DRIVE_IMPL: desc2"),
            ("error-handling:suggestion", "#SUGGEST_EDGE_CASE: desc3"),
            ("pattern:momentum", "#PATTERN_MOMENTUM: desc4"),
        ]
        
        stats = get_category_stats(normalized_tags)
        expected = {
            "error-handling": 2,
            "implementation": 1,
            "pattern": 1
        }
        assert stats == expected
        
    def test_empty_tags_stats(self):
        """Test stats for empty tag list."""
        stats = get_category_stats([])
        assert stats == {}
        
    def test_unknown_category_stats(self):
        """Test stats including unknown categories."""
        normalized_tags = [
            ("unknown:other", "#UNKNOWN_TAG: desc1"),
            ("implementation:assumption", "#COMPLETION_DRIVE_IMPL: desc2"),
        ]
        
        stats = get_category_stats(normalized_tags)
        expected = {
            "unknown": 1,
            "implementation": 1
        }
        assert stats == expected


class TestRaTagMappings:
    """Tests for RA_TAG_MAPPINGS completeness and consistency."""
    
    def test_all_documented_prefixes_mapped(self):
        """Test that all documented RA tag prefixes are in mappings."""
        # These are the core prefixes documented in RA instructions
        core_prefixes = [
            "COMPLETION_DRIVE_IMPL",
            "COMPLETION_DRIVE_INTEGRATION", 
            "CONTEXT_DEGRADED",
            "CONTEXT_RECONSTRUCT",
            "CARGO_CULT",
            "PATTERN_MOMENTUM",
            "ASSOCIATIVE_GENERATION",
            "PATTERN_CONFLICT",
            "TRAINING_CONTRADICTION",
            "SUGGEST_ERROR_HANDLING",
            "SUGGEST_EDGE_CASE",
            "SUGGEST_VALIDATION",
            "SUGGEST_CLEANUP",
            "SUGGEST_DEFENSIVE",
        ]
        
        for prefix in core_prefixes:
            assert prefix in RA_TAG_MAPPINGS, f"Missing mapping for core prefix: {prefix}"
            
    def test_mapping_format_consistency(self):
        """Test that all mappings follow category:subcategory format."""
        for prefix, normalized_type in RA_TAG_MAPPINGS.items():
            assert ":" in normalized_type, f"Mapping for {prefix} should have category:subcategory format"
            parts = normalized_type.split(":")
            assert len(parts) == 2, f"Mapping for {prefix} should have exactly one colon"
            category, subcategory = parts
            assert category, f"Category cannot be empty for {prefix}"
            assert subcategory, f"Subcategory cannot be empty for {prefix}"
            
    def test_mapping_character_constraints(self):
        """Test that mappings use lowercase and hyphens only."""
        for prefix, normalized_type in RA_TAG_MAPPINGS.items():
            # Should be lowercase
            assert normalized_type.islower(), f"Mapping for {prefix} should be lowercase"
            # Should only contain letters, hyphens, and one colon
            allowed_chars = set("abcdefghijklmnopqrstuvwxyz-:")
            actual_chars = set(normalized_type)
            assert actual_chars.issubset(allowed_chars), f"Mapping for {prefix} contains invalid characters"


class TestPerformance:
    """Performance tests for RA tag processing."""
    
    def test_batch_processing_performance(self):
        """Test processing large batches of RA tags meets performance requirements."""
        # Generate 100+ tags for performance test as specified in acceptance criteria
        test_tags = []
        tag_patterns = [
            "#SUGGEST_ERROR_HANDLING: Description {}",
            "#COMPLETION_DRIVE_IMPL: Implementation detail {}",
            "#PATTERN_MOMENTUM: Pattern usage {}",
            "#CONTEXT_DEGRADED: Context issue {}",
        ]
        
        for i in range(25):  # 25 * 4 patterns = 100 tags
            for pattern in tag_patterns:
                test_tags.append(pattern.format(i))
        
        # Measure processing time - should be fast enough for interactive use
        import time
        start_time = time.time()
        
        results = []
        for tag in test_tags:
            results.append(normalize_ra_tag(tag))
            
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process 100+ tags in reasonable time (under 1 second for interactive use)
        assert processing_time < 1.0, f"Processing 100 tags took {processing_time:.3f}s, should be under 1.0s"
        assert len(results) == 100, "Should process all 100 tags"
        
        # Verify all results are valid
        for normalized_type, original_text in results:
            assert isinstance(normalized_type, str)
            assert isinstance(original_text, str)
            assert ":" in normalized_type or normalized_type == "unknown:other"


class TestIntegrationWithRealExamples:
    """Integration tests with real RA tag examples from the codebase."""
    
    def test_real_codebase_examples(self):
        """Test normalization with actual RA tags found in the codebase."""
        real_examples = [
            ("#COMPLETION_DRIVE_IMPL: Database connection handling", "implementation:assumption"),
            ("#SUGGEST_ERROR_HANDLING: Consider non-consecutive port allocation", "error-handling:suggestion"),
            ("#SUGGEST_VALIDATION: Add comprehensive project schema validation", "validation:suggestion"),
            ("#SUGGEST_DEFENSIVE: This should never happen but defensive check", "defensive:suggestion"),
            ("#COMPLETION_DRIVE_IMPL: Unix signal handling pattern assumed", "implementation:assumption"),
            ("#SUGGEST_ERROR_HANDLING: Consider non-fatal warning instead", "error-handling:suggestion"),
            ("#SUGGEST_DEFENSIVE: Browser launch failure shouldn't stop server", "defensive:suggestion"),
            ("#SUGGEST_ERROR_HANDLING: Add timeout for graceful process shutdown", "error-handling:suggestion"),
        ]
        
        for ra_tag, expected_type in real_examples:
            normalized_type, original_text = normalize_ra_tag(ra_tag)
            assert normalized_type == expected_type
            assert original_text == ra_tag
            
    def test_json_format_from_mcp_tools(self):
        """Test parsing JSON format used by MCP tools in the system."""
        # Example from actual MCP tool usage in codebase
        mcp_json = '''["#COMPLETION_DRIVE_INTEGRATION: Email service provider selection", 
                      "#SUGGEST_ERROR_HANDLING: Failed delivery retry logic", 
                      "#PATTERN_MOMENTUM: Template system from common patterns", 
                      "#CONTEXT_RECONSTRUCT: Assuming multi-channel notification needs"]'''
        
        result = parse_ra_tag_list(mcp_json)
        assert len(result) == 4
        
        expected = [
            ("integration:assumption", "#COMPLETION_DRIVE_INTEGRATION: Email service provider selection"),
            ("error-handling:suggestion", "#SUGGEST_ERROR_HANDLING: Failed delivery retry logic"),
            ("pattern:momentum", "#PATTERN_MOMENTUM: Template system from common patterns"),
            ("context:reconstruct", "#CONTEXT_RECONSTRUCT: Assuming multi-channel notification needs"),
        ]
        
        assert result == expected