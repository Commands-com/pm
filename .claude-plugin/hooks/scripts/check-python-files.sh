#!/bin/bash
set -e

# CRITICAL: Consume stdin (hooks receive JSON via stdin)
tool_info=$(cat)

# Extract file path to check if it's a Python file
file_path=$(echo "$tool_info" | jq -r '.tool_input.file_path // empty')

# Only run for Python files
if [[ ! "$file_path" =~ \.py$ ]]; then
    exit 0
fi

# Only run if we're in a Python project
if [ ! -f "$CLAUDE_PROJECT_DIR/pyproject.toml" ] && [ ! -f "$CLAUDE_PROJECT_DIR/setup.py" ]; then
    exit 0
fi

# Change to project directory
cd "$CLAUDE_PROJECT_DIR"

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
