# Development Guide

Comprehensive guide for contributors and developers working on Project Manager MCP.

## Getting Started

### Prerequisites

- Python 3.9+ 
- Git
- SQLite (usually pre-installed)

### Development Setup

```bash
# Clone the repository
git clone https://github.com/example/project-manager-mcp.git
cd project-manager-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e .[dev,test,lint]

# Verify installation
project-manager-mcp --help
```

### Development Dependencies

The development environment includes:

- **pytest**: Testing framework with async support
- **pytest-cov**: Coverage reporting
- **httpx**: Async HTTP client for API testing
- **websockets**: WebSocket client for real-time testing
- **black**: Code formatting
- **ruff**: Fast linting and import sorting
- **mypy**: Static type checking

## Project Structure

```
project-manager-mcp/
├── src/task_manager/          # Main source code
│   ├── __init__.py
│   ├── cli.py                 # Command-line interface
│   ├── api.py                 # FastAPI REST endpoints
│   ├── mcp_server.py          # MCP server implementation
│   ├── database.py            # SQLite database layer
│   └── tools.py               # MCP tool implementations
├── test/project_manager/      # Test suite
│   ├── conftest.py            # Pytest configuration
│   ├── test_api.py            # API endpoint tests
│   ├── test_database.py       # Database layer tests
│   ├── test_cli.py            # CLI functionality tests
│   ├── test_mcp_server.py     # MCP server tests
│   ├── test_tools.py          # MCP tool tests
│   └── test_integration.py    # End-to-end tests
├── examples/                  # Sample project files
│   ├── simple-project.yaml
│   └── complex-project.yaml
├── docs/                      # Documentation
│   ├── usage.md
│   ├── api.md
│   └── development.md
├── pyproject.toml             # Package configuration
└── README.md                  # Project overview
```

### Key Architecture Decisions

**Source Layout**: Uses `src/` layout for cleaner packaging and import resolution.

**SQLite with WAL Mode**: Chosen for simplicity, zero-config deployment, and ACID compliance with good concurrent read performance.

**FastAPI + WebSockets**: Modern async framework with built-in WebSocket support for real-time features.

**Click CLI**: Provides clean command-line interface with automatic help generation.

**Pydantic Validation**: Ensures type safety and input validation across API boundaries.

## Testing Strategy

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=task_manager --cov-report=html

# Run specific test categories
pytest test/project_manager/test_api.py          # API tests only
pytest test/project_manager/test_database.py     # Database tests only
pytest test/project_manager/test_integration.py  # Integration tests

# Run with verbose output
pytest -v

# Run in parallel (install pytest-xdist)
pip install pytest-xdist
pytest -n auto
```

### Test Categories

#### Unit Tests
Focus on individual components in isolation:

```python
# Example: test_database.py
def test_task_creation(db):
    task_id = db.create_task("Test Task", "Description", 1)
    assert task_id is not None
    
    task = db.get_task(task_id)
    assert task["name"] == "Test Task"
    assert task["status"] == "pending"
```

#### API Integration Tests
Test REST endpoints and WebSocket functionality:

```python
# Example: test_api.py
@pytest.mark.asyncio
async def test_task_status_update(client, sample_task):
    response = await client.post(
        f"/api/task/{sample_task['id']}/status",
        json={"status": "completed", "agent_id": "test-agent"}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
```

#### MCP Tool Tests
Validate MCP tool functionality and responses:

```python
# Example: test_tools.py
@pytest.mark.asyncio
async def test_get_available_tasks(db, websocket_manager):
    tool = GetAvailableTasks(db, websocket_manager)
    
    # Create test tasks
    db.create_task("Task 1", "Description", 1)
    db.create_task("Task 2", "Description", 1) 
    
    result = await tool.apply(status="TODO")
    tasks = json.loads(result)
    assert len(tasks) == 2
```

#### End-to-End Tests
Test complete workflows from CLI to database:

```python
# Example: test_integration.py
@pytest.mark.asyncio
async def test_full_agent_workflow(running_server):
    # Connect MCP client
    # Query available tasks
    # Acquire lock
    # Update status
    # Verify WebSocket events
    pass
```

### Test Fixtures

Common fixtures are defined in `test/conftest.py`:

```python
@pytest.fixture
def db():
    """Clean database for each test."""
    db_path = ":memory:"  # In-memory SQLite
    database = TaskDatabase(db_path)
    yield database
    database.close()

@pytest.fixture
async def client():
    """FastAPI test client."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def sample_project():
    """Sample project data for testing."""
    return {
        "epics": [
            {
                "name": "Test Epic",
                "status": "ACTIVE",
                "stories": [
                    {
                        "name": "Test Story",
                        "status": "TODO",
                        "tasks": [
                            {
                                "name": "Test Task",
                                "status": "TODO"
                            }
                        ]
                    }
                ]
            }
        ]
    }
```

### Testing Best Practices

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Cleanup**: Use fixtures to ensure clean state for each test
3. **Async Testing**: Use `pytest-asyncio` for testing async code
4. **Database Testing**: Use in-memory SQLite for fast, isolated database tests
5. **Mock External Dependencies**: Mock file systems, network calls, etc.
6. **Test Edge Cases**: Invalid inputs, boundary conditions, error scenarios

## Code Quality Standards

### Formatting

**Black** is used for code formatting with 100-character line length:

```bash
# Format all code
black src/ test/

# Check formatting without changes
black --check src/ test/
```

Configuration in `pyproject.toml`:
```toml
[tool.black]
line-length = 100
target-version = ["py39", "py310", "py311", "py312"]
```

### Linting

**Ruff** provides fast linting and import sorting:

```bash
# Run linter
ruff check src/ test/

# Fix auto-fixable issues
ruff check --fix src/ test/

# Sort imports
ruff check --select I --fix src/ test/
```

### Type Checking

**MyPy** enforces static typing:

```bash
# Run type checking
mypy src/

# Check specific files
mypy src/task_manager/database.py
```

Configuration enforces strict typing:
```toml
[tool.mypy]
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_return_any = true
```

### Pre-commit Hooks

Set up pre-commit hooks for automated quality checks:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

Example `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
```

## Debugging and Development Tools

### Logging Configuration

The system uses Python's built-in logging with configurable levels:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or use CLI flag
project-manager-mcp --verbose
```

### Database Inspection

Direct SQLite access for debugging:

```bash
# Open database in SQLite CLI
sqlite3 project_manager.db

# Common queries
.tables                                    # List tables
.schema tasks                             # Show table structure
SELECT * FROM tasks WHERE lock_holder IS NOT NULL;  # Show locked tasks
SELECT * FROM tasks ORDER BY id DESC LIMIT 5;       # Recent tasks
```

### Development Server

For development, start the server with auto-reload:

```bash
# Development mode with verbose logging
project-manager-mcp --verbose --no-browser

# Custom database for development
project-manager-mcp --db-path dev_project.db --verbose

# Test with sample project
project-manager-mcp --project examples/simple-project.yaml --verbose
```

### MCP Client Testing

Test MCP functionality using WebSocket clients:

```bash
# Install websocat for WebSocket testing
# macOS: brew install websocat
# Linux: cargo install websocat

# Connect to WebSocket endpoint
websocat ws://127.0.0.1:8080/ws/updates

# Test MCP over SSE
curl -N http://127.0.0.1:8081/sse
```

## Contributing Workflow

### Development Process

1. **Fork and Clone**: Fork the repository and clone your fork
2. **Branch**: Create a feature branch from `main`
3. **Develop**: Implement your changes with tests
4. **Quality**: Run formatting, linting, and type checking
5. **Test**: Ensure all tests pass
6. **Document**: Update documentation for new features
7. **PR**: Submit pull request with clear description

### Branch Naming

Use descriptive branch names:
- `feature/add-task-priorities`
- `fix/websocket-connection-leak`
- `docs/api-examples`
- `refactor/database-connection-pool`

### Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Examples:
```
feat(api): add task priority field to endpoints

Add priority field to task creation and update endpoints.
Includes database migration and WebSocket event updates.

Closes #123
```

```
fix(websocket): prevent connection memory leak

Connection manager wasn't properly cleaning up closed connections.
Added explicit cleanup in disconnect handler.
```

### Pull Request Guidelines

**Title**: Clear, descriptive summary of changes

**Description**: Include:
- What changed and why
- Testing performed
- Documentation updates
- Breaking changes (if any)
- Related issues

**Checklist**:
- [ ] Tests pass locally
- [ ] Code formatted with Black
- [ ] Linting passes with Ruff
- [ ] Type checking passes with MyPy
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (for significant changes)

### Code Review Process

**For Reviewers**:
- Check functionality and test coverage
- Verify code follows style guidelines
- Ensure documentation is adequate
- Test complex changes locally

**For Authors**:
- Respond to feedback promptly
- Make requested changes in separate commits
- Update PR description if scope changes
- Squash commits before merge (if requested)

## Performance Optimization

### Database Performance

**Query Optimization**:
```sql
-- Use indexes for common queries
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_lock_holder ON tasks(lock_holder);
CREATE INDEX idx_tasks_story_id ON tasks(story_id);

-- Analyze query performance
EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE status = 'pending';
```

**WAL Mode Benefits**:
```python
# WAL mode enables concurrent reads during writes
db.execute("PRAGMA journal_mode=WAL")
db.execute("PRAGMA synchronous=NORMAL")  # Faster, still safe
```

### Memory Management

**Connection Pooling**:
```python
# Consider connection pooling for high concurrency
# Current implementation uses single connection per instance
```

**WebSocket Management**:
```python
# Monitor connection count
connection_count = connection_manager.get_connection_count()
if connection_count > 1000:
    logger.warning(f"High WebSocket connection count: {connection_count}")
```

### Profiling Tools

**Python Profiling**:
```bash
# Profile API endpoints
python -m cProfile -o profile.stats -m uvicorn task_manager.api:app

# Analyze with snakeviz
pip install snakeviz
snakeviz profile.stats
```

**Memory Profiling**:
```bash
# Install memory profiler
pip install memory-profiler

# Profile memory usage
python -m memory_profiler scripts/profile_memory.py
```

## Deployment Considerations

### Production Deployment

**Environment Variables**:
```bash
export DATABASE_PATH=/var/lib/project-manager/project_manager.db
export LOG_LEVEL=INFO
export WORKERS=4
```

**Systemd Service** (`/etc/systemd/system/project-manager-mcp.service`):
```ini
[Unit]
Description=Project Manager MCP
After=network.target

[Service]
Type=simple
User=project-manager
WorkingDirectory=/opt/project-manager-mcp
ExecStart=/opt/project-manager-mcp/venv/bin/project-manager-mcp --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Reverse Proxy** (nginx):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Docker Deployment

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

EXPOSE 8080 8081
CMD ["project-manager-mcp", "--host", "0.0.0.0"]
```

**Docker Compose**:
```yaml
version: '3.8'
services:
  project-manager:
    build: .
    ports:
      - "8080:8080"
      - "8081:8081"
    volumes:
      - ./data:/data
    environment:
      - DATABASE_PATH=/data/project_manager.db
```

## Troubleshooting Development Issues

### Common Problems

**Import Errors**:
```bash
# Ensure editable install
pip install -e .

# Check Python path
python -c "import task_manager; print(task_manager.__file__)"
```

**Database Locked**:
```bash
# Check for competing processes
ps aux | grep project-manager-mcp

# Remove lock file if corrupted
rm project_manager.db-wal project_manager.db-shm
```

**Port Conflicts**:
```bash
# Find process using port
lsof -i :8080

# Kill process if needed
kill -9 <PID>
```

**Test Failures**:
```bash
# Run single failing test with output
pytest -v -s test/project_manager/test_api.py::test_failing_function

# Debug with pdb
pytest --pdb test/project_manager/test_api.py::test_failing_function
```

### Debugging Techniques

**Logging**:
```python
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Variable value: {variable}")
```

**Breakpoints**:
```python
import pdb; pdb.set_trace()
# Or in Python 3.7+
breakpoint()
```

**WebSocket Debugging**:
```javascript
// Browser console
const ws = new WebSocket('ws://localhost:8080/ws/updates');
ws.onmessage = (e) => console.log('Received:', JSON.parse(e.data));
```

## Release Process

### Version Management

Versions follow semantic versioning (SemVer):
- **Major**: Breaking changes (1.0.0 → 2.0.0)
- **Minor**: New features, backward compatible (1.0.0 → 1.1.0)
- **Patch**: Bug fixes (1.0.0 → 1.0.1)

### Release Checklist

1. **Update Version**: Update version in `pyproject.toml`
2. **Update CHANGELOG**: Document all changes since last release
3. **Run Tests**: Ensure all tests pass on supported Python versions
4. **Build Package**: `python -m build`
5. **Test Install**: Install and test built package
6. **Tag Release**: `git tag v1.0.0`
7. **Push**: `git push origin v1.0.0`
8. **GitHub Release**: Create release with changelog
9. **PyPI Upload**: `twine upload dist/*`

### CI/CD Pipeline

Example GitHub Actions workflow (`.github/workflows/ci.yml`):

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11, 3.12]

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e .[dev,test,lint]
    
    - name: Lint
      run: |
        black --check src/ test/
        ruff check src/ test/
        mypy src/
    
    - name: Test
      run: |
        pytest --cov=task_manager --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Getting Help

### Documentation
- [Usage Guide](usage.md) - End-user documentation
- [API Documentation](api.md) - REST and WebSocket API reference
- [README](../README.md) - Project overview and quick start

### Community
- **Issues**: Report bugs and request features on GitHub
- **Discussions**: Ask questions and share ideas
- **Discord/Slack**: Real-time community chat (if available)

### Maintainers
- Check MAINTAINERS.md for current maintainer list
- Tag maintainers in issues for urgent matters
- Follow code review timelines and processes

---

Thank you for contributing to Project Manager MCP! Your contributions help make this project better for everyone.