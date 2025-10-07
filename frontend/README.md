# Frontend

This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 20.3.4.

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Web Test Runner](https://modern-web.dev/docs/test-runner/overview/), use the following command:

```bash
npm test
```

This will launch the test runner, build the test environment, and execute all `.spec.ts` files in a headless Chromium browser.

### Testing Environment Setup

The project is configured to use the [Web Test Runner](https://modern-web.dev/docs/test-runner/overview/) with Playwright for running unit tests. The configuration is located in `web-test-runner.config.mjs`.

To ensure the test runner can launch the browser, you must install the Playwright browsers and their dependencies by running the following command:

```bash
npx playwright install --with-deps
```

**Note:** As of the last update, there is an unresolved issue where the test runner fails to launch the browser in some WSL environments. This is due to the test runner incorrectly detecting and attempting to use the Windows Chrome executable. Attempts to resolve this by explicitly setting the executable path to the Playwright-provided browser have been unsuccessful, suggesting a deeper issue with how the browser process is launched in the WSL environment.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
