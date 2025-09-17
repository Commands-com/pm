"""
Pydantic models for Task Manager API request/response validation.

Provides data validation models for knowledge management endpoints,
task operations, and error response formatting.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import json


class KnowledgeRequest(BaseModel):
    """Request model for creating/updating knowledge items."""

    knowledge_id: Optional[int] = Field(
        None, description="ID for update operations, omit for create"
    )
    title: Optional[str] = Field(
        None, min_length=1, max_length=500, description="Knowledge item title"
    )
    content: Optional[str] = Field(None, min_length=1, description="Knowledge item content")
    category: Optional[str] = Field(None, max_length=100, description="Category classification")
    tags: Optional[List[str]] = Field(None, description="Array of tag strings")
    parent_id: Optional[int] = Field(None, description="Parent knowledge item ID for hierarchy")
    project_id: Optional[int] = Field(None, description="Associated project ID")
    epic_id: Optional[int] = Field(None, description="Associated epic ID")
    task_id: Optional[int] = Field(None, description="Associated task ID")
    priority: Optional[int] = Field(0, ge=0, le=5, description="Priority level 0-5")
    is_active: Optional[bool] = Field(True, description="Whether item is active")
    created_by: Optional[str] = Field(None, max_length=100, description="Creator identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata object")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        """Validate tags are non-empty strings."""
        if v is not None:
            for tag in v:
                if not isinstance(tag, str) or not tag.strip():
                    raise ValueError("All tags must be non-empty strings")
        return v


class KnowledgeResponse(BaseModel):
    """Response model for knowledge item operations."""

    success: bool
    message: Optional[str] = None
    knowledge_id: Optional[int] = None
    operation: Optional[str] = None  # "created" or "updated"
    version: Optional[int] = None
    knowledge_item: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class LogRequest(BaseModel):
    """Request model for appending knowledge log entries."""

    action_type: str = Field(min_length=1, max_length=50, description="Type of action performed")
    change_reason: Optional[str] = Field(
        None, max_length=500, description="Reason for the action/change"
    )
    created_by: Optional[str] = Field(
        None, max_length=100, description="User who performed the action"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata object")


class LogResponse(BaseModel):
    """Response model for knowledge log operations."""

    success: bool
    message: Optional[str] = None
    log_id: Optional[int] = None
    knowledge_id: Optional[int] = None
    knowledge_title: Optional[str] = None
    created_at: Optional[str] = None
    error: Optional[str] = None


class KnowledgeDetailResponse(BaseModel):
    """Response model for knowledge item retrieval with logs."""

    success: bool
    message: Optional[str] = None
    knowledge_items: Optional[List[Dict[str, Any]]] = None
    total_count: Optional[int] = None
    filters_applied: Optional[Dict[str, Any]] = None
    logs: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response model."""

    success: bool = False
    error: str
    code: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseModel):
    """Standard success response model."""

    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


# Utility function to create consistent error responses
def create_error_response(
    message: str, code: Optional[int] = None, details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized error response dictionary."""
    return {"success": False, "error": message, "code": code, "details": details}


# Utility function to create consistent success responses
def create_success_response(message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a standardized success response dictionary."""
    return {"success": True, "message": message, "data": data}


# Assumption Intelligence API Models


class ValidationExample(BaseModel):
    """Model for recent validation example in insights response."""

    id: int
    task_id: int
    task_name: str
    ra_tag: str
    outcome: str
    confidence: int
    validator_id: str
    validated_at: str
    notes: Optional[str] = None


class InsightsSummary(BaseModel):
    """Response model for /api/assumptions/insights endpoint."""

    success: bool = True
    total_validations: int
    success_rate: float = Field(description="Success rate between 0.0 and 1.0")
    outcome_breakdown: Dict[str, int] = Field(
        description="Count by outcome: validated, rejected, partial"
    )
    tag_type_breakdown: Dict[str, int] = Field(description="Count by normalized tag type")
    recent_examples: List[ValidationExample]
    trend_data: Optional[Dict[str, Any]] = None
    cache_timestamp: Optional[str] = None


class RecentValidation(BaseModel):
    """Model for recent validation activity."""

    id: int
    task_id: int
    ra_tag_id: str = Field(description="Unique ID of the specific RA tag")
    task_name: str
    project_name: Optional[str]
    epic_name: Optional[str]
    ra_tag: str
    ra_tag_type: str = Field(description="Normalized tag type from RA utilities")
    outcome: str
    confidence: int
    validator_id: str
    validated_at: str
    notes: Optional[str] = None
    context_snapshot: Optional[str] = None


class RecentValidationsResponse(BaseModel):
    """Response model for /api/assumptions/recent endpoint."""

    success: bool = True
    validations: List[RecentValidation]
    total_count: int
    has_more: bool
    next_cursor: Optional[int] = None


class TagTypeInfo(BaseModel):
    """Model for available RA tag type information."""

    normalized_type: str
    category: str
    subcategory: str
    count: int
    example_tags: List[str] = Field(max_length=3, description="Up to 3 example original tags")


class TagTypesResponse(BaseModel):
    """Response model for /api/assumptions/tag-types endpoint."""

    success: bool = True
    tag_types: List[TagTypeInfo]
    total_types: int
    cache_timestamp: Optional[str] = None


# Multi-Model Consensus Models


class AgreementLevel(str, Enum):
    """Enum for consensus agreement classification levels."""

    NO_DATA = "no_data"     # No validations available
    WEAK = "weak"           # <50% consensus
    MODERATE = "moderate"   # 50-74% consensus
    STRONG = "strong"       # 75-89% consensus
    UNANIMOUS = "unanimous" # 90%+ consensus


class ModelProvider(str, Enum):
    """Enum for AI model providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    META = "meta"
    GOOGLE = "google"
    UNKNOWN = "unknown"


class ModelInfo(BaseModel):
    """Model information extracted from validator_id."""

    provider: ModelProvider = Field(description="AI model provider")
    name: str = Field(description="Model name (e.g., 'claude-3-opus')")
    version: Optional[str] = Field(default=None, description="Model version if available")
    display_name: str = Field(description="Human-readable display name")
    weight: float = Field(ge=0.0, le=2.0, description="Model weight for consensus calculation")


class ConsensusResult(BaseModel):
    """Result model for consensus calculation across multiple model validations."""

    consensus: float = Field(
        ge=0.0, le=1.0,
        description="Weighted consensus score from 0.0 to 1.0"
    )
    overall_score: int = Field(
        ge=0, le=100,
        description="Normalized overall score (0-100) for human-friendly comparisons"
    )
    outcome: str = Field(
        description="Dominant outcome: 'validated', 'rejected', or 'partial'"
    )
    agreement_level: AgreementLevel = Field(
        description="Classification of agreement strength"
    )
    model_disagreement: bool = Field(
        description="True when consensus < 75% indicating significant disagreement"
    )
    total_validations: int = Field(
        ge=0,
        description="Total number of model validations included"
    )
    model_breakdown: Dict[str, int] = Field(
        description="Count of validations by outcome for transparency"
    )
    weighted_confidence: float = Field(
        ge=0.0, le=1.0,
        description="Average confidence weighted by model weights"
    )


class ContentiousTag(BaseModel):
    """Model for RA tags with low consensus (contentious)."""

    ra_tag_id: str = Field(description="Unique RA tag identifier")
    ra_tag_text: str = Field(description="Original RA tag text")
    consensus: float = Field(ge=0.0, le=1.0, description="Consensus score for this tag")
    total_validations: int = Field(ge=0, description="Number of validations for this tag")
    disagreement_reason: str = Field(description="Why this tag is contentious")


class HighConfidenceTag(BaseModel):
    """Model for RA tags with high consensus (high confidence)."""

    ra_tag_id: str = Field(description="Unique RA tag identifier")
    ra_tag_text: str = Field(description="Original RA tag text")
    consensus: float = Field(ge=0.0, le=1.0, description="Consensus score for this tag")
    total_validations: int = Field(ge=0, description="Number of validations for this tag")
    outcome: str = Field(description="Dominant validation outcome")


class ConsensusSummaryResponse(BaseModel):
    """Response model for task consensus summary endpoint."""

    success: bool = True
    task_id: int = Field(description="Task ID for the summary")
    overall_consensus: float = Field(
        ge=0.0, le=1.0,
        description="Average consensus across all RA tags in task"
    )
    total_ra_tags: int = Field(ge=0, description="Total number of RA tags in task")
    validated_tags: int = Field(ge=0, description="Number of tags with at least one validation")
    validation_coverage: float = Field(
        ge=0.0, le=1.0,
        description="Percentage of tags with validations"
    )
    contentious_tags: List[ContentiousTag] = Field(
        description="Tags with consensus < 75% indicating disagreement"
    )
    high_confidence_tags: List[HighConfidenceTag] = Field(
        description="Tags with consensus > 90% indicating strong agreement"
    )
    cache_timestamp: Optional[str] = Field(
        default=None,
        description="Timestamp when consensus calculations were cached"
    )


class ModelConfig(BaseModel):
    """Configuration for an individual AI model."""

    id: str = Field(description="Unique model identifier")
    provider: str = Field(description="Model provider (anthropic, openai, etc.)")
    name: str = Field(description="Technical model name")
    display_name: str = Field(description="Human-readable display name")
    weight: float = Field(ge=0.0, le=2.0, description="Weight for consensus calculations")
    enabled: bool = Field(default=True, description="Whether model is enabled for validation")
    description: Optional[str] = Field(default=None, description="Model description")
    api_endpoint: Optional[str] = Field(default=None, description="API endpoint URL")


class ConsensusConfig(BaseModel):
    """Configuration for consensus calculation thresholds."""

    contentious_threshold: float = Field(
        default=0.75,
        ge=0.0, le=1.0,
        description="Threshold below which tags are considered contentious"
    )
    high_confidence_threshold: float = Field(
        default=0.90,
        ge=0.0, le=1.0,
        description="Threshold above which tags are considered high confidence"
    )
    minimum_models: int = Field(
        default=2,
        ge=1,
        description="Minimum number of models required for consensus calculation"
    )
    cache_ttl_minutes: int = Field(
        default=5,
        ge=1,
        description="Cache TTL in minutes for consensus results"
    )


class AvailableModelsResponse(BaseModel):
    """Response model for available models API endpoint."""

    success: bool = True
    models: List[ModelConfig] = Field(description="List of available AI models")
    consensus_config: ConsensusConfig = Field(description="Consensus calculation configuration")
    total_models: int = Field(ge=0, description="Total number of configured models")
    enabled_models: int = Field(ge=0, description="Number of enabled models")
    last_updated: Optional[str] = Field(
        default=None,
        description="Timestamp when configuration was last loaded"
    )


class ValidationWithModel(BaseModel):
    """Validation result with associated model information."""

    validation_id: int = Field(description="Unique validation identifier")
    outcome: str = Field(description="Validation outcome: validated, rejected, or partial")
    reason: str = Field(description="Validation reason or explanation")
    confidence: int = Field(ge=0, le=100, description="Validation confidence percentage")
    created_at: str = Field(description="ISO timestamp of validation creation")
    reviewer_agent_id: str = Field(description="Agent that performed the validation")
    model_info: ModelInfo = Field(description="Information about the model that performed validation")


class MultiModelResponse(BaseModel):
    """Response model for multi-model view API endpoint."""

    success: bool = True
    task_id: int = Field(description="Task ID for the RA tag")
    ra_tag_id: str = Field(description="RA tag identifier")
    ra_tag_text: str = Field(description="Original RA tag text")
    consensus: ConsensusResult = Field(description="Consensus calculation results")
    validations: List[ValidationWithModel] = Field(
        description="All validations for this RA tag with model information"
    )
    model_count: int = Field(ge=0, description="Number of unique models that validated this tag")
    cached: bool = Field(description="Whether result was served from cache")
    generated_at: str = Field(description="ISO timestamp when response was generated")
