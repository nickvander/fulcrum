# Task: Phase 2 - The Cross-Platform PWA Management App

## Goal

To build a functional, customizable, and cross-platform Progressive Web App
(PWA) for inventory management. This application will serve as the primary user
interface for the Fulcrum platform, providing a seamless, native-like experience
on web, Android, and iOS from a single codebase.

## High-Level Approach

We will initialize a new Angular workspace and structure the application using a
modular architecture. This involves creating a `CoreModule` for essential
singleton services, a `SharedModule` for reusable UI components, and distinct
`FeatureModules` for each major domain (e.g., Products, Settings). This approach
ensures a clean separation of concerns and improves scalability. We will use
Angular Material for UI components to maintain a consistent and professional
look and feel.

## Detailed Implementation Plan

### 1. **Step 1: Angular Project Initialization**

- Create a new directory named `frontend/`.
- Initialize a new Angular application using the Angular CLI (`ng new`).
- Add Angular Material to the project (`ng add @angular/material`).
- Configure basic project settings, including routing and SCSS for styling.

### 2. **Step 2: Core Structure & Authentication**

- **Create Core Services:**
  - `AuthService`: To handle user login, logout, and JWT token management
    (storing/retrieving from `localStorage`).
  - `ApiService`: A centralized service to handle all HTTP communication with
    the FastAPI backend.
- **Implement Authentication Flow:**
  - Create a `LoginComponent` with a form for users to authenticate.
  - Implement an `AuthGuard` to protect application routes from unauthenticated
    access.
  - Create an `HttpInterceptor` to automatically attach the JWT token to the
    headers of all outgoing API requests.

### 3. **Step 3: UI Layout (The Application Shell)**

- Create a `LayoutModule` responsible for the main application structure.
- Implement a `HeaderComponent` containing the application title, search bar,
  and user menu (logout).
- Implement a `SidenavComponent` for primary navigation (e.g., links to
  Dashboard, Products, Suppliers, Settings).
- Use Angular Material's Sidenav component to ensure the layout is responsive
  and mobile-friendly.

### 4. **Step 4: Feature Implementation (Products CRUD)**

- Create a `ProductsModule` dedicated to product management.
- **`ProductService`:** A feature-specific service to interact with the
  `/api/v1/products/` backend endpoints.
- **`ProductListComponent`:**
  - Use an Angular Material Table to display a list of products.
  - Include buttons for creating, editing, and deleting products.
  - Integrate the `AiSearchBarComponent` (from the original plan) for semantic
    search.
- **`ProductFormComponent`:**
  - A reactive form for creating and editing product details.
  - This component will be used for both the "create new product" and "edit
    product" views.
- **`DeleteConfirmationDialogComponent`:**
  - A modal dialog (using Angular Material Dialog) to provide a simple UX
    confirmation before permanently deleting a product.

### 5. **Step 5: PWA Conversion**

- Once the core application is functional, run `ng add @angular/pwa`.
- This command will automatically:
  - Create the `manifest.webmanifest` file to define the app's name, icon, and
    theme colors.
  - Set up the Angular service worker (`ngsw-worker.js`) for network request
    caching and basic offline capabilities.

## Validation

- All new components will be accompanied by unit tests.
- The application will be tested for responsiveness on different screen sizes.
- End-to-end tests will be added later in the project to validate the full user
  flow.
