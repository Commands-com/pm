# RA Tag Context Detection Usage Guide

## Overview

The Simple RA Tag Creation feature provides zero-effort context detection for Response Awareness (RA) tags. When developers add RA tags to track assumptions and uncertainties, the system automatically captures relevant development context including file location, git state, and code symbols.

## Quick Start

### CLI Usage

```bash
# Basic RA tag addition with automatic context detection
python -m task_manager.cli add-ra-tag "#COMPLETION_DRIVE_IMPL: Assuming user validation is handled upstream" --task-id 123

# With explicit file context
python -m task_manager.cli add-ra-tag "#SUGGEST_ERROR_HANDLING: Should validate API response" --task-id 123 --file-path src/api.py --line-number 42

# With code snippet for additional context
python -m task_manager.cli add-ra-tag "#PATTERN_MOMENTUM: Following existing async pattern" --task-id 123 --file-path src/handlers.py --line-number 15 --code-snippet "async def process_request():"
```

### MCP Tool Usage

```python
# Using the MCP tool directly
from src.task_manager.tools import AddRATagTool
from src.task_manager.database import DatabaseManager

db = DatabaseManager()
tool = AddRATagTool(db)

result = await tool.apply(
    task_id="123",
    ra_tag_text="#COMPLETION_DRIVE_INTEGRATION: Email service integration assumed",
    file_path="src/notifications.py",
    line_number=28,
    agent_id="claude-agent"
)
```

## Context Detection Features

### Automatic Context Fields

When you add an RA tag, the system automatically detects and stores:

| Field | Description | Example |
|-------|-------------|---------|
| `timestamp` | When the RA tag was created | `2024-01-15T14:30:00Z` |
| `agent_id` | Agent or user who added the tag | `claude-agent` |
| `file_path` | File being edited (if detectable) | `src/task_manager/api.py` |
| `line_number` | Specific line in file | `42` |
| `language` | Programming language | `python` |
| `symbol_context` | Function/class name at line | `async_handler` |
| `git_branch` | Current git branch | `feature/notification-system` |
| `git_commit` | Current git commit hash | `abc123def456` |
| `code_snippet` | Code context around the line | `async def process_data():` |

### Context Detection Methods

**File Context:**
- Automatic detection from environment variables (`EDITOR_FILE`)
- Explicit specification via `--file-path` parameter
- Language detection from file extension
- Symbol extraction (function/class names) from source code

**Git Context:**
- Branch name from `git branch --show-current`
- Commit hash from `git rev-parse HEAD`
- Automatic detection of git repository status
- Graceful fallback when not in git repository

**Development Context:**
- Code snippet analysis for nearby symbols
- Relative path calculation from current working directory
- Performance-optimized detection (under 200ms total)

## RA Tag Format Examples

### Standard RA Tag Categories

```bash
# Implementation assumptions
add-ra-tag "#COMPLETION_DRIVE_IMPL: Using JWT for session management" --task-id 123

# Integration assumptions  
add-ra-tag "#COMPLETION_DRIVE_INTEGRATION: Assuming Redis is available for caching" --task-id 123

# Context reconstruction
add-ra-tag "#CONTEXT_RECONSTRUCT: Filling in missing error handling based on similar patterns" --task-id 123

# Pattern-based suggestions
add-ra-tag "#SUGGEST_ERROR_HANDLING: Should validate input before database insertion" --task-id 123
add-ra-tag "#SUGGEST_VALIDATION: Email format validation needed" --task-id 123

# Pattern momentum detection
add-ra-tag "#PATTERN_MOMENTUM: Following existing authentication middleware pattern" --task-id 123

# Conflict awareness
add-ra-tag "#PATTERN_CONFLICT: Multiple valid approaches for error handling" --task-id 123
```

### Context-Rich Examples

```bash
# Adding RA tag with specific code context
add-ra-tag "#COMPLETION_DRIVE_IMPL: Assuming async pattern for database queries" \
  --task-id 123 \
  --file-path src/database.py \
  --line-number 15 \
  --code-snippet "async def get_user(user_id: int):"

# Multiple related RA tags for complex assumptions
add-ra-tag "#SUGGEST_ERROR_HANDLING: Connection timeout handling needed" --task-id 123 --file-path src/api.py --line-number 42
add-ra-tag "#SUGGEST_VALIDATION: Request payload size limits" --task-id 123 --file-path src/api.py --line-number 45  
add-ra-tag "#PATTERN_MOMENTUM: Using existing retry logic pattern" --task-id 123 --file-path src/api.py --line-number 50
```

## Frontend Display

### Dashboard Integration

RA tags with context are displayed in the task details view:

```
🏷️ #COMPLETION_DRIVE_IMPL: Assuming user validation is handled upstream
   📁 src/auth.py:23 | 🌿 feature/auth-system | ⚡ validate_user()
   🕒 2024-01-15 14:30:00 | 👤 claude-agent

🏷️ #SUGGEST_ERROR_HANDLING: Should validate API response structure  
   📁 src/api.py:67 | 🌿 main | ⚡ process_response()
   💻 async def process_response(data):
   🕒 2024-01-15 14:32:15 | 👤 developer
```

### Context Information

- **File Context**: Shows file path, line number, and detected programming language
- **Git Context**: Displays current branch and commit for traceability
- **Symbol Context**: Function or class name where the RA tag was added
- **Code Context**: Relevant code snippet for understanding the assumption
- **Metadata**: Timestamp and agent information for audit trails

## Advanced Usage

### Batch RA Tag Addition

```bash
# Multiple RA tags for a complex feature
add-ra-tag "#COMPLETION_DRIVE_IMPL: Database schema supports user preferences" --task-id 123 --file-path models.py --line-number 15
add-ra-tag "#SUGGEST_VALIDATION: User preference validation rules needed" --task-id 123 --file-path models.py --line-number 25
add-ra-tag "#PATTERN_MOMENTUM: Following existing model validation patterns" --task-id 123 --file-path models.py --line-number 30
```

### Integration with Development Workflow

```bash
# During code review - flag assumptions
add-ra-tag "#CONTEXT_RECONSTRUCT: Assuming this handles edge case from requirements" --task-id 123

# During implementation - track integration points
add-ra-tag "#COMPLETION_DRIVE_INTEGRATION: External API rate limiting assumed to be 1000/hour" --task-id 123

# During testing - document test assumptions
add-ra-tag "#SUGGEST_ERROR_HANDLING: Mock service failures for resilience testing" --task-id 123
```

### Performance Considerations

- Context detection is optimized for under 200ms execution time
- Git operations use short timeouts (5 seconds) to prevent blocking
- File operations are cached when possible
- Symbol detection uses efficient regex patterns

## Troubleshooting

### Common Issues

**Missing Git Context:**
```
# If git commands fail, context will show:
git_branch: null
git_commit: null

# Solution: Ensure you're in a git repository and git is accessible
git status  # Verify git works
```

**File Context Not Detected:**
```
# If file path detection fails:
file_path: null
language: null

# Solution: Explicitly specify file path
add-ra-tag "..." --file-path /full/path/to/file.py
```

**Symbol Context Missing:**
```
# If symbol detection fails:
symbol_context: null

# This is normal for:
# - Binary files
# - Files with no functions/classes at the specified line
# - Unsupported programming languages
```

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "Task not found" | Invalid task ID | Verify task exists with correct ID |
| "RA tag text cannot be empty" | Empty tag text provided | Provide meaningful RA tag text |
| "Invalid line number" | Line number < 1 or beyond file | Use valid line numbers |
| "File not accessible" | Permission or existence issues | Check file permissions and path |

### Debug Mode

```bash
# Enable verbose output for debugging
python -m task_manager.cli add-ra-tag "..." --task-id 123 --verbose

# Check database contents
python -c "
from src.task_manager.database import DatabaseManager
db = DatabaseManager()
details = db.get_task_details(123)
print(details['ra_tags'])
"
```

## Integration Examples

### With IDE Extensions

Future IDE extensions can integrate with this system:

```javascript
// VS Code extension example
const addRATag = async (tagText) => {
  const currentFile = vscode.window.activeTextEditor.document.fileName;
  const currentLine = vscode.window.activeTextEditor.selection.active.line + 1;
  const taskId = await getCurrentTaskId();
  
  await executeCLICommand([
    'add-ra-tag', tagText,
    '--task-id', taskId,
    '--file-path', currentFile,
    '--line-number', currentLine
  ]);
};
```

### With Git Hooks

```bash
# Pre-commit hook to capture RA tags from commit messages
#!/bin/bash
if git diff --cached --name-only | grep -E '\.(py|js|ts)$'; then
  # Extract RA tags from commit message
  COMMIT_MSG=$(cat .git/COMMIT_EDITMSG)
  if echo "$COMMIT_MSG" | grep -q '#[A-Z_]*:'; then
    echo "Found RA tags in commit message"
    # Process and add to current task
  fi
fi
```

### With CI/CD Pipelines

```yaml
# GitHub Actions example
- name: Extract RA Tags from Code
  run: |
    # Scan for RA tag comments in code
    grep -r "#[A-Z_]*:" src/ | while read -r line; do
      echo "Found RA tag: $line"
      # Add to task management system
    done
```

## Best Practices

### RA Tag Content

1. **Be Specific**: Include concrete assumptions, not vague statements
2. **Use Standard Categories**: Follow the established RA tag patterns
3. **Provide Context**: Include relevant details about why the assumption was made
4. **Link to Code**: Use file paths and line numbers for traceability

### Development Workflow

1. **Add Tags During Implementation**: Capture assumptions as they occur
2. **Review Tags During Code Review**: Validate assumptions with team
3. **Update Tags as Code Evolves**: Keep RA tags current with code changes
4. **Use for Knowledge Transfer**: RA tags help onboard new team members

### Task Management

1. **Associate with Appropriate Tasks**: Link RA tags to relevant tasks
2. **Group Related Assumptions**: Multiple RA tags per feature are normal
3. **Review in Task Completion**: Validate assumptions before marking tasks done
4. **Archive Resolved Assumptions**: Keep history but distinguish active vs resolved

## API Reference

### MCP Tool Parameters

```python
async def add_ra_tag(
    task_id: str,                    # Required: Task to add RA tag to
    ra_tag_text: str,               # Required: RA tag content with category
    file_path: Optional[str] = None, # Optional: File path for context
    line_number: Optional[int] = None, # Optional: Line number in file
    code_snippet: Optional[str] = None, # Optional: Code context
    agent_id: str = "system"        # Optional: Agent identifier
) -> str
```

### CLI Parameters

```bash
python -m task_manager.cli add-ra-tag [RA_TAG_TEXT] [OPTIONS]

Arguments:
  RA_TAG_TEXT  The RA tag text including category and description

Options:
  -t, --task-id TEXT       Task ID to add the RA tag to [required]
  -f, --file-path TEXT     File path for context detection
  -l, --line-number INT    Line number in the file
  -s, --code-snippet TEXT  Code snippet for context
  -a, --agent-id TEXT      Agent identifier [default: cli-user]
  --verbose               Enable verbose output
  --help                  Show help message
```

### Context Detection Functions

```python
from src.task_manager.context_utils import (
    create_enriched_context,  # Main context creation function
    detect_file_context,      # File-based context detection
    get_git_context,         # Git repository context
    detect_language,         # Programming language detection
    extract_symbol_context,  # Function/class name extraction
    validate_context        # Context validation and cleanup
)

# Create complete context
context = create_enriched_context(
    file_path="src/api.py",
    line_number=42,
    code_snippet="async def handler():"
)
```

This guide covers the complete usage of the RA Tag Context Detection system. For additional support, refer to the test files for comprehensive examples of all features and edge cases.