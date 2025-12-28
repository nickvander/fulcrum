#!/bin/bash
# Git pre-push hook for Fulcrum project
# Runs a comprehensive but efficient CI test suite before allowing a push

echo "Running pre-push checks for Fulcrum..."

# Run fast backend tests (non-db tests only) - this is much quicker
echo "Running fast backend tests..."
if [ -f ".venv/bin/activate" ]; then
    # Use virtual environment if available
    source .venv/bin/activate
    cd backend && python -m pytest -c pytest.ini -m 'not db and not integration'
    backend_result=$?
    cd ..
elif command -v pytest &> /dev/null; then
    # Fallback to system pytest if available
    cd backend && pytest -c pytest.ini -m 'not db and not integration'
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
    # Run frontend tests
    npm run test:frontend -- --watch=false
    frontend_result=$?

    if [ $frontend_result -eq 0 ]; then
        echo "✅ Frontend tests passed."
    else
        echo "❌ Frontend tests failed. Push blocked."
    fi
else
    echo "❌ npm not found. Cannot run frontend tests."
    exit 1
fi

if [ $frontend_result -ne 0 ]; then
    echo "❌ Frontend tests failed. Push blocked."
    exit 1
fi

# Run lint checks
echo "Running lint checks..."
# Try multiple approaches to run ruff
if command -v npx &> /dev/null && npx ruff check . --force-exclude 2>/dev/null; then
    echo "✅ Lint checks passed."
    lint_result=0
elif [ -f ".venv/bin/ruff" ] && .venv/bin/ruff check . --force-exclude 2>/dev/null; then
    echo "✅ Lint checks passed."
    lint_result=0
elif command -v ruff &> /dev/null && ruff check . --force-exclude 2>/dev/null; then
    echo "✅ Lint checks passed."
    lint_result=0
elif command -v python && python -c "import ruff" 2>/dev/null && python -m ruff check . --force-exclude 2>/dev/null; then
    echo "✅ Lint checks passed."
    lint_result=0
else
    # If all else fails, try running the ruff command and see if it succeeds
    ruff check . --force-exclude 2>/dev/null
    lint_result=$?
    if [ $lint_result -eq 0 ]; then
        echo "✅ Lint checks passed."
    else
        echo "❌ Lint checks failed. Push blocked."
        echo "Please install ruff to run lint checks:"
        echo "  pip install ruff"
        echo "  # or"
        echo "  npm install -g ruff"
        exit 1
    fi
fi

echo "✅ All checks passed. Proceeding with push..."
exit 0