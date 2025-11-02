#!/bin/bash
set -e

echo "🧪 Running PM Dashboard Full Test Suite"
echo "========================================"

# Activate virtual environment
if [ -f "./activate.sh" ]; then
    echo "✓ Activating virtual environment..."
    source activate.sh
else
    echo "⚠️  Warning: activate.sh not found, assuming venv is already active"
fi

# Run database tests
echo ""
echo "1️⃣  Database Tests..."
python -m pytest test/project_manager/test_database.py -v

# Run API tests
echo ""
echo "2️⃣  API Tests..."
python -m pytest test/project_manager/test_api.py::TestBoardStateEndpoint -v

# Run MCP server tests
echo ""
echo "3️⃣  MCP Server Tests..."
python -m pytest test/project_manager/test_mcp_server.py -v

# Code formatting check
echo ""
echo "4️⃣  Code Formatting (Black)..."
black --check .

# Type checking
echo ""
echo "5️⃣  Type Checking (mypy)..."
mypy src/

echo ""
echo "✅ All tests passed!"
echo "========================================"
