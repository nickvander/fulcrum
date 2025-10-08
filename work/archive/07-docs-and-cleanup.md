# Task: Documentation Cleanup & Standardization

## Goal

To improve the quality and consistency of the project's documentation and remove
all remnants of the legacy Karma testing framework.

## Implementation Plan

1.  **Remove Legacy Test Configuration:**
    - Deleted the `karma.conf.js` file.
    - Uninstalled all remaining Karma, Jasmine, and Playwright dependencies from
      the frontend's `package.json`.
    - Removed the temporary `web-test-runner.config.mjs` file to ensure a clean
      slate for the future implementation.

2.  **Standardize Development Principles:**
    - Updated `GEMINI.md` to include a new "Development Principles" section,
      codifying the project's standards for frontend testing (Web Test Runner)
      and Markdown formatting (Prettier).

3.  **Update and Format Documentation:**
    - Updated the main `README.md`, `frontend/README.md`, and all documents in
      the `docs/` directory to reflect the current state of the project and the
      new testing strategy.
    - Corrected inconsistent formatting in all Markdown files, ensuring that all
      code blocks are properly formatted with surrounding newlines for
      readability.
    - Ran `npm run format:md` to apply consistent styling across all
      documentation.
