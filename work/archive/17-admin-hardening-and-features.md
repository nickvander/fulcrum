# Task: Phase 3.8 - Admin Module Hardening & Feature Completion

## Goal

To transition the recently implemented admin module from a functional prototype to a production-ready feature set. This phase will focus on closing critical security gaps, adding essential user management features, improving user experience with clear feedback, and ensuring the new functionality is covered by a robust suite of automated tests.

## Critique of Current Implementation & Proposed Enhancements

1.  **Insecure Frontend Authorization:** The `AuthService` currently grants superuser privileges to all users by default (`isSuperuser() { return of(true); }`). This was a temporary measure for development and is a critical security vulnerability.
    -   **Enhancement:** Implement proper JWT decoding in the `AuthService` to accurately determine a user's superuser status from the access token.

2.  **Incomplete User Management Lifecycle:** The admin UI allows for editing users but lacks the ability to create new users or delete existing ones. This leaves the user management workflow incomplete.
    -   **Enhancement:**
        -   Add a "Create User" button and a dedicated route/form for creating new users.
        -   Implement a "Delete" button with a confirmation dialog in the `UserListComponent`.

3.  **Missing Password Management:** Administrators have no way to reset a user's password, which is a common and essential administrative task.
    -   **Enhancement:** Add a password field to the `UserFormComponent` that allows an admin to set a new password for a user.

4.  **Lack of User Feedback:** The application does not provide clear notifications to the user upon the success or failure of an action (e.g., saving a user). This can lead to a confusing user experience.
    -   **Enhancement:** Integrate Angular Material's `MatSnackBar` to provide clear, non-intrusive feedback after creating, updating, or deleting users, and for handling API errors.

5.  **No Test Coverage:** The new backend endpoints and frontend components were created without corresponding automated tests, creating a risk of regressions.
    -   **Enhancement:**
        -   Write `pytest` tests for all new `/api/v1/users` endpoints on the backend.
        -   Write unit tests for the `UserListComponent` and `UserFormComponent` on the frontend.

## Implementation Plan

### 1. Frontend: Security Hardening

-   **Task:** Secure the frontend by properly checking user roles.
-   **Actions:**
    -   Update the `AuthService` to decode the JWT access token.
    -   Implement a method `isSuperuser()` that returns an observable boolean based on the `is_superuser` claim in the token.
    -   Ensure the "Users" sidenav link correctly shows or hides based on the real token data.

### 2. Backend: API Enhancements

-   **Task:** Add the necessary API support for the new frontend features.
-   **Actions:**
    -   The existing `create_user` and `update_user` endpoints are sufficient.
    -   Add a `DELETE /{user_id}` endpoint to `backend/src/api/v1/endpoints/users.py` for deleting users.
    -   Ensure the `update_user` function in `crud_user.py` can correctly handle password updates (i.e., hash the new password if provided).

### 3. Frontend: User Lifecycle Features

-   **Task:** Implement the full create and delete functionality in the `UsersModule`.
-   **Actions:**
    -   **Create:**
        -   Add a "Create User" button to `UserListComponent`.
        -   Update `UsersRoutingModule` to include a `new` route that opens the `UserFormComponent`.
        -   Modify `UserFormComponent` to handle both creating and editing users.
    -   **Delete:**
        -   Add a "Delete" button to the actions column in `UserListComponent`.
        -   Implement the `deleteUser()` method in `UserService` and the component, including a confirmation dialog.
    -   **Password:**
        -   Add a `password` form control to the `UserFormComponent`.

### 4. Frontend: UX & Error Handling

-   **Task:** Integrate user feedback and handle API errors gracefully.
-   **Actions:**
    -   Create a `NotificationService` that wraps `MatSnackBar`.
    -   Inject this service into the user components and call it on success (e.g., "User created successfully").
    -   Implement error handling in the `UserService` or components to catch API errors and display a relevant message using the `NotificationService`.

### 5. Quality: Automated Testing

-   **Task:** Write tests for all new functionality.
-   **Actions:**
    -   **Backend:** In a new `test_users_api.py` file, write tests for all user endpoints (create, read, update, delete, login), including tests for the superuser protection.
    -   **Frontend:**
        -   Write unit tests for `UserListComponent`, mocking the `UserService` and testing the data display.
        -   Write unit tests for `UserFormComponent`, testing form validation and submission.

## Validation

-   All existing and new backend/frontend tests must pass.
-   A regular user cannot see the "Users" link or access `/users` routes.
-   An admin user can create, view, edit, and delete other users.
-   An admin can reset a user's password.
-   Clear success or error notifications are shown after each action.
