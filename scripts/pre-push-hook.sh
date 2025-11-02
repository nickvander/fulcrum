#!/bin/bash
# Git pre-push hook for Fulcrum project
# Runs a comprehensive but efficient CI test suite before allowing a push

echo "Running pre-push checks for Fulcrum..."

# Run fast backend tests (non-db tests only) - this is much quicker
echo "Running fast backend tests..."
if [ -f ".venv/bin/activate" ]; then
    # Use virtual environment if available
    source .venv/bin/activate
    cd backend && python -m pytest -c pytest.ini -m 'not db'
    backend_result=$?
    cd ..
elif command -v pytest &> /dev/null; then
    # Fallback to system pytest if available
    cd backend && pytest -c pytest.ini -m 'not db'
    backend_result=$?
    cd ..
else
    # Fallback to npm script
    if command -v npm &> /dev/null; then
        npm run test:backend:fast
        backend_result=$?
    else
        echo "❌ No way to run fast backend tests. Please install pytest or npm."
        exit 1
    fi
fi

if [ $backend_result -ne 0 ]; then
    echo "❌ Fast backend tests failed. Push blocked."
    exit 1
else
    echo "✅ Fast backend tests passed."
fi

# Run frontend tests
echo "Running frontend tests..."
if command -v npm &> /dev/null; then
    npm run test:frontend
    frontend_result=$?
else
    echo "❌ npm not found. Cannot run frontend tests."
    exit 1
fi

if [ $frontend_result -ne 0 ]; then
    echo "❌ Frontend tests failed. Push blocked."
    exit 1
else
    echo "✅ Frontend tests passed."
fi

# Run lint checks
echo "Running lint checks..."
if command -v npx &> /dev/null; then
    npx ruff check . --force-exclude
    lint_result=$?
elif [ -f ".venv/bin/ruff" ]; then
    # Use virtual environment ruff if available
    .venv/bin/ruff check . --force-exclude
    lint_result=$?
elif command -v ruff &> /dev/null; then
    ruff check . --force-exclude
    lint_result=$?
else
    echo "❌ Ruff linter not found. Please install ruff or npx."
    exit 1
fi

if [ $lint_result -ne 0 ]; then
    echo "❌ Lint checks failed. Push blocked."
    exit 1
else
    echo "✅ Lint checks passed."
fi

echo "✅ All checks passed. Proceeding with push..."
exit 0