import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { RouterTestingModule } from '@angular/router/testing';

import { MatTooltip } from '@angular/material/tooltip';

import { LowStockListWidgetComponent } from './low-stock-list.component';
import { LowStockReport, LowStockRow } from '../../services/low-stock.service';
import { getTranslocoTestingModule } from '../../../testing/transloco-testing';

function row(overrides: Partial<LowStockRow> = {}): LowStockRow {
    return {
        product_id: 1,
        product_name: 'Tea',
        product_sku: 'TEA-001',
        on_hand: 3,
        threshold: 10,
        reorder_point: 10,
        reorder_quantity: null,
        suggested_reorder_qty: 30,
        daily_velocity: 0.5,
        days_of_inventory: 6.0,
        severity: 'low',
        ...overrides,
    };
}

describe('LowStockListWidgetComponent', () => {
    let component: LowStockListWidgetComponent;
    let fixture: ComponentFixture<LowStockListWidgetComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                LowStockListWidgetComponent,
                RouterTestingModule,
                getTranslocoTestingModule(),
            ],
        }).compileComponents();

        fixture = TestBed.createComponent(LowStockListWidgetComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('shows the empty state when the report is null', () => {
        component.report = null;
        fixture.detectChanges();
        const empty = fixture.debugElement.query(By.css('.empty-state'));
        expect(empty).toBeTruthy();
    });

    it('shows the empty state when the report has zero rows', () => {
        component.report = { rows: [], total_critical: 0, total_low: 0, total_watch: 0 };
        fixture.detectChanges();
        expect(fixture.debugElement.query(By.css('.empty-state'))).toBeTruthy();
    });

    it('renders one table row per low-stock entry', () => {
        const report: LowStockReport = {
            rows: [
                row(),
                row({ product_id: 2, product_name: 'Coffee', severity: 'critical', on_hand: 0 }),
            ],
            total_critical: 1,
            total_low: 1,
            total_watch: 0,
        };
        component.report = report;
        fixture.detectChanges();

        const rows = fixture.debugElement.queryAll(By.css('[data-testid^="lowstock-row-"]'));
        expect(rows.length).toBe(2);
    });

    it('shows Create-PO (reorder) as the primary action when out of warehouse stock', () => {
        // No internal_on_hand → nothing to transfer → reorder from supplier.
        component.report = {
            rows: [row({ product_id: 7, internal_on_hand: 0, ml_full_on_hand: 0 })],
            total_critical: 0,
            total_low: 1,
            total_watch: 0,
        };
        fixture.detectChanges();

        const link = fixture.debugElement.query(By.css('[data-testid="create-po-7"]'));
        expect(link).toBeTruthy();
        const href = link.nativeElement.getAttribute('href');
        expect(href).toContain('/suppliers/po/create');
        expect(href).toContain('product_id=7');
        // The disambiguating label + tooltip make the meaning reachable.
        expect(link.nativeElement.textContent).toContain('Create PO');
        expect(link.injector.get(MatTooltip).message).toContain('from your supplier');

        // No "Enviar a ML Full" action when there's no warehouse stock to move.
        expect(fixture.debugElement.query(By.css('[data-testid="send-to-full-7"]'))).toBeNull();
    });

    it('shows Send-to-ML-Full as the primary action when warehouse stock exists', () => {
        // Warehouse (internal) stock present → the remedy is a TRANSFER, not a
        // purchase. Reorder stays available as a secondary link.
        component.report = {
            rows: [row({ product_id: 9, product_sku: 'TEA-009', internal_on_hand: 12 })],
            total_critical: 0,
            total_low: 1,
            total_watch: 0,
        };
        fixture.detectChanges();

        const transfer = fixture.debugElement.query(By.css('[data-testid="send-to-full-9"]'));
        expect(transfer).toBeTruthy();
        const href = transfer.nativeElement.getAttribute('href');
        expect(href).toContain('/marketplaces/transfers/planner');
        // Pre-targets the product by SKU so the planner lands filtered.
        expect(href).toContain('q=TEA-009');
        expect(transfer.nativeElement.textContent).toContain('Send to ML Full');
        expect(transfer.injector.get(MatTooltip).message).toContain('warehouse');

        // Reorder is still discoverable as a secondary action on the same row.
        const reorder = fixture.debugElement.query(By.css('[data-testid="create-po-9"]'));
        expect(reorder).toBeTruthy();
        expect(reorder.injector.get(MatTooltip).message).toContain('from your supplier');
    });

    it('canTransferToFull / transferQueryParams reflect warehouse stock', () => {
        expect(component.canTransferToFull(row({ internal_on_hand: 0 }))).toBe(false);
        expect(component.canTransferToFull(row({ internal_on_hand: 5 }))).toBe(true);
        // Missing field is treated as zero (no transfer remedy).
        expect(component.canTransferToFull(row({ internal_on_hand: undefined }))).toBe(false);
        // Prefer SKU, fall back to product name.
        expect(component.transferQueryParams(row({ product_sku: 'TEA-001' }))).toEqual({ q: 'TEA-001' });
        expect(component.transferQueryParams(row({ product_sku: null, product_name: 'Tea' }))).toEqual({ q: 'Tea' });
    });

    it('renders severity chips when totals are non-zero', () => {
        component.report = {
            rows: [row()],
            total_critical: 2,
            total_low: 5,
            total_watch: 1,
        };
        fixture.detectChanges();
        expect(fixture.debugElement.query(By.css('[data-testid="chip-critical"]'))).toBeTruthy();
        expect(fixture.debugElement.query(By.css('[data-testid="chip-low"]'))).toBeTruthy();
        expect(fixture.debugElement.query(By.css('[data-testid="chip-watch"]'))).toBeTruthy();
    });

    it('formats velocity and days-left dashes when velocity is zero', () => {
        const r = row({ daily_velocity: 0, days_of_inventory: 999 });
        expect(component.velocityLabel(r)).toBe('—');
        expect(component.daysLeftLabel(r)).toBe('—');
    });

    it('formats velocity and days-left numerically when velocity is positive', () => {
        const r = row({ daily_velocity: 1.234, days_of_inventory: 4.7 });
        expect(component.velocityLabel(r)).toBe('1.23/day');
        expect(component.daysLeftLabel(r)).toBe('4.7d');
    });
});
