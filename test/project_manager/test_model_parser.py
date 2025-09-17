"""
Unit tests for model identification parser.

Tests the ModelParser class with various validator_id formats,
edge cases, and provider-specific patterns.
"""

import pytest
from src.task_manager.model_parser import ModelParser, parse_validator_id, get_model_weight, get_available_models
from src.task_manager.models import ModelInfo, ModelProvider


class TestModelParser:
    """Test suite for ModelParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ModelParser()

    def test_anthropic_claude_models(self):
        """Test parsing of Anthropic Claude model formats."""
        test_cases = [
            ("claude-3-opus", "Claude 3 Opus", ModelProvider.ANTHROPIC),
            ("claude-3-5-sonnet", "Claude 3.5 Sonnet", ModelProvider.ANTHROPIC),
            ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet", ModelProvider.ANTHROPIC),
            ("claude-3-haiku", "Claude 3 Haiku", ModelProvider.ANTHROPIC),
            ("CLAUDE-3-OPUS", "Claude 3 Opus", ModelProvider.ANTHROPIC),  # Case insensitive
        ]

        for validator_id, expected_display, expected_provider in test_cases:
            result = self.parser.parse_validator_id(validator_id)
            assert result.provider == expected_provider
            assert result.display_name == expected_display
            assert result.weight == 1.0
            assert "claude" in result.name.lower()

    def test_openai_gpt_models(self):
        """Test parsing of OpenAI GPT model formats."""
        test_cases = [
            ("gpt-4", "GPT-4", ModelProvider.OPENAI),
            ("gpt-4-turbo", "GPT-4 Turbo", ModelProvider.OPENAI),
            ("gpt-3.5-turbo", "GPT-3.5 Turbo", ModelProvider.OPENAI),
            ("gpt-3.5-turbo-16k", "GPT-3.5 Turbo", ModelProvider.OPENAI),
            ("GPT-4-TURBO", "GPT-4 Turbo", ModelProvider.OPENAI),  # Case insensitive
        ]

        for validator_id, expected_display, expected_provider in test_cases:
            result = self.parser.parse_validator_id(validator_id)
            assert result.provider == expected_provider
            assert result.display_name == expected_display
            assert result.weight == 1.0
            assert "gpt" in result.name.lower()

    def test_google_models(self):
        """Test parsing of Google model formats."""
        test_cases = [
            ("gemini-pro", "Gemini Pro", ModelProvider.GOOGLE),
            ("gemini-1.5-pro", "Gemini 1.5 Pro", ModelProvider.GOOGLE),
            ("palm-2", "PaLM 2", ModelProvider.GOOGLE),
            ("GEMINI-PRO", "Gemini Pro", ModelProvider.GOOGLE),  # Case insensitive
        ]

        for validator_id, expected_display, expected_provider in test_cases:
            result = self.parser.parse_validator_id(validator_id)
            assert result.provider == expected_provider
            assert result.display_name == expected_display
            assert result.weight == 1.0

    def test_meta_llama_models(self):
        """Test parsing of Meta Llama model formats."""
        test_cases = [
            ("llama-3-70b", "Llama 3 70B", ModelProvider.META),
            ("llama-2-13b", "Llama 2 13B", ModelProvider.META),
            ("llama-2-13b-chat", "Llama 2 13B Chat", ModelProvider.META),
            ("LLAMA-3-70B", "Llama 3 70B", ModelProvider.META),  # Case insensitive
        ]

        for validator_id, expected_display, expected_provider in test_cases:
            result = self.parser.parse_validator_id(validator_id)
            assert result.provider == expected_provider
            assert result.display_name == expected_display
            assert result.weight == 0.8  # Meta has lower default weight

    def test_unknown_models_fallback(self):
        """Test fallback handling for unknown model formats."""
        test_cases = [
            ("custom-ai-model", "Custom Ai Model"),
            ("experimental-llm-v2", "Experimental Llm V2"),
            ("unknown-provider-xyz", "Unknown Provider Xyz"),
            ("legacy-model-format", "Legacy Model Format")
        ]

        for validator_id, expected_display in test_cases:
            result = self.parser.parse_validator_id(validator_id)
            assert result.provider == ModelProvider.UNKNOWN
            assert result.weight == 0.7  # Default unknown weight
            assert result.name == validator_id.lower()
            assert result.display_name == expected_display

    def test_edge_cases(self):
        """Test edge cases and malformed inputs."""
        edge_cases = [
            ("", "Unknown Model"),
            (None, "Unknown Model"),
            ("   ", "Unknown Model"),
            ("a", "A"),
            ("-", "-"),
            ("model-", "Model "),
            ("123", "123"),
        ]

        for validator_id, expected_display in edge_cases:
            result = self.parser.parse_validator_id(validator_id)
            assert result.provider == ModelProvider.UNKNOWN
            assert result.display_name == expected_display
            assert result.weight == 0.7

    def test_version_extraction(self):
        """Test version extraction from various formats."""
        test_cases = [
            ("claude-3-5-sonnet-20241022", "20241022"),  # Date version
            ("gpt-4-turbo", None),  # No explicit version
            ("gemini-1.5-pro", "1.5"),  # Semantic version
            ("llama-3-70b", None),  # No explicit version (model name part)
        ]

        for validator_id, expected_version in test_cases:
            result = self.parser.parse_validator_id(validator_id)
            assert result.version == expected_version

    def test_custom_weights(self):
        """Test parser with custom model weights."""
        custom_weights = {
            ModelProvider.ANTHROPIC: 1.5,
            ModelProvider.OPENAI: 0.8,
            ModelProvider.UNKNOWN: 0.1
        }

        parser = ModelParser(custom_weights=custom_weights)

        # Test custom weights applied
        claude_result = parser.parse_validator_id("claude-3-opus")
        assert claude_result.weight == 1.5

        gpt_result = parser.parse_validator_id("gpt-4")
        assert gpt_result.weight == 0.8

        unknown_result = parser.parse_validator_id("custom-model")
        assert unknown_result.weight == 0.1

        # Test unchanged weights
        gemini_result = parser.parse_validator_id("gemini-pro")
        assert gemini_result.weight == 1.0  # Default unchanged

    def test_model_weight_function(self):
        """Test get_model_weight convenience function."""
        test_cases = [
            ("claude-3-opus", 1.0),
            ("gpt-4-turbo", 1.0),
            ("gemini-pro", 1.0),
            ("llama-3-70b", 0.8),
            ("unknown-model", 0.7)
        ]

        for validator_id, expected_weight in test_cases:
            weight = self.parser.get_model_weight(validator_id)
            assert weight == expected_weight

    def test_available_models_config(self):
        """Test get_available_models configuration."""
        config = self.parser.get_available_models()

        # Check structure
        assert isinstance(config, dict)
        assert "anthropic" in config
        assert "openai" in config
        assert "google" in config
        assert "meta" in config
        assert "unknown" in config

        # Check anthropic config
        anthropic = config["anthropic"]
        assert anthropic["name"] == "Anthropic"
        assert anthropic["weight"] == 1.0
        assert isinstance(anthropic["examples"], list)
        assert len(anthropic["examples"]) > 0

        # Check meta has different weight
        meta = config["meta"]
        assert meta["weight"] == 0.8

    def test_case_insensitive_parsing(self):
        """Test that parsing is case insensitive."""
        test_cases = [
            ("claude-3-opus", "CLAUDE-3-OPUS"),
            ("gpt-4-turbo", "GPT-4-TURBO"),
            ("gemini-pro", "GEMINI-PRO"),
            ("llama-3-70b", "LLAMA-3-70B")
        ]

        for lower_case, upper_case in test_cases:
            lower_result = self.parser.parse_validator_id(lower_case)
            upper_result = self.parser.parse_validator_id(upper_case)

            assert lower_result.provider == upper_result.provider
            assert lower_result.display_name == upper_result.display_name
            assert lower_result.weight == upper_result.weight

    def test_complex_validator_ids(self):
        """Test complex real-world validator_id formats."""
        test_cases = [
            "claude-3-5-sonnet-20241022-v2",
            "gpt-4-turbo-preview-0125",
            "gemini-1.5-pro-001",
            "llama-3-8b-instruct-q4"
        ]

        for validator_id in test_cases:
            result = self.parser.parse_validator_id(validator_id)
            # Should not crash and should return valid result
            assert isinstance(result, ModelInfo)
            assert result.provider in ModelProvider
            assert isinstance(result.display_name, str)
            assert result.weight > 0

    def test_model_name_construction(self):
        """Test model name construction logic."""
        test_cases = [
            ("claude-3-opus", "claude-3-opus"),
            ("gpt-4-turbo", "gpt-4-turbo"),
            ("llama-3-70b", "llama-3-70b"),
        ]

        for validator_id, expected_name_pattern in test_cases:
            result = self.parser.parse_validator_id(validator_id)
            assert expected_name_pattern in result.name

    def test_convenience_functions(self):
        """Test module-level convenience functions."""
        # Test parse_validator_id function
        result = parse_validator_id("claude-3-opus")
        assert result.provider == ModelProvider.ANTHROPIC
        assert result.display_name == "Claude 3 Opus"

        # Test get_model_weight function
        weight = get_model_weight("gpt-4")
        assert weight == 1.0

        # Test get_available_models function
        models = get_available_models()
        assert isinstance(models, dict)
        assert "anthropic" in models

    def test_regex_pattern_priority(self):
        """Test that specific patterns take priority over generic ones."""
        # Should match anthropic pattern, not generic
        result = self.parser.parse_validator_id("claude-3-opus")
        assert result.provider == ModelProvider.ANTHROPIC
        assert "Claude" in result.display_name

        # Should match openai pattern, not generic
        result = self.parser.parse_validator_id("gpt-4")
        assert result.provider == ModelProvider.OPENAI
        assert "GPT" in result.display_name

    def test_performance_bulk_parsing(self):
        """Test performance with bulk parsing operations."""
        import time

        validator_ids = [
            "claude-3-opus", "gpt-4-turbo", "gemini-pro", "llama-3-70b",
            "claude-3-5-sonnet", "gpt-3.5-turbo", "palm-2", "llama-2-13b"
        ] * 25  # 200 total

        start_time = time.time()
        results = [self.parser.parse_validator_id(vid) for vid in validator_ids]
        end_time = time.time()

        # Should complete quickly
        processing_time = (end_time - start_time) * 1000
        assert processing_time < 100, f"Bulk parsing took {processing_time:.2f}ms"

        # Verify all results are valid
        assert len(results) == 200
        for result in results:
            assert isinstance(result, ModelInfo)
            assert result.weight > 0

    def test_display_name_formatting(self):
        """Test display name formatting consistency."""
        test_cases = [
            ("claude-3-opus", "Claude 3 Opus"),
            ("gpt-4-turbo", "GPT-4 Turbo"),
            ("gemini-1.5-pro", "Gemini 1.5 Pro"),
            ("llama-3-70b-chat", "Llama 3 70B Chat"),
            ("palm-2", "PaLM 2")
        ]

        for validator_id, expected_display in test_cases:
            result = self.parser.parse_validator_id(validator_id)
            assert result.display_name == expected_display