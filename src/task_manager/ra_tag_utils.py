"""
RA Tag Normalization Utilities

This module provides utilities for extracting canonical tag types from free-form RA tag text
while preserving original content. Enables consistent grouping and analysis of assumption
patterns across different tasks.

Pattern Recognition Rules:
- Tags follow format "#PREFIX_SUFFIX: description text" or "#PREFIX: description text"
- Normalized types use format "category:subcategory" (lowercase, dash-separated)
- Unknown tags return "unknown:other" type with full preservation of original text
- Case-insensitive prefix matching with flexible description handling
"""

import re
from typing import Tuple, Dict


# RA tag prefix to normalized category mapping
RA_TAG_MAPPINGS: Dict[str, str] = {
    # Implementation assumption tags
    "COMPLETION_DRIVE_IMPL": "implementation:assumption",
    "COMPLETION_DRIVE_INTEGRATION": "integration:assumption", 
    "COMPLETION_DRIVE_ARCHITECTURE": "architecture:assumption",
    "COMPLETION_DRIVE_UI": "ui:assumption",
    "COMPLETION_DRIVE_WEBSOCKET": "websocket:assumption",
    "COMPLETION_DRIVE_FALLBACK": "fallback:assumption",
    "COMPLETION_DRIVE_RESILIENCE": "resilience:assumption",
    "COMPLETION_DRIVE_REALTIME": "realtime:assumption",
    "COMPLETION_DRIVE_CONFLICT": "conflict:assumption",
    "COMPLETION_DRIVE_LIFECYCLE": "lifecycle:assumption",
    "COMPLETION_DRIVE_SETUP": "setup:assumption",
    "COMPLETION_DRIVE_STARTUP": "startup:assumption",
    "COMPLETION_DRIVE_FILTERING": "filtering:assumption",
    "COMPLETION_DRIVE_INIT": "initialization:assumption",
    "COMPLETION_DRIVE_RA": "ra-methodology:assumption",
    "COMPLETION_DRIVE_MODAL": "modal:assumption",
    "COMPLETION_DRIVE_TABS": "tabs:assumption",
    "COMPLETION_DRIVE_PERFORMANCE": "performance:assumption",
    "COMPLETION_DRIVE_UX": "user-experience:assumption",
    "COMPLETION_DRIVE_RESPONSIVE": "responsive:assumption",
    "COMPLETION_DRIVE_DRAGDROP": "drag-drop:assumption",
    "COMPLETION_DRIVE_OPTIMISTIC": "optimistic-updates:assumption",
    "COMPLETION_DRIVE_SESSION": "session:assumption",
    
    # Context reconstruction tags
    "CONTEXT_DEGRADED": "context:degraded",
    "CONTEXT_RECONSTRUCT": "context:reconstruct",
    
    # Pattern detection tags
    "CARGO_CULT": "pattern:cargo-cult",
    "PATTERN_MOMENTUM": "pattern:momentum",
    "ASSOCIATIVE_GENERATION": "pattern:associative",
    "PATTERN_CONFLICT": "pattern:conflict",
    "TRAINING_CONTRADICTION": "pattern:contradiction",
    
    # Suggestion tags
    "SUGGEST_ERROR_HANDLING": "error-handling:suggestion",
    "SUGGEST_EDGE_CASE": "edge-case:suggestion", 
    "SUGGEST_VALIDATION": "validation:suggestion",
    "SUGGEST_CLEANUP": "cleanup:suggestion",
    "SUGGEST_DEFENSIVE": "defensive:suggestion",
    "SUGGEST_PERFORMANCE": "performance:suggestion",
    "SUGGEST_RESPONSIVE": "responsive:suggestion",
    "SUGGEST_ACCESSIBILITY": "accessibility:suggestion",
    "SUGGEST_IMPLEMENTATION": "implementation:suggestion",
    "SUGGEST_EDGE_CASE": "edge-case:suggestion",
    
    # Generic completion drive tags (catch-all)
    "COMPLETION_DRIVE": "completion-drive:general",
    
    # Path decision tags (from RA planning)
    "PATH_DECISION": "planning:path-decision",
}


def normalize_ra_tag(ra_tag_text: str) -> Tuple[str, str]:
    """
    Extract canonical tag type from RA tag text while preserving original content.
    
    Args:
        ra_tag_text: Raw RA tag text (e.g., "#SUGGEST_ERROR_HANDLING: Input validation needed")
        
    Returns:
        Tuple of (normalized_type, original_text) where:
        - normalized_type: Canonical type like "error-handling:suggestion"
        - original_text: Full original text preserved exactly as provided
        
    Examples:
        >>> normalize_ra_tag("#SUGGEST_ERROR_HANDLING: Input validation")
        ("error-handling:suggestion", "#SUGGEST_ERROR_HANDLING: Input validation")
        
        >>> normalize_ra_tag("#COMPLETION_DRIVE_IMPL: Database connection handling")  
        ("implementation:assumption", "#COMPLETION_DRIVE_IMPL: Database connection handling")
        
        >>> normalize_ra_tag("#UNKNOWN_TAG: Some description")
        ("unknown:other", "#UNKNOWN_TAG: Some description")
    """
    if not ra_tag_text or not isinstance(ra_tag_text, str):
        return ("unknown:other", str(ra_tag_text) if ra_tag_text is not None else "")
    
    # Preserve exact original text
    original_text = ra_tag_text
    
    # Extract tag prefix using regex pattern
    # Matches: #PREFIX or #PREFIX_SUFFIX at start, followed by optional colon and description
    tag_pattern = r'^#([A-Z_]+)(?::\s*.*)?$'
    match = re.match(tag_pattern, ra_tag_text.strip(), re.IGNORECASE)
    
    if not match:
        return ("unknown:other", original_text)
    
    tag_prefix = match.group(1).upper()
    
    # Look up normalized type from mapping
    normalized_type = RA_TAG_MAPPINGS.get(tag_prefix, "unknown:other")
    
    return (normalized_type, original_text)


def extract_tag_category(tag_prefix: str) -> str:
    """
    Extract the primary category from a tag prefix.
    
    Args:
        tag_prefix: Tag prefix like "SUGGEST_ERROR_HANDLING" or "COMPLETION_DRIVE_IMPL"
        
    Returns:
        Primary category like "error-handling" or "implementation"
        
    Examples:
        >>> extract_tag_category("SUGGEST_ERROR_HANDLING")
        "error-handling"
        
        >>> extract_tag_category("COMPLETION_DRIVE_IMPL") 
        "implementation"
        
        >>> extract_tag_category("UNKNOWN_PREFIX")
        "unknown"
    """
    if not tag_prefix or not isinstance(tag_prefix, str):
        return "unknown"
    
    tag_prefix = tag_prefix.upper().strip()
    
    # Look up in mappings and extract category part (before colon)
    normalized_type = RA_TAG_MAPPINGS.get(tag_prefix, "unknown:other")
    category = normalized_type.split(":")[0]
    
    return category


def get_tag_subcategory(tag_prefix: str) -> str:
    """
    Extract the subcategory from a tag prefix.
    
    Args:
        tag_prefix: Tag prefix like "SUGGEST_ERROR_HANDLING" or "COMPLETION_DRIVE_IMPL"
        
    Returns:
        Subcategory like "suggestion" or "assumption"
        
    Examples:
        >>> get_tag_subcategory("SUGGEST_ERROR_HANDLING")
        "suggestion"
        
        >>> get_tag_subcategory("COMPLETION_DRIVE_IMPL")
        "assumption"
        
        >>> get_tag_subcategory("UNKNOWN_PREFIX") 
        "other"
    """
    if not tag_prefix or not isinstance(tag_prefix, str):
        return "other"
    
    tag_prefix = tag_prefix.upper().strip()
    
    # Look up in mappings and extract subcategory part (after colon)
    normalized_type = RA_TAG_MAPPINGS.get(tag_prefix, "unknown:other")
    parts = normalized_type.split(":")
    subcategory = parts[1] if len(parts) > 1 else "other"
    
    return subcategory


def parse_ra_tag_list(ra_tags_json: str) -> list[Tuple[str, str]]:
    """
    Parse JSON string of RA tags and normalize each one.
    
    Args:
        ra_tags_json: JSON string like '["#TAG1: desc", "#TAG2: desc"]'
        
    Returns:
        List of (normalized_type, original_text) tuples
        
    Examples:
        >>> parse_ra_tag_list('["#SUGGEST_ERROR_HANDLING: Input validation", "#COMPLETION_DRIVE_IMPL: DB logic"]')
        [("error-handling:suggestion", "#SUGGEST_ERROR_HANDLING: Input validation"), 
         ("implementation:assumption", "#COMPLETION_DRIVE_IMPL: DB logic")]
    """
    import json
    
    if not ra_tags_json or not isinstance(ra_tags_json, str):
        return []
    
    try:
        tags = json.loads(ra_tags_json)
        if not isinstance(tags, list):
            return []
        
        normalized_tags = []
        for tag in tags:
            if isinstance(tag, str):
                normalized_tags.append(normalize_ra_tag(tag))
        
        return normalized_tags
        
    except (json.JSONDecodeError, TypeError):
        return []


def get_category_stats(normalized_tags: list[Tuple[str, str]]) -> Dict[str, int]:
    """
    Get category breakdown statistics from normalized tags.
    
    Args:
        normalized_tags: List of (normalized_type, original_text) tuples
        
    Returns:
        Dictionary mapping categories to counts
        
    Examples:
        >>> tags = [("error-handling:suggestion", "#SUGGEST_ERROR_HANDLING: desc1"),
        ...         ("implementation:assumption", "#COMPLETION_DRIVE_IMPL: desc2")]
        >>> get_category_stats(tags)
        {"error-handling": 1, "implementation": 1}
    """
    category_counts = {}
    
    for normalized_type, _ in normalized_tags:
        category = normalized_type.split(":")[0]
        category_counts[category] = category_counts.get(category, 0) + 1
    
    return category_counts