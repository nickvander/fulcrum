# Frontend Refactoring & Modernization Plan

## Goal

To modernize the `frontend` codebase by establishing a robust design system,
ensuring logical code organization, and preparing for global scale. We will
create a unique "Calm & Professional" personality for the app and optimize for
three distinct form factors: PC, Tablet (POS), and Phone.

## Use of Artifacts

This document is the source of truth for the high-level plan. Detailed progress
is tracked in `task.md` (ephemeral artifact) and the daily `PROGRESS.md`.

## User Review Required

> [!IMPORTANT] **Transloco Installation:** `@ngneat/transloco` has been added to
> the project. **Breaking Style Changes:** Global styles have been updated to
> the new "Calm & Professional" palette.

## Phases

### Phase 1: Design System & Foundation (Completed)

- [x] Create `ThemeModule` or centralize theme SCSS.
- [x] **Define Unique Palette**: "Calm & Professional" (Deep Slate, Soft Blue,
      Crisp White).
- [x] **Responsive Strategy**: Defined breakpoints in SCSS.
- [x] Create reusable SCSS mixins/classes: `kpi-card`, `status-badge`,
      `filter-toolbar`, `touch-target`.
- [x] Install and configure `transloco`.

### Phase 2: Refactoring & Logical Organization

- [x] **Audit `src/app`**: Review current structure.
- [x] **Separation of Concerns**: Moved loose models to feature modules
      (`expenses`).
- [x] **Feature Modules**: Confirmed modular structure looks correct.

### Phase 3: Component Modernization (Unification)

- [x] **Marketing**: Update styles to use new global mixins (match new palette).
- [x] **Users**: Refactor `UserList` to use new badges and filters.
- [/] **Products (Major Redesign)**:
  - [x] Make "List View" the default.
  - [x] **PC View**: High density, sortable columns.
  - [ ] **Tablet View**: "POS Mode" - larger touch targets, simplified columns,
        management actions (Adjust Stock).
  - [ ] **Phone View**: "On-the-go Mode" - minimal info, swipe actions, pure
        mobile optimization.
- [ ] **Purchase Orders**: Update widgets to align with `kpi-card`.

### Phase 4: Multilingual Execution

- [ ] Set up translation files (`en.json`, `es-MX.json`).
- [ ] Replace hardcoded strings in `UserList`, `Marketing`, and `Products` with
      Transloco pipes.
- [ ] Document i18n workflow in `docs/guides/i18n.md`.

## Verification Plan

### Automated Tests

- `ng test`: Ensure regressions are caught.

### Manual Verification

1.  **Visual & Palette**: Check the new "Calm" look and feel.
2.  **Responsiveness**:
    - Open app on Desktop -> check List View density.
    - Open DevTools Device Mode (Tablet) -> check touch targets.
    - Open DevTools Device Mode (Mobile) -> check simplified layout.
3.  **i18n**: Verify strings are externalized.
