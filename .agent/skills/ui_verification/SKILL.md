---
name: UI Verification
description:
  Visually test and verify frontend features using browser automation,
  screenshots, and user flow testing.
---

# UI Verification Skill

You are a QA engineer for the Fulcrum project. Your role is to visually verify
UI features, test user flows, and document results using browser automation.

## When to Use This Skill

Use this skill when:

- Verifying a new component or feature looks correct.
- Testing user flows (create product, login, etc.).
- Checking dark/light mode appearance.
- Creating visual documentation or demos.
- Debugging UI issues reported by the user.

---

## Prerequisites

Before running UI tests:

1. **Start the frontend dev server**:

   ```bash
   cd frontend && ng serve
   ```

   Wait for: `Application bundle generation complete.` Default URL:
   `http://localhost:4200`

2. **Start the backend** (if testing API-connected features):
   ```bash
   docker compose up -d
   ```

---

## Browser Testing Workflow

### Step 1: Navigate to Page

Use the browser subagent to open the application:

- Open `http://localhost:4200` for the Angular app
- Navigate to specific routes like `/products`, `/expenses`, `/settings`

### Step 2: Verify Visual Elements

Check for:

- Component renders correctly
- Theme variables applied (colors, spacing, shadows)
- No broken layouts or overflow issues
- Icons and images display properly
- Text is readable and properly localized

### Step 3: Test Interactions

- Click buttons and verify actions
- Fill out forms and submit
- Open dialogs and verify content
- Test dropdown menus and selects
- Verify toast/snackbar notifications

### Step 4: Capture Evidence

- Take screenshots for documentation
- Record browser sessions for demo videos
- Note any visual bugs or issues

---

## Common Test Scenarios

### 1. Component Visual Check

```
Task: Open http://localhost:4200/products
1. Verify the product list table displays
2. Check that the header, filters, and pagination are visible
3. Take a screenshot
```

### 2. Dark Mode Verification

```
Task: Test dark mode appearance
1. Open http://localhost:4200/settings
2. Navigate to the General tab
3. Toggle the "Dark Mode" switch
4. Verify:
   - Background changes to dark (--bg-app: #0f172a)
   - Cards use dark background (--bg-card: #1e293b)
   - Text is light colored (--text-main: #f1f5f9)
5. Navigate to other pages to verify consistency
```

### 3. Form Submission Flow

```
Task: Test product creation
1. Open http://localhost:4200/products
2. Click "Add Product" button
3. Fill in the form:
   - Name: "Test Product"
   - SKU: "TEST-001"
   - Price: 99.99
4. Click Save
5. Verify:
   - Dialog closes
   - Product appears in list
   - Success notification shown
```

### 4. Dialog Testing

```
Task: Verify expense dialog
1. Open http://localhost:4200/expenses
2. Click "Add Expense" button
3. Verify dialog opens with:
   - Proper title (localized)
   - Form fields: Description, Amount, Category, Date
   - Cancel and Save buttons
4. Fill form and submit
5. Verify dialog closes and list updates
```

### 5. Localization Check

```
Task: Verify Spanish translations
1. Open http://localhost:4200/settings
2. Switch language to "Español (MX)"
3. Navigate to Products page
4. Verify:
   - Nav items translated
   - Button labels translated
   - Table headers translated
5. Take screenshots for documentation
```

### 6. Responsive Layout

```
Task: Test mobile layout
1. Open http://localhost:4200/products
2. Resize browser window to mobile width (375px)
3. Verify:
   - Navigation collapses to hamburger menu
   - Table adapts or shows mobile view
   - Buttons are touch-friendly
4. Take screenshot
```

---

## Theme Variables to Verify

When checking visual appearance, verify these CSS variables are applied:

| Variable          | Light Mode | Dark Mode |
| ----------------- | ---------- | --------- |
| `--bg-app`        | #F4F6F8    | #0f172a   |
| `--bg-card`       | #FFFFFF    | #1e293b   |
| `--text-main`     | #2C3E50    | #f1f5f9   |
| `--primary-color` | #2E3A59    | #8fa3d6   |
| `--accent-color`  | #00BFA5    | #00DBBD   |
| `--border-radius` | 12px       | 12px      |

---

## Recording Demos

When creating demo recordings:

1. **Name recordings descriptively**:
   - `product_creation_flow`
   - `dark_mode_toggle`
   - `expense_form_test`

2. **Plan the flow**:
   - Start from a clean state
   - Perform actions at readable pace
   - End on a meaningful screen

3. **Keep recordings focused**:
   - One feature per recording
   - 10-30 seconds ideal

---

## Reporting Issues

When documenting UI bugs:

1. **Screenshot the issue**
2. **Note the conditions**:
   - Browser/viewport size
   - Light or dark mode
   - Language setting
   - Steps to reproduce
3. **Check related CSS**:
   - Component SCSS file
   - Theme variables
   - Global styles

---

## Fulcrum-Specific Pages

| Route           | Page           | Key Elements                 |
| --------------- | -------------- | ---------------------------- |
| `/`             | Dashboard      | Widgets, charts, quick stats |
| `/products`     | Product List   | Table, filters, Add button   |
| `/products/:id` | Product Detail | Form, images, tabs           |
| `/expenses`     | Expense List   | Table, filters, summary      |
| `/suppliers`    | Suppliers      | List, PO management          |
| `/settings`     | Settings       | Tabs: General, Admin, Sync   |
| `/marketing`    | Campaigns      | Quick posts, campaigns list  |

---

## Verification Checklist

After UI testing:

- [ ] Core functionality works as expected
- [ ] Visual appearance matches design
- [ ] Dark mode renders correctly
- [ ] Light mode renders correctly
- [ ] Both languages work (en, es-MX)
- [ ] No console errors
- [ ] Screenshots/recordings saved if needed
