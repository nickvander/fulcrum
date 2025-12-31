# Frontend Architecture & UI Guidelines

## Overview

Fulcrum uses a **modern, responsive, mobile-first** architecture built with Angular Material. The interface is designed to adapt seamlessly across Desktop, Tablet, and Mobile form factors, prioritizing data density on desktop and touch-friendliness on mobile.

## Core Services

### ScreenService (`src/app/core/services/screen.service.ts`)

The `ScreenService` is the single source of truth for responsive logic. It exposes Observables that components should subscribe to:

-   `isMobile$`: `< 768px` (Phone)
-   `isTablet$`: `768px - 1023px` (Tablet)
-   `isDesktop$`: `>= 1024px` (Desktop)
-   `deviceType$`: Returns `'mobile' | 'tablet' | 'desktop'`

**Usage:**

```typescript
// Component pattern
constructor(private screen: ScreenService) {
  this.isMobile$ = this.screen.isMobile$;
}
```

## App Shell Layout

The application uses a responsive shell strategy (`app.component.html`):

-   **Desktop**:
    -   **Sidebar**: Permanent, "glassmorphism" style sidebar on the left.
    -   **Header**: Hidden. Navigation and User Profile are integrated into the sidebar.
    -   **Content**: Maximized vertical space (no top navbar).
-   **Mobile/Tablet**:
    -   **Sidebar**: Collapsible Drawer (overlay) triggered by a hamburger menu.
    -   **Header**: Visible top bar containing the branding and hamburger toggle.

## Navigation Patterns

-   **Primary Navigation**: Global routes (Dashboard, Products, Purchasing) live in the Sidenav.
-   **Contextual Navigation**: Content-specific actions (e.g., "Add Product") live in the main view's toolbar.
-   **Dialogs vs Pages**:
    -   **Dialogs**: Used for quick view, simple edits, and maintaining context (e.g., Product Details).
    -   **Dialog History**: Dialogs support internal navigation stacks (e.g., clicking a bundle component opens it in the *same* dialog with a "Back" button).
    -   **Pages**: Used for complex workflows or full reports.

## UI Components & Styling

### Buttons & Actions
-   **Primary**: `mat-flat-button color="primary"` (Solid primary color)
-   **Secondary**: `mat-stroked-button` or `mat-button`
-   **Icons**: Use Google Material Symbols (Rounded or Sharp).

### Data Display
-   **Stat Pills**: Compact, rounded badges for key metrics (Price, Stock) in headers.
    -   *Style*: `background: #F1F5F9; color: #334155; border-radius: 12px;`
-   **Tables**: Use `mat-table` for dense data.
    -   **Mobile**: Tables automatically hide non-essential columns or switch to card view (via `*ngIf` logic based on `ScreenService`).

## Branding

-   **Logo**: "Fulcrum" text with a Triangle (`change_history`) icon representing the pivot point.
-   **Colors**:
    -   Primary: Deep Slate / Indigo `#3f51b5` (or custom theme variable).
    -   Accent: Teal / Cyan.
