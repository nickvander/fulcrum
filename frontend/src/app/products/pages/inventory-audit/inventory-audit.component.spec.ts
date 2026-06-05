import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { of, throwError } from 'rxjs';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { provideRouter } from '@angular/router';

import { InventoryAuditComponent } from './inventory-audit.component';
import {
  InventoryAdjustmentRow,
  InventoryAuditService,
} from '../../services/inventory-audit.service';
import { ReportDownloadService } from '../../../core/services/report-download.service';

describe('InventoryAuditComponent', () => {
  let component: InventoryAuditComponent;
  let fixture: ComponentFixture<InventoryAuditComponent>;
  let auditStub: {
    list: ReturnType<typeof vi.fn>;
    listReasonCodes: ReturnType<typeof vi.fn>;
    listSources: ReturnType<typeof vi.fn>;
    reverse: ReturnType<typeof vi.fn>;
  };
  let dialogStub: { open: ReturnType<typeof vi.fn> };
  let snackStub: { open: ReturnType<typeof vi.fn> };
  let afterClosed: any;

  function row(overrides: Partial<InventoryAdjustmentRow> = {}): InventoryAdjustmentRow {
    return {
      id: 1, timestamp: '2026-05-01T12:00:00Z', product_id: 5,
      product_sku: 'SKU-5', product_name: 'Widget', adjustment: -5,
      reason_code: 'shrinkage', reason: 'shelf damage', created_by: 'op@example.com',
      source: null, source_id: null,
      reverses_adjustment_id: null, reversed_by_id: null, reversible: true,
      ...overrides,
    };
  }

  async function setup(rows: InventoryAdjustmentRow[]) {
    afterClosed = of(true);
    auditStub = {
      list: vi.fn().mockReturnValue(of({ rows, total: rows.length })),
      listReasonCodes: vi.fn().mockReturnValue(of(['shrinkage', 'recount'])),
      listSources: vi.fn().mockReturnValue(of(['purchase_order', 'stock_transfer', 'sales_order'])),
      reverse: vi.fn().mockReturnValue(of(row({ id: 99, adjustment: 5, reason_code: 'correction' }))),
    };
    dialogStub = { open: vi.fn().mockReturnValue({ afterClosed: () => afterClosed }) };
    snackStub = { open: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [
        InventoryAuditComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        provideRouter([]),
        { provide: InventoryAuditService, useValue: auditStub },
        { provide: ReportDownloadService, useValue: { download: vi.fn() } },
      ],
    })
      // MatDialog / MatSnackBar are provided by the modules the component
      // imports, so its own injector resolves the real services unless we
      // override at the component level.
      .overrideComponent(InventoryAuditComponent, {
        add: {
          providers: [
            { provide: MatDialog, useValue: dialogStub },
            { provide: MatSnackBar, useValue: snackStub },
          ],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(InventoryAuditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  it('shows a Reverse button for a reversible row', async () => {
    await setup([row({ id: 1, reversible: true })]);
    expect(
      fixture.debugElement.query(By.css('[data-testid="audit-reverse-1"]')),
    ).not.toBeNull();
  });

  it('hides the Reverse button for a non-reversible row', async () => {
    await setup([row({ id: 2, reversible: false, reason_code: 'sale' })]);
    expect(
      fixture.debugElement.query(By.css('[data-testid="audit-reverse-2"]')),
    ).toBeNull();
  });

  it('shows a "reversed" badge when the row has been reversed', async () => {
    await setup([row({ id: 3, reversible: false, reversed_by_id: 88 })]);
    expect(
      fixture.debugElement.query(By.css('.reversed-badge')),
    ).not.toBeNull();
  });

  it('confirms then reverses, reloading the page and notifying', async () => {
    await setup([row({ id: 1 })]);
    auditStub.list.mockClear();
    component.reverseRow(row({ id: 1 }));
    expect(dialogStub.open).toHaveBeenCalled();
    expect(auditStub.reverse).toHaveBeenCalledWith(1);
    expect(snackStub.open).toHaveBeenCalled();
    expect(auditStub.list).toHaveBeenCalled(); // page reloaded
    expect(component.reversingId).toBeNull();
  });

  it('does not reverse when the confirmation is dismissed', async () => {
    await setup([row({ id: 1 })]);
    afterClosed = of(false);
    component.reverseRow(row({ id: 1 }));
    expect(auditStub.reverse).not.toHaveBeenCalled();
  });

  it('ignores reverseRow for a non-reversible row', async () => {
    await setup([row({ id: 1 })]);
    component.reverseRow(row({ id: 1, reversible: false }));
    expect(dialogStub.open).not.toHaveBeenCalled();
  });

  it('surfaces a reverse failure via snackbar and clears the in-flight flag', async () => {
    await setup([row({ id: 1 })]);
    auditStub.reverse.mockReturnValueOnce(throwError(() => new Error('boom')));
    component.reverseRow(row({ id: 1 }));
    expect(snackStub.open).toHaveBeenCalled();
    expect(component.reversingId).toBeNull();
  });

  it('reasonCodeLabel localizes known codes and falls back to a capitalized form', async () => {
    await setup([]);
    // Empty test translations → translate() returns the key, so known + unknown
    // codes both exercise the capitalized fallback (no hardcoded English).
    expect(component.reasonCodeLabel('')).toBe('');
    expect(component.reasonCodeLabel('damaged')).toBe('Damaged');
    expect(component.reasonCodeLabel('weird_code')).toBe('Weird_code');
  });

  // --- Source filter + column (P2-8 follow-up) ----------------------------

  it('loads the structured-source dropdown options on init', async () => {
    await setup([]);
    expect(auditStub.listSources).toHaveBeenCalled();
    expect(component.sources).toEqual(['purchase_order', 'stock_transfer', 'sales_order']);
  });

  it('passes the selected source to the list query', async () => {
    await setup([]);
    auditStub.list.mockClear();
    component.source = 'stock_transfer';
    component.loadPage();
    expect(auditStub.list).toHaveBeenCalledWith(
      expect.objectContaining({ source: 'stock_transfer' }),
    );
  });

  it('counts source as an active filter and clears it', async () => {
    await setup([]);
    component.source = 'sales_order';
    expect(component.hasActiveFilters()).toBe(true);
    component.clearFilters();
    expect(component.source).toBe('');
  });

  it('sourceLabel localizes known sources, the none sentinel, and falls back', async () => {
    await setup([]);
    expect(component.sourceLabel('')).toBe('');
    // Empty test translations → translate() echoes the key, so this exercises
    // the capitalized fallback for an otherwise-known source.
    expect(component.sourceLabel('stock_transfer')).toBe('Stock_transfer');
    expect(component.sourceLabel('future_source')).toBe('Future_source');
  });

  it('renders the source column with the label + #source_id', async () => {
    await setup([row({ id: 1, source: 'purchase_order', source_id: 42 })]);
    const text = fixture.debugElement.query(By.css('.source-chip'))?.nativeElement.textContent ?? '';
    expect(text).toContain('#42');
  });
});
