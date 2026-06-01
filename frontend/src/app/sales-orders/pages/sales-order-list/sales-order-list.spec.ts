import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import { SalesOrderListComponent } from './sales-order-list';
import {
  SalesOrder,
  SalesOrderListResponse,
  SalesOrdersService,
} from '../../services/sales-orders.service';
import { ReportDownloadService } from '../../../core/services/report-download.service';
import { getTranslocoTestingModule } from '../../../testing/transloco-testing';


function makeOrder(over: Partial<SalesOrder> = {}): SalesOrder {
  return {
    id: 1,
    status: 'COMPLETED',
    total_price: 400,
    currency: 'MXN',
    created_at: '2026-01-01T00:00:00Z',
    source: 'MERCADOLIBRE',
    external_order_id: 'ML-1',
    net_margin_percent: 22.5,
    ...over,
  };
}

function envelope(items: SalesOrder[], total = items.length): SalesOrderListResponse {
  return { items, total, skip: 0, limit: 25 };
}


describe('SalesOrderListComponent', () => {
  let fixture: ComponentFixture<SalesOrderListComponent>;
  let component: SalesOrderListComponent;
  let salesStub: { list: ReturnType<typeof vi.fn> };
  let reportStub: { download: ReturnType<typeof vi.fn> };
  let routerStub: { navigate: ReturnType<typeof vi.fn> };
  let queryParams: Record<string, string>;

  async function setup(initialParams: Record<string, string> = {}): Promise<void> {
    queryParams = initialParams;
    salesStub = {
      list: vi.fn().mockReturnValue(of(envelope([]))),
      exportListCsv: vi.fn().mockReturnValue(of(new Blob())),
      exportListPdf: vi.fn().mockReturnValue(of(new Blob())),
    } as any;
    reportStub = { download: vi.fn() };
    routerStub = { navigate: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [
        SalesOrderListComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        getTranslocoTestingModule(),
      ],
      providers: [
        { provide: SalesOrdersService, useValue: salesStub },
        { provide: ReportDownloadService, useValue: reportStub },
        { provide: Router, useValue: routerStub },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParams } } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SalesOrderListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  beforeEach(async () => {
    await setup();
  });

  it('fetches on init with page 0 (skip 0, limit 25) + the 30d default', () => {
    expect(salesStub.list).toHaveBeenCalledWith({ days: 30, skip: 0, limit: 25 });
  });

  it('parses the envelope into rows + total', () => {
    salesStub.list.mockReturnValue(of(envelope([makeOrder({ id: 7 }), makeOrder({ id: 8 })], 42)));
    component.load();
    expect(component.rows.length).toBe(2);
    expect(component.total).toBe(42);
  });

  it('paginator events refetch with skip = pageIndex × pageSize', () => {
    salesStub.list.mockClear();
    component.onPage({ pageIndex: 2, pageSize: 25, length: 100 } as any);
    expect(component.pageIndex).toBe(2);
    expect(component.pageSize).toBe(25);
    expect(salesStub.list).toHaveBeenCalledWith({ days: 30, skip: 50, limit: 25 });
  });

  it('source filter resets page to 0 and refetches', () => {
    component.pageIndex = 3;
    salesStub.list.mockClear();
    component.source = 'AMAZON';
    component.onFilterChange();
    expect(component.pageIndex).toBe(0);
    expect(salesStub.list).toHaveBeenCalledWith({ source: 'AMAZON', days: 30, skip: 0, limit: 25 });
  });

  it('debounces search, resets to page 0, and sends the trimmed term', () => {
    vi.useFakeTimers();
    try {
      component.pageIndex = 4;
      salesStub.list.mockClear();

      component.search = '  ML-AB ';
      component.onSearchChange();
      // Nothing yet — still inside the debounce window.
      expect(salesStub.list).not.toHaveBeenCalled();

      vi.advanceTimersByTime(300);
      expect(component.pageIndex).toBe(0);
      expect(salesStub.list).toHaveBeenCalledWith({ search: 'ML-AB', days: 30, skip: 0, limit: 25 });
    } finally {
      vi.useRealTimers();
    }
  });

  it('blank search sends no search param', () => {
    vi.useFakeTimers();
    try {
      salesStub.list.mockClear();
      component.search = '   ';
      component.onSearchChange();
      vi.advanceTimersByTime(300);
      expect(salesStub.list).toHaveBeenCalledWith({ days: 30, skip: 0, limit: 25 });
    } finally {
      vi.useRealTimers();
    }
  });

  it('hasActiveSearch reflects a trimmed term', () => {
    expect(component.hasActiveSearch).toBe(false);
    component.search = '   ';
    expect(component.hasActiveSearch).toBe(false);
    component.search = 'ML-9';
    expect(component.hasActiveSearch).toBe(true);
  });

  it('marginClass() bands match the order-detail thresholds', () => {
    expect(component.marginClass(-5)).toBe('margin-loss');
    expect(component.marginClass(0)).toBe('margin-thin');
    expect(component.marginClass(14.9)).toBe('margin-thin');
    expect(component.marginClass(15)).toBe('margin-healthy');
    expect(component.marginClass(40)).toBe('margin-healthy');
    expect(component.marginClass(null)).toBe('');
    expect(component.marginClass(undefined)).toBe('');
  });

  it('renders a banded margin value and an em-dash for null', () => {
    salesStub.list.mockReturnValue(of(envelope([
      makeOrder({ id: 1, net_margin_percent: 30 }),
      makeOrder({ id: 2, net_margin_percent: null }),
    ], 2)));
    component.load();
    fixture.detectChanges();

    const cells = fixture.nativeElement.querySelectorAll('[data-testid="orders-margin"]');
    expect(cells.length).toBe(2);
    expect(cells[0].textContent).toContain('30');
    expect(cells[0].classList).toContain('margin-healthy');
    expect(cells[1].textContent.trim()).toBe('—');
    expect(cells[1].classList).toContain('margin-unknown');
  });

  it('shows the no-results state when a search returns nothing', () => {
    component.search = 'ZZZ';
    salesStub.list.mockReturnValue(of(envelope([], 0)));
    component.load();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-testid="orders-no-results"]')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('[data-testid="orders-empty"]')).toBeFalsy();
  });

  it('shows the empty-window state when there is no search and no rows', () => {
    component.search = '';
    salesStub.list.mockReturnValue(of(envelope([], 0)));
    component.load();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-testid="orders-empty"]')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('[data-testid="orders-no-results"]')).toBeFalsy();
  });

  it('exports pass the current source + search scope', () => {
    component.source = 'AMAZON';
    component.search = ' ML-7 ';
    component.exportCsv();
    expect(reportStub.download).toHaveBeenCalled();
    expect((salesStub as any).exportListCsv).toHaveBeenCalledWith({
      source: 'AMAZON', search: 'ML-7', days: 30,
    });
  });

  it('clears rows + total on a load error', () => {
    component.rows = [makeOrder()];
    component.total = 5;
    salesStub.list.mockReturnValue(throwError(() => new Error('boom')));
    component.load();
    expect(component.rows).toEqual([]);
    expect(component.total).toBe(0);
  });

  // --- Sorting -------------------------------------------------------------

  it('matSortChange maps the column → backend sort_by/sort_dir, resets page, refetches', () => {
    component.pageIndex = 3;
    salesStub.list.mockClear();

    // UI column id "total" maps to backend "total_price".
    component.onSortChange({ active: 'total', direction: 'asc' } as any);

    expect(component.pageIndex).toBe(0);
    expect(salesStub.list).toHaveBeenCalledWith({
      sort_by: 'total_price', sort_dir: 'asc', days: 30, skip: 0, limit: 25,
    });
  });

  it('matSortChange maps margin → net_margin_percent', () => {
    salesStub.list.mockClear();
    component.onSortChange({ active: 'margin', direction: 'asc' } as any);
    expect(salesStub.list).toHaveBeenCalledWith({
      sort_by: 'net_margin_percent', sort_dir: 'asc', days: 30, skip: 0, limit: 25,
    });
  });

  it('clearing the sort (empty direction) falls back to the created_at desc default', () => {
    component.onSortChange({ active: 'total', direction: 'asc' } as any);
    salesStub.list.mockClear();
    component.onSortChange({ active: 'total', direction: '' } as any);
    // Default sort is omitted from the params.
    expect(salesStub.list).toHaveBeenCalledWith({ days: 30, skip: 0, limit: 25 });
  });

  // --- Status filter -------------------------------------------------------

  it('status filter refetches with the status param and resets page', () => {
    component.pageIndex = 2;
    salesStub.list.mockClear();
    component.status = 'SHIPPED';
    component.onFilterChange();
    expect(component.pageIndex).toBe(0);
    expect(salesStub.list).toHaveBeenCalledWith({
      status: 'SHIPPED', days: 30, skip: 0, limit: 25,
    });
  });

  it('the ALL status sends no status param', () => {
    salesStub.list.mockClear();
    component.status = 'ALL';
    component.onFilterChange();
    expect(salesStub.list).toHaveBeenCalledWith({ days: 30, skip: 0, limit: 25 });
  });

  // --- URL persistence -----------------------------------------------------

  it('writes the view to the URL on a filter change (defaults nulled out)', () => {
    routerStub.navigate.mockClear();
    component.source = 'AMAZON';
    component.status = 'PAID';
    component.onFilterChange();

    expect(routerStub.navigate).toHaveBeenCalled();
    const [, extras] = routerStub.navigate.mock.calls.at(-1)!;
    expect(extras.queryParamsHandling).toBe('merge');
    expect(extras.queryParams.source).toBe('AMAZON');
    expect(extras.queryParams.status).toBe('PAID');
    // Untouched defaults are nulled so they drop out of the URL.
    expect(extras.queryParams.days).toBeNull();
    expect(extras.queryParams.page).toBeNull();
    expect(extras.queryParams.sort_by).toBeNull();
  });

  it('persists sort + page in the URL', () => {
    routerStub.navigate.mockClear();
    component.onSortChange({ active: 'total', direction: 'asc' } as any);
    const [, extras] = routerStub.navigate.mock.calls.at(-1)!;
    expect(extras.queryParams.sort_by).toBe('total_price');
    expect(extras.queryParams.sort_dir).toBe('asc');
  });

  it('restores the full view from query params on init', async () => {
    TestBed.resetTestingModule();
    await setup({
      source: 'AMAZON',
      status: 'SHIPPED',
      days: '90',
      search: 'ML-42',
      sort_by: 'total_price',
      sort_dir: 'asc',
      page: '2',
      size: '50',
    });

    expect(component.source).toBe('AMAZON');
    expect(component.status).toBe('SHIPPED');
    expect(component.days).toBe(90);
    expect(component.search).toBe('ML-42');
    expect(component.sortActive).toBe('total');
    expect(component.sortDirection).toBe('asc');
    expect(component.pageIndex).toBe(2);
    expect(component.pageSize).toBe(50);

    // The first fetch reflects the restored view.
    expect(salesStub.list).toHaveBeenCalledWith({
      source: 'AMAZON', status: 'SHIPPED', search: 'ML-42',
      sort_by: 'total_price', sort_dir: 'asc',
      days: 90, skip: 100, limit: 50,
    });
  });
});
