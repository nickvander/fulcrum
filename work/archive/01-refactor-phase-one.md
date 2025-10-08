# Task: Refactor and Harden Phase 1 Backend

## Goal

To refactor the existing Phase 1 codebase to a higher standard of quality,
implement foundational security, and establish clear development patterns that
will be used for the rest of the project.

## Critique of Current Code

1.  **Repetitive Code:** The API and schema definitions are highly repetitive,
    violating the DRY (Don't Repeat Yourself) principle.
2.  **Lack of Security:** There are no authentication or authorization
    mechanisms. Passwords are not handled securely.
3.  **Suboptimal Project Structure:** The API routing can be centralized for
    clarity, and the configuration management can be made more robust.
4.  **Inefficient Testing:** The test suite is slower than necessary due to
    inefficient database fixture management.

## Implementation Plan

1.  **Refactor to Repository Pattern:**
    - Implement a generic `CRUDBase` class in `src/crud/base.py`.
    - Create specific repository files (e.g., `src/crud/crud_product.py`) for
      each model.
    - Refactor all API endpoints in `src/api/v1/endpoints/` to use the new
      repository methods, making the API layer thin and clean.

2.  **Centralize API Routing:**
    - The `src/api/v1/api.py` file will be the single point of entry for all v1
      routers.
    - Each endpoint file's `APIRouter` will have its `prefix` and `tags` defined
      there, not in the endpoint file itself.
    - `main.py` will only include the main `api_router`.

3.  **Implement Basic Security:**
    - Create a `src/core/security.py` module.
    - Add `passlib` and `bcrypt` dependencies.
    - Implement `get_password_hash` and `verify_password` functions.
    - Create a `crud_user.py` repository that correctly handles password hashing
      on user creation.
    - Create a `/api/v1/users/` endpoint for creating new users.

4.  **Improve Test Suite:**
    - Refactor `tests/conftest.py` to use session-scoped database fixtures for
      improved performance.
    - Create reusable data fixtures (e.g., `test_product`) to make tests cleaner
      and less repetitive.

5.  **Update `GEMINI.md`:**
    - Add a "Development Principles" section to codify these new patterns as the
      standard for all future development.

## Validation

- All existing and new unit tests must pass after the refactoring.
- The `ruff` linter must pass with no errors.
- The GitHub Actions CI pipeline must pass successfully.
