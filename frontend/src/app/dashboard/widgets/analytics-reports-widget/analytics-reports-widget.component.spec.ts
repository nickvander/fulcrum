import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of } from 'rxjs';

import { AnalyticsReportsWidgetComponent } from './analytics-reports-widget.component';
import { AnalyticsReportsService } from '../../services/analytics-reports.service';
import { ReportDownloadService } from '../../../core/services/report-download.service';

describe('AnalyticsReportsWidgetComponent', () => {
  let fixture: ComponentFixture<AnalyticsReportsWidgetComponent>;
  let component: AnalyticsReportsWidgetComponent;
  let analyticsStub: {
    exportVelocityCsv: ReturnType<typeof vi.fn>;
    exportVelocityPdf: ReturnType<typeof vi.fn>;
    exportMarginCsv: ReturnType<typeof vi.fn>;
    exportMarginPdf: ReturnType<typeof vi.fn>;
    exportStockoutCsv: ReturnType<typeof vi.fn>;
    exportStockoutPdf: ReturnType<typeof vi.fn>;
  };
  let downloaderStub: { download: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    analyticsStub = {
      exportVelocityCsv: vi.fn().mockReturnValue(of(new Blob())),
      exportVelocityPdf: vi.fn().mockReturnValue(of(new Blob())),
      exportMarginCsv:   vi.fn().mockReturnValue(of(new Blob())),
      exportMarginPdf:   vi.fn().mockReturnValue(of(new Blob())),
      exportStockoutCsv: vi.fn().mockReturnValue(of(new Blob())),
      exportStockoutPdf: vi.fn().mockReturnValue(of(new Blob())),
    };
    downloaderStub = { download: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [
        AnalyticsReportsWidgetComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: AnalyticsReportsService, useValue: analyticsStub },
        { provide: ReportDownloadService, useValue: downloaderStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AnalyticsReportsWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  function clickButton(testId: string): void {
    const btn = fixture.debugElement.query(By.css(`[data-testid="${testId}"]`));
    if (!btn) throw new Error(`button [${testId}] did not render`);
    btn.nativeElement.click();
    fixture.detectChanges();
  }

  it('renders one row per report', () => {
    expect(fixture.debugElement.query(By.css('[data-testid="analytics-report-velocity"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="analytics-report-margin"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="analytics-report-stockout"]'))).not.toBeNull();
  });

  // ---- Velocity row --------------------------------------------------------

  it('velocity CSV button calls the service with the current windowDays and routes the blob to the downloader', () => {
    clickButton('velocity-export-csv');
    expect(analyticsStub.exportVelocityCsv).toHaveBeenCalledWith(30, 2000, undefined);
    expect(downloaderStub.download).toHaveBeenCalledTimes(1);
    expect(downloaderStub.download.mock.calls[0][1]).toBe('fulcrum-velocity');
    expect(downloaderStub.download.mock.calls[0][2]).toBe('csv');
  });

  it('velocity PDF button calls the PDF service method', () => {
    clickButton('velocity-export-pdf');
    expect(analyticsStub.exportVelocityPdf).toHaveBeenCalledWith(30, 2000, undefined);
    expect(downloaderStub.download.mock.calls[0][2]).toBe('pdf');
  });

  // ---- Margin row ----------------------------------------------------------

  it('margin CSV / PDF buttons route to the margin service methods with the right stem', () => {
    clickButton('margin-export-csv');
    expect(analyticsStub.exportMarginCsv).toHaveBeenCalledWith(30, 2000, undefined);
    expect(downloaderStub.download.mock.calls[0][1]).toBe('fulcrum-margin');
    expect(downloaderStub.download.mock.calls[0][2]).toBe('csv');

    clickButton('margin-export-pdf');
    expect(analyticsStub.exportMarginPdf).toHaveBeenCalledWith(30, 2000, undefined);
    expect(downloaderStub.download.mock.calls[1][2]).toBe('pdf');
  });

  // ---- Stockout row --------------------------------------------------------

  it('stockout CSV / PDF buttons route to the stockout service methods with the right stem', () => {
    clickButton('stockout-export-csv');
    expect(analyticsStub.exportStockoutCsv).toHaveBeenCalledWith(30, 7, 14, 2000, undefined);
    expect(downloaderStub.download.mock.calls[0][1]).toBe('fulcrum-stockout');
    expect(downloaderStub.download.mock.calls[0][2]).toBe('csv');

    clickButton('stockout-export-pdf');
    expect(analyticsStub.exportStockoutPdf).toHaveBeenCalledWith(30, 7, 14, 2000, undefined);
    expect(downloaderStub.download.mock.calls[1][2]).toBe('pdf');
  });

  // ---- Window selector -----------------------------------------------------

  it('changing windowDays forwards the new value to subsequent calls', () => {
    component.windowDays = 90;
    fixture.detectChanges();

    clickButton('velocity-export-csv');
    clickButton('margin-export-pdf');
    clickButton('stockout-export-csv');

    expect(analyticsStub.exportVelocityCsv).toHaveBeenCalledWith(90, 2000, undefined);
    expect(analyticsStub.exportMarginPdf).toHaveBeenCalledWith(90, 2000, undefined);
    expect(analyticsStub.exportStockoutCsv).toHaveBeenCalledWith(90, 7, 14, 2000, undefined);
  });

  // ---- Busy guard ----------------------------------------------------------

  it('double-clicking the same button only fires one request until the busy flag clears', () => {
    clickButton('velocity-export-csv');
    clickButton('velocity-export-csv');
    expect(analyticsStub.exportVelocityCsv).toHaveBeenCalledTimes(1);
    expect(downloaderStub.download).toHaveBeenCalledTimes(1);
  });

  it('busy is per-(report,ext) — the CSV busy flag does not block the PDF button on the same row', () => {
    clickButton('velocity-export-csv');
    clickButton('velocity-export-pdf');
    expect(analyticsStub.exportVelocityCsv).toHaveBeenCalledTimes(1);
    expect(analyticsStub.exportVelocityPdf).toHaveBeenCalledTimes(1);
    expect(downloaderStub.download).toHaveBeenCalledTimes(2);
  });

  // ---- Date range ----------------------------------------------------------

  it('passes the start/end picker values to the service as a DateRange', () => {
    component.startDate = new Date(2026, 0, 15);  // Jan 15
    component.endDate = new Date(2026, 2, 31);    // Mar 31
    fixture.detectChanges();

    clickButton('velocity-export-csv');
    expect(analyticsStub.exportVelocityCsv).toHaveBeenCalledWith(30, 2000, {
      startDate: '2026-01-15',
      endDate: '2026-03-31',
    });
  });

  it('passes a partial range when only one picker is set', () => {
    component.startDate = new Date(2026, 0, 15);
    component.endDate = null;
    fixture.detectChanges();

    clickButton('margin-export-csv');
    expect(analyticsStub.exportMarginCsv).toHaveBeenCalledWith(30, 2000, {
      startDate: '2026-01-15',
      endDate: null,
    });
  });

  it('omits the range param when both pickers are empty so windowDays is the only filter', () => {
    component.startDate = null;
    component.endDate = null;
    clickButton('velocity-export-csv');
    expect(analyticsStub.exportVelocityCsv).toHaveBeenCalledWith(30, 2000, undefined);
  });

  it('clearRange() resets both pickers and re-enables the window selector', () => {
    component.startDate = new Date(2026, 0, 1);
    component.endDate = new Date(2026, 2, 31);
    component.clearRange();
    expect(component.startDate).toBeNull();
    expect(component.endDate).toBeNull();
    expect(component.hasExplicitRange()).toBe(false);
  });

  it('rangeInverted() flags start > end so download buttons disable', () => {
    component.startDate = new Date(2026, 2, 31);
    component.endDate = new Date(2026, 0, 1);
    fixture.detectChanges();

    expect(component.rangeInverted()).toBe(true);
    // Inverted-range banner renders.
    expect(fixture.debugElement.query(By.css('[data-testid="analytics-reports-range-error"]'))).not.toBeNull();

    // Click is gated — the click handler still fires but the disabled
    // attribute is set on every CSV/PDF button. Verify one:
    const btn = fixture.debugElement.query(By.css('[data-testid="velocity-export-csv"]'));
    expect(btn.nativeElement.disabled).toBe(true);
  });
});
