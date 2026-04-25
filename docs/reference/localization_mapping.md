# Backend to Frontend Localization Mapping

This document serves as a reference for mapping backend enum values and
constants to their corresponding localization keys in the frontend. This ensures
consistent translation across the application.

## Conventions

- Backend values (typically snake_case or lowercase strings) are mapped
  dynamically in frontend templates using the Transloco pipe:
  `{{ t('module.status.' + value) }}`.
- New status values added to the backend **MUST** have a corresponding key added
  to `frontend/src/assets/i18n/en.json` and `es-MX.json`.

## Purchase Orders

**Translation Key Prefix:** `purchaseOrders.`

| Backend Status       | Translation Key                    | English Value      |
| :------------------- | :--------------------------------- | :----------------- |
| `draft`              | `purchaseOrders.draft`             | Draft              |
| `pending`            | `purchaseOrders.pending`           | Pending            |
| `ordered`            | `purchaseOrders.ordered`           | Ordered            |
| `shipped`            | `purchaseOrders.shipped`           | Shipped            |
| `received`           | `purchaseOrders.received`          | Received           |
| `partially_received` | `purchaseOrders.partiallyReceived` | Partially Received |
| `cancelled`          | `purchaseOrders.cancelled`         | Cancelled          |

## Marketing Campaigns

**Translation Key Prefix:** `marketing.status.`

| Backend Status | Translation Key              | English Value |
| :------------- | :--------------------------- | :------------ |
| `active`       | `marketing.status.active`    | Active        |
| `draft`        | `marketing.status.draft`     | Draft         |
| `scheduled`    | `marketing.status.scheduled` | Scheduled     |
| `completed`    | `marketing.status.completed` | Completed     |

## Quick Posts

**Translation Key Prefix:** `marketing.status.`

| Backend Status | Translation Key              | English Value |
| :------------- | :--------------------------- | :------------ |
| `published`    | `marketing.status.published` | Published     |
| `failed`       | `marketing.status.failed`    | Failed        |
| `draft`        | `marketing.status.draft`     | Draft         |

## Products

### Stock Status (Computed)

**Translation Key Prefix:** `products.stockStatus.`

| Condition              | Translation Key                   | English Value |
| :--------------------- | :-------------------------------- | :------------ |
| Stock > Low Threshold  | `products.stockStatus.inStock`    | In Stock      |
| Stock == 0             | `products.stockStatus.outOfStock` | Out of Stock  |
| Stock <= Low Threshold | `products.stockStatus.lowStock`   | Low Stock     |

## Translation Validation

To maintain consistency and ensure all keys are translated, the project includes
an automated validation script: `check_i18n_consistency.py`.

### Automated Checks

This script is automatically run during:

- **Git pre-commit hook**: Prevents committing code with missing or
  non-standardized translations.
- **Git pre-push hook**: Final verification before pushing to the repository.
- **CI Pipeline**: Automated check in GitHub Actions for all pull requests.

### Manual Usage

You can run the script manually from the root directory:

```bash
python3 check_i18n_consistency.py frontend/src/assets/i18n/en.json
```

The script will:

1. Verify that all keys in `en.json` exist in other language files (e.g.,
   `es-MX.json`).
2. Identify potential standardization candidates for the `common` section.
3. Detect duplicate keys.
