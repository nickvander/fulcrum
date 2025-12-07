# Future Work: Frontend Testing Migration to Jest

## Problem Summary

Two related issues affect frontend test reliability:

1. **Bazel Sandbox Issue**: The Angular `@angular-devkit/build-angular:web-test-runner` 
   builder fails to detect `@web/test-runner` in Bazel's sandbox environment.

2. **Intermittent Timeouts**: Tests randomly timeout (120s) during parallel runs, 
   especially in pre-push hooks, due to Web Test Runner resource contention.

## Historical Context

**Previous Jest Attempt (Failed)** - See `work/archive/05-frontend-testing-hardening.md`:
- Jest migration was attempted but failed due to deep dependency conflicts
- `Cannot find module '@angular/animations/browser'` couldn't be resolved
- `moduleNameMapper` workarounds didn't work

**Why Web Test Runner Was Chosen** - See `work/archive/06-frontend-testing-migration-to-web-test-runner.md`:
- Angular's officially supported modern test runner
- Avoids Karma legacy complexities
- Cleaner integration with Angular application builder

## Angular 2025 Roadmap: Testing

> **From the Angular team's 2025 strategy blog post:**
> 
> "Replace Karma — with the deprecation of Karma we'd like to identify a good 
> replacement that we'll enable as the default recommendation for apps built with
> Angular. We've been exploring **Web Test Runner, Jest, and Vitest** and as part 
> of this project will evaluate each of these runners and integrate it with the CLI."

This means:
1. **Angular team acknowledges testing needs improvement**
2. **Official CLI integration is coming** for the chosen runner
3. **All three options are being evaluated** (not just WTR)

### Recommendation: Wait vs. Migrate Now

| Option | Pros | Cons |
|--------|------|------|
| **Wait for Angular's choice** | Official support, CLI schematics, less work | Continued intermittent timeouts |
| **Migrate to Jest now** | Immediate stability, Bazel support | May need re-migration if Angular picks Vitest |
| **Try Vitest** | Faster than Jest, modern ESM-first | Less Angular ecosystem support currently |

**Suggested approach:** Wait until Angular v20 (expected mid-2025) for the official
recommendation. If timeouts become blocking before then, migrate to Jest since it
has the most mature Bazel integration.

## Why Jest? (If Not Waiting)

- **Mature & Stable**: Battle-tested in thousands of Angular projects
- **Better Parallelism**: Worker-based isolation prevents resource contention
- **Bazel Support**: `rules_jest` has excellent community support
- **Faster Execution**: Jest's caching and parallelization are more efficient
- **Better DX**: Clearer error messages, snapshot testing, better mocking

---

## Migration Plan

### Phase 1: Setup (Estimated: 2-4 hours)

1. **Install Jest dependencies**:
   ```bash
   cd frontend
   pnpm add -D jest @types/jest jest-preset-angular @angular-builders/jest
   ```

2. **Create `jest.config.js`**:
   ```javascript
   module.exports = {
     preset: 'jest-preset-angular',
     setupFilesAfterEnv: ['<rootDir>/src/setup-jest.ts'],
     testPathIgnorePatterns: ['/node_modules/', '/dist/'],
     globals: {
       'ts-jest': {
         tsconfig: '<rootDir>/tsconfig.spec.json',
         stringifyContentPathRegex: '\\.html$'
       }
     },
     moduleNameMapper: {
       '@app/(.*)': '<rootDir>/src/app/$1',
       '@environments/(.*)': '<rootDir>/src/environments/$1'
     },
     testMatch: ['**/*.spec.ts'],
     collectCoverageFrom: ['src/app/**/*.ts', '!src/app/**/*.module.ts']
   };
   ```

3. **Create `src/setup-jest.ts`**:
   ```typescript
   import 'jest-preset-angular/setup-jest';
   
   // Mock global objects not available in jsdom
   Object.defineProperty(window, 'getComputedStyle', {
     value: () => ({ getPropertyValue: () => '' })
   });
   ```

4. **Update `angular.json`**:
   ```json
   "test": {
     "builder": "@angular-builders/jest:run",
     "options": {
       "configPath": "jest.config.js"
     }
   }
   ```

### Phase 2: Test Syntax Updates (Estimated: 4-8 hours)

Most Jasmine tests work directly in Jest, but some changes are needed:

| Jasmine | Jest |
|---------|------|
| `jasmine.createSpyObj()` | `jest.fn()` with object |
| `spyOn().and.returnValue()` | `jest.spyOn().mockReturnValue()` |
| `spyOn().and.callFake()` | `jest.spyOn().mockImplementation()` |
| `expect().toHaveBeenCalledWith(jasmine.any())` | `expect().toHaveBeenCalledWith(expect.any())` |

**Automated migration tool**:
```bash
npx jest-codemods --force --parser ts src/**/*.spec.ts
```

### Phase 3: Bazel Integration (Estimated: 2-4 hours)

1. **Add `rules_jest` to `WORKSPACE.bazel`**:
   ```starlark
   http_archive(
       name = "aspect_rules_jest",
       sha256 = "...",
       strip_prefix = "rules_jest-0.18.4",
       url = "https://github.com/aspect-build/rules_jest/releases/download/v0.18.4/rules_jest-v0.18.4.tar.gz",
   )
   
   load("@aspect_rules_jest//jest:dependencies.bzl", "rules_jest_dependencies")
   rules_jest_dependencies()
   ```

2. **Update `frontend/BUILD.bazel`**:
   ```starlark
   load("@aspect_rules_jest//jest:defs.bzl", "jest_test")
   
   jest_test(
       name = "test",
       config = "jest.config.js",
       data = [
           ":node_modules",
           "//frontend/src:sources",
       ],
       node_modules = "//:node_modules",
   )
   ```

### Phase 4: CI/Hook Updates (Estimated: 1 hour)

1. Update `package.json` scripts:
   ```json
   "test": "jest",
   "test:watch": "jest --watch",
   "test:coverage": "jest --coverage"
   ```

2. Pre-push hook already uses `npm test` - no changes needed

---

## Rollback Plan

Keep Web Test Runner config files until Jest is fully validated:
- `angular.json` (backup test config)
- `web-test-runner.config.js` (if created)

---

## Success Criteria

- [ ] All 302 tests pass with Jest
- [ ] No intermittent timeouts in pre-push or CI
- [ ] `bazel test //frontend:test` works in sandbox
- [ ] Test execution time ≤ current baseline (ideally faster)

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-05 | Accept local WTR workaround | Other Bazel phases more urgent |
| 2025-12-06 | Queue Jest migration | Intermittent timeouts + Bazel issues justify investment |
| 2025-12-06 | Consider waiting for Angular v20 | Angular team evaluating WTR/Jest/Vitest for official recommendation |

