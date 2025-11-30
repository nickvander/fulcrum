# User Management Guide

This guide details the features and workflows of the User Management system in Fulcrum.

## Overview

The User Management system allows administrators to manage users, roles, and security settings. It includes features for creating users, managing profiles, and enforcing security policies.

## Features

### User Roles
- **Admin**: Full access to all features, including user management and system settings.
- **Employee**: Access to operational features (inventory, orders) but restricted from system settings.
- **Customer**: Limited access to their own profile and orders.

### Creating Users
Administrators can create new users via the "Users" section in the sidebar.
- **Required Fields**: Email, First Name, Last Name, User Type.
- **Optional Fields**: Avatar URL, Employee ID (auto-generated if empty).
- **Security**: Admins can set an initial password and toggle "Force Password Change" to require the user to change it upon first login.

### Force Password Change
To enhance security, administrators can force a user to change their password on their next login.
- **Trigger**:
    - When creating a new user (default is ON for admin-created users).
    - When editing an existing user (toggle "Force Password Change").
    - When an admin resets a user's password.
- **User Flow**:
    1. User logs in with their current (or temporary) password.
    2. System detects the `force_password_change` flag.
    3. User is immediately redirected to the "Change Password" page.
    4. User must enter their current password and a new strong password.
    5. Upon success, the flag is cleared, and the user is redirected to the dashboard.

### Password Policy
Passwords must meet the following criteria:
- Minimum 8 characters.
- At least one uppercase letter.
- At least one lowercase letter.
- At least one number.
- At least one special character.

### Account Management
Users can manage their own profile via the "Account" link in the header.
- **Profile**: Update name and avatar.
- **Security**: Change password (if not forced).

## Technical Details

### Backend
- **Model**: `User` model includes `force_password_change` (boolean).
- **API**:
    - `POST /api/v1/users/`: Create user.
    - `POST /api/v1/users/change-password`: Change password and clear force flag.
    - `GET /api/v1/users/me`: Get current user profile.

### Frontend
- **Components**:
    - `UserList`: List and filter users.
    - `UserForm`: Create/Edit users.
    - `ForcePasswordChangeComponent`: Dedicated page for forced password updates.
- **Security**: `AuthService` checks user status on login and handles redirection.
