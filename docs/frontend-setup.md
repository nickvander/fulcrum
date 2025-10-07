# Frontend Setup & Architecture

This document provides a comprehensive guide to setting up, running, and
understanding the architecture of the Fulcrum frontend application.

## 1. Prerequisites

Before you begin, ensure you have the following installed:

- [Node.js](https://nodejs.org/) (LTS version recommended)
- [Angular CLI](https://angular.dev/tools/cli) (install globally with
  `npm install -g @angular/cli`)

## 2. Project Setup

1.  **Navigate to the frontend directory:**

    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

## 3. Key Scripts

All commands should be run from the `frontend/` directory.

- **Run the development server:**

  ```bash
  ng serve
  ```

  The application will be available at `http://localhost:4200/`.

- **Run unit tests:**

  ```bash
  npm test
  ```

  **Note:** The frontend test runner is currently non-functional due to complex
  dependency and environment issues. While all generated components and services
  have corresponding `.spec.ts` files, the test suite will not execute
  successfully. Resolving this is a high-priority task documented in
  `work/05-frontend-testing-hardening.md`.

- **Build for production:**
  ```bash
  ng build
  ```
  The production-ready static files will be generated in the
  `frontend/dist/frontend/browser/` directory.

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
