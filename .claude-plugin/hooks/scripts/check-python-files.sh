#!/bin/bash
# Check Python files after Edit/Write operations

# Only run if we're in a Python project
if [ ! -f "pyproject.toml" ] && [ ! -f "setup.py" ]; then
    exit 0
fi

# Check if virtual environment exists and activate it
if [ -f "activate.sh" ]; then
    source activate.sh 2>/dev/null || true
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate 2>/dev/null || true
fi

echo "🔍 Running Python code quality checks..."

# Run mypy type checking
if command -v mypy &> /dev/null && [ -d "src" ]; then
    echo "Running mypy..."
    mypy src/ 2>&1 | head -20
fi

# Run black formatting check
if command -v black &> /dev/null; then
    echo "Running black --check..."
    black --check . 2>&1 | head -10
fi

exit 0
