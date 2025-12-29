# User Guide: Settings

The **Settings** tab provides configuration options for your Fulcrum instance,
including marketplace credentials, user management, and application preferences.

## Accessing Settings

Click **Settings** in the left sidebar.

## Settings Sections

### Marketplace Credentials

Configure the **App Credentials** (Client ID/Secret) required to connect to
external marketplaces.

1. Click **Marketplaces** in the Settings menu.
2. For each platform (Amazon, MercadoLibre):
   - Click **Configure**.
   - Enter your **Client ID** and **Client Secret**.
   - Click **Save**.

> **Security**: Credentials are encrypted at rest using AES-256-GCM.

### Connected Accounts

View and manage all connected marketplace accounts:

- See connection status (Active, Expired, Error).
- **Refresh Token**: Click to re-authenticate if a token expires.
- **Disconnect**: Remove an account connection.

### User Management

Administrators can manage user accounts:

1. Click **Users** in the Settings menu.
2. View all users and their roles.
3. Click **+ Add User** to invite a new team member.
4. Click on a user to edit their role or deactivate their account.

### Profile

Update your personal profile:

- **Name**: Display name.
- **Email**: Login email (cannot be changed).
- **Password**: Change your password.

### Inventory Settings

Configure global defaults for inventory alerts:

- **Low Stock Threshold**: The default quantity below which a product is considered "Low Stock" (e.g., 10 units).
  - *Note*: This can be overridden on a per-product basis in the Product Edit page.

### Appearance (Future)

Planned settings for:

- Dark/Light mode toggle.
- Language preferences.
- Dashboard widget customization.

## Security Best Practices

- **Use Strong Passwords**: At least 12 characters with mixed case, numbers, and
  symbols.
- **Rotate Marketplace Credentials**: Periodically regenerate and update your
  Client Secrets.
- **Limit Admin Access**: Only give Admin roles to trusted team members.

---

_Last Updated: December 2025_
