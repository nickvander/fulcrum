# Google Sheets Integration Guide

Fulcrum provides **bidirectional sync** with Google Sheets, allowing you to:

- **Pull** inventory, products, and suppliers from Fulcrum into a Sheet
- **Push** edits made in the Sheet back to Fulcrum

This integration is completely modular—your Fulcrum app works 100% without it.

## Prerequisites

- A running Fulcrum backend (`http://localhost:8000` for local development)
- A Google account with access to Google Sheets
- A Fulcrum API Key (generated from Settings)

---

## Step 1: Generate an API Key in Fulcrum

1. Log into Fulcrum and go to **Settings**
2. Scroll down to the **Integrations & Data** section
3. In the **API Keys** card, enter a name like "Google Sheets" and click
   **Generate Key**
4. **Copy the key immediately** — you won't be able to see it again!
5. Store the key securely (you'll need it for Google Sheets)

> [!CAUTION] API keys provide full access to your account. Never share them or
> commit them to version control.

---

## Step 2: Create Your Google Sheet

1. Go to [Google Sheets](https://sheets.google.com) and create a new
   spreadsheet
2. Name it something like "Fulcrum Inventory Sync"

---

## Step 3: Add the Fulcrum Apps Script

1. In your Sheet, go to **Extensions > Apps Script**
2. Delete any existing code in the editor
3. Copy the contents of `scripts/google-sheets-addon/Code.gs` from the Fulcrum
   repository
4. Paste it into the Apps Script editor
5. **Save** the project (Ctrl+S or Cmd+S)
6. Close the Apps Script editor and **refresh** your Google Sheet

---

## Step 4: Configure the Connection

1. After refreshing, you should see a new **⚙️ Fulcrum** menu in the menu bar
2. Click **⚙️ Fulcrum > 🔧 Setup Connection**
3. Enter your **API URL** (e.g., `http://localhost:8000/api/v1` for local dev)
4. Paste your **API Key** from Step 1
5. Click **Save & Connect**

---

## Testing with a Local VM / Development Server

If you're running Fulcrum on a local VM (e.g., `localhost:8000`), Google Sheets
**cannot directly reach it** because Apps Script runs on Google's servers.

### Option A: Use ngrok (Recommended for Testing)

[ngrok](https://ngrok.com/) creates a secure tunnel from the internet to your
local server.

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/download

# Start a tunnel to your backend
ngrok http 8000
```

You'll get a public URL like `https://abc123.ngrok.io`. Use this as your
**API URL** in the Apps Script setup dialog:

```
https://abc123.ngrok.io/api/v1
```

### Option B: Deploy to a Cloud Server

For persistent testing, deploy your Fulcrum backend to a cloud provider
(Railway, Render, AWS, etc.) and use that public URL.

### Option C: Use a VPN with Static IP

If your VM has a public IP or is accessible via VPN, use that IP address
directly in the API URL.

## Using the Integration

### Pulling Data (Fulcrum → Sheets)

| Menu Item         | What It Does                                                   |
| ----------------- | -------------------------------------------------------------- |
| 🔄 Pull Products  | Fetches all products and creates/updates the "Products" sheet  |
| 📦 Pull Inventory | Fetches stock levels into the "Inventory" sheet                |
| 🏭 Pull Suppliers | Fetches suppliers into the "Suppliers" sheet                   |

Each pull operation:

- Creates the sheet if it doesn't exist
- Clears existing data and replaces with fresh data
- Auto-resizes columns for readability

### Pushing Changes (Sheets → Fulcrum)

> [!IMPORTANT]
> Changes pushed from Google Sheets are **staged for review** — they are NOT
> applied immediately. You must approve them in the Fulcrum app.

1. Make edits in the **Products** sheet (e.g., update cost price or resale
   price)
2. Click **⚙️ Fulcrum > ⬆️ Push Changes to Fulcrum**
3. A confirmation dialog shows how many changes will be submitted
4. Click **Yes** to submit the changes for review
5. A success dialog directs you to approve changes in Fulcrum

**Approving Changes in Fulcrum:**

1. Go to **Settings > Integrations** in Fulcrum
2. Look for the **Pending Sync Changes** section
3. A badge shows the number of pending changes
4. Click **Review** to open the approval dialog
5. Review each change with the "Old Value → New Value" diff
6. Select changes to approve or reject
7. Click **Approve Selected** or **Reject Selected**

**Currently supported push fields:**

- `cost_price`
- `resale_price`
- `name`

> [!NOTE] Stock quantity sync is logged but requires the full inventory
> adjustment workflow on the backend. This is a planned enhancement.

## Change Audit Trail

All changes to products — whether from Sheets imports or direct edits in
Fulcrum — are logged with source attribution.

**View the Change Log:**

1. Go to **Settings > Integrations** in Fulcrum
2. Click **View Log** in the Change Log section
3. Filter by source: `Sheets Import`, `Direct Edit`, or `API`

Each log entry shows:

- Entity and field changed
- Old value → New value
- Source (how the change was made)
- Who made the change
- When it was changed

## API Endpoints Reference

The Apps Script uses these Fulcrum API endpoints:

| Endpoint                                 | Method | Purpose                              |
| ---------------------------------------- | ------ | ------------------------------------ |
| `/api/v1/integrations/sheets/sync-pull`  | POST   | Pull data from Fulcrum               |
| `/api/v1/integrations/sheets/sync-push`  | POST   | Stage changes for review             |
| `/api/v1/integrations/sync/pending`      | GET    | List pending change batches          |
| `/api/v1/integrations/sync/pending/count`| GET    | Get pending change count             |
| `/api/v1/integrations/sync/approve`      | POST   | Approve or reject pending changes    |
| `/api/v1/integrations/change-logs`       | GET    | View change audit trail              |
| `/api/v1/integrations/export/products`   | GET    | Export products (CSV/JSON)           |
| `/api/v1/integrations/export/inventory`  | GET    | Export inventory levels              |
| `/api/v1/integrations/export/suppliers`  | GET    | Export suppliers                     |

### Sync Pull Request

```json
{
  "entity": "products" | "inventory" | "suppliers",
  "last_sync_timestamp": "2024-01-01T00:00:00Z" // Optional
}
```

### Sync Push Request

```json
{
  "entity": "products",
  "changes": [
    { "id": 123, "field": "cost_price", "new_value": 15.99 },
    { "id": 456, "field": "resale_price", "new_value": 29.99 }
  ]
}
```

## Troubleshooting

### "API Error 401: Unauthorized"

Your API key is invalid or expired. Generate a new JWT token from Fulcrum.

### "API Error 404: Not Found"

Check that your `FULCRUM_API_URL` is correct and includes `/api/v1`.

### Menu Not Appearing

1. Make sure you saved the Apps Script
2. Refresh the Google Sheet
3. Check the Apps Script editor for syntax errors

### View Logs

Go to **⚙️ Fulcrum > Settings > View Sync Log** to see recent activity.

## Security Considerations

- **Never share** your Google Sheet if it contains your API key in the script
- For team use, deploy the script as an Add-on with OAuth
- Use short-lived JWT tokens and refresh them regularly

---

## Publishing as a Google Workspace Add-on (Advanced)

For a **cleaner, installable integration**, you can publish the Apps Script as a
Google Workspace Add-on. This allows users to install it from the Google
Workspace Marketplace or share it as a private add-on.

### Step 1: Prepare the Script

1. In the Apps Script editor, click **Project Settings** (gear icon)
2. Note your **Script ID** (you'll need this for testing)
3. Add a description and required OAuth scopes in the manifest

### Step 2: Create an Apps Script Manifest

Create or edit `appsscript.json` with the following:

```json
{
  "timeZone": "America/Los_Angeles",
  "dependencies": {},
  "exceptionLogging": "STACKDRIVER",
  "runtimeVersion": "V8",
  "oauthScopes": [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/script.external_request"
  ],
  "addOns": {
    "common": {
      "name": "Fulcrum Connect",
      "logoUrl": "https://your-domain.com/fulcrum-icon.png",
      "useLocaleFromApp": true,
      "homepageTrigger": {
        "runFunction": "onOpen"
      }
    },
    "sheets": {
      "macros": []
    }
  }
}
```

### Step 3: Deploy as an Add-on

1. In the Apps Script editor, click **Deploy > Test deployments**
2. Click **Install** to test the add-on in your own account
3. Once tested, click **Deploy > New deployment**
4. Select **Add-on** as the deployment type
5. Fill in the description and version notes
6. Click **Deploy**

### Step 4: Share Privately (Recommended for Teams)

For private/internal use without public Marketplace listing:

1. Go to your [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable the **Google Workspace Marketplace SDK**
4. Configure the add-on for **Private** visibility
5. Share the installation link with your team

### Step 5: Publish to Marketplace (Optional)

For public distribution:

1. Complete the [Google Workspace Marketplace requirements](https://developers.google.com/workspace/marketplace/how-to-publish)
2. Submit for review (Google reviews all public add-ons)
3. Once approved, users can install from the Marketplace

> [!NOTE] Publishing to the public Marketplace requires a Google Cloud project,
> OAuth consent screen verification, and compliance with Google's policies.

---

## API Keys: Design Philosophy

**Current Design: Per-User API Keys**

API keys in Fulcrum are tied to individual **users**, not the store as a whole.
This is the recommended approach for several reasons:

| Aspect        | Per-User Keys                    | Per-Store Keys           |
| ------------- | -------------------------------- | ------------------------ |
| Audit Trail   | ✅ Know who made each request    | ❌ No user attribution   |
| Revocation    | ✅ Revoke one user without       | ❌ Affects everyone      |
|               | affecting others                 |                          |
| Permissions   | ✅ Can scope keys to user roles  | ❌ All-or-nothing access |
| Best Practice | ✅ Industry standard             | ❌ Less secure           |

**How It Works:**

1. Each user generates their own API key from Settings
2. The key is hashed and stored with a reference to the user ID
3. When the key is used, requests are authenticated as that user
4. Audit logs reflect the key owner's actions

---

## Future Enhancements

- [ ] Scheduled auto-sync (time-driven triggers)
- [ ] Conflict resolution for concurrent edits
- [ ] Full inventory adjustment support (stock sync)
- [ ] OAuth-based authentication flow (for Add-on)
