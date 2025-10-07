# Task: Implement Frontend Testing with Web Test Runner

## Goal

To establish a stable, modern, and CI-friendly testing environment for the
Angular frontend by migrating from the legacy Karma/Jasmine setup to the Web
Test Runner.

## Implementation Plan

1.  **Cleanup Legacy Configuration:**
    - Uninstalled all Karma, Puppeteer, and related dependencies from
      `package.json`.

2.  **Install Web Test Runner Dependencies:**
    - Installed `@web/test-runner`, `@web/test-runner-playwright`,
      `@rollup/plugin-commonjs`, and `@rollup/plugin-replace` as development
      dependencies.

3.  **Configure Web Test Runner:**
    - Created a `web-test-runner.config.mjs` file to configure the test runner
      to use Playwright with a headless Chromium browser.

4.  **Update Angular Configuration:**
    - Modified `angular.json` to include a `test.ts` file in the test builder's
      `polyfills`. This file initializes the Angular testing environment.

5.  **Update `package.json`:**
    - Modified the `test` script to `ng build && wtr`.

6.  **Update CI Pipeline:**
    - Modified the `.github/workflows/ci.yml` file to execute the `npm test`
      command in a headless environment, ensuring automated tests run on every
      pull request.

## Validation

- The frontend test suite now runs successfully both locally and in the CI
  pipeline.
