#!/bin/bash
# Git pre-push hook for Fulcrum project
# Runs the full CI test suite before allowing a push

echo "Running pre-push checks for Fulcrum..."

# Check if tests pass
echo "Running backend tests..."
npm run test:backend

if [ $? -ne 0 ]; then
    echo "❌ Backend tests failed. Push blocked."
    exit 1
else
    echo "✅ Backend tests passed."
fi

echo "Running frontend tests..."
npm run test:frontend

if [ $? -ne 0 ]; then
    echo "❌ Frontend tests failed. Push blocked."
    exit 1
else
    echo "✅ Frontend tests passed."
fi

echo "Running lint checks..."
npx ruff check .

if [ $? -ne 0 ]; then
    echo "❌ Lint checks failed. Push blocked."
    exit 1
else
    echo "✅ Lint checks passed."
fi

echo "✅ All checks passed. Proceeding with push..."
exit 0