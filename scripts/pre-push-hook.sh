#!/bin/bash
# Git pre-push hook for Fulcrum project
# Runs the full CI test suite before allowing a push

echo "Running pre-push checks for Fulcrum..."

# Check if tests pass
echo "Running backend tests..."
if command -v npm &> /dev/null; then
    npm run test:backend
    backend_result=$?
else
    echo "❌ npm not found. Cannot run backend tests."
    exit 1
fi

if [ $backend_result -ne 0 ]; then
    echo "❌ Backend tests failed. Push blocked."
    exit 1
else
    echo "✅ Backend tests passed."
fi

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

echo "Running lint checks..."
if command -v npx &> /dev/null; then
    npx ruff check . --force-exclude
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