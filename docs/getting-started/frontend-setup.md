# Frontend Setup & Local Development

This document provides a guide to setting up and running the Angular frontend
application for local development.

## Prerequisites

- [Node.js and npm](https://nodejs.org/)
- The backend services must be running. See the
  [Backend Setup Guide](./backend-setup.md) for instructions.

For Debian/Ubuntu-based systems, you can install Node.js and npm with the
following command:

```bash
sudo apt-get update && sudo apt-get install -y nodejs npm
```

## First-Time Setup

1.  **Install Dependencies:** Navigate to the `frontend` directory and install
    the required npm packages.

    ```bash
    # From the project root
    cd frontend
    npm install
    ```

    > [!NOTE]
    > **Bazel & pnpm Strictness**: This project uses Bazel with `rules_js` and `pnpm`, which enforces strict dependency rules. The Angular CLI relies on several dependencies that are not always explicitly declared in its own `package.json` (phantom dependencies). We have added these to `devDependencies` in `frontend/package.json` to ensure the build works in strict environments.
    >
    > If you are setting up the environment from scratch and encounter `MODULE_NOT_FOUND` errors, you may need to explicitly install these dependencies.
    >
    > **Required Phantom Dependencies:**
    > `picocolors`, `nanoid`, `postcss-media-query-parser`, `css-select`, `css-what`, `domhandler`, `htmlparser2`, `boolbase`, `domutils`, `nth-check`, `domelementtype`, `entities`, `@jridgewell/sourcemap-codec`, `mrmime`, `@ampproject/remapping`, `@jridgewell/trace-mapping`, `@jridgewell/resolve-uri`, `@babel/core`, `@babel/generator`, `@babel/traverse`, `@babel/types`, `@babel/parser`, `@babel/template`, `@babel/code-frame`, `@babel/helpers`, `to-fast-properties`, `@babel/helper-string-parser`, `@babel/helper-validator-identifier`, `@babel/helper-compilation-targets`, `@babel/helper-module-transforms`, `@jridgewell/remapping`, `convert-source-map`, `gensync`, `json5`, `semver`, `debug`, `@babel/helper-annotate-as-pure`, `@babel/helper-plugin-utils`, `@babel/helper-split-export-declaration`, `@babel/helper-create-class-features-plugin`, `fast-glob`, `glob-parent`, `is-glob`, `merge2`, `micromatch`, `@nodelib/fs.stat`, `@nodelib/fs.walk`, `is-extglob`, `fill-range`, `to-regex-range`, `is-number`, `@nodelib/fs.scandir`, `run-parallel`, `queue-microtask`, `fastq`, `reusify`, `@web/test-runner`, `globby` (v11), `portfinder`, `nanocolors`, `playwright`, `@web/test-runner-playwright`
    >
    > **Install Command:**
    > ```bash
    > pnpm add -D picocolors nanoid postcss-media-query-parser css-select css-what domhandler htmlparser2 boolbase domutils nth-check domelementtype entities @jridgewell/sourcemap-codec mrmime @ampproject/remapping @jridgewell/trace-mapping @jridgewell/resolve-uri @babel/core @babel/generator @babel/traverse @babel/types @babel/parser @babel/template @babel/code-frame @babel/helpers to-fast-properties @babel/helper-string-parser @babel/helper-validator-identifier @babel/helper-compilation-targets @babel/helper-module-transforms @jridgewell/remapping convert-source-map gensync json5 semver debug @babel/helper-annotate-as-pure @babel/helper-plugin-utils @babel/helper-split-export-declaration @babel/helper-create-class-features-plugin fast-glob glob-parent is-glob merge2 micromatch @nodelib/fs.stat @nodelib/fs.walk is-extglob fill-range to-regex-range is-number @nodelib/fs.scandir run-parallel queue-microtask fastq reusify @web/test-runner globby@^11 portfinder nanocolors playwright @web/test-runner-playwright
    > ```
    >
    > **Note on Bazel Testing:**
    > Currently, `bazel test //frontend:test` is blocked by a Sass compilation environment incompatibility (`sass-embedded` in sandbox).
    > We recommend running tests locally using:
    > ```bash
    > pnpm ng test
    > ```

2.  **Create an Initial User:** If this is your first time running the
    application, the database will be empty. The system does not have a public
    user registration page, so you must create the first user via the API.

    With the backend services running, open a new terminal and run the following
    command:

    ```bash
    curl -X POST "http://localhost:8000/api/v1/users/" \
         -H "Content-Type: application/json" \
         -d '{"email": "admin@example.com", "password": "changeme"}'
    ```

    You can now use these credentials to log into the frontend application.

## Development Server

To start the local development server, run the following command from the
`frontend` directory:

```bash
npm start
```

This will start the Angular development server, which typically runs on
`http://localhost:4200/`. The application will automatically reload if you
change any of the source files.

### API Proxying

The frontend development server is configured to proxy API requests to the
backend. The file `frontend/proxy.conf.json` is configured to forward any
request to a path starting with `/api` to the backend server running at
`http://localhost:8000`. This avoids CORS issues during development.

## Key `npm` Scripts

All scripts should be run from the `frontend` directory.

- **`npm start`**: Runs the local development server.
- **`npm run build`**: Compiles and builds the application for production. The
  output is placed in the `frontend/dist/` directory.
- **`npm test`**: Runs the unit test suite using the Web Test Runner. See the
  [Testing & CI Guide](../guides/testing-and-ci.md) for more details.
