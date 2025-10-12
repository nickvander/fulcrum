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
