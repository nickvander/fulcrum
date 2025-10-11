# Task: Resolve Persistent Product Module Bugs

## Goal

To diagnose and definitively resolve the remaining bugs that are preventing the product creation and ingestion workflows from functioning correctly. This plan will serve as the primary focus for the next development session.

## Summary of Lingering Issues

Despite numerous fixes and passing tests, the application is still failing in a real-world scenario. The core issues are:

1.  **Backend `500 Internal Server Error`:** When creating a product, the backend still throws a `relation "product_custom_fields" does not exist` error. This indicates that even after manual intervention, the database migrations are not being applied reliably on application startup.
2.  **Frontend `ECONNRESET` Error:** The frontend is experiencing `Http failure response` and `ECONNRESET` errors when communicating with the backend. This suggests a problem with the proxy configuration or the backend server crashing.
3.  **Frontend `[Object Object]` Error:** The photo ingestion workflow continues to display `[Object Object]` in the form, suggesting a data handling issue between the ingestion component and the product form.
4.  **Confusing UX:** The "Upload Images" button is disabled on product creation, which is not intuitive.

## Retrospective: What Has Been Tried

-   **Database:** We have tried running `docker compose exec backend alembic upgrade head` multiple times. We have also completely destroyed and rebuilt the database volume. These manual steps have not been a reliable solution.
-   **API Routing:** We have corrected various import paths and router configurations to resolve `404` errors.
-   **Photo Ingestion:** We refactored the `capturePhoto` method in `product-ingestion.ts` to use a pure RxJS pipeline, which should have fixed the data passing issue.

## New Implementation Plan for Next Session

### 1. **Automate Database Migrations on Startup**

-   **Hypothesis:** Manually running migrations is unreliable. The application's API container must wait for the database to be healthy and then run migrations *before* starting the web server.
-   **Action:**
    1.  Modify the `command` for the `backend` service in `docker-compose.yml`.
    2.  Instead of directly calling `uvicorn`, we will use the existing `migrate.sh` script as the entrypoint. This script will be modified to wait for the database and then run `alembic upgrade head` before executing the `uvicorn` command.
    3.  This will guarantee that the database is always up-to-date when the application starts.

### 2. **Diagnose and Fix Frontend Proxy & Backend Stability**

-   **Hypothesis:** The `ECONNRESET` error is caused by either the Angular proxy failing or the backend container crashing and restarting.
-   **Action:**
    1.  Review the `proxy.conf.json` file in the `frontend` directory to ensure it is correctly configured.
    2.  Add more detailed logging to the backend's startup process to see if it is crashing silently.
    3.  Monitor the Docker container logs (`docker compose logs -f backend`) during frontend interaction to catch any crashes.

### 3. **Diagnose and Fix Photo Ingestion**

-   **Hypothesis:** The data being passed in the navigation state is still not in the expected format, despite the RxJS refactor.
-   **Action:**
    1.  Add `console.log` statements in `product-ingestion.ts` immediately before the `router.navigate` call to inspect the `productData` object.
    2.  Add `console.log` statements in the `ngOnInit` of `product-form.ts` to inspect the `productData` received from the navigation state.
    3.  This will give us a clear picture of what is being sent versus what is being received, allowing us to pinpoint the exact source of the `[Object Object]` error.

### 4. **Improve Product Creation UX**

-   **Hypothesis:** Redirecting the user after creating a product is a jarring experience.
-   **Action:**
    1.  Refactor the `onSubmit` method in `product-form.ts`.
    2.  After a successful product creation, instead of navigating away, the component will simply transition from "create mode" to "edit mode" in place.
    3.  This involves setting `this.isEditMode = true`, updating the URL with the new product ID using the `Router` service, and enabling the "Upload Images" section. This creates a seamless workflow for the user.
