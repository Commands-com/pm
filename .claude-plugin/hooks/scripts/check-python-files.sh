#!/bin/bash
# Check Python files after Edit/Write operations

# Only run if we're in a Python project
if [ ! -f "pyproject.toml" ] && [ ! -f "setup.py" ]; then
    exit 0
fi

# Check if virtual environment exists and activate it
if [ -f "activate.sh" ]; then
    source activate.sh >/dev/null 2>&1 || true
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate >/dev/null 2>&1 || true
fi

# Run mypy type checking if available
if command -v mypy &> /dev/null && [ -d "src" ]; then
    echo "🔍 Running mypy type check..."
    if ! mypy src/ 2>&1 | head -20; then
        echo "⚠️  Type checking found issues"
    fi
fi

# Run black formatting check if available
if command -v black &> /dev/null; then
    echo "🔍 Checking code formatting..."
    BLACK_OUTPUT=$(black --check . 2>&1 | head -10)
    if echo "$BLACK_OUTPUT" | grep -q "would reformat"; then
        echo "⚠️  Some files need formatting (run: black .)"
        echo "$BLACK_OUTPUT" | grep "would reformat" | head -5
    else
        echo "✅ Code formatting OK"
    fi
fi

exit 0
