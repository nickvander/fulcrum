# Task: Phase 3.7 - Admin Features & UX Enhancements

## Goal

To significantly improve the usability and feature-richness of the application
by introducing critical administrative capabilities and refining the user
experience. This phase will focus on building a complete user management module
for administrators and implementing key UX improvements in the product module.

## Critique of Current Implementation & Proposed Enhancements

1.  **No User Management:** Currently, there is no way to manage the users who
    have access to the application. This is a critical feature for any
    real-world system.
    - **Enhancement:** Implement a full CRUD interface for user management,
      restricted to admin users.

2.  **Limited Data Interaction:** The product list provides server-side semantic
    search but lacks immediate, client-side filtering and sorting capabilities.
    This makes it cumbersome for users to quickly find items in the currently
    loaded view.
    - **Enhancement:** Leverage the existing `MatTableDataSource` to add instant
      client-side filtering.

3.  **Poor "Empty State" Experience:** When there are no products in the system,
    the product list simply shows an empty table, which can be confusing for new
    users.
    - **Enhancement:** Add a user-friendly "empty state" message with a
      call-to-action button to guide users.

4.  **Lack of Admin Roles:** The backend `User` model does not have a concept of
    an administrator or "superuser," which is a prerequisite for restricting
    access to sensitive areas like user management.
    - **Enhancement:** Add an `is_superuser` flag to the `User` model and create
      an authorization dependency to protect admin-only endpoints.

## Implementation Plan

### 1. Backend: User Management Foundation

- **Task:** Update the `User` model and create the necessary database and
  security structures.
- **Actions:**
  - Add a new `is_superuser: bool` field to the `User` model in
    `backend/src/models/user.py`.
  - Generate a new Alembic migration to apply this change to the database.
  - In `backend/src/api/dependencies.py`, create a new `get_current_superuser`
    dependency that verifies the logged-in user has the `is_superuser` flag set.

### 2. Backend: User Management API

- **Task:** Build the API endpoints for managing users.
- **Actions:**
  - In `backend/src/crud/crud_user.py`, add new functions to get all users and
    to update a user.
  - In `backend/src/api/v1/endpoints/users.py`, create new endpoints for:
    - `GET /`: Retrieve a list of all users.
    - `GET /{user_id}`: Retrieve a single user.
    - `PUT /{user_id}`: Update a user's details (e.g., toggling their
      `is_superuser` status).
  - Protect all of these new endpoints using the `get_current_superuser`
    dependency.

### 3. Frontend: User Management Module

- **Task:** Create the frontend interface for administrators to manage users.
- **Actions:**
  - Create a new, lazy-loaded `UsersModule`.
  - Create a `UserListComponent` that displays a table of all users.
  - Create a `UserFormComponent` that allows an admin to edit a user's details.
  - Add a new "Users" link to the main sidenav, visible only to superusers.
  - Implement the necessary methods in a new `UserService` to interact with the
    new backend API endpoints.

### 4. Frontend: Product List UX Enhancements

- **Task:** Improve the usability of the existing product list.
- **Actions:**
  - **Client-Side Filtering:**
    - In `ProductListComponent`, modify the `onSearchQuery` method to apply a
      client-side filter to the `MatTableDataSource` in addition to the
      server-side search. This provides instant feedback as the user types.
    - The "Clear Search" button will clear this filter.
  - **Empty State UI:**
    - In `product-list.html`, add a new container with a message like "No
      products found." and a "Create Your First Product" button that appears
      only when the `dataSource` is empty.

## Validation

- All existing and new backend/frontend tests must pass.
- A regular user cannot access the `/api/v1/users` endpoints or see the "Users"
  link in the UI.
- An admin user can successfully view, edit, and update other users.
- The product list filters instantly as the user types in the search bar.
- A helpful message and button are displayed on the product page when no
  products exist.
