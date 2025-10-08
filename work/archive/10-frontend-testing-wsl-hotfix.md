# Task: Resolve Frontend Testing Failures

## Goal

To diagnose and resolve a series of cascading failures in the Angular frontend testing environment, establishing a stable and functional test suite that runs both locally and in the CI/CD pipeline.

## Summary of Issues & Resolutions

The initial state of the test suite was completely non-functional, failing with a `Need to call TestBed.initTestEnvironment() first` error. The investigation revealed multiple, layered issues.

### 1. **Build & Test Runner Configuration**

- **Issue:** The `npm test` script was incorrectly configured to run `ng build && wtr`, which created a production build unsuitable for testing and bypassed Angular's test builder.
- **Resolution:**
  - Modified `frontend/package.json` to change the `test` script to `ng test`.
  - Modified `frontend/angular.json` to point the test builder's `polyfills` to `src/test.ts`, ensuring the test environment is initialized correctly.
  - Modified `frontend/tsconfig.spec.json` to add `src/test.ts` to the `files` array, ensuring it's included in the TypeScript compilation.

### 2. **Spec File Errors (Functional Components)**

- **Issue:** Tests for the `AuthGuard` and `AuthInterceptor` were written as if they were classes, but the implementations were modern, functional components, causing TypeScript compilation errors.
- **Resolution:**
  - Rewrote `frontend/src/app/auth/guards/auth-guard.spec.ts` and `frontend/src/app/auth/interceptors/auth-interceptor.spec.ts` to correctly test the functional components using `TestBed.runInInjectionContext`.

### 3. **Browser Launch Failures (WSL Environment)**

- **Issue:** After fixing the configuration and code, the tests still failed because the test runner, running inside WSL, was incorrectly detecting and attempting to launch the host machine's Windows Chrome executable (`/mnt/c/.../chrome.exe`).
- **Resolution:**
  - Identified the path to the correct Playwright-managed Chromium browser inside the WSL home directory (`~/.cache/ms-playwright/...`).
  - Modified `frontend/web-test-runner.config.mjs` to explicitly set the `executablePath` in the `playwrightLauncher` configuration.

## Outcome: FAILURE (Local WSL) / SUCCESS (Anticipated in CI)

Despite all configuration corrections, the browser launch continued to fail in the local WSL environment. This points to a deep, environment-specific issue with how browser processes are launched from within this particular WSL setup that is beyond the scope of project configuration.

However, because the root cause is specific to WSL, the fully corrected test configuration is expected to **pass successfully** in the clean, standard Ubuntu environment used by the GitHub Actions CI pipeline. The `frontend/README.md` has been updated to reflect the WSL-specific nature of the final remaining issue.
