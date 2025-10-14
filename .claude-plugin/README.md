# Project Manager MCP Plugin

A comprehensive Claude Code plugin for AI-powered project management with task tracking, epic planning, and Response Awareness methodology.

## What's Included

This plugin provides:

### 🤖 **MCP Server**
- **Automatic installation** of the Project Manager MCP server via `uvx`
- Full project, epic, and task management capabilities
- Atomic task locking for multi-agent coordination
- Response Awareness (RA) methodology support
- Knowledge management system

### ⚡ **Slash Commands** (`/pm:*`)
- `/pm:init` - Initialize PM Adaptive Workflow
- `/pm:prd-new` - Create new Product Requirements Document
- `/pm:prd-to-epic` - Transform PRD into technical epic
- `/pm:epic-tasks` - Break epic into actionable tasks
- `/pm:epic-run` - Execute entire epic with parallelization
- `/pm:task-start` - Start task with adaptive workflow
- `/pm:task-sync` - Sync task progress to GitHub
- `/pm:verify` - Deploy verification agent for RA tags
- `/pm:assess` - Assess task complexity
- `/pm:plan-review` - Review implementation plans
- `/pm:status` - View all projects, epics, and tasks
- `/pm:next` - Get next recommended task
- `/pm:help` - Show comprehensive help

### 🎯 **Specialized Agents**
- **adaptive-assessor** - Intelligent complexity assessment
- **planning-reviewer** - Lightweight RA planning validation
- **survey-agent** - Comprehensive codebase survey
- **task-runner-adaptive** - Adaptive task execution
- **verification-adaptive** - Intelligent verification with RA

## Installation

### Quick Install (Recommended)

```bash
# Add the marketplace
/plugin marketplace add Commands-com/pm

# Install the plugin
/plugin install project-manager

# Restart Claude Code to activate
```

### Manual Install

```bash
# Clone the repository
git clone https://github.com/Commands-com/pm.git
cd pm

# Install via pip (for MCP server)
pip install project-manager-mcp

# Or use uvx (no installation needed)
uvx project-manager-mcp
```

## Usage

### Starting a New Project

```bash
# Initialize the workflow
/pm:init

# Create a PRD
/pm:prd-new

# Convert to epic and tasks
/pm:prd-to-epic
/pm:epic-tasks

# View status
/pm:status

# Start working
/pm:next
/pm:task-start
```

### Working with Tasks

```bash
# Get next recommended task
/pm:next

# Start a task (with automatic complexity assessment)
/pm:task-start

# Verify assumptions (RA methodology)
/pm:verify

# Sync progress to GitHub
/pm:task-sync
```

### Advanced Workflows

```bash
# Run entire epic with maximum parallelization
/pm:epic-run

# Assess task complexity standalone
/pm:assess

# Review implementation plan before coding
/pm:plan-review
```

## MCP Server Integration

The plugin automatically configures the MCP server with:

```json
{
  "mcpServers": {
    "project-manager-mcp": {
      "command": "uvx",
      "args": ["project-manager-mcp"]
    }
  }
}
```

This provides access to all MCP tools:
- `create_task`, `update_task`, `get_task_details`
- `acquire_task_lock`, `release_task_lock`
- `list_projects`, `list_epics`, `list_tasks`
- `get_knowledge`, `upsert_knowledge`
- `add_ra_tag`, `capture_assumption_validation`
- And more!

## Response Awareness (RA) Methodology

This plugin implements the RA methodology for managing AI assumptions:

- **Complexity Assessment** - Automatic 1-10 scoring
- **RA Tags** - Track assumptions during implementation
- **Verification Agents** - Validate assumptions before completion
- **Knowledge Capture** - Document hard-won insights

Learn more: See `/pm:help` for detailed RA workflow

## Requirements

- Claude Code (terminal or VS Code)
- Python 3.9+ (for MCP server)
- `uvx` (recommended) or `pip`

## Support

- **Documentation**: https://github.com/Commands-com/pm#readme
- **Issues**: https://github.com/Commands-com/pm/issues
- **PyPI**: https://pypi.org/project/project-manager-mcp/

## License

MIT License - see [LICENSE](https://github.com/Commands-com/pm/blob/main/LICENSE)
