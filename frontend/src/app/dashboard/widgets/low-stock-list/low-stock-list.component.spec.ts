import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslocoTestingModule } from '@ngneat/transloco';

import { LowStockListWidgetComponent } from './low-stock-list.component';
import { LowStockReport, LowStockRow } from '../../services/low-stock.service';

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
                TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } }),
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

    it('exposes a Create-PO link with the product_id query param per row', () => {
        component.report = {
            rows: [row({ product_id: 7 })],
            total_critical: 0,
            total_low: 1,
            total_watch: 0,
        };
        fixture.detectChanges();
        const link = fixture.debugElement.query(By.css('[data-testid="create-po-7"]'));
        expect(link).toBeTruthy();
        const href = link.nativeElement.getAttribute('href');
        expect(href).toContain('product_id=7');
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
