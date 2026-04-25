# Progress Log

## Status

- [/] **Phase 10**: Frontend Evolution Sprint (In Progress)
  - See `70-frontend-evolution-sprint.md` for full plan

## Log

- **2025-12-31**: Implemented Integrations & Data Export (Parts 2-3)
  - Created `integrations.py` backend with export (CSV/JSON) and Sheets sync
    APIs.
  - Added `ApiKey` model and management endpoints (create/list/revoke).
  - Created `Code.gs` Apps Script with secure `PropertiesService` storage and
    setup dialog.
  - Added API Keys UI and Data Export UI to Settings page.
  - Fixed CRUD import issue (`product` vs `crud_product`).
  - Updated `google-sheets-integration.md` with ngrok local testing, Add-on
    deployment guide, and API Key design philosophy.

- **2025-12-30**: Created Phase 10 Frontend Evolution Sprint plan.
  - Researched project structure: 12 feature modules, established design system.
  - Identified key opportunities: branding refresh, data export, UX
    improvements.
  - Drafted comprehensive plan covering logo, exports, Google Sheets, and UX.
  - Completed branding tasks: logo, PWA icons, manifest, index.html updates.
  - **Completed Part 4: Mobile Polish & UX**:
    - Implemented `ScreenService` for unified responsive logic.
    - Redesigned App Shell: Permanent desktop sidebar, mobile drawer.
    - Polished Product Details: Dialog history, condensed layout, mobile grid.
    - Updated Navigation: Grouped sidebar menu, user profile footer.
    - Added `docs/guides/frontend-architecture.md`.
    - **Post-Launch Polish**:
      - Fixed Product List overflow (10th item hidden).
      - Fixed Supplier Table sorting (async data loading issue).
      - Added Marketing Campaign Table sorting.

- **2025-12-29**: Started Phase 1 of Frontend Refactoring & Modernization.
  - Defined "Calm & Professional" design palette (Deep Slate / Soft Teal).
  - Created global SCSS mixins for Cards, Badges, and Filters.
  - Installed `@ngneat/transloco` for multilingual support.
