# Missing Items & Known Issues

## High Priority

### Frontend Refactor & Localization ✅ COMPLETE

- [x] Add language selector (English, Español México) to Settings
- [x] Expand translation files to cover entire UI
- [x] Apply translations to all module templates
- [x] Standardize common translation keys
- [x] Automate i18n validation in Git hooks and CI

### Infinite Scroll Enhancement (Paused)

- [ ] Fix grid view infinite scroll in Products page
- [ ] Integrate infinite scroll toggle into pagination controls
- [ ] Update default page size from 10 to 25 across all lists
- [ ] Apply infinite scroll to all list views (suppliers, POs, expenses,
      marketing)

## Backlog

### Frontend Testing

- [ ] `UserBulkImportDialogComponent` tests disabled due to 120s timeout
- [ ] Product form tests intermittently flaky

### Code Modularity

- [ ] Create shared MaterialModule for consolidated imports
- [ ] Split ProductList into smaller focused components
- [ ] Extract reusable empty-state and loading-spinner components

### Documentation

- [ ] Update user guide with infinite scroll feature documentation
- [x] Document localization/translation workflow
