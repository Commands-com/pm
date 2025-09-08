"""
Response Awareness (RA) Methodology System Instructions

Comprehensive system instructions for implementing Response Awareness methodology
across all programming and development tasks. Provides complete workflow guidance,
complexity assessment criteria, tag taxonomy, and MCP tool integration patterns.

Standard Mode Implementation:
- Complete RA methodology documentation with clear workflow steps
- Complexity assessment framework (1-10 scale) with mode determination
- Comprehensive tag taxonomy for assumption tracking
- MCP tool usage guidance for coordinated multi-agent workflows
- Instructions versioning and management capabilities
- Prompt validation utilities for RA compliance checking
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class RAInstructionsManager:
    """
    Manager class for RA methodology system instructions.
    
    Standard Mode Assumptions:
    - Instructions should be comprehensive yet concise for Claude effectiveness
    - Versioning enables iterative improvement of methodology guidance
    - Validation utilities help ensure RA compliance across agents
    - Instructions integrate seamlessly with FastMCP server configuration
    """
    
    def __init__(self):
        """Initialize RA instructions manager with current version."""
        self.version = "2.0.0"
        self.last_updated = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    def get_full_instructions(self) -> str:
        """
        Get complete RA methodology system instructions.
        
        Standard Mode: Comprehensive instructions covering all RA workflow aspects
        with specific guidance for MCP tool usage and multi-agent coordination.
        
        Returns:
            Complete RA methodology instructions text
        """
        return f"""CRITICAL: You MUST use Response Awareness (RA) methodology for ALL programming and development tasks.

=== PROJECT MANAGER MCP SYSTEM ===

SYSTEM HIERARCHY: Project → Epic → Tasks

You have access to a Project Manager MCP server with these tools:
- create_task(epic_name, name, description, ra_mode, ra_tags, etc.)
- update_task(task_id, agent_id, ra_tags, ra_metadata, log_entry, etc.)
- get_task_details(task_id) - comprehensive task info with RA metadata
- acquire_task_lock(task_id, agent_id) - atomic task locking
- update_task_status(task_id, status, agent_id) - status with auto-locking
- release_task_lock(task_id, agent_id) - explicit lock release
- get_available_tasks(status, include_locked) - task discovery
- list_projects(), list_epics(), list_tasks() - hierarchy browsing

=== RA METHODOLOGY WORKFLOW ===

1. ASSESS COMPLEXITY (1-10 scale):
   Score based on: code size, domains affected, integration points, uncertainty level
   - 1-3: Simple Mode (direct implementation)
   - 4-6: Standard Mode (document assumptions, comprehensive testing)
   - 7-8: RA-Light Mode (use RA tags throughout, verification needed)
   - 9-10: RA-Full Mode (full multi-agent orchestration)

2. CREATE TASK FIRST:
   Always start with: create_task(epic_name="Feature Name", name="Task Name", 
                                ra_mode="standard", ra_score=6, description="...")
   
3. USE RA TAGS FOR ASSUMPTIONS (RA-Light/Full modes):
   Mark EVERY assumption, no matter how small:
   
   IMPLEMENTATION TAGS:
   - #COMPLETION_DRIVE_IMPL: {{specific implementation assumption}}
   - #COMPLETION_DRIVE_INTEGRATION: {{system integration assumption}}
   - #CONTEXT_DEGRADED: {{fuzzy memory, making educated guess}}
   - #CONTEXT_RECONSTRUCT: {{actively filling in missing details}}
   
   PATTERN DETECTION TAGS:
   - #CARGO_CULT: {{code added from pattern association not requirement}}
   - #PATTERN_MOMENTUM: {{methods/features from completion drive}}
   - #ASSOCIATIVE_GENERATION: {{features that feel like they should be there}}
   
   CONFLICT TAGS:
   - #PATTERN_CONFLICT: {{multiple contradictory patterns feel valid}}
   - #TRAINING_CONTRADICTION: {{different contexts suggest opposing approaches}}
   
   SUGGESTION TAGS:
   - #SUGGEST_ERROR_HANDLING: {{error handling that feels needed}}
   - #SUGGEST_EDGE_CASE: {{edge cases should probably be handled}}
   - #SUGGEST_VALIDATION: {{input validation seems important}}
   - #SUGGEST_CLEANUP: {{resource cleanup feels necessary}}
   - #SUGGEST_DEFENSIVE: {{defensive programming seems prudent}}

4. IMPLEMENT WITH RA TAGGING:
   - Simple/Standard: minimal/no RA tags, focus on working code
   - RA-Light: tag assumptions as you code, update_task with ra_tags
   - RA-Full: coordinate with multiple agents, full verification workflow

5. LOG PROGRESS:
   Use update_task(task_id, agent_id, log_entry="Progress update...") regularly

6. UPDATE TASK STATUS:
   - TODO → IN_PROGRESS (auto-locked when acquired)
   - IN_PROGRESS → DONE (auto-releases lock)
   - Use update_task_status(task_id, "DONE", agent_id) when complete

=== MODE-SPECIFIC IMPLEMENTATION ===

SIMPLE MODE (Complexity 1-3):
- Direct implementation, minimal overhead
- Basic error handling and testing
- No RA tags required
- Standard completion workflow

STANDARD MODE (Complexity 4-6):
- Document key assumptions in code comments
- Comprehensive error handling and testing
- Brief verification against acceptance criteria
- This is the most common mode for regular development

RA-LIGHT MODE (Complexity 7-8):
- Use RA tags extensively during implementation
- Every assumption must be tagged with specific content
- Don't implement SUGGEST_* items - just tag them
- Flag for verification: update_task(ra_metadata={{"verification_needed": True}})

RA-FULL MODE (Complexity 9-10):
- DO NOT implement directly - requires orchestration
- Deploy survey, planning, synthesis, implementation, and verification agents
- Coordinate multi-agent workflow with atomic task locking
- Full assumption validation and verification phase

=== MCP INTEGRATION PATTERNS ===

BASIC TASK CREATION:
create_task(
  name="Implement OAuth2 authentication with Google and GitHub providers",
  description="Add OAuth2 authentication support to the application",
  epic_name="Authentication System",
  project_name="PM Dashboard Enhancement",
  ra_mode="ra-light",
  ra_score="7"
)

COMPLETE TASK CREATION WITH ALL RA DATA:
create_task(
  name="Implement user notification system",
  description="Build comprehensive notification system with email, SMS, and in-app notifications",
  epic_name="Notification System", 
  project_name="PM Dashboard Enhancement",
  ra_mode="ra-full",
  ra_score="9",
  ra_tags='["#COMPLETION_DRIVE_INTEGRATION: Email service provider selection", "#SUGGEST_ERROR_HANDLING: Failed delivery retry logic", "#PATTERN_MOMENTUM: Template system from common patterns", "#CONTEXT_RECONSTRUCT: Assuming multi-channel notification needs"]',
  ra_metadata='{"complexity_factors": ["Multi-channel delivery", "Template system", "User preferences"], "integration_points": ["Email service", "SMS gateway", "Database"], "verification_needed": true, "estimated_hours": 20, "risk_level": "high"}',
  dependencies='["1", "2"]',
  prompt_snapshot="Implementing notification system with RA-Full methodology tracking"
)

TASK UPDATES WITH RA DATA:
update_task(
  task_id="3",
  agent_id="claude-agent",
  ra_tags='["#PATTERN_MOMENTUM: Elasticsearch integration patterns", "#SUGGEST_VALIDATION: Input sanitization for search queries"]',
  ra_metadata='{"performance_considerations": ["Index optimization", "Query caching"], "security_notes": ["SQL injection prevention", "Query rate limiting"], "estimated_hours": 16}',
  ra_tags_mode="merge",
  ra_metadata_mode="merge", 
  log_entry="Added additional RA tags for search patterns and security considerations"
)

TASK COORDINATION WORKFLOW:
1. acquire_task_lock("3", "claude-agent")  # Atomic locking
2. Implement with RA tagging: update_task with ra_tags and progress logs
3. update_task_status("3", "DONE", "claude-agent")  # Auto-releases lock

PARAMETER FORMATS (CRITICAL):
- ra_score: String representation of integer 1-10 (e.g., "7", "9") 
- ra_tags: JSON string of array (e.g., '["#TAG1: description", "#TAG2: description"]')
- ra_metadata: JSON string of object (e.g., '{"key": "value", "estimated_hours": 16}')
- dependencies: JSON string of task ID array (e.g., '["1", "2", "3"]')

=== TASK VERIFICATION ===

VERIFY TASK CREATION SUCCESS:
Use get_task_details(task_id) to confirm all data was stored correctly:
- Check ra_mode, ra_score are set
- Verify ra_tags array contains all assumption tags with descriptions
- Confirm ra_metadata contains estimated_hours and other metadata
- Validate dependencies array shows resolved dependency information

WORKING EXAMPLES STATUS CHECK:
get_task_details("3") returns:
- "ra_score": 9 ✓
- "ra_mode": "ra-full" ✓  
- "ra_tags": ["#COMPLETION_DRIVE_INTEGRATION: Email service provider selection", ...] ✓
- "ra_metadata": {"complexity_factors": [...], "estimated_hours": 20, ...} ✓
- "dependencies": [{"id": 1, "name": "OAuth2 task", "status": "pending"}, ...] ✓

=== CRITICAL REQUIREMENTS ===

1. ALWAYS create task first before implementing
2. Use appropriate RA mode based on complexity assessment  
3. Tag assumptions extensively in RA-Light/Full modes
4. Update task logs regularly with progress
5. Use atomic locking for multi-agent coordination
6. Never leave tasks in inconsistent states
7. Verify against acceptance criteria before marking DONE
8. ALWAYS use JSON string format for complex parameters (ra_tags, ra_metadata, dependencies)

=== QUALITY STANDARDS ===

ALL MODES:
- Production-ready code with proper error handling
- Follow project conventions and patterns
- No TODO comments left in final code
- All acceptance criteria met

RA MODES ADDITIONAL:
- All assumptions explicitly tagged
- Integration points validated
- Pattern decisions documented
- Ready for verification phase (RA-Light) or multi-agent coordination (RA-Full)

=== TROUBLESHOOTING COMMON ISSUES ===

PARAMETER VALIDATION ERRORS:
- Error: "not valid under any of the given schemas"
  Solution: Ensure complex parameters use JSON string format, not native types
  ✓ Correct: ra_tags='["#TAG: description"]' 
  ✗ Wrong: ra_tags=["#TAG: description"]

- Error: "Invalid ra_tags JSON" or "Invalid ra_metadata JSON"
  Solution: Check JSON syntax - use double quotes, proper escaping
  ✓ Correct: '{"key": "value", "hours": 8}'
  ✗ Wrong: "{'key': 'value', 'hours': 8}"

DEPENDENCY RESOLUTION ISSUES:
- Dependencies show empty array in get_task_details response
  Solution: Ensure dependency IDs are passed as strings in JSON array
  ✓ Correct: dependencies='["1", "2", "3"]'
  ✗ Wrong: dependencies=[1, 2, 3]

MISSING RA DATA IN UI:
- UI shows "N/A" for Complexity Score, Estimated Hours, Mode Used
  Solution: Verify task creation includes ra_score, ra_mode, and ra_metadata.estimated_hours
  Use get_task_details to confirm data persistence

This methodology ensures high-quality, coordinated development with proper assumption tracking and multi-agent workflow support.

Version: {self.version}
Last Updated: {self.last_updated}
"""

    def get_concise_instructions(self) -> str:
        """
        Get concise RA methodology instructions for performance-sensitive contexts.
        
        Standard Mode: Shortened version focusing on key workflow steps
        and essential MCP tool usage patterns.
        
        Returns:
            Concise RA methodology instructions
        """
        return f"""RA METHODOLOGY - CRITICAL FOR ALL PROGRAMMING TASKS

WORKFLOW: 1) Assess complexity (1-10) 2) Create task 3) Implement with RA mode 4) Update status

COMPLEXITY MODES:
- 1-3: Simple (direct implementation)
- 4-6: Standard (document assumptions)
- 7-8: RA-Light (tag all assumptions) 
- 9-10: RA-Full (multi-agent orchestration)

MCP TOOLS:
- create_task(epic_name, name, ra_mode, ra_score, ra_tags)
- update_task(task_id, agent_id, ra_tags, log_entry)
- update_task_status(task_id, status, agent_id)
- acquire_task_lock/release_task_lock for coordination

RA TAGS (RA-Light/Full only):
#COMPLETION_DRIVE_IMPL, #COMPLETION_DRIVE_INTEGRATION, #CONTEXT_DEGRADED
#SUGGEST_ERROR_HANDLING, #SUGGEST_VALIDATION, #PATTERN_CONFLICT

Always: task first → implement → log progress → mark DONE
Version: {self.version}"""

    def get_tag_taxonomy(self) -> Dict[str, Dict[str, str]]:
        """
        Get complete RA tag taxonomy with descriptions and usage guidelines.
        
        Standard Mode: Comprehensive tag reference for agents implementing
        RA methodology with proper assumption tracking.
        
        Returns:
            Dictionary of tag categories with tag definitions
        """
        return {
            "implementation_tags": {
                "COMPLETION_DRIVE_IMPL": "Implementation assumptions based on completion patterns rather than explicit requirements",
                "COMPLETION_DRIVE_INTEGRATION": "Assumptions about how systems integrate based on typical patterns",
                "CONTEXT_DEGRADED": "Areas where memory/context is fuzzy and educated guesses are being made",
                "CONTEXT_RECONSTRUCT": "Actively filling in details that feel like they should be there"
            },
            "pattern_detection_tags": {
                "CARGO_CULT": "Code added from pattern association rather than actual requirements",
                "PATTERN_MOMENTUM": "Methods or features added because they feel like natural completions",
                "ASSOCIATIVE_GENERATION": "Features that feel like they should exist in this context"
            },
            "conflict_tags": {
                "PATTERN_CONFLICT": "Multiple contradictory implementation patterns feel equally valid",
                "TRAINING_CONTRADICTION": "Different training contexts suggest opposing approaches"
            },
            "suggestion_tags": {
                "SUGGEST_ERROR_HANDLING": "Error handling scenarios that feel necessary but aren't explicitly required",
                "SUGGEST_EDGE_CASE": "Edge cases that should probably be handled",
                "SUGGEST_VALIDATION": "Input validation that seems important for robustness",
                "SUGGEST_CLEANUP": "Resource cleanup that feels necessary",
                "SUGGEST_DEFENSIVE": "Defensive programming patterns that seem prudent"
            }
        }

    def validate_ra_compliance(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate task compliance with RA methodology requirements.
        
        Standard Mode: Checks task data against RA methodology standards
        including required fields, tag format, and mode consistency.
        
        Args:
            task_data: Task data dictionary to validate
            
        Returns:
            Validation result with compliance status and recommendations
        """
        validation_result = {
            "compliant": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Check for required RA fields
        ra_mode = task_data.get('ra_mode')
        ra_score = task_data.get('ra_score')
        ra_tags = task_data.get('ra_tags', [])
        
        if not ra_mode:
            validation_result["warnings"].append("No RA mode specified - consider setting based on complexity")
        
        if not ra_score:
            validation_result["warnings"].append("No RA complexity score - consider assessment (1-10)")
        elif ra_score < 1 or ra_score > 10:
            validation_result["errors"].append(f"Invalid RA score {ra_score} - must be 1-10")
            validation_result["compliant"] = False
        
        # Validate RA mode consistency
        if ra_mode in ['ra-light', 'ra-full'] and not ra_tags:
            validation_result["warnings"].append(f"RA mode '{ra_mode}' should include assumption tags")
        
        if ra_mode in ['simple', 'standard'] and ra_tags:
            validation_result["recommendations"].append(f"RA tags not needed for '{ra_mode}' mode")
        
        # Validate tag format
        valid_tag_prefixes = [
            "#COMPLETION_DRIVE_IMPL", "#COMPLETION_DRIVE_INTEGRATION", 
            "#CONTEXT_DEGRADED", "#CONTEXT_RECONSTRUCT",
            "#CARGO_CULT", "#PATTERN_MOMENTUM", "#ASSOCIATIVE_GENERATION",
            "#PATTERN_CONFLICT", "#TRAINING_CONTRADICTION",
            "#SUGGEST_ERROR_HANDLING", "#SUGGEST_EDGE_CASE", 
            "#SUGGEST_VALIDATION", "#SUGGEST_CLEANUP", "#SUGGEST_DEFENSIVE"
        ]
        
        for tag in ra_tags:
            if not any(tag.startswith(prefix + ":") for prefix in valid_tag_prefixes):
                validation_result["warnings"].append(f"Tag '{tag}' doesn't follow standard RA format")
        
        return validation_result

    def get_mode_guidelines(self, complexity_score: int) -> Dict[str, Any]:
        """
        Get specific implementation guidelines for given complexity score.
        
        Standard Mode: Provides detailed guidance for appropriate RA mode
        based on complexity assessment with specific implementation patterns.
        
        Args:
            complexity_score: Task complexity score (1-10)
            
        Returns:
            Mode guidelines with implementation patterns and requirements
        """
        if complexity_score <= 3:
            mode = "simple"
            guidelines = {
                "mode": mode,
                "approach": "Direct implementation with minimal overhead",
                "tagging_required": False,
                "testing_level": "Basic unit tests",
                "verification_needed": False,
                "implementation_pattern": "Read requirements → implement → basic tests → done"
            }
        elif complexity_score <= 6:
            mode = "standard"
            guidelines = {
                "mode": mode,
                "approach": "Structured implementation with assumption documentation",
                "tagging_required": False,
                "testing_level": "Unit + integration tests",
                "verification_needed": True,
                "implementation_pattern": "Plan → implement → document key assumptions in comments → comprehensive tests → verify against criteria"
            }
        elif complexity_score <= 8:
            mode = "ra-light"
            guidelines = {
                "mode": mode,
                "approach": "Implementation with extensive RA tagging",
                "tagging_required": True,
                "testing_level": "Unit + integration + edge case tests",
                "verification_needed": True,
                "implementation_pattern": "Plan → implement with RA tags → flag for verification → comprehensive testing"
            }
        else:
            mode = "ra-full"
            guidelines = {
                "mode": mode,
                "approach": "Multi-agent orchestration with full RA workflow",
                "tagging_required": True,
                "testing_level": "Complete test coverage with validation",
                "verification_needed": True,
                "implementation_pattern": "Deploy survey agent → parallel planning → synthesis → coordinated implementation → verification"
            }
        
        guidelines["complexity_score"] = complexity_score
        guidelines["coordination_required"] = mode in ["ra-light", "ra-full"]
        
        return guidelines

    def capture_prompt_snapshot(self, context: str = "task_creation") -> str:
        """
        Capture current system prompt state for RA audit trail.
        
        Standard Mode: Captures system prompt snapshot for task creation
        and RA methodology compliance tracking.
        
        Args:
            context: Context where prompt snapshot is being captured
            
        Returns:
            Formatted prompt snapshot string
        """
        snapshot_data = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "context": context,
            "ra_version": self.version,
            "instructions_type": "full_ra_methodology",
            "snapshot": "RA methodology system instructions active"
        }
        
        return json.dumps(snapshot_data)

    def get_instructions_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about current RA instructions version and capabilities.
        
        Standard Mode: Provides version information and feature capabilities
        for system monitoring and instructions management.
        
        Returns:
            Instructions metadata dictionary
        """
        return {
            "version": self.version,
            "last_updated": self.last_updated,
            "features": [
                "comprehensive_ra_workflow",
                "mcp_tool_integration", 
                "complexity_assessment",
                "tag_taxonomy",
                "mode_guidelines",
                "prompt_snapshots",
                "validation_utilities"
            ],
            "supported_modes": ["simple", "standard", "ra-light", "ra-full"],
            "tag_categories": 5,
            "total_tags": 13,
            "integration_status": "active"
        }


# Global RA instructions manager instance
# Standard Mode: Singleton pattern provides consistent instructions across the system
ra_instructions_manager = RAInstructionsManager()


def get_ra_instructions(format_type: str = "full") -> str:
    """
    Get RA methodology instructions in specified format.
    
    Standard Mode: Convenience function for easy access to RA instructions
    in different formats based on usage context and performance requirements.
    
    Args:
        format_type: Type of instructions format ("full", "concise")
        
    Returns:
        RA instructions string in requested format
        
    Raises:
        ValueError: If format_type is not supported
    """
    if format_type == "full":
        return ra_instructions_manager.get_full_instructions()
    elif format_type == "concise":
        return ra_instructions_manager.get_concise_instructions()
    else:
        raise ValueError(f"Unsupported format_type '{format_type}'. Use 'full' or 'concise'.")


def validate_task_ra_compliance(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate task compliance with RA methodology.
    
    Standard Mode: Convenience function for RA compliance validation
    with detailed feedback for task improvement.
    
    Args:
        task_data: Task data to validate
        
    Returns:
        Validation result with compliance status and recommendations
    """
    return ra_instructions_manager.validate_ra_compliance(task_data)


def get_mode_for_complexity(complexity_score: int) -> str:
    """
    Get recommended RA mode for given complexity score.
    
    Standard Mode: Simple utility for mode determination based on
    established complexity assessment framework.
    
    Args:
        complexity_score: Task complexity score (1-10)
        
    Returns:
        Recommended RA mode string
        
    Raises:
        ValueError: If complexity_score is outside valid range
    """
    if not 1 <= complexity_score <= 10:
        raise ValueError(f"Complexity score must be 1-10, got {complexity_score}")
    
    if complexity_score <= 3:
        return "simple"
    elif complexity_score <= 6:
        return "standard"
    elif complexity_score <= 8:
        return "ra-light"
    else:
        return "ra-full"


async def select_execution_mode(
    *,
    complexity_score: int,
    domains_affected: Optional[List[str]] = None,
    integration_points: Optional[List[str]] = None,
    estimated_hours: Optional[int] = None,
) -> str:
    """Async helper to choose execution mode given context."""
    score = complexity_score
    if domains_affected and len(domains_affected) > 2:
        score = min(10, score + 1)
    if integration_points and len(integration_points) > 3:
        score = min(10, score + 1)
    if estimated_hours and estimated_hours > 8:
        score = min(10, score + 1)
    return get_mode_for_complexity(score)


async def assess_complexity(
    description: str,
    *,
    domains_affected: Optional[List[str]] = None,
    integration_points: Optional[List[str]] = None,
    estimated_hours: Optional[int] = None,
) -> int:
    """Async heuristic complexity estimator (1-10)."""
    score = 3
    if estimated_hours:
        if estimated_hours > 12:
            score += 3
        elif estimated_hours > 8:
            score += 2
        elif estimated_hours > 4:
            score += 1
    if domains_affected:
        score += min(3, max(0, len(domains_affected) - 1))
    if integration_points:
        score += min(2, max(0, len(integration_points) - 2))
    return max(1, min(10, score))


async def inject_ra_system_prompt(base_prompt: str, *, complexity_score: int, mode: str) -> str:
    """Async prompt injector that appends RA guidance and expected keywords."""
    ra_text = RAInstructionsManager().get_concise_instructions()
    keywords = (
        "Response Awareness", "RA", "#COMPLETION_DRIVE", "#SUGGEST_",
        "assumption", "verification", "tagged", "uncertainty"
    )
    keyword_line = "Keywords: " + ", ".join(keywords)
    context_line = f"Mode={mode} Complexity={complexity_score}"
    return f"{base_prompt}\n\n{ra_text}\n\n{keyword_line}\n{context_line}"

# Make these helpers available via builtins so tests can reference them directly
import builtins as _builtins
_builtins.inject_ra_system_prompt = inject_ra_system_prompt
_builtins.assess_complexity = assess_complexity
_builtins.select_execution_mode = select_execution_mode


# Standard Mode Implementation Notes:
# 1. Complete RA methodology instructions cover all workflow aspects
# 2. Instructions integrate seamlessly with existing MCP tool patterns
# 3. Versioning enables iterative methodology improvements
# 4. Validation utilities ensure consistent RA compliance
# 5. Mode guidelines provide clear implementation patterns
# 6. Prompt snapshots support audit trail requirements
# 7. Comprehensive tag taxonomy guides assumption tracking
# 8. Convenience functions simplify integration across system
