"""
MCP Tools Library for Project Manager.

Modular organization of MCP tool implementations with focused modules
for better maintainability and clarity.

Organization:
- base: Abstract BaseTool class and shared utilities
- tasks: Task management tools (create, update, lock, status)
- projects: Project and epic listing tools
- knowledge: Knowledge management tools
- instructions: RA instructions retrieval tool
- assumptions: RA tag and assumption validation tools
"""

from typing import Dict, Type

from ..database import TaskDatabase
from ..api import ConnectionManager

# Import base class
from .base import BaseTool

# Import task-related tools
from .tasks import (
    GetAvailableTasks,
    AcquireTaskLock,
    UpdateTaskStatus,
    ReleaseTaskLock,
    CreateTaskTool,
    UpdateTaskTool,
    GetTaskDetailsTool,
    DeleteTaskTool,
)

# Import project/epic tools
from .projects import (
    ListProjectsTool,
    ListEpicsTool,
    ListTasksTool,
)

# Import knowledge management tools
from .knowledge import (
    GetKnowledgeTool,
    UpsertKnowledgeTool,
    AppendKnowledgeLogTool,
    GetKnowledgeLogsTool,
)

# Import instructions tool
from .instructions import (
    GetInstructionsTool,
    get_task_knowledge_context,
)

# Import assumption/RA tag tools
from .assumptions import (
    CaptureAssumptionValidationTool,
    AddRATagTool,
)

# Tool registry for factory pattern
AVAILABLE_TOOLS: Dict[str, Type[BaseTool]] = {
    "get_available_tasks": GetAvailableTasks,
    "acquire_task_lock": AcquireTaskLock,
    "update_task_status": UpdateTaskStatus,
    "release_task_lock": ReleaseTaskLock,
    "create_task": CreateTaskTool,
    "update_task": UpdateTaskTool,
    "get_task_details": GetTaskDetailsTool,
    "list_projects": ListProjectsTool,
    "list_epics": ListEpicsTool,
    "list_tasks": ListTasksTool,
    "delete_task": DeleteTaskTool,
    "get_knowledge": GetKnowledgeTool,
    "upsert_knowledge": UpsertKnowledgeTool,
    "append_knowledge_log": AppendKnowledgeLogTool,
    "get_knowledge_logs": GetKnowledgeLogsTool,
}


def create_tool_instance(
    tool_name: str, database: TaskDatabase, websocket_manager: ConnectionManager
) -> BaseTool:
    """
    Factory function to create tool instances with dependencies.

    Provides a clean interface for MCP server integration to create
    tool instances with proper dependency injection.

    Args:
        tool_name: Name of the tool to create
        database: TaskDatabase instance for data operations
        websocket_manager: ConnectionManager for real-time broadcasting

    Returns:
        Configured tool instance ready for use

    Raises:
        KeyError: If tool_name is not found in AVAILABLE_TOOLS
    """
    if tool_name not in AVAILABLE_TOOLS:
        raise KeyError(
            f"Unknown tool '{tool_name}'. Available tools: {list(AVAILABLE_TOOLS.keys())}"
        )

    tool_class = AVAILABLE_TOOLS[tool_name]
    return tool_class(database, websocket_manager)


__all__ = [
    "BaseTool",
    "GetAvailableTasks",
    "AcquireTaskLock",
    "UpdateTaskStatus",
    "ReleaseTaskLock",
    "CreateTaskTool",
    "UpdateTaskTool",
    "GetTaskDetailsTool",
    "DeleteTaskTool",
    "ListProjectsTool",
    "ListEpicsTool",
    "ListTasksTool",
    "GetKnowledgeTool",
    "UpsertKnowledgeTool",
    "AppendKnowledgeLogTool",
    "GetKnowledgeLogsTool",
    "GetInstructionsTool",
    "get_task_knowledge_context",
    "CaptureAssumptionValidationTool",
    "AddRATagTool",
    "AVAILABLE_TOOLS",
    "create_tool_instance",
]
