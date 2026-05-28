import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { ReturnsPageComponent } from './returns-page.component';
import {
  AnalyticsReportsService,
  ReturnsListResponse,
  ReturnsListRow,
} from '../../services/analytics-reports.service';


function makeRow(over: Partial<ReturnsListRow> = {}): ReturnsListRow {
  return {
    return_id: 1,
    received_at: '2025-01-01T00:00:00Z',
    order_id: 100,
    external_order_id: 'ML-X',
    source: 'MERCADOLIBRE',
    product_id: 7,
    product_sku: 'SKU-A',
    product_name: 'Widget',
    quantity: 2,
    reason: 'damaged',
    notes: null,
    recorded_by_email: 'ops@example.com',
    value_at_cost: 20.0,
    ...over,
  };
}


describe('ReturnsPageComponent', () => {
  let fixture: ComponentFixture<ReturnsPageComponent>;
  let component: ReturnsPageComponent;
  let analyticsStub: { returnsList: ReturnType<typeof vi.fn> };

  function setResponse(items: ReturnsListRow[], total = items.length): void {
    const resp: ReturnsListResponse = {
      window_label: 'window 30d', items, total,
    };
    analyticsStub.returnsList.mockReturnValue(of(resp));
  }

  beforeEach(async () => {
    analyticsStub = {
      returnsList: vi.fn().mockReturnValue(of({
        window_label: 'window 30d', items: [], total: 0,
      })),
    };

    await TestBed.configureTestingModule({
      imports: [
        ReturnsPageComponent,
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

    fixture = TestBed.createComponent(ReturnsPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('fetches on init with the 30d default + page 0', () => {
    expect(analyticsStub.returnsList).toHaveBeenCalledWith(30, 0, 50, undefined);
  });

  it('passes the source filter through (lowercased) when set', () => {
    analyticsStub.returnsList.mockClear();
    component.sourceFilter = 'AMAZON';
    component.onFilterChange();
    expect(analyticsStub.returnsList).toHaveBeenCalledWith(30, 0, 50, 'amazon');
  });

  it('resets pageIndex to 0 when the filter changes', () => {
    component.pageIndex = 4;
    analyticsStub.returnsList.mockClear();
    component.sourceFilter = 'MERCADOLIBRE';
    component.onFilterChange();
    expect(component.pageIndex).toBe(0);
    expect(analyticsStub.returnsList).toHaveBeenCalledWith(30, 0, 50, 'mercadolibre');
  });

  it('honors paginator events (skip = page × size)', () => {
    analyticsStub.returnsList.mockClear();
    component.onPage({ pageIndex: 2, pageSize: 25, length: 100 } as any);
    expect(analyticsStub.returnsList).toHaveBeenCalledWith(30, 50, 25, undefined);
  });

  it('channelLabel() formats source codes and falls back to "—" on null', () => {
    expect(component.channelLabel('MERCADOLIBRE')).toBe('MercadoLibre');
    expect(component.channelLabel('AMAZON')).toBe('Amazon');
    expect(component.channelLabel('FULCRUM')).toBe('Fulcrum');
    expect(component.channelLabel(null)).toBe('—');
    expect(component.channelLabel('UNKNOWN')).toBe('UNKNOWN');
  });

  it('surfaces the error state on initial load failure', () => {
    component.rows = [];
    analyticsStub.returnsList.mockReturnValue(throwError(() => new Error('boom')));
    component.load();
    expect(component.errored).toBe(true);
    expect(component.rows).toEqual([]);
    expect(component.totalRows).toBe(0);
  });

  it('populates rows + totalRows + windowLabel on success', () => {
    setResponse([makeRow({ return_id: 7 }), makeRow({ return_id: 8 })], 17);
    component.load();
    expect(component.rows.length).toBe(2);
    expect(component.totalRows).toBe(17);
    expect(component.windowLabel).toBe('window 30d');
  });
});
