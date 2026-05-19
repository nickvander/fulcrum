import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
  TestRequest,
} from '@angular/common/http/testing';

import { AnalyticsReportsService } from './analytics-reports.service';
import { environment } from '../../../environments/environment';

describe('AnalyticsReportsService', () => {
  let service: AnalyticsReportsService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AnalyticsReportsService],
    });
    service = TestBed.inject(AnalyticsReportsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  function expectBlobRequest(url: string): TestRequest {
    const req = httpMock.expectOne((r) => r.url === url);
    expect(req.request.method).toBe('GET');
    expect(req.request.responseType).toBe('blob');
    return req;
  }

  // ---- Velocity ------------------------------------------------------------

  it('exportVelocityCsv hits /reports/velocity/export with default window + limit', () => {
    service.exportVelocityCsv().subscribe();
    const req = expectBlobRequest(`${environment.apiUrl}/reports/velocity/export`);
    expect(req.request.params.get('window_days')).toBe('30');
    expect(req.request.params.get('limit')).toBe('2000');
    req.flush(new Blob());
  });

  it('exportVelocityPdf forwards custom window + limit to the -pdf endpoint', () => {
    service.exportVelocityPdf(60, 5000).subscribe();
    const req = expectBlobRequest(`${environment.apiUrl}/reports/velocity/export-pdf`);
    expect(req.request.params.get('window_days')).toBe('60');
    expect(req.request.params.get('limit')).toBe('5000');
    req.flush(new Blob());
  });

  // ---- Margin --------------------------------------------------------------

  it('exportMarginCsv hits /reports/margin/export with default window + limit', () => {
    service.exportMarginCsv().subscribe();
    const req = expectBlobRequest(`${environment.apiUrl}/reports/margin/export`);
    expect(req.request.params.get('window_days')).toBe('30');
    expect(req.request.params.get('limit')).toBe('2000');
    req.flush(new Blob());
  });

  it('exportMarginPdf forwards a custom window', () => {
    service.exportMarginPdf(90).subscribe();
    const req = expectBlobRequest(`${environment.apiUrl}/reports/margin/export-pdf`);
    expect(req.request.params.get('window_days')).toBe('90');
    req.flush(new Blob());
  });

  // ---- Stockout ------------------------------------------------------------

  it('exportStockoutCsv hits /reports/stockout/export with default thresholds', () => {
    service.exportStockoutCsv().subscribe();
    const req = expectBlobRequest(`${environment.apiUrl}/reports/stockout/export`);
    expect(req.request.params.get('window_days')).toBe('30');
    expect(req.request.params.get('imminent_days')).toBe('7');
    expect(req.request.params.get('watch_days')).toBe('14');
    expect(req.request.params.get('limit')).toBe('2000');
    req.flush(new Blob());
  });

  it('exportStockoutPdf forwards custom imminent / watch / window values', () => {
    service.exportStockoutPdf(60, 10, 21, 5000).subscribe();
    const req = expectBlobRequest(`${environment.apiUrl}/reports/stockout/export-pdf`);
    expect(req.request.params.get('window_days')).toBe('60');
    expect(req.request.params.get('imminent_days')).toBe('10');
    expect(req.request.params.get('watch_days')).toBe('21');
    expect(req.request.params.get('limit')).toBe('5000');
    req.flush(new Blob());
  });

  // ---- Phase 8 cost-rollup endpoints ---------------------------------------

  it('costRollup() GETs /reports/cost-rollup with window_days', () => {
    service.costRollup(7).subscribe();
    const req = httpMock.expectOne(r => r.url === `${environment.apiUrl}/reports/cost-rollup`);
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('window_days')).toBe('7');
    expect(req.request.params.has('source')).toBe(false);
    req.flush({});
  });

  it('costRollup() forwards the optional source query param when set', () => {
    service.costRollup(30, 'amazon').subscribe();
    const req = httpMock.expectOne(r => r.url === `${environment.apiUrl}/reports/cost-rollup`);
    expect(req.request.params.get('source')).toBe('amazon');
    req.flush({});
  });

  it('costRollupByChannel() GETs the by-channel endpoint', () => {
    service.costRollupByChannel(60).subscribe();
    const req = httpMock.expectOne(r => r.url === `${environment.apiUrl}/reports/cost-rollup/by-channel`);
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('window_days')).toBe('60');
    req.flush({ window_days: 60, channels: [] });
  });

  it('costRollupDaily() GETs the daily-series endpoint', () => {
    service.costRollupDaily(14).subscribe();
    const req = httpMock.expectOne(r => r.url === `${environment.apiUrl}/reports/cost-rollup/daily`);
    expect(req.request.params.get('window_days')).toBe('14');
    req.flush({ window_days: 14, series: [] });
  });

  it('topMovers() GETs /reports/top-movers with window + limit', () => {
    service.topMovers(30, 5).subscribe();
    const req = httpMock.expectOne(r => r.url === `${environment.apiUrl}/reports/top-movers`);
    expect(req.request.params.get('window_days')).toBe('30');
    expect(req.request.params.get('limit')).toBe('5');
    req.flush({ window_days: 30, limit: 5, rows: [] });
  });

  it('deadStock() GETs /reports/dead-stock with window + threshold + limit', () => {
    service.deadStock(60, 0.2, 30).subscribe();
    const req = httpMock.expectOne(r => r.url === `${environment.apiUrl}/reports/dead-stock`);
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('window_days')).toBe('60');
    expect(req.request.params.get('threshold_daily_velocity')).toBe('0.2');
    expect(req.request.params.get('limit')).toBe('30');
    req.flush({ window_days: 60, threshold_daily_velocity: 0.2, rows: [] });
  });

  it('refundsSummary() GETs /reports/refunds-summary with the window', () => {
    service.refundsSummary(30).subscribe();
    const req = httpMock.expectOne(r => r.url === `${environment.apiUrl}/reports/refunds-summary`);
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('window_days')).toBe('30');
    expect(req.request.params.get('start_date')).toBeNull();
    expect(req.request.params.get('end_date')).toBeNull();
    req.flush({ window_label: 'window 30d', totals: {}, by_channel: [] });
  });

  it('refundsSummary() forwards an explicit date range to the backend', () => {
    service.refundsSummary(30, { startDate: '2026-01-01', endDate: '2026-03-31' }).subscribe();
    const req = httpMock.expectOne(r => r.url === `${environment.apiUrl}/reports/refunds-summary`);
    expect(req.request.params.get('start_date')).toBe('2026-01-01');
    expect(req.request.params.get('end_date')).toBe('2026-03-31');
    req.flush({ window_label: 'window 30d', totals: {}, by_channel: [] });
  });
});
