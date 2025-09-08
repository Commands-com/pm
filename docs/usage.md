# Usage Guide

Comprehensive guide to using Project Manager MCP, covering CLI options, MCP tool specifications, WebSocket events, and project configuration.

## Command Line Interface

### Basic Commands

```bash
# Start with default configuration
project-manager-mcp
# Starts dashboard on http://127.0.0.1:8080
# Starts MCP SSE server on http://127.0.0.1:8081

# Custom port configuration
project-manager-mcp --port 9000
# Dashboard: http://127.0.0.1:9000
# MCP SSE: http://127.0.0.1:9001

# Disable automatic browser launch
project-manager-mcp --no-browser

# Import project on startup
project-manager-mcp --project examples/simple-project.yaml

# Enable verbose logging
project-manager-mcp --verbose
```

### Transport Modes

#### SSE Transport (Default)

```bash
project-manager-mcp --mcp-transport sse
# MCP server available at http://127.0.0.1:8081
# Use for network-based MCP clients
```

**Client Connection Example:**
```python
import httpx

# Connect to SSE endpoint
async with httpx.AsyncClient() as client:
    async with client.stream('GET', 'http://localhost:8081/sse') as response:
        async for line in response.aiter_lines():
            # Process MCP messages
            pass
```

#### Stdio Transport

```bash
project-manager-mcp --mcp-transport stdio
# MCP communication via stdin/stdout
# Dashboard runs in background thread
```

**Use Cases:**
- Shell script integration
- Local AI agent development
- Command-line MCP client testing

#### None Transport (Dashboard Only)

```bash
project-manager-mcp --mcp-transport none
# Disables MCP server entirely
# Only web dashboard available
```

### CLI Options Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--port` | int | 8080 | Dashboard server port |
| `--mcp-transport` | choice | sse | MCP transport: sse, stdio, or none |
| `--project` | path | None | Project YAML file to import |
| `--no-browser` | flag | False | Skip automatic browser launch |
| `--host` | string | 127.0.0.1 | Server bind address |
| `--db-path` | path | project_manager.db | Database file location |
| `--verbose` | flag | False | Enable debug logging |

### Configuration Examples

```bash
# Development setup with custom database
project-manager-mcp --db-path /tmp/dev_project.db --verbose

# Production deployment
project-manager-mcp --host 0.0.0.0 --port 8080 --no-browser --mcp-transport sse

# Testing with imported project
project-manager-mcp --project examples/complex-project.yaml --verbose

# Shell integration mode
project-manager-mcp --mcp-transport stdio --no-browser

# Dashboard-only deployment
project-manager-mcp --mcp-transport none --port 3000
```

## MCP Tools Specification

### GetAvailableTasks

Query tasks available for work, filtered by status and lock availability.

**Parameters:**
- `status` (string, optional): Task status filter. Default: "TODO"
  - Valid values: `"pending"`, `"in_progress"`, `"completed"`, `"blocked"`, `"TODO"`, `"DONE"`
- `include_locked` (boolean, optional): Include locked tasks. Default: `false`
- `limit` (integer, optional): Maximum tasks to return

**Returns:**
Array of task objects with availability metadata.

**Example Request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "get_available_tasks",
    "arguments": {
      "status": "TODO",
      "include_locked": false,
      "limit": 10
    }
  }
}
```

**Example Response:**
```json
[
  {
    "id": 1,
    "name": "Create registration form UI",
    "description": "Design and implement user registration form", 
    "status": "pending",
    "story_id": 1,
    "available": true,
    "lock_holder": null,
    "lock_expires_at": null
  },
  {
    "id": 2,
    "name": "Implement registration API endpoint",
    "description": "Backend endpoint to handle user registration",
    "status": "pending", 
    "story_id": 1,
    "available": true,
    "lock_holder": null,
    "lock_expires_at": null
  }
]
```

### AcquireTaskLock

Acquire exclusive lock on a task with atomic status change to IN_PROGRESS.

**Parameters:**
- `task_id` (string): Task ID to lock (converted to integer)
- `agent_id` (string): Agent identifier requesting lock
- `timeout` (integer, optional): Lock timeout in seconds. Default: 300, Max: 3600

**Returns:**
Success/failure status with lock details.

**Example Request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "acquire_task_lock",
    "arguments": {
      "task_id": "1",
      "agent_id": "agent-alice",
      "timeout": 600
    }
  }
}
```

**Success Response:**
```json
{
  "success": true,
  "message": "Acquired lock on task 1",
  "task_id": 1,
  "agent_id": "agent-alice",
  "timeout": 600,
  "expires_at": "2024-01-15T14:30:00.000Z"
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "Task 1 is already locked",
  "lock_holder": "agent-bob",
  "expires_at": "2024-01-15T14:25:00.000Z"
}
```

### UpdateTaskStatus

Update task status with lock validation and auto-release on completion.

**Parameters:**
- `task_id` (string): Task ID to update
- `status` (string): New task status
  - Valid values: `"pending"`, `"in_progress"`, `"completed"`, `"blocked"`, `"TODO"`, `"DONE"`, `"IN_PROGRESS"`
- `agent_id` (string): Agent identifier (must match lock holder)

**Behavior:**
- Validates agent holds the lock
- Updates task status
- Auto-releases lock when status becomes `"completed"` or `"DONE"`
- Broadcasts status change events

**Example Request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "update_task_status",
    "arguments": {
      "task_id": "1",
      "status": "completed",
      "agent_id": "agent-alice"
    }
  }
}
```

**Success Response (with auto-release):**
```json
{
  "success": true,
  "message": "Task 1 status updated to completed and lock auto-released",
  "task_id": 1,
  "status": "completed",
  "agent_id": "agent-alice",
  "lock_released": true
}
```

### ReleaseTaskLock

Explicitly release task lock with agent validation.

**Parameters:**
- `task_id` (string): Task ID to unlock
- `agent_id` (string): Agent identifier (must match lock holder)

**Example Request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "release_task_lock", 
    "arguments": {
      "task_id": "1",
      "agent_id": "agent-alice"
    }
  }
}
```

**Success Response:**
```json
{
  "success": true,
  "message": "Released lock on task 1",
  "task_id": 1,
  "agent_id": "agent-alice"
}
```

## WebSocket Event Specification

Connect to `/ws/updates` for real-time event streaming.

### Event Types

#### task.status_changed

Triggered when task status is updated.

```json
{
  "type": "task.status_changed",
  "timestamp": "2024-01-15T14:30:00.000Z",
  "task_id": 1,
  "status": "completed",
  "agent_id": "agent-alice",
  "lock_released": true
}
```

#### task.locked

Triggered when task lock is acquired.

```json
{
  "type": "task.locked",
  "timestamp": "2024-01-15T14:25:00.000Z", 
  "task_id": 1,
  "agent_id": "agent-alice",
  "status": "in_progress",
  "timeout": 600
}
```

#### task.unlocked

Triggered when task lock is released.

```json
{
  "type": "task.unlocked",
  "timestamp": "2024-01-15T14:30:00.000Z",
  "task_id": 1,
  "agent_id": "agent-alice",
  "reason": "auto_release_on_completion"
}
```

### WebSocket Client Example

```javascript
const ws = new WebSocket('ws://localhost:8080/ws/updates');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'task.status_changed':
            console.log(`Task ${data.task_id} status: ${data.status}`);
            break;
        case 'task.locked':
            console.log(`Task ${data.task_id} locked by ${data.agent_id}`);
            break;
        case 'task.unlocked':
            console.log(`Task ${data.task_id} unlocked by ${data.agent_id}`);
            break;
    }
};

ws.onopen = function(event) {
    console.log('WebSocket connected');
};

ws.onclose = function(event) {
    console.log('WebSocket disconnected');
};
```

## Project YAML Format

### Schema Specification

```yaml
epics:
  - name: string              # Epic name (required)
    description: string       # Epic description (optional)
    status: string           # Epic status (required) 
    stories:                 # List of stories (required)
      - name: string         # Story name (required)
        description: string  # Story description (optional)
        status: string      # Story status (required)
        tasks:              # List of tasks (required)
          - name: string    # Task name (required)
            description: string # Task description (optional)
            status: string  # Task status (required)
```

### Valid Status Values

**Epic Status:**
- `"ACTIVE"` - Currently in development
- `"PLANNED"` - Future epic
- `"COMPLETED"` - Finished epic
- `"CANCELLED"` - Cancelled epic

**Story Status:**
- `"TODO"` - Not started
- `"IN_PROGRESS"` - Currently being worked on
- `"COMPLETED"` - Finished story
- `"BLOCKED"` - Cannot proceed

**Task Status:**
- `"TODO"` / `"pending"` - Ready for work
- `"IN_PROGRESS"` / `"in_progress"` - Currently being worked on
- `"COMPLETED"` / `"completed"` - Finished task
- `"BLOCKED"` / `"blocked"` - Cannot proceed

### Example Project

```yaml
epics:
  - name: "Authentication System"
    description: "User login and registration system"
    status: "ACTIVE"
    stories:
      - name: "User Registration"
        description: "Allow new users to create accounts"
        status: "IN_PROGRESS"
        tasks:
          - name: "Design registration form"
            description: "Create wireframes and UI design"
            status: "COMPLETED"
          - name: "Implement registration API"
            description: "Backend endpoint for user creation"
            status: "IN_PROGRESS"
          - name: "Add email verification"
            description: "Send verification emails"
            status: "TODO"
            
      - name: "User Login"
        description: "Authentication for existing users"
        status: "TODO"
        tasks:
          - name: "Design login form"
            description: "Login UI with validation"
            status: "TODO"
          - name: "Implement login API"
            description: "Authentication endpoint"
            status: "TODO"
```

### Project Import

```bash
# Import project on startup
project-manager-mcp --project /path/to/project.yaml

# Import validates:
# - YAML syntax
# - Required fields (name, status)  
# - Status value validity
# - Hierarchical structure consistency
```

## Agent Workflow Patterns

### Basic Task Assignment

```python
# 1. Query available tasks
tasks = await mcp_client.call_tool("get_available_tasks", {
    "status": "TODO",
    "limit": 5
})

# 2. Select task and acquire lock
task_id = tasks[0]["id"]
lock_result = await mcp_client.call_tool("acquire_task_lock", {
    "task_id": str(task_id),
    "agent_id": "my-agent",
    "timeout": 600
})

# 3. Perform work...

# 4. Update status (auto-releases lock on completion)
await mcp_client.call_tool("update_task_status", {
    "task_id": str(task_id),
    "status": "completed",
    "agent_id": "my-agent"
})
```

### Multi-Agent Coordination

```python
# Agent A: Query and lock task
available = await mcp_client.call_tool("get_available_tasks")
task_id = available[0]["id"]
lock_result = await mcp_client.call_tool("acquire_task_lock", {
    "task_id": str(task_id), 
    "agent_id": "agent-a"
})

# Agent B: Cannot acquire same task (conflict prevention)
conflict_result = await mcp_client.call_tool("acquire_task_lock", {
    "task_id": str(task_id),
    "agent_id": "agent-b"  
})
# Returns: {"success": false, "message": "Task already locked"}

# Agent A: Release early if needed
await mcp_client.call_tool("release_task_lock", {
    "task_id": str(task_id),
    "agent_id": "agent-a"
})

# Agent B: Now can acquire
success_result = await mcp_client.call_tool("acquire_task_lock", {
    "task_id": str(task_id),
    "agent_id": "agent-b"
})
```

### Error Handling

```python
try:
    # Attempt task operations
    result = await mcp_client.call_tool("acquire_task_lock", {
        "task_id": "123",
        "agent_id": "my-agent"
    })
    
    if not result.get("success"):
        # Handle lock acquisition failure
        if "already locked" in result.get("message", ""):
            # Task unavailable, try another
            pass
        elif "not found" in result.get("message", ""):
            # Task doesn't exist
            pass
        
except Exception as e:
    # Handle connection/protocol errors
    logger.error(f"MCP communication error: {e}")
```

## Troubleshooting

### Common MCP Issues

**Connection refused:**
```bash
# Check server is running
curl http://localhost:8080/healthz

# Verify MCP port (default: 8081)
curl http://localhost:8081/sse
```

**Lock acquisition failures:**
```bash
# Check for expired locks (cleans up automatically)
# Locks expire after timeout (default: 5 minutes)

# View current locks in database
sqlite3 project_manager.db "SELECT * FROM tasks WHERE lock_holder IS NOT NULL;"
```

**Status update failures:**
```json
// Common error: Agent doesn't hold lock
{
  "success": false,
  "message": "Task 1 must be locked by requesting agent"
}

// Solution: Acquire lock first
// acquire_task_lock -> update_task_status
```

**WebSocket disconnections:**
```javascript
// Implement reconnection logic
ws.onclose = function(event) {
    console.log('Reconnecting in 5 seconds...');
    setTimeout(() => {
        ws = new WebSocket('ws://localhost:8080/ws/updates');
    }, 5000);
};
```

### Performance Optimization

**High-frequency operations:**
- Use `limit` parameter in `get_available_tasks` 
- Implement client-side caching of task lists
- Use WebSocket events for real-time updates instead of polling

**Large project imports:**
- Break large YAML files into smaller projects
- Use database transaction batching for bulk operations
- Consider periodic database maintenance (`VACUUM`)

**Multi-agent scaling:**
- Reduce lock timeout for faster turnover
- Implement exponential backoff for lock acquisition retries
- Use task priorities to optimize work distribution