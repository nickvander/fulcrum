# Task: Phase 6.1 - Refine CI Workflows & Documentation

## 1. Goal

To refine the CI/CD pipeline by disabling the failing documentation deployment for private repositories, while retaining the build validation. Additionally, to improve the organization of the GitHub Actions UI for better clarity.

## 2. Implementation Strategy

1.  **Disable Docs Deployment:**
    -   **Action:** Modify the `.github/workflows/deploy-docs.yml` file. Comment out the `peaceiris/actions-gh-pages` step.
    -   **Action:** Add a comment explaining that the step is disabled for private repositories and how to re-enable it.
    -   **Benefit:** Fixes the CI failure while keeping the essential documentation build check in place.

2.  **Reorganize Workflows with Naming Conventions:**
    -   **Action:** Rename the workflow files using a prefix-based naming scheme (e.g., `ci-lint.yml`, `backend-tests.yml`, `docs-build.yml`) to group them logically in the GitHub Actions sidebar.
    -   **Benefit:** Makes the CI/CD pipeline easier to navigate and understand at a glance.
