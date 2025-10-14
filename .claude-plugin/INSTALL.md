# Post-Installation Steps

## MCP Server Setup

This plugin requires the Project Manager MCP server to be installed and configured.

### Install the MCP Server

```bash
# Install via pip
pip install project-manager-mcp

# Or use uvx (recommended - no installation needed)
uvx project-manager-mcp
```

### Configure MCP Server

Add the MCP server to your Claude Code configuration:

```bash
claude mcp add project-manager-mcp -- uvx project-manager-mcp
```

Or manually add to your MCP configuration file:

**Claude Code:**
Add to `~/.claude/settings.json`:
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

**Cline (VS Code):**
Add to your Cline MCP settings:
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

### Verify Installation

1. Restart Claude Code
2. Try a command: `/pm:help`
3. Check MCP connection: The commands should have access to the task management tools

### Troubleshooting

**Commands work but tools are missing:**
- Ensure the MCP server is running: `uvx project-manager-mcp`
- Check MCP configuration in settings
- Restart Claude Code

**Commands not found:**
- Verify plugin installation: `/plugin list`
- Check commands are installed: `/help` (look for `/pm:*` commands)

**For more help:**
- Documentation: https://github.com/Commands-com/pm#readme
- Issues: https://github.com/Commands-com/pm/issues
