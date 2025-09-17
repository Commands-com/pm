"""
Model Identification Parser for Multi-Model Validation System

Parses validator_id strings to extract model provider, name, version,
and configuration information for consensus calculations and UI display.
"""

import re
from typing import Dict, Optional, Tuple
import logging
from .models import ModelInfo, ModelProvider

logger = logging.getLogger(__name__)


class ModelParser:
    """
    Parser for AI model validator IDs with flexible pattern matching.

    Supports various naming conventions from different providers and
    gracefully handles unknown formats with fallback values.
    """

    # Default model weights for consensus calculation
    DEFAULT_WEIGHTS = {
        ModelProvider.ANTHROPIC: 1.0,
        ModelProvider.OPENAI: 1.0,
        ModelProvider.GOOGLE: 1.0,
        ModelProvider.META: 0.8,
        ModelProvider.UNKNOWN: 0.7
    }

    # Regex patterns for different model formats
    MODEL_PATTERNS = [
        # Anthropic models: claude-3-opus, claude-3-5-sonnet-20241022
        {
            'pattern': re.compile(r'^claude-(\d+(?:-\d+)?)-(.+?)(?:-(\d{8}))?$', re.IGNORECASE),
            'provider': ModelProvider.ANTHROPIC,
            'extract': lambda m: ('claude', m.group(1).replace('-', '.'), m.group(2), m.group(3))
        },
        # OpenAI models: gpt-4, gpt-4-turbo, gpt-3.5-turbo-16k
        {
            'pattern': re.compile(r'^gpt-(\d+(?:\.\d+)?)-?(.+?)?(?:-(\w+))?$', re.IGNORECASE),
            'provider': ModelProvider.OPENAI,
            'extract': lambda m: ('gpt', m.group(1), m.group(2), m.group(3))
        },
        # Simple GPT models: gpt-4, gpt-3.5
        {
            'pattern': re.compile(r'^gpt-(\d+(?:\.\d+)?)$', re.IGNORECASE),
            'provider': ModelProvider.OPENAI,
            'extract': lambda m: ('gpt', m.group(1), None, None)
        },
        # Google models: gemini-pro, gemini-1.5-pro, palm-2
        {
            'pattern': re.compile(r'^(gemini|palm)(?:-(\d+(?:\.\d+)?))?(?:-(.+?))?$', re.IGNORECASE),
            'provider': ModelProvider.GOOGLE,
            'extract': lambda m: (m.group(1), m.group(2), m.group(3), None)
        },
        # Meta models: llama-3-70b, llama-2-13b-chat
        {
            'pattern': re.compile(r'^llama-(\d+)-(\d+)b?(?:-(.+?))?$', re.IGNORECASE),
            'provider': ModelProvider.META,
            'extract': lambda m: ('llama', m.group(1), f"{m.group(2)}b", m.group(3))
        },
        # Generic fallback pattern
        {
            'pattern': re.compile(r'^(.+?)(?:-v?(\d+(?:\.\d+)?(?:\.\d+)?))?(?:-(.+?))?$', re.IGNORECASE),
            'provider': ModelProvider.UNKNOWN,
            'extract': lambda m: (m.group(1), m.group(2), m.group(3), None)
        }
    ]

    def __init__(self, custom_weights: Optional[Dict[ModelProvider, float]] = None):
        """
        Initialize model parser.

        Args:
            custom_weights: Custom weight overrides for model providers
        """
        self.weights = {**self.DEFAULT_WEIGHTS}
        if custom_weights:
            self.weights.update(custom_weights)

    def parse_validator_id(self, validator_id: str) -> ModelInfo:
        """
        Parse validator_id string to extract model information.

        Args:
            validator_id: String identifier like "claude-3-opus" or "gpt-4-turbo"

        Returns:
            ModelInfo with extracted provider, name, version, and display name

        Examples:
            >>> parser = ModelParser()
            >>> info = parser.parse_validator_id("claude-3-opus")
            >>> info.provider  # ModelProvider.ANTHROPIC
            >>> info.display_name  # "Claude 3 Opus"
        """
        if not validator_id or not isinstance(validator_id, str) or not str(validator_id).strip():
            logger.warning(f"Invalid validator_id: {validator_id}")
            return self._create_fallback_model_info(str(validator_id) if validator_id else "unknown")

        # Clean input
        clean_id = validator_id.strip().lower()

        # Try each pattern until one matches
        for pattern_config in self.MODEL_PATTERNS:
            match = pattern_config['pattern'].match(clean_id)
            if match:
                try:
                    provider = pattern_config['provider']
                    base_name, version_1, version_2, extra = pattern_config['extract'](match)

                    # Construct model name and version
                    name = self._construct_model_name(base_name, version_1, version_2, extra)
                    version = self._extract_version(version_1, version_2, extra)
                    display_name = self._generate_display_name(provider, base_name, version_1, version_2, extra)
                    weight = self.weights.get(provider, self.DEFAULT_WEIGHTS[ModelProvider.UNKNOWN])

                    return ModelInfo(
                        provider=provider,
                        name=name,
                        version=version,
                        display_name=display_name,
                        weight=weight
                    )

                except Exception as e:
                    logger.warning(f"Error parsing validator_id '{validator_id}': {e}")
                    continue

        # If no pattern matched, return fallback
        logger.info(f"No pattern matched for validator_id: {validator_id}")
        return self._create_fallback_model_info(validator_id)

    def _construct_model_name(self, base_name: str, version_1: Optional[str],
                            version_2: Optional[str], extra: Optional[str]) -> str:
        """Construct model name from parsed components."""
        parts = [base_name] if base_name else []

        if version_1:
            parts.append(version_1)
        if version_2:
            parts.append(version_2)

        return '-'.join(filter(None, parts))

    def _extract_version(self, version_1: Optional[str], version_2: Optional[str],
                        extra: Optional[str]) -> Optional[str]:
        """Extract version information from parsed components."""
        # For date-based versions (like Claude 20241022)
        if extra and len(extra) == 8 and extra.isdigit():
            return extra

        # For explicit versions like "1.5" in Gemini models
        if version_1 and '.' in version_1 and not version_1.startswith('3.'):
            return version_1

        return None

    def _generate_display_name(self, provider: ModelProvider, base_name: str,
                              version_1: Optional[str], version_2: Optional[str],
                              extra: Optional[str]) -> str:
        """Generate human-readable display name."""
        if provider == ModelProvider.ANTHROPIC:
            # Claude 3 Opus, Claude 3.5 Sonnet
            version_part = f" {version_1}" if version_1 else ""
            model_part = f" {version_2.title()}" if version_2 else ""
            return f"Claude{version_part}{model_part}"

        elif provider == ModelProvider.OPENAI:
            # GPT-4, GPT-4 Turbo, GPT-3.5 Turbo
            version_part = f"-{version_1}" if version_1 else ""
            model_part = f" {version_2.title()}" if version_2 and version_2.strip() else ""
            return f"GPT{version_part}{model_part}"

        elif provider == ModelProvider.GOOGLE:
            # Gemini Pro, Gemini 1.5 Pro, PaLM 2
            if base_name.lower() == 'gemini':
                version_part = f" {version_1}" if version_1 else ""
                model_part = f" {version_2.title()}" if version_2 and version_2.strip() else ""
                return f"Gemini{version_part}{model_part}"
            elif base_name.lower() == 'palm':
                version_part = f" {version_1}" if version_1 else ""
                return f"PaLM{version_part}"
            else:
                return base_name.title()

        elif provider == ModelProvider.META:
            # Llama 3 70B, Llama 2 13B Chat
            version_part = f" {version_1}" if version_1 else ""
            size_part = f" {version_2.upper()}" if version_2 else ""
            extra_part = f" {extra.title()}" if extra and extra.strip() else ""
            return f"Llama{version_part}{size_part}{extra_part}"

        else:
            # Unknown provider - construct a human-readable name from available parts
            if not base_name or not base_name.strip():
                return "Unknown Model"

            # Build a composite name including detected version parts when present
            parts = [base_name]
            if version_1:
                # Preserve a leading 'V' for unknown providers to match expectations (e.g., v2 -> V2)
                parts.append(f"v{version_1}")
            if version_2:
                parts.append(version_2)

            raw = '-'.join(filter(None, parts))
            friendly = raw.replace('-', ' ').replace('_', ' ')

            # Edge-case: if replacement results in empty/whitespace, return original base
            if not friendly.strip():
                return base_name

            return friendly.title()

    def _create_fallback_model_info(self, validator_id: str) -> ModelInfo:
        """Create fallback ModelInfo for unknown formats."""
        # Normalize edge cases: empty/whitespace/None -> "Unknown Model"
        if validator_id is None or not str(validator_id).strip():
            display = "Unknown Model"
            name = "unknown"
        else:
            display = (
                "Unknown Model" if str(validator_id).strip().lower() in ("unknown",)
                else str(validator_id).replace('-', ' ').replace('_', ' ').title()
            )
            name = str(validator_id).lower()
        return ModelInfo(
            provider=ModelProvider.UNKNOWN,
            name=name,
            version=None,
            display_name=display,
            weight=self.weights[ModelProvider.UNKNOWN]
        )

    def get_model_weight(self, validator_id: str) -> float:
        """
        Get model weight for consensus calculation.

        Args:
            validator_id: String identifier for the model

        Returns:
            Float weight value for the model
        """
        model_info = self.parse_validator_id(validator_id)
        return model_info.weight

    def get_available_models(self) -> Dict[str, Dict[str, any]]:
        """
        Get configuration of all available model providers.

        Returns:
            Dictionary with provider information and weights
        """
        return {
            "anthropic": {
                "name": "Anthropic",
                "weight": self.weights[ModelProvider.ANTHROPIC],
                "examples": ["claude-3-opus", "claude-3-5-sonnet"]
            },
            "openai": {
                "name": "OpenAI",
                "weight": self.weights[ModelProvider.OPENAI],
                "examples": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
            },
            "google": {
                "name": "Google",
                "weight": self.weights[ModelProvider.GOOGLE],
                "examples": ["gemini-pro", "gemini-1.5-pro", "palm-2"]
            },
            "meta": {
                "name": "Meta",
                "weight": self.weights[ModelProvider.META],
                "examples": ["llama-3-70b", "llama-2-13b"]
            },
            "unknown": {
                "name": "Other",
                "weight": self.weights[ModelProvider.UNKNOWN],
                "examples": ["custom-model", "experimental-ai"]
            }
        }


# Convenience functions for backward compatibility
def parse_validator_id(validator_id: str) -> ModelInfo:
    """Parse validator_id using default parser instance."""
    parser = ModelParser()
    return parser.parse_validator_id(validator_id)


def get_model_weight(validator_id: str) -> float:
    """Get model weight using default parser instance."""
    parser = ModelParser()
    return parser.get_model_weight(validator_id)


def get_available_models() -> Dict[str, Dict[str, any]]:
    """Get available models using default parser instance."""
    parser = ModelParser()
    return parser.get_available_models()
