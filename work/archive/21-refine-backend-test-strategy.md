# Task: Phase 5.2 - Refine Backend Test Strategy

## 1. Goal

To correctly implement and solidify the backend testing strategy that separates
fast unit tests from slower, database-dependent integration tests. This will fix
the CI failures, improve the developer experience, and align the testing process
with the project's goal of having rapid feedback for small changes.

## 2. Implementation Strategy

1.  **Commit the Fix:**
    - **Action:** Commit the newly created `backend/tests/test_security.py`
      file.
    - **Benefit:** This immediately fixes the `backend-unit-tests` CI failure by
      providing a valid, non-database test for the runner to execute.

2.  **Simplify Local Testing Scripts:**
    - **Action:** Modify the root `package.json` to remove the
      `test:backend:unit` and `test:backend:db` scripts.
    - **Action:** Create a single `test:backend` script that runs the entire
      backend test suite within Docker.
    - **Action:** Create a new `test:backend:fast` script that runs only the
      non-database tests, intended for quick local checks. The `test:all` script
      will be updated to use the full `test:backend` script.
    - **Benefit:** Provides both a comprehensive "CI-like" test command and a
      rapid feedback command for local development.

3.  **Update Documentation:**
    - **Action:** Update `docs/testing-and-ci.md` to reflect the new
      `test:backend` and `test:backend:fast` commands.
    - **Action:** Clarify the purpose of each command and when it should be
      used.

4.  **Future-Proofing:**
    - **Action:** Add a comment to `backend/tests/conftest.py` explaining why
      `autouse=True` should not be used for session-level fixtures to prevent
      this issue from recurring.
