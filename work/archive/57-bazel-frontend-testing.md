# Frontend Testing Migration to Vitest

## Problem Summary

Two related issues affect frontend test reliability:

1. **Bazel Sandbox Issue**: The Angular
   `@angular-devkit/build-angular:web-test-runner` builder fails to detect
   `@web/test-runner` in Bazel's sandbox environment.

2. **Intermittent Timeouts**: Tests randomly timeout (120s) during parallel
   runs, especially in pre-push hooks, due to Web Test Runner resource
   contention.

## Solution: Angular v21 Makes Vitest the Default! 🎉

**Angular v21 (released November 2025) promotes Vitest to STABLE and makes it
the default test runner!**

> "After getting positive feedback from the community we decided on Vitest as
> our new default test runner, and are promoting it to stable in Angular v21 🎉"

**Key changes:**

- ✅ **Vitest is now STABLE** and production-ready
- ✅ **Official migration schematic** available
- ⚠️ **WTR and Jest are DEPRECATED** (will be removed in v22)

---

## Migration Plan

### Step 1: Upgrade to Angular v21

```bash
ng update @angular/core @angular/cli
```

### Step 2: Run the Official Migration Schematic

```bash
ng g @schematics/angular:refactor-jasmine-vitest
```

This automatically refactors your tests from Jasmine to Vitest syntax.

### Step 3: Run Tests

```bash
ng test
```

That's it! 🎉

---

## Why Vitest?

| Feature                      | Status                 |
| ---------------------------- | ---------------------- |
| **Official Angular Support** | ✅ Stable in v21       |
| **Browser Testing**          | ✅ Supported           |
| **Watch Mode**               | ✅ Built-in            |
| **Migration Path**           | ✅ Official schematic  |
| **Future-proof**             | ✅ WTR/Jest deprecated |

---

## Historical Context

**Previous Jest Attempt (Failed)** - See
`work/archive/05-frontend-testing-hardening.md`:

- Jest migration was attempted but failed due to deep dependency conflicts
- `Cannot find module '@angular/animations/browser'` couldn't be resolved

**Why Web Test Runner Was Chosen** - See
`work/archive/06-frontend-testing-migration-to-web-test-runner.md`:

- Angular's officially supported modern test runner at the time
- Avoids Karma legacy complexities
- Now superseded by Angular v20's official Vitest support

---

## Bazel Integration (Future)

Once Vitest is working locally, Bazel integration options:

1. **Use `rules_vitest`** (if available) from Aspect
2. **Custom Bazel rule** invoking vitest directly
3. **Skip Bazel for tests** - run locally with `ng test`, rely on CI

---

## Success Criteria

- [x] All 226 tests pass with Vitest
- [x] No intermittent timeouts in pre-push or CI
- [x] Update test file imports to use Vitest
- [~] `bazel test //frontend:test` works (Deferred: Sandbox incompatibility)

---

## Decision Log

| Date       | Decision                            | Rationale                                                                                               |
| ---------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------- |
| 2025-12-05 | Accept local WTR workaround         | Other Bazel phases more urgent                                                                          |
| 2025-12-06 | **Upgrade to Angular v21 + Vitest** | v21 makes Vitest STABLE with official migration schematic                                               |
| 2025-12-27 | **Defer Bazel Integration**         | Angular Builder incompatible with Bazel sandbox; Direct Vitest blocked by native deps. Using `ng test`. |
