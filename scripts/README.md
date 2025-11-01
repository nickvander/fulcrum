# Scripts Directory

This directory contains utility scripts used by the project, including git hooks for quality assurance.

## Git Hooks

These scripts are used as git hooks to enforce code quality:

### pre-commit-hook.sh
- Runs fast backend tests (excluding database tests)
- Runs the linter on the codebase
- Blocks commits if any checks fail

### pre-push-hook.sh
- Runs the full backend test suite (including database tests)
- Runs the frontend test suite
- Runs the linter on the codebase
- Blocks pushes if any checks fail

These hooks ensure that code meets quality standards before being committed or pushed to the repository.