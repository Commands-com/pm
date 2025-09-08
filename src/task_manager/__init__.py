"""
Task Manager Module

Provides database layer and atomic locking mechanisms for the Project Manager MCP system.
This module coordinates AI agents working on project tasks through SQLite with WAL mode.

Package provides:
- TaskDatabase: Core database interface with atomic locking
- CLI: Command-line interface via project-manager-mcp script  
- MCP Server: Model Context Protocol server implementation
- FastAPI: Web dashboard for task management
"""

from .database import TaskDatabase

# Package version - synchronized with pyproject.toml
# ASSUMPTION: Version will be managed manually until automated versioning is implemented
__version__ = "0.1.0"

# Package metadata for runtime access
__title__ = "project-manager-mcp"
__description__ = "Project Manager MCP with SQLite database layer and atomic locking"
__author__ = "Project Manager MCP Contributors"
__license__ = "MIT"

# Public API exports
__all__ = [
    'TaskDatabase',
    '__version__',
    '__title__',
    '__description__',
    '__author__',
    '__license__',
]

# Package exports TaskDatabase as primary interface per MVP specification
# Additional exports (utilities, exceptions) can be added as system grows
# Version and metadata provide standard Python package introspection support