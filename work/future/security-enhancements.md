# Security Enhancements

This document outlines future security enhancements for the Fulcrum platform.

## Force Password Change on First Login

**Objective:** Require users to change their password upon their first successful login, especially after being created via bulk import or admin creation.

### Proposed Implementation

1.  **Database Schema Changes:**
    *   Add `must_change_password` (Boolean, default=False) column to the `users` table.
    *   Set default to `True` for users created via Bulk Import or Admin Create User.

2.  **Backend Logic:**
    *   Update `login_access_token` endpoint:
        *   Check `user.must_change_password` flag.
        *   If `True`, return a specific response code or flag indicating a password change is required (or allow login but restrict access).
        *   Alternatively, allow login but add a claim to the JWT (e.g., `scope: "password_change_required"`) that restricts access to only the password change endpoint.
    *   Update `update_user_profile` (or a dedicated `change_password` endpoint) to set `must_change_password` to `False` upon successful password update.

3.  **Frontend Logic:**
    *   Intercept login response.
    *   If password change is required, redirect user to a "Change Password" screen.
    *   Prevent navigation to other parts of the app until password is changed (using Route Guards).

4.  **User Experience:**
    *   Clear messaging explaining why the password change is required.
    *   Validation for the new password (complexity requirements).
