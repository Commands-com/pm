"""
Backward Compatibility Shim for MCP Tools

This module provides backward compatibility for code importing from
task_manager.tools by re-exporting all tools from the refactored tools_lib package.

DEPRECATED: New code should import directly from tools_lib.
This compatibility layer will be removed in a future version.

Migration guide:
    OLD: from task_manager.tools import CreateTaskTool
    NEW: from task_manager.tools_lib import CreateTaskTool
"""

import warnings

# Issue deprecation warning when this module is imported
warnings.warn(
    "Importing from 'task_manager.tools' is deprecated. "
    "Please update imports to 'task_manager.tools_lib'. "
    "This compatibility shim will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export all tools from the refactored tools_lib package
from .tools_lib import (
    # Base class
    BaseTool,

    # Task tools
    GetAvailableTasks,
    AcquireTaskLock,
    UpdateTaskStatus,
    ReleaseTaskLock,
    CreateTaskTool,
    UpdateTaskTool,
    GetTaskDetailsTool,
    DeleteTaskTool,

    # Project/Epic tools
    ListProjectsTool,
    ListEpicsTool,
    ListTasksTool,

    # Knowledge tools
    GetKnowledgeTool,
    UpsertKnowledgeTool,
    AppendKnowledgeLogTool,
    GetKnowledgeLogsTool,

    # Instructions tool
    GetInstructionsTool,
    get_task_knowledge_context,

    # Assumption/RA tools
    CaptureAssumptionValidationTool,
    AddRATagTool,

    # Registry and factory
    AVAILABLE_TOOLS,
    create_tool_instance,
)

# Re-export utility functions and managers needed by tests
from .context_utils import create_enriched_context
from .ra_tag_utils import normalize_ra_tag
from .ra_instructions import ra_instructions_manager

__all__ = [
    'BaseTool',
    'GetAvailableTasks',
    'AcquireTaskLock',
    'UpdateTaskStatus',
    'ReleaseTaskLock',
    'CreateTaskTool',
    'UpdateTaskTool',
    'GetTaskDetailsTool',
    'DeleteTaskTool',
    'ListProjectsTool',
    'ListEpicsTool',
    'ListTasksTool',
    'GetKnowledgeTool',
    'UpsertKnowledgeTool',
    'AppendKnowledgeLogTool',
    'GetKnowledgeLogsTool',
    'GetInstructionsTool',
    'get_task_knowledge_context',
    'CaptureAssumptionValidationTool',
    'AddRATagTool',
    'AVAILABLE_TOOLS',
    'create_tool_instance',
    # Utility functions and managers
    'create_enriched_context',
    'normalize_ra_tag',
    'ra_instructions_manager',
]
