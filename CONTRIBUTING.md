# Contributing to PM Dashboard

Thank you for your interest in contributing to PM Dashboard! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Submitting Changes](#submitting-changes)
- [Response Awareness (RA) Methodology](#response-awareness-ra-methodology)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/pm.git
   cd pm
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/pm.git
   ```

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Node.js 18+ (for dashboard frontend)
- Git

### Environment Setup

1. **Activate the virtual environment**:
   ```bash
   source activate.sh
   ```

2. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Verify installation**:
   ```bash
   python -m pytest --version
   black --version
   mypy --version
   ```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-user-authentication`
- `fix/database-connection-leak`
- `docs/update-api-documentation`

### Commit Messages

Write clear, concise commit messages:

```
Add user authentication with OAuth2

- Implement OAuth2 flow for Google and GitHub
- Add user session management
- Update API endpoints to require authentication

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

**Format**:
- First line: Brief summary (50 chars or less)
- Blank line
- Detailed description with bullet points
- Reference any related issues: `Fixes #123`

### Code Style

We follow standard Python conventions:

- **PEP 8** style guide
- **Type hints** for all function signatures
- **Docstrings** for all public functions and classes
- **Black** for code formatting (line length: 100)

## Testing

### Running Tests

Run all tests before submitting:

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest test/project_manager/test_database.py -v

# Run with coverage
python -m pytest --cov=task_manager
```

### Writing Tests

- Place tests in `test/project_manager/` directory
- Use descriptive test names: `test_user_authentication_with_valid_credentials`
- Include docstrings explaining what the test validates
- Test both success and failure cases
- Use fixtures for common setup

**Example**:

```python
def test_create_task_with_valid_data(self, db):
    """Test task creation with all required fields."""
    task_id = db.create_task(
        epic_id=1,
        name="Test Task",
        description="Test description"
    )

    assert task_id is not None
    task = db.get_task_by_id(task_id)
    assert task["name"] == "Test Task"
```

## Code Quality

Before submitting, ensure your code passes all quality checks:

### 1. Format Code
```bash
black .
```

### 2. Lint Code
```bash
ruff check .
ruff check . --fix  # Auto-fix issues
```

### 3. Type Checking
```bash
mypy src/
```

### 4. Run Tests
```bash
python -m pytest
```

All checks must pass before your PR can be merged.

## Submitting Changes

### Pull Request Process

1. **Update your fork**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create Pull Request** on GitHub with:
   - Clear title describing the change
   - Detailed description of what changed and why
   - Reference to any related issues
   - Screenshots (if UI changes)

4. **PR Description Template**:

   ```markdown
   ## Summary
   Brief description of changes

   ## Changes Made
   - Added user authentication system
   - Updated API endpoints to require auth
   - Added tests for authentication flow

   ## Testing
   - [ ] All existing tests pass
   - [ ] Added new tests for new functionality
   - [ ] Manual testing completed

   ## Checklist
   - [ ] Code follows project style guidelines
   - [ ] Tests added/updated
   - [ ] Documentation updated
   - [ ] No deprecation warnings
   - [ ] Type hints added

   Fixes #123
   ```

5. **Review Process**:
   - Address review feedback promptly
   - Push additional commits to the same branch
   - Request re-review after changes

## Response Awareness (RA) Methodology

This project uses Response Awareness (RA) methodology for task management and implementation tracking.

### Complexity Assessment

When implementing features, assess complexity (1-10):
- **1-3**: Simple Mode - Direct implementation
- **4-6**: Standard Mode - Document assumptions, comprehensive testing
- **7-8**: RA-Light Mode - Tag assumptions with RA tags
- **9-10**: RA-Full Mode - Multi-agent coordination required

### RA Tags (for complex features)

When working on complex features (complexity 7+), use RA tags to document assumptions:

```python
# #COMPLETION_DRIVE_IMPL: Assuming database connection pooling is handled by SQLite
def get_connection(self):
    return sqlite3.connect(self.db_path)
```

**Common RA Tags**:
- `#COMPLETION_DRIVE_IMPL`: Implementation assumption
- `#SUGGEST_ERROR_HANDLING`: Error handling suggestion
- `#PATTERN_MOMENTUM`: Following common patterns
- `#CONTEXT_DEGRADED`: Filling in missing details

### Using MCP Tools

For task creation and management:

```bash
# Create a task with RA metadata
python -m task_manager.cli create-task \
  --name "Add user authentication" \
  --epic "Security Features" \
  --ra-mode standard \
  --ra-score 6
```

See [CLAUDE.md](CLAUDE.md) for detailed RA methodology guidelines.

## Questions?

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Tag issues appropriately: `bug`, `enhancement`, `documentation`, `question`

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to PM Dashboard! 🚀
