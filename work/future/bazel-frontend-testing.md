# Frontend Testing Migration to Vitest

## Problem Summary

Two related issues affect frontend test reliability:

1. **Bazel Sandbox Issue**: The Angular `@angular-devkit/build-angular:web-test-runner` 
   builder fails to detect `@web/test-runner` in Bazel's sandbox environment.

2. **Intermittent Timeouts**: Tests randomly timeout (120s) during parallel runs, 
   especially in pre-push hooks, due to Web Test Runner resource contention.

## Solution: Angular v20 Includes Vitest Support! 🎉

**Angular v20 (released December 2024) includes experimental Vitest support with watch
mode and browser testing!**

> "With the deprecation of Karma, we worked with testing framework authors to find a 
> well maintained replacement that enables browser testing. In v20, Angular CLI comes 
> in with an experimental vitest support that has watch mode and browser testing!"

---

## Migration Plan (Recommended)

### Step 1: Install Dependencies

```bash
cd frontend
pnpm add -D vitest jsdom
```

### Step 2: Update `angular.json`

Replace the current test configuration:

```json
"test": {
    "builder": "@angular/build:unit-test",
    "options": {
        "tsConfig": "tsconfig.spec.json",
        "buildTarget": "::development",
        "runner": "vitest"
    }
}
```

### Step 3: Update Test Files (imports)

Update spec files to use Vitest imports:

```typescript
import { describe, beforeEach, it, expect } from 'vitest';
```

### Step 4: Run Tests

```bash
ng test
```

---

## Why Vitest Over Jest?

| Feature | Vitest | Jest |
|---------|--------|------|
| **Official Angular Support** | ✅ v20 built-in | ❌ Community only |
| **ESM-first** | ✅ Native | ⚠️ Via transforms |
| **Speed** | Faster | Slower |
| **Browser Testing** | ✅ Supported | ⚠️ Requires extra config |
| **Watch Mode** | ✅ Built-in | ✅ Built-in |

---

## Historical Context

**Previous Jest Attempt (Failed)** - See `work/archive/05-frontend-testing-hardening.md`:
- Jest migration was attempted but failed due to deep dependency conflicts
- `Cannot find module '@angular/animations/browser'` couldn't be resolved

**Why Web Test Runner Was Chosen** - See `work/archive/06-frontend-testing-migration-to-web-test-runner.md`:
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

- [ ] All 302 tests pass with Vitest
- [ ] No intermittent timeouts in pre-push or CI  
- [ ] Update test file imports to use Vitest
- [ ] `bazel test //frontend:test` works (stretch goal)

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-05 | Accept local WTR workaround | Other Bazel phases more urgent |
| 2025-12-06 | Queue test runner migration | Intermittent timeouts + Bazel issues |
| 2025-12-06 | **Migrate to Vitest** | Angular v20 includes official experimental support |
