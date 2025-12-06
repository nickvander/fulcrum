# Session: Audit Log Consolidation & Bootstrap Error Fix

**Date:** 2025-12-05

## Summary of Work Completed

This session focused on resolving a user-reported "Unknown Error" on the Audit
Logs tab and subsequent issues that arose during debugging.

### Issues Identified and Resolved

1.  **Audit Log Consolidation:**
    -   Removed the redundant `/admin/audit-logs` route and component that was
        showing "Unknown Error".
    -   Updated the Sidenav to remove the duplicate "Audit Logs" link.
    -   Preserved the working audit logs accessible via the "Users" section
        (`/users/audit-logs`), protected by `AdminGuard`.
    -   Deleted orphaned files:
        `frontend/src/app/admin/components/audit-logs/*` and
        `frontend/src/app/admin/services/audit-log.service.ts`.

2.  **JIT Compilation Error Fix (Blank Page):**
    -   After removing the audit logs component, a hard refresh revealed a
        previously latent issue causing a blank page.
    -   **Root Cause:** `main.ts` was using `platformBrowser()` (AOT-only) but
        the dev server required the JIT compiler.
    -   **Fix:** Changed `platformBrowser` to `platformBrowserDynamic` in
        `frontend/src/main.ts`.

3.  **Missing `isAdmin()` Method:**
    -   The `Sidenav` component called `authService.isAdmin()`, but this method
        did not exist in `AuthService`.
    -   **Fix:** Implemented the `isAdmin()` method in
        `frontend/src/app/auth/services/auth.ts`. It decodes the JWT to check
        for `user_type === 'admin'` or `is_superuser === true`.

4.  **Circular Dependency in AuthInterceptor:**
    -   The `AuthInterceptor` was injecting `AuthService`, which in turn
        requires `HttpClient`, creating a circular dependency that caused the
        app to hang on startup.
    -   **Fix:** Refactored `AuthInterceptor` to read the JWT directly from
        `localStorage` instead of using `AuthService`.

5.  **`HttpClientModule` Restoration:**
    -   Restored `HttpClientModule` import in `AppModule` for compatibility with
        older Material components that may depend on it.

6.  **Global Error Handler:**
    -   Added a `window.onerror` handler in `main.ts` that displays runtime
        errors directly on the page, preventing future "blank page" scenarios
        from hiding critical error information.

### Files Modified

-   `frontend/src/main.ts` - JIT bootstrap, error handler
-   `frontend/src/app/auth/services/auth.ts` - Added `isAdmin()` method
-   `frontend/src/app/auth/interceptors/auth-interceptor.ts` - Removed circular
    dep
-   `frontend/src/app/app-module.ts` - Restored `HttpClientModule`
-   `frontend/src/app/app-routing-module.ts` - Removed admin audit-logs route
-   `frontend/src/app/core/components/sidenav/sidenav.html` - Removed audit logs
    link

### Files Deleted

-   `frontend/src/app/admin/components/audit-logs/`
-   `frontend/src/app/admin/services/audit-log.service.ts`

### Verification

-   ✅ Dev server starts successfully
-   ✅ Login page loads and functions
-   ✅ Sidenav displays correctly (no audit logs link)
-   ✅ Audit logs accessible via Users section
-   ✅ No console errors on startup
