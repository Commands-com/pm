---
name: pm-dashboard-dev
description: Development patterns for PM Dashboard plugin including MCP tools, FastAPI endpoints, database operations, WebSocket broadcasting, and testing requirements. Use when working on src/task_manager/, adding features, or modifying the plugin codebase.
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# PM Dashboard Development Patterns

This skill guides development on the PM Dashboard plugin codebase with established patterns, architecture, and testing requirements.

## Architecture Overview

```
Database Layer (SQLite + WAL)
      ↓
Tools Layer (MCP tools via tools_lib/)
      ↓
MCP Server (FastMCP integration)
      ↓
API Layer (FastAPI + WebSocket)
      ↓
Frontend (Static HTML/CSS/JS)
```

For detailed architecture, see [ARCHITECTURE.md](reference/ARCHITECTURE.md).

## Quick Start Commands

```bash
# Activate virtual environment
source activate.sh

# Install dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest test/project_manager/ -v

# Run specific test file
python -m pytest test/project_manager/test_database.py -v

# Type checking
mypy src/

# Code formatting
black .

# Lint code
ruff check .

# Start API server
python -m task_manager.api

# Start MCP server
python -m task_manager.mcp_server
```

## Project Structure

```
src/task_manager/
├── database/
│   ├── connection.py      # Database initialization & schema
│   ├── tasks.py           # Task CRUD operations
│   ├── locks.py           # Atomic task locking
│   └── projects.py        # Project/epic operations
├── tools_lib/
│   ├── base.py            # BaseTool class
│   ├── tasks.py           # Task management tools
│   ├── knowledge.py       # Knowledge management tools
│   └── assumptions.py     # RA tag tools
├── routers/
│   ├── board.py           # Board state endpoint
│   ├── tasks.py           # Task endpoints
│   ├── projects.py        # Project endpoints
│   └── knowledge.py       # Knowledge endpoints
├── api.py                 # FastAPI app + WebSocket manager
├── mcp_server.py          # FastMCP server
├── models.py              # Pydantic models
└── static/                # Frontend assets
```

## Adding New MCP Tools

See [ADDING_MCP_TOOLS.md](reference/ADDING_MCP_TOOLS.md) for complete step-by-step guide.

### Quick Pattern

1. **Create tool class** in `tools_lib/`:
```python
from .base import BaseTool

class MyNewTool(BaseTool):
    async def apply(self, param1: str, param2: Optional[int] = None) -> str:
        """Tool description."""
        try:
            # Implementation
            return self._format_success_response(
                "Operation successful",
                result_data=data
            )
        except Exception as e:
            return self._format_error_response("Operation failed", error_details=str(e))
```

2. **Register in MCP server** (`mcp_server.py`):
```python
@mcp.tool
async def my_new_tool(param1: str, param2: Optional[int] = None) -> str:
    """
    Tool description for MCP clients.

    Args:
        param1: Description
        param2: Description (optional)

    Returns:
        JSON string with results
    """
    tool = MyNewTool(self.db, self.websocket_manager)
    return await tool.apply(param1, param2)
```

3. **Add tests** in `test/project_manager/test_tools.py`

## Database Patterns

### Status Vocabulary Mapping

**UI Vocabulary** (for frontend):
- TODO
- IN_PROGRESS
- REVIEW
- DONE
- BACKLOG

**Database Vocabulary** (internal):
- pending
- in_progress
- review
- completed
- backlog

Always map between these in API endpoints!

### Atomic Operations

**Prefer atomic patterns** for concurrency safety:

```python
# GOOD - Atomic single UPDATE
cursor.execute("""
    UPDATE tasks SET lock_holder = ?, lock_expires_at = ?
    WHERE id = ? AND (lock_holder IS NULL OR lock_expires_at < ?)
""", (agent_id, expires_at, task_id, current_time))

# BAD - Race condition risk
lock_status = get_lock_status(task_id)
if not lock_status["is_locked"]:
    acquire_lock(task_id, agent_id)  # Another agent could lock between these!
```

### JSON Validation

All JSON fields have database-level validation:

```sql
CONSTRAINT json_ra_tags CHECK (
    ra_tags IS NULL OR (
        json_valid(ra_tags) AND
        json_type(ra_tags) = 'array'
    )
)
```

Ensure your code generates valid JSON!

## WebSocket Broadcasting

```python
from ..api import connection_manager

# Broadcast event to all connected clients
await connection_manager.optimized_broadcast({
    "type": "task.status_changed",
    "task_id": task_id,
    "status": "IN_PROGRESS",
    "agent_id": "claude"
})
```

**Common event types:**
- `task.created`
- `task.updated`
- `task.status_changed`
- `task.locked`
- `task.unlocked`
- `task_deleted`
- `project_deleted`
- `epic_deleted`

## Testing Requirements

See [TESTING.md](reference/TESTING.md) for comprehensive guide.

### Before Every Commit

Run this test suite (all must pass):

```bash
# 1. Database tests
python -m pytest test/project_manager/test_database.py -v

# 2. API tests
python -m pytest test/project_manager/test_api.py::TestBoardStateEndpoint -v

# 3. MCP server tests
python -m pytest test/project_manager/test_mcp_server.py -v

# 4. Code formatting
black --check .

# 5. Type checking
mypy src/
```

### Test Script

Use the provided test runner:

```bash
bash scripts/run-full-tests.sh
```

## Code Style

- **Black** for formatting (line length: 100)
- **Type hints** required for all functions
- **Docstrings** for public APIs (Google style)
- **Pydantic models** for validation
- **Async/await** for I/O operations

## Common Patterns

### Error Handling in API Endpoints

```python
try:
    result = db.some_operation(param)
    if result["success"]:
        await connection_manager.broadcast({...})
        return {"success": True, "data": result}
    else:
        raise HTTPException(status_code=400, detail=result["error"])
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

### MCP Tool Response Format

```python
# Success
return self._format_success_response(
    "Task created successfully",
    task_id=task_id,
    task_name=name
)

# Error
return self._format_error_response(
    "Task not found",
    task_id=task_id
)
```

### Parameter Validation (MCP Tools)

MCP tools receive **string parameters only**:

```python
# Convert to appropriate types
task_id = int(task_id_str)
limit = int(limit_str) if limit_str else None

# Parse JSON strings
ra_tags = json.loads(ra_tags_str) if ra_tags_str else []
ra_metadata = json.loads(ra_metadata_str) if ra_metadata_str else {}
```

## Security Considerations

- **SQL injection**: Use parameterized queries (we do this everywhere)
- **Input validation**: Pydantic models validate all API inputs
- **No authentication**: This is a local-only tool (documented limitation)
- **JSON validation**: Database constraints prevent invalid JSON

## Performance Tips

- **Database**: WAL mode enabled for concurrent reads/writes
- **Indexes**: 25+ strategic indexes for common queries
- **WebSocket**: Optimized parallel broadcasting with asyncio.gather
- **Caching**: Connection manager caches connection stats

## Common Pitfalls

### ❌ Wrong: Hardcoded IDs
```python
db.get_task(42)  # Fragile!
```

### ✅ Right: Dynamic IDs
```python
task_id = result["task_id"]
db.get_task(task_id)
```

### ❌ Wrong: Missing Status Mapping
```python
return {"status": "pending"}  # Frontend expects "TODO"!
```

### ✅ Right: Map to UI Vocabulary
```python
status_map = {"pending": "TODO", "in_progress": "IN_PROGRESS"}
return {"status": status_map[db_status]}
```

### ❌ Wrong: Sync Database Call
```python
def get_tasks():  # Blocking!
    return db.get_all_tasks()
```

### ✅ Right: Async Pattern
```python
async def get_tasks():
    # Database operations are sync, but endpoint should be async
    tasks = db.get_all_tasks()
    return tasks
```

## File Organization

- **Database code** → `database/`
- **MCP tools** → `tools_lib/`
- **API endpoints** → `routers/`
- **Tests** → `test/project_manager/`
- **Frontend** → `static/`

Keep related code together!

## Versioning

Check `pyproject.toml` for current version. Update version when:
- Adding new MCP tools (minor version bump)
- Breaking API changes (major version bump)
- Bug fixes (patch version bump)

Current: `v0.2.2`

## Need Help?

- Architecture questions → [ARCHITECTURE.md](reference/ARCHITECTURE.md)
- Adding tools → [ADDING_MCP_TOOLS.md](reference/ADDING_MCP_TOOLS.md)
- Testing guide → [TESTING.md](reference/TESTING.md)
- Run tests → `bash scripts/run-full-tests.sh`
