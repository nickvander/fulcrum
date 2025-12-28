#!/bin/bash
# Git pre-commit hook for Fulcrum project
# Runs fast checks before allowing a commit

echo "Running pre-commit checks for Fulcrum..."

# Check if fast backend tests pass (non-db tests only)
echo "Running fast backend tests..."

# Try to run tests using npm first, fallback to direct execution if needed
if command -v npm &> /dev/null && npm run test:backend:fast &> /dev/null; then
    echo "✅ Fast backend tests passed."
else
    # Fallback: run with virtual environment if npm command fails
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        cd backend && pytest -c pytest.ini -m 'not db and not slow'
        result=$?
    else
        echo "❌ No virtual environment found, attempting direct pytest"
        cd backend && pytest -c pytest.ini -m 'not db and not slow'
        result=$?
    fi
    
    if [ $result -ne 0 ]; then
        echo "❌ Fast backend tests failed. Commit blocked."
        exit 1
    else
        echo "✅ Fast backend tests passed."
    fi
fi

# Run linter
echo "Running linter..."
if command -v npx &> /dev/null && npx ruff check . --force-exclude &> /dev/null; then
    lint_result=$?
elif [ -f ".venv/bin/activate" ]; then
    # Fallback to direct ruff in virtual environment
    source .venv/bin/activate
    ruff check . --force-exclude
    lint_result=$?
elif command -v ruff &> /dev/null; then
    # Fallback to direct ruff if available
    ruff check . --force-exclude
    lint_result=$?
else
    echo "❌ Ruff linter not found. Please install ruff."
    exit 1
fi

if [ $lint_result -ne 0 ]; then
    echo "❌ Lint checks failed. Commit blocked."
    exit 1
else
    echo "✅ Lint checks passed."
fi

echo "✅ All pre-commit checks passed. Proceeding with commit..."
exit 0