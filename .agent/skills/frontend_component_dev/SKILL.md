---
name: Frontend Component Development
description:
  Create new Angular components following Fulcrum's patterns (Standalone,
  Transloco, Angular Material, Theme Variables).
---

# Frontend Component Development Skill

You are a frontend developer for the Fulcrum project. Your role is to create new
Angular components that follow the project's established patterns and
conventions.

## When to Use This Skill

Use this skill when the user wants to:

- Create a new Angular component.
- Add a new dialog, page, or widget.
- Extend an existing module with new functionality.

---

## Pre-Flight Checks

Before creating a component, gather:

1. **Component Name**: PascalCase (e.g., `ProductScanner`).
2. **Component Type**: `page`, `dialog`, `widget`, or `shared`.
3. **Parent Module Path**: Where it lives (e.g., `frontend/src/app/products/`).
4. **Translation Keys**: What text needs localization.

---

## File Structure

**Standard Components:**

```
frontend/src/app/<module>/components/<feature-name>/
├── <feature-name>.component.ts
├── <feature-name>.component.html
├── <feature-name>.component.scss
└── <feature-name>.component.spec.ts
```

**Dialogs (note: some use `.ts` only, others use `.component.ts`):**

```
frontend/src/app/<module>/components/<feature>-dialog/
├── <feature>-dialog.ts           # OR <feature>-dialog.component.ts
├── <feature>-dialog.html
├── <feature>-dialog.scss
└── <feature>-dialog.spec.ts
```

---

## TypeScript Template

```typescript
import { Component, Inject, OnInit } from "@angular/core";
import { CommonModule } from "@angular/common";
import {
  FormBuilder,
  FormGroup,
  Validators,
  ReactiveFormsModule,
} from "@angular/forms";
import { TranslocoModule, TranslocoService } from "@ngneat/transloco";

// Material Imports - import individually, NOT MaterialModule in feature components
import {
  MatDialogRef,
  MAT_DIALOG_DATA,
  MatDialogModule,
} from "@angular/material/dialog";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatSelectModule } from "@angular/material/select";
import { MatProgressSpinnerModule } from "@angular/material/progress-spinner";

// Shared Components (use when applicable)
// import { LoadingSpinnerComponent } from '@shared/components/loading-spinner/loading-spinner.component';
// import { EmptyStateComponent } from '@shared/components/empty-state/empty-state.component';
// import { ConfirmationDialog } from '@shared/components/confirmation-dialog/confirmation-dialog';

@Component({
  selector: "app-feature-name",
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TranslocoModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSelectModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: "./feature-name.component.html",
  styleUrl: "./feature-name.component.scss", // Note: styleUrl (singular) in newer Angular
})
export class FeatureNameComponent implements OnInit {
  // Inject using constructor (project pattern)
  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<FeatureNameComponent>,
    @Inject(MAT_DIALOG_DATA) public data: FeatureDialogData,
    private translocoService: TranslocoService,
  ) {
    this.currentLang = this.translocoService.getActiveLang();
  }

  currentLang: string;

  ngOnInit(): void {
    // Initialization logic
  }

  onSubmit(): void {
    this.dialogRef.close(/* result */);
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}

export interface FeatureDialogData {
  itemId?: number;
  mode?: "create" | "edit";
}
```

---

## HTML Template

Use `mat-dialog-*` directives for dialogs:

```html
<ng-container *transloco="let t">
  <h2 mat-dialog-title>{{ t('module.dialogTitle') }}</h2>

  <mat-dialog-content>
    <form [formGroup]="form">
      <mat-form-field appearance="outline">
        <mat-label>{{ t('module.fieldLabel') }}</mat-label>
        <input matInput formControlName="fieldName" />
      </mat-form-field>
    </form>

    <!-- Loading State -->
    <div *ngIf="isLoading" class="loading-container">
      <mat-spinner diameter="40"></mat-spinner>
    </div>

    <!-- Empty State (use shared component) -->
    <app-empty-state
      *ngIf="!isLoading && items.length === 0"
      icon="inbox"
      [title]="t('common.noData')"
      [description]="t('module.emptyDescription')"
    >
    </app-empty-state>
  </mat-dialog-content>

  <mat-dialog-actions align="end">
    <button mat-button (click)="onCancel()">{{ t('common.cancel') }}</button>
    <button
      mat-flat-button
      color="primary"
      (click)="onSubmit()"
      [disabled]="!form.valid"
    >
      {{ t('common.save') }}
    </button>
  </mat-dialog-actions>
</ng-container>
```

---

## SCSS Template - Use Theme Variables!

**CRITICAL**: Always use CSS custom properties from `theme/variables.scss`:

```scss
@use "theme/variables";
@use "theme/mixins";

.feature-container {
  padding: var(--card-padding);
  background-color: var(--bg-card);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow-md);
}

// Loading overlay pattern
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 32px;
}

// Status chips - use semantic colors
.status-chip {
  &.success {
    background-color: var(--success-bg);
    color: var(--success-color);
  }
  &.warning {
    background-color: var(--warning-bg);
    color: var(--warning-color);
  }
  &.error {
    background-color: var(--error-bg);
    color: var(--error-color);
  }
}

// Form sections
.form-section {
  background: var(--bg-card);
  padding: var(--card-padding);
  border-radius: var(--border-radius);
  margin-bottom: calc(var(--spacing-unit) * 2);

  h3 {
    color: var(--text-secondary);
    margin-bottom: calc(var(--spacing-unit) * 2);
  }
}

// Drag-and-drop zone (common pattern)
.drop-zone {
  border: 2px dashed var(--border-color);
  border-radius: var(--border-radius);
  padding: 32px;
  text-align: center;
  transition: all 0.2s ease;

  &.dragging {
    border-color: var(--accent-color);
    background-color: var(--bg-hover);
  }
}
```

### Available Theme Variables

| Variable                          | Purpose                               |
| --------------------------------- | ------------------------------------- |
| `--primary-color`                 | Primary brand color (Deep Slate Blue) |
| `--accent-color`                  | Action/accent color (Soft Teal)       |
| `--success-color`, `--success-bg` | Success states                        |
| `--warning-color`, `--warning-bg` | Warning states                        |
| `--error-color`, `--error-bg`     | Error states                          |
| `--bg-app`                        | App background                        |
| `--bg-card`                       | Card/dialog background                |
| `--bg-hover`                      | Hover state                           |
| `--text-main`                     | Primary text                          |
| `--text-secondary`                | Secondary/muted text                  |
| `--text-hint`                     | Placeholder text                      |
| `--border-color`                  | Borders                               |
| `--border-radius`                 | Standard border radius (12px)         |
| `--card-padding`                  | Standard card padding (24px)          |
| `--spacing-unit`                  | Base spacing (8px)                    |
| `--shadow-sm/md/lg`               | Shadows                               |

---

## Shared Components to Reuse

| Component                 | Location                                 | Purpose                     |
| ------------------------- | ---------------------------------------- | --------------------------- |
| `ConfirmationDialog`      | `shared/components/confirmation-dialog/` | Yes/No confirmation dialogs |
| `LoadingSpinnerComponent` | `shared/components/loading-spinner/`     | Loading states              |
| `EmptyStateComponent`     | `shared/components/empty-state/`         | Empty list states           |
| `ImageDialogComponent`    | `shared/components/image-dialog/`        | Image preview               |
| `AiSearchBarComponent`    | `shared/components/ai-search-bar/`       | AI-powered search           |

**Using ConfirmationDialog:**

```typescript
import { ConfirmationDialog, ConfirmationDialogData } from '@shared/components/confirmation-dialog/confirmation-dialog';

// In component
openConfirmation(): void {
  const dialogRef = this.dialog.open(ConfirmationDialog, {
    data: {
      title: this.t('common.confirmDelete'),
      message: this.t('module.deleteMessage')
    } as ConfirmationDialogData
  });

  dialogRef.afterClosed().subscribe(confirmed => {
    if (confirmed) {
      this.delete();
    }
  });
}
```

---

## Test Template (Web Test Runner)

```typescript
import { expect } from "@esm-bundle/chai";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { getTranslocoModule } from "../../../testing/transloco-testing.module";

import { FeatureDialogComponent } from "./feature-dialog.component";

describe("FeatureDialogComponent", () => {
  let component: FeatureDialogComponent;
  let fixture: ComponentFixture<FeatureDialogComponent>;

  const mockDialogRef = {
    close: () => {},
  };

  const mockDialogData = {
    itemId: 1,
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        FeatureDialogComponent,
        NoopAnimationsModule,
        getTranslocoModule(),
      ],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: mockDialogData },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(FeatureDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).to.exist;
  });

  it("should close dialog on cancel", () => {
    const closeSpy = sinon.spy(mockDialogRef, "close");
    component.onCancel();
    expect(closeSpy.calledOnce).to.be.true;
  });
});
```

---

## Localization Checklist

**ALWAYS** add translations to both files:

1. `frontend/src/assets/i18n/en.json`
2. `frontend/src/assets/i18n/es-MX.json`

**Key Naming Convention:**

- Module-scoped: `products.dialogTitle`, `expenses.addNew`
- Common actions: `common.save`, `common.cancel`, `common.delete`,
  `common.loading`
- Navigation: `nav.products`, `nav.dashboard`

---

## Verification Steps

After creating the component:

1. **Build Check**: `cd frontend && ng build`
2. **Lint Check**: `cd frontend && ng lint`
3. **Test Check**: `npm test --prefix frontend`
4. **Visual Check**: `cd frontend && ng serve`
5. **Dark Mode Check**: Toggle dark mode in Settings to verify theme variables
   work
6. **Language Check**: Switch language in Settings → Language
