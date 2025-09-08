# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the PM Dashboard project.

## Development Environment Setup

**Virtual Environment:**
- `source activate.sh` - Activate the Python virtual environment (uses venv/bin/activate)
- `deactivate` - Deactivate the virtual environment

**Dependencies:**
- `pip install -e ".[dev]"` - Install project in editable mode with development dependencies
- `pip install -e ".[test]"` - Install with test dependencies only
- `pip install -e ".[lint]"` - Install with linting dependencies

## Development Commands

**Testing:**
- `python -m pytest` - Run all tests
- `python -m pytest test/project_manager/` - Run project manager tests
- `python -m pytest test/project_manager/test_database.py -v` - Run database tests with verbose output
- `python -m pytest test/project_manager/test_mcp_server.py -v` - Run MCP server tests
- `python -m pytest -m "not slow"` - Skip slow tests
- `python -m pytest --cov=task_manager` - Run tests with coverage

**Code Quality:**
- `black --check .` - Check code formatting
- `black .` - Format code
- `ruff check .` - Lint code
- `ruff check . --fix` - Lint and auto-fix issues
- `mypy src/` - Type checking

**Running the Application:**
- `python -m task_manager.cli` - Run CLI interface
- `python -m task_manager.mcp_server` - Start MCP server
- `python -m task_manager.api` - Start REST API server

## Project Structure

```
src/task_manager/
├── __init__.py
├── api.py              # REST API endpoints
├── cli.py              # Command-line interface  
├── database.py         # SQLite database layer
├── mcp_server.py       # FastMCP server
├── models.py           # Data models
├── tools.py            # MCP tools implementation
└── static/
    └── index.html      # Frontend dashboard
```

## Database Management

**Fresh Schema Initialization:**
- The database supports clean slate initialization
- Schema includes: projects, epics, tasks, task_logs tables
- JSON validation constraints for RA metadata
- Performance indexes for optimal queries

**Key Tables:**
- `projects` - Top-level project organization
- `epics` - Project subdivisions (references project_id)
- `tasks` - Individual work items with RA fields (references epic_id)
- `task_logs` - Sequence-based task activity logging

## MCP Tools

**Available Tools:**
- `create_task` - Create new tasks with RA metadata
- `update_task` - Update existing tasks
- `get_task_details` - Retrieve task details with logs
- `list_projects` - List all projects
- `list_epics` - List epics with project filtering
- `list_tasks` - List tasks with hierarchy filtering

## Response Awareness (RA) Methodology

The project implements RA methodology with:
- **Complexity Scoring** (1-10): Simple → Standard → RA-Light → RA-Full
- **RA Tags**: #COMPLETION_DRIVE_IMPL, #SUGGEST_ERROR_HANDLING, etc.
- **RA Modes**: simple, standard, ra-light, ra-full
- **Verification Phases**: For complex implementations

## Status Vocabulary

**UI Vocabulary**: TODO, IN_PROGRESS, REVIEW, DONE
**Database Vocabulary**: pending, in_progress, review, completed, blocked

The system maps between UI and database vocabularies automatically.

## Testing Requirements

**Always run these before committing:**
1. `source activate.sh` - Activate virtual environment first
2. `python -m pytest test/project_manager/test_database.py -v` - Database tests (33 tests)
3. `python -m pytest test/project_manager/test_api.py::TestBoardStateEndpoint -v` - API tests (3 tests)
4. `python -m pytest test/project_manager/test_mcp_server.py -v` - MCP server tests  
5. `black --check .` - Code formatting check
6. `mypy src/` - Type checking

**Note:** Remove any existing `project_manager.db` file before running tests to ensure clean schema initialization.

## Architecture Notes

- **Database**: SQLite with WAL mode, JSON validation constraints
- **MCP Server**: FastMCP with system prompt injection
- **Frontend**: Single-page HTML with WebSocket real-time updates
- **Hierarchy**: Projects → Epics → Tasks (stories table removed in schema update)
- **Concurrency**: Atomic task locking with timeout handling