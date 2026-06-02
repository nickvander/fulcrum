import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { HttpErrorResponse } from '@angular/common/http';
import type { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';

import { RepricingPageComponent } from './repricing-page.component';
import {
  AnalyticsReportsService,
  RepricingReport,
  RepricingRow,
} from '../../services/analytics-reports.service';


function makeRow(over: Partial<RepricingRow> = {}): RepricingRow {
  return {
    listing_id: 1,
    product_id: 10,
    product_name: 'Widget',
    product_sku: 'SKU-A',
    marketplace_id: 2,
    marketplace_name: 'MercadoLibre',
    external_listing_id: 'MLM-1',
    cost_price: 40,
    current_price: 45,
    effective_fee_rate: 0.16,
    shipping_per_unit: 0,
    rate_source: 'estimated',
    current_margin_percent: -4.9,
    margin_floor_percent: 10,
    suggested_price: 54.06,
    suggested_margin_percent: 10,
    status: 'loss',
    ...over,
  };
}


describe('RepricingPageComponent', () => {
  let fixture: ComponentFixture<RepricingPageComponent>;
  let component: RepricingPageComponent;
  let analyticsStub: {
    repricing: ReturnType<typeof vi.fn>;
    applyPrice: ReturnType<typeof vi.fn>;
  };

  function setResponse(rows: RepricingRow[], loss = 0, below = 0): void {
    const resp: RepricingReport = {
      rows, margin_floor_percent: 10, total_loss: loss, total_below_floor: below,
    };
    analyticsStub.repricing.mockReturnValue(of(resp));
  }

  beforeEach(async () => {
    analyticsStub = {
      repricing: vi.fn().mockReturnValue(of({
        rows: [], margin_floor_percent: 10, total_loss: 0, total_below_floor: 0,
      })),
      applyPrice: vi.fn().mockReturnValue(of({ listing_id: 1, marketplace_price: 54.06 })),
    };

    await TestBed.configureTestingModule({
      imports: [
        RepricingPageComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: AnalyticsReportsService, useValue: analyticsStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(RepricingPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('fetches on init with the 10% default floor', () => {
    expect(analyticsStub.repricing).toHaveBeenCalledWith(10);
  });

  it('reloads with the new floor when it changes', () => {
    analyticsStub.repricing.mockClear();
    component.marginFloorPercent = 15;
    component.onFilterChange();
    expect(analyticsStub.repricing).toHaveBeenCalledWith(15);
  });

  it('populates rows + totals on success', () => {
    setResponse([makeRow(), makeRow({ listing_id: 2, status: 'below_floor' })], 1, 2);
    component.load();
    expect(component.rows.length).toBe(2);
    expect(component.totalLoss).toBe(1);
    expect(component.totalBelowFloor).toBe(2);
  });

  it('applies a price, drops the row, and recounts', () => {
    const snackBar = (component as unknown as { snackBar: MatSnackBar }).snackBar;
    const openSpy = vi.spyOn(snackBar, 'open');
    setResponse([makeRow({ listing_id: 1 }), makeRow({ listing_id: 2, status: 'below_floor' })], 1, 2);
    component.load();
    component.apply(component.rows[0]);
    expect(analyticsStub.applyPrice).toHaveBeenCalledWith(1, 54.06);
    expect(component.rows.some((r) => r.listing_id === 1)).toBe(false);
    expect(component.totalLoss).toBe(0);
    expect(component.totalBelowFloor).toBe(1);
    expect(openSpy).toHaveBeenCalled();
  });

  it('flips the row into reconnect state on a 409 needs_reauthorization', () => {
    setResponse([makeRow({ listing_id: 1 })]);
    component.load();
    analyticsStub.applyPrice.mockReturnValue(
      throwError(() => new HttpErrorResponse({
        status: 409, error: { code: 'needs_reauthorization' },
      })),
    );
    component.apply(component.rows[0]);
    expect(component.reauthId).toBe(1);
    expect(component.rows.some((r) => r.listing_id === 1)).toBe(true);
  });

  it('shows a generic apply error on other failures', () => {
    setResponse([makeRow({ listing_id: 1 })]);
    component.load();
    analyticsStub.applyPrice.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 500 })),
    );
    component.apply(component.rows[0]);
    expect(component.applyErrorId).toBe(1);
  });

  it('does not apply infeasible rows (no suggested price)', () => {
    const row = makeRow({ status: 'infeasible', suggested_price: null });
    component.apply(row);
    expect(analyticsStub.applyPrice).not.toHaveBeenCalled();
  });

  it('surfaces the error state on load failure', () => {
    analyticsStub.repricing.mockReturnValue(throwError(() => new Error('boom')));
    component.load();
    expect(component.errored).toBe(true);
    expect(component.rows).toEqual([]);
  });
});
