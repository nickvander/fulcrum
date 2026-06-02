import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { ReplenishmentPageComponent } from './replenishment-page.component';
import {
  AnalyticsReportsService,
  ReplenishmentReport,
  ReplenishmentRow,
} from '../../services/analytics-reports.service';
import { ReportDownloadService } from '../../../core/services/report-download.service';


function makeRow(over: Partial<ReplenishmentRow> = {}): ReplenishmentRow {
  return {
    product_id: 1,
    product_name: 'Widget',
    product_sku: 'SKU-A',
    supplier_id: 5,
    daily_velocity: 1.0,
    internal_on_hand: 50,
    full_on_hand: 10,
    in_transit_to_full: 0,
    full_available: 10,
    days_cover_full: 10,
    days_cover_pipeline: 60,
    send_to_full_qty: 30,
    send_to_full_by: '2026-06-01',
    supplier_lead_time_days: 20,
    reorder_qty: 0,
    reorder_by: null,
    severity: 'soon',
    ...over,
  };
}


describe('ReplenishmentPageComponent', () => {
  let fixture: ComponentFixture<ReplenishmentPageComponent>;
  let component: ReplenishmentPageComponent;
  let analyticsStub: {
    replenishment: ReturnType<typeof vi.fn>;
    exportReplenishmentCsv: ReturnType<typeof vi.fn>;
    exportReplenishmentPdf: ReturnType<typeof vi.fn>;
  };
  let downloadStub: { download: ReturnType<typeof vi.fn> };

  function setResponse(rows: ReplenishmentRow[], sendNow = 0, reorderNow = 0): void {
    const resp: ReplenishmentReport = {
      rows,
      velocity_window_days: 30,
      full_transfer_lead_days: 14,
      target_cover_days: 30,
      total_send_now: sendNow,
      total_reorder_now: reorderNow,
    };
    analyticsStub.replenishment.mockReturnValue(of(resp));
  }

  beforeEach(async () => {
    analyticsStub = {
      replenishment: vi.fn().mockReturnValue(of({
        rows: [], velocity_window_days: 30, full_transfer_lead_days: 14,
        target_cover_days: 30, total_send_now: 0, total_reorder_now: 0,
      })),
      exportReplenishmentCsv: vi.fn().mockReturnValue(of(new Blob())),
      exportReplenishmentPdf: vi.fn().mockReturnValue(of(new Blob())),
    };
    downloadStub = { download: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [
        ReplenishmentPageComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: AnalyticsReportsService, useValue: analyticsStub },
        { provide: ReportDownloadService, useValue: downloadStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ReplenishmentPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('fetches on init with the default window/lead/cover', () => {
    expect(analyticsStub.replenishment).toHaveBeenCalledWith(30, 14, 30);
  });

  it('reloads with new params when a filter changes', () => {
    analyticsStub.replenishment.mockClear();
    component.velocityWindowDays = 60;
    component.fullTransferLeadDays = 21;
    component.onFilterChange();
    expect(analyticsStub.replenishment).toHaveBeenCalledWith(60, 21, 30);
  });

  it('populates rows + totals on success', () => {
    setResponse([makeRow(), makeRow({ product_id: 2 })], 2, 1);
    component.load();
    expect(component.rows.length).toBe(2);
    expect(component.totalSendNow).toBe(2);
    expect(component.totalReorderNow).toBe(1);
  });

  it('surfaces the error state on load failure', () => {
    analyticsStub.replenishment.mockReturnValue(throwError(() => new Error('boom')));
    component.load();
    expect(component.errored).toBe(true);
    expect(component.rows).toEqual([]);
    expect(component.totalSendNow).toBe(0);
  });

  it('routes CSV/PDF exports through the download service', () => {
    component.exportCsv();
    expect(analyticsStub.exportReplenishmentCsv).toHaveBeenCalledWith(30, 14, 30);
    expect(downloadStub.download).toHaveBeenCalledWith(expect.anything(), 'fulcrum-replenishment', 'csv');
    component.exportPdf();
    expect(downloadStub.download).toHaveBeenCalledWith(expect.anything(), 'fulcrum-replenishment', 'pdf');
  });

  it('isDue() flags past/today dates and ignores nulls + future', () => {
    expect(component.isDue('2000-01-01')).toBe(true);
    expect(component.isDue(null)).toBe(false);
    expect(component.isDue('2999-01-01')).toBe(false);
  });
});
