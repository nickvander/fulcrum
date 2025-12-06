# Future Work: Bazel Frontend Testing

## Issue Summary

The Angular `@angular-devkit/build-angular:web-test-runner` builder fails to detect
`@web/test-runner` when running in Bazel's sandbox environment, despite the package
being correctly installed in `node_modules`.

**Error**: "Web Test Runner is not installed"

## Root Cause

1. **Experimental Builder**: The Web Test Runner builder is marked as experimental
   and not production-ready.
2. **Bazel Sandbox Isolation**: Bazel's strict sandboxing creates different
   `node_modules` resolution paths than the builder expects.
3. **Module Resolution**: The builder uses internal `require()` calls that fail in
   the sandboxed environment.

## Attempted Solutions (Did Not Work)

- Adding `@web/test-runner` as explicit dependency
- Adding ~50 phantom dependencies for Bazel sandbox
- Patching pnpm with `onlyBuiltDependencies`
- Setting `NODE_PRESERVE_SYMLINKS=1`

## Current Workaround

Run frontend tests locally using `pnpm ng test` instead of `bazel test
//frontend:test`. All 144 tests pass with this approach.

## Future Options

### Option 1: Wait for Angular Maturity (Recommended)

Monitor Angular releases for Web Test Runner stability improvements. The builder is
still experimental and may receive fixes that resolve Bazel compatibility.

### Option 2: Migrate to Jest

Replace Web Test Runner with Jest + `jest-preset-angular`:

1. Install Jest dependencies:
   ```bash
   pnpm add -D jest @types/jest jest-preset-angular
   ```

2. Create `jest.config.js` with Angular preset

3. Update `angular.json` to use Jest builder (or custom Bazel rules)

4. Use Bazel's `rules_jest` which has better community support

**Effort**: Medium-High (requires test syntax review, setup changes)

### Option 3: Custom Bazel Rule

Write a custom Bazel rule that invokes `@web/test-runner` directly, bypassing the
Angular builder's detection logic.

**Effort**: High (requires deep Bazel and Web Test Runner knowledge)

## Decision Log

**Date**: 2025-12-05
**Decision**: Accept local testing workaround (Option A)
**Rationale**: The local workflow functions correctly, and other Bazel phases
(CI/CD, documentation, frontend container) provide more immediate value.
