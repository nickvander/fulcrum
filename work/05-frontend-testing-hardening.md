# Task: Harden Frontend Testing Environment

## Goal

To establish a stable, reliable, and CI-friendly testing environment for the Angular frontend application. The previous attempts were blocked by a series of complex, environment-specific configuration issues. This task is dedicated to resolving these issues systematically.

## Background & Problem Statement

During the initial setup, the Karma test runner failed due to a cascade of problems:
1.  **Sass Compilation Errors:** The modern `@use` syntax in Angular 18's build system caused persistent `Undefined function` errors for Material theming functions.
2.  **Missing Chrome Binary:** The default `ChromeHeadless` launcher failed in the CI-like environment, which is common.
3.  **Puppeteer Configuration Issues:** While Puppeteer was installed to provide a local browser, the Karma runner failed to connect to it, citing a missing Chromium revision and other configuration path errors.

## Proposed Plan

1.  **Isolate the Test Runner:**
    *   Temporarily remove all custom Karma configuration (`karma.conf.js`) and revert the `angular.json` to its default test configuration.
    *   Run the simplest possible test (`ng test`) to establish a baseline.

2.  **Systematically Re-introduce Configuration:**
    *   **Browser:** Instead of Puppeteer, we will try the `karma-chrome-launcher` again but with a direct path to the Chrome binary if available. If not, we will re-attempt the Puppeteer configuration from scratch, ensuring the post-install script is run correctly.
    *   **CI-Friendly Flags:** Re-introduce the `--no-sandbox` and `--disable-gpu` flags one by one.

3.  **Address Theming for Tests:**
    *   If the Sass issues persist *only* in the test environment, create a separate `tsconfig.spec.json` or `angular.json` configuration to provide a mock or pre-built theme *only* for the tests. This will decouple the testing environment from the complexities of custom theming.

4.  **Write Foundational Tests:**
    *   Once the runner is stable, write simple, foundational unit tests for the following:
        *   `AuthService`: Mock the `HttpClient` and test the `login`, `logout`, and `isLoggedIn` methods.
        *   `ProductService`: Test that the `getProducts` method returns the mock data correctly.
        *   `LoginComponent`: Test that the form is initially invalid and becomes valid when filled out.

## Validation

*   The command `npm test -- --watch=false` must run successfully without any build or configuration errors.
*   The command must execute all existing and new unit tests.
*   The GitHub Actions CI pipeline must pass successfully when running the frontend tests.
