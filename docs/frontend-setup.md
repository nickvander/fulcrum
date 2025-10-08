# Frontend Application Setup & Architecture

This document provides a comprehensive guide to the setup, architecture, and
development workflows for the Fulcrum frontend application.

## 1. Getting Started

To run the application for the first time, you need to start the backend
services and create an initial administrative user.

### **Step 1: Launch the Backend**

The entire backend stack (API, database, background worker) is managed by Docker
Compose. To start all services, run the following command from the root of the
project:

```bash
docker-compose up --build
```

On Linux, you may need to use `sudo`:

```bash
sudo docker-compose up -d --build
```

### **Step 2: Create an Initial User**

The system does not have a public user registration page. You must create the
first user via the API. Open a new terminal and run the following command:

```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@example.com", "password": "changeme"}'
```

This will create a user with the email `admin@example.com` and the password
`changeme`. You can now use these credentials to log into the frontend
application.

## 2. Core Technologies

- **Framework:** Angular 18
- **UI Components:** Angular Material
- **State Management:** RxJS with component-level services (no central store)
- **Testing:** Web Test Runner with Playwright

## 3. Project Structure

The `frontend/` directory is a standard Angular CLI workspace. Key directories
include:

- `src/app/core`: Singleton services, guards, and interceptors.
- `src/app/shared`: Reusable components, directives, and pipes.
- `src/app/auth`: Components and services related to authentication.
- `src/app/[feature]`: Feature modules (e.g., `products`, `settings`).

## 4. Key Scripts

- `ng serve`: Runs the development server.
- `ng build`: Builds the application for production.
- `npm test`: Runs the unit test suite using the Web Test Runner.


## 4. Application Architecture

The frontend application is built with Angular and follows a modular,
feature-based architecture to ensure a clean separation of concerns and
scalability.

### Core Modules

- **`CoreModule`**: Located in `src/app/core/`, this module provides singleton
  services and core layout components that are used application-wide. This
  includes the main `HeaderComponent` and `SidenavComponent`.

- **`SharedModule`**: Located in `src/app/shared/`, this module contains
  reusable components, directives, and pipes that can be imported and used by
  multiple feature modules. The `AiSearchBarComponent` is a good example.

### Feature Modules

Each primary feature of the application is encapsulated within its own module.
This makes the codebase easier to maintain and allows for lazy loading, which
improves initial application load times.

- **`AuthModule`**: (`src/app/auth/`)
  - **Purpose**: Handles all user authentication logic.
  - **Key Components**: `LoginComponent`
  - **Key Services**: `AuthService` (manages JWT tokens), `AuthGuard` (protects
    routes), `AuthInterceptor` (attaches auth headers to API requests).

- **`ProductsModule`**: (`src/app/products/`)
  - **Purpose**: Manages the full CRUD lifecycle for products.
  - **Key Components**: `ProductListComponent` (displays products in a table),
    `ProductFormComponent` (for creating and editing products).
  - **Key Services**: `ProductService` (handles all API interactions for
    products).

- **`SettingsModule`**: (`src/app/settings/`)
  - **Purpose**: Allows administrators to configure application settings.
  - **Key Components**: `SettingsComponent` (provides a form for updating
    settings).

### Progressive Web App (PWA)

The application is a fully-featured PWA. The `@angular/pwa` schematic has
configured the following:

- **Service Worker**: Caches network requests, allowing for offline or
  low-connectivity access to the application.
- **Web App Manifest**: The `manifest.webmanifest` file provides metadata that
  allows users to "install" the application to their home screen on mobile and
  desktop devices for a native-like experience.
