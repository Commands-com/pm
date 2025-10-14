# Project Manager MCP

[![PyPI version](https://badge.fury.io/py/project-manager-mcp.svg)](https://badge.fury.io/py/project-manager-mcp)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://github.com/Commands-com/pm/actions/workflows/tests.yml/badge.svg)](https://github.com/Commands-com/pm/actions/workflows/tests.yml)
[![Coverage](https://codecov.io/gh/Commands-com/pm/branch/main/graph/badge.svg)](https://codecov.io/gh/Commands-com/pm)

## Quick Start

### Option 1: Claude Code Plugin (Recommended)

The easiest way to get started with Claude Code:

```bash
# Add the plugin marketplace
/plugin marketplace add Commands-com/pm

# Install the plugin
/plugin install project-manager

# Restart Claude Code - you're ready to go!
```

This automatically installs:
- ✅ MCP server (via `uvx`)
- ✅ All `/pm:*` slash commands
- ✅ Specialized agents (adaptive-assessor, task-runner, etc.)

### Option 2: Manual Installation

1. **Install from PyPI**
```bash
pip install project-manager-mcp
# or
uvx project-manager-mcp
```

2. **Add MCP server to your AI assistant:**

**Claude Code:**
```bash
claude mcp add project-manager -- uvx project-manager-mcp
```

**Codex:**
```toml
[mcp_servers.project-manager-mcp]
command = "uvx"
args = ["project-manager-mcp"]
```

**Gemini:**
```json
"mcpServers": {
  "project-manager": {
    "type": "stdio",
    "command": "uvx",
    "args": ["project-manager-mcp"],
    "env": {}
  }
}
```

3. **Install Claude assets (commands & agents) to your project:**
```bash
project-manager-mcp install-claude-assets --target-dir ~/my-project
```

## Features

A comprehensive project management system with Model Context Protocol (MCP) support, enabling AI agents to manage projects, epics, and tasks through both programmatic interfaces and a web dashboard.

- **AI Agent Integration**: MCP tools for autonomous project management
- **Web Dashboard**: Real-time web interface for project visualization
- **Task Locking System**: Atomic operations prevent concurrent modifications
- **WebSocket Updates**: Real-time synchronization across all clients
- **SQLite Backend**: Lightweight, serverless database with WAL mode
- **Zero-Config Setup**: Single command deployment with automatic port allocation
- **Project Import**: YAML-based project definition and import system
- **RA Tag Context Detection**: Zero-effort context capture for Response Awareness tags

## Installation & Usage

### Installation Options

```bash
# Install from source (development)
pip install -e .

# Or install development dependencies
pip install -e .[dev]

# Run directly with uvx (no installation needed)
uvx --from . project-manager-mcp
```

### Basic Usage

```bash
# Start with default configuration (dashboard on :8080, MCP over stdio)
project-manager-mcp

# Custom port and options
project-manager-mcp --port 9000 --no-browser

# Import a project on startup
project-manager-mcp --project examples/simple-project.yaml

# MCP over stdio (default; for shell integration)
project-manager-mcp --mcp-transport stdio

# Add RA tags with automatic context detection
python -m task_manager.cli add-ra-tag "#COMPLETION_DRIVE_IMPL: Assuming user validation upstream" --task-id 123

# Install Claude agents and commands to your project
project-manager-mcp install-claude-assets --target-dir ~/my-project
```

After startup, access the dashboard at `http://localhost:8080` (or your chosen port).

### MCP Client Integration

Connect MCP clients to interact programmatically:

```bash
# Stdio transport (default)
# Connect via stdin/stdout

# SSE transport (optional)
project-manager-mcp --mcp-transport sse
# Connect to http://localhost:8081/sse

# Using uvx for MCP integration
uvx --from . project-manager-mcp --mcp-transport stdio
uvx --from . project-manager-mcp --mcp-transport sse --port 9000
```

## Architecture Overview

### Core Components

- **CLI Interface** (`task_manager.cli`): Zero-config server coordination
- **FastAPI Backend** (`task_manager.api`): REST endpoints and WebSocket broadcasting
- **MCP Server** (`task_manager.mcp_server`): AI agent tool integration
- **Database Layer** (`task_manager.database`): SQLite with atomic locking
- **MCP Tools** (`task_manager.tools`): GetAvailableTasks, AcquireTaskLock, UpdateTaskStatus, ReleaseTaskLock, AddRATag
- **Context Detection** (`task_manager.context_utils`): Automatic file, git, and symbol context detection

### Data Model

```
Projects (top-level containers)
├── Epics (high-level initiatives)
    ├── Tasks (specific work items)
```

Each task supports:
- **Status tracking**: pending → in_progress → completed
- **Atomic locking**: Prevent concurrent modifications
- **Agent assignment**: Track work ownership
- **Real-time updates**: WebSocket broadcasting
- **RA Tag Context**: Automatic context detection for Response Awareness tags

### Transport Modes

1. **SSE (Server-Sent Events)**: HTTP-based MCP for network clients
2. **Stdio**: Pipe-based MCP for shell and local integration
3. **None**: Dashboard-only mode without MCP server

## Key Features

### Atomic Task Locking

Two patterns are supported:

1) Single-call update (auto-lock):
```python
# Automatically acquires a short-lived lock if unlocked, updates status, then releases.
mcp_client.call_tool("update_task_status", {
    "task_id": "123",
    "status": "DONE",            # UI vocabulary also accepted
    "agent_id": "agent-1"
})
```

2) Explicit lock + update (long-running work):
```python
# Acquire exclusive lock on task (status moves to IN_PROGRESS)
mcp_client.call_tool("acquire_task_lock", {
    "task_id": "123",
    "agent_id": "agent-1",
    "timeout": 300
})

# Perform work...

# Update status and auto-release on DONE
mcp_client.call_tool("update_task_status", {
    "task_id": "123",
    "status": "DONE",
    "agent_id": "agent-1"
})
```

### Real-time Dashboard Updates

WebSocket events keep all clients synchronized:
- `task.status_changed` - Task status updates
- `task.locked` - Task lock acquisition
- `task.unlocked` - Task lock release

### Project Import System

Define projects in YAML and import on startup:

```yaml
projects:
  - name: "User Management System"
    description: "Complete user lifecycle management"
    epics:
      - name: "User Authentication"
        status: "ACTIVE"
        tasks:
          - name: "Create registration form"
            status: "TODO"
          - name: "Implement login validation"
            status: "TODO"
```

## Use Cases

### AI Agent Workflows

1. **Query available work**: `get_available_tasks`
2. **Claim exclusive access**: `acquire_task_lock` 
3. **Update progress**: `update_task_status`
4. **Release when done**: Auto-release on completion

### Multi-Agent Coordination

- **Prevent conflicts**: Atomic locking prevents multiple agents on same task
- **Work distribution**: Available task querying enables load balancing
- **Progress tracking**: Status updates provide visibility across agents
- **Real-time sync**: WebSocket updates keep all systems current

### Dashboard Management

- **Project visualization**: Project → Epic → Task hierarchy
- **Real-time monitoring**: Live updates from agent activity
- **Manual intervention**: Override task states when needed
- **Project import**: Load new projects without restart

## Configuration

### CLI Options

- `--port PORT`: Dashboard server port (default: 8080)
- `--mcp-transport {stdio|sse|none}`: MCP transport mode (default: stdio)
- `--project PATH`: Import project YAML on startup
- `--no-browser`: Skip automatic browser launch
- `--host HOST`: Server bind address (default: 127.0.0.1)
- `--db-path PATH`: Database file location (default: project_manager.db)
- `--verbose`: Enable debug logging

### Claude Assets Installation

Install Claude Code agents and commands to your projects:

```bash
# Install both agents and commands to a project
project-manager-mcp install-claude-assets --target-dir ~/my-project

# Install with overwrite protection
project-manager-mcp install-claude-assets --target-dir ~/my-project --force

# Install only agents
project-manager-mcp install-claude-assets --target-dir ~/my-project --agents-only

# Install only commands
project-manager-mcp install-claude-assets --target-dir ~/my-project --commands-only

# Verbose output showing all installed files
project-manager-mcp install-claude-assets --target-dir ~/my-project --verbose

# Alternative standalone command
pm-install-claude-assets --target-dir ~/my-project
```

This creates a `.claude/` directory in your target location with:
- **Agents** (`.claude/agents/`): Specialized agents for adaptive assessment, planning review, task execution, and verification
- **Commands** (`.claude/commands/pm/`): Project management commands for task workflow, epic management, and status tracking

### Environment Variables

- `DATABASE_PATH`: Override default database location
- `DEBUG`: Enable verbose logging

## Performance Characteristics

- **Startup time**: < 2 seconds with empty database
- **Task operations**: < 50ms for lock acquisition/release
- **WebSocket latency**: < 10ms for local connections
- **Concurrent agents**: Tested with 50+ simultaneous agents
- **Database size**: Handles 10,000+ tasks efficiently

## Error Recovery

- **Port conflicts**: Automatic alternative port allocation
- **Database corruption**: WAL mode provides crash recovery
- **WebSocket disconnections**: Automatic reconnection handling
- **Lock timeouts**: Automatic cleanup of expired locks
- **Agent failures**: Lock expiration prevents indefinite blocking

## Security Model

- **No authentication**: Open access for development and testing
- **Local binding**: Default 127.0.0.1 limits network exposure
- **File permissions**: Database protected by filesystem ACLs
- **Input validation**: Pydantic models prevent injection attacks
- **Resource limits**: Lock timeouts prevent resource exhaustion

## Troubleshooting

### Common Issues

**Port already in use**
```bash
# Use alternative ports
project-manager-mcp --port 9000

# Check what's using the port
lsof -i :8080
```

**Database locked errors**
```bash
# Check for competing processes
ps aux | grep project-manager-mcp

# Remove database if corrupted
rm project_manager.db
```

**WebSocket connection refused**
```bash
# Verify server is running
curl http://localhost:8080/healthz

# Check WebSocket endpoint
curl -H "Upgrade: websocket" http://localhost:8080/ws/updates
```

**MCP client connection issues**
```bash
# Test SSE endpoint (when using --mcp-transport sse)
curl http://localhost:8081/sse

# For stdio mode, verify no conflicting processes
project-manager-mcp --mcp-transport stdio --verbose
```

## Documentation

- [Detailed Usage Guide](docs/usage.md) - CLI options, MCP tools, WebSocket events
- [API Documentation](docs/api.md) - REST endpoints, request/response formats
- [Development Guide](docs/development.md) - Contributing, testing, architecture decisions
- [RA Tag Context Usage Guide](docs/ra-tag-context-usage.md) - Complete guide for Response Awareness tag context detection

## Examples

- [`examples/simple-project.yaml`](examples/simple-project.yaml) - Basic project structure
- [`examples/complex-project.yaml`](examples/complex-project.yaml) - Multi-epic enterprise project

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this software for any purpose, including commercial use.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup instructions
- Code style guidelines
- Testing requirements
- Pull request process
- Response Awareness (RA) methodology guidelines

For detailed architecture and development information, see [Development Guide](docs/development.md).
