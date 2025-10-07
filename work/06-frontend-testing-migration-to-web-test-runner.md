# Task: Migrate Frontend Testing to Web Test Runner

## Goal

To establish a stable, modern, and CI-friendly testing environment for the Angular frontend by migrating from the legacy Karma/Jasmine setup to the Web Test Runner.

## Rationale

Previous attempts to stabilize the testing environment with Karma and a planned migration to Jest were fraught with complex dependency and configuration issues. The Web Test Runner is a modern, lightweight, and standards-based tool that integrates cleanly with Angular's application builder, avoiding the legacy complexities of Karma. This migration will provide a more reliable and future-proof foundation for our frontend testing strategy.

## Implementation Plan

1.  **Cleanup Legacy Configuration:**
    -   Uninstall all Karma, Puppeteer, and related dependencies from `package.json`.
    -   Delete the `karma.conf.js` configuration file.

2.  **Install Web Test Runner Dependencies:**
    -   Install `@web/test-runner` and the official Angular builder `@angular-builders/web-test-runner` as development dependencies.

3.  **Update Angular Configuration:**
    -   Modify `angular.json` to replace the Karma test builder (`@angular/build:karma`) with the new Web Test Runner builder (`@angular-builders/web-test-runner:test`).

4.  **Validate Configuration:**
    -   Ensure `tsconfig.spec.json` is correctly configured to include Jasmine types for the test files.
    -   Run the test suite to confirm that the new runner can successfully discover and execute all existing `.spec.ts` files.

5.  **Update CI Pipeline:**
    -   Modify the `.github/workflows/ci.yml` file to execute the `npm test` command in a headless environment, ensuring automated tests run on every pull request.

**NOTE:** This task is currently blocked by environmental issues that are preventing the Web Test Runner from launching a browser. The configuration is correct, but the tests are unable to run.