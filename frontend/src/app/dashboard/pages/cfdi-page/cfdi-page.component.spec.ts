import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { CfdiPageComponent } from './cfdi-page.component';
import { CfdiService, CfdiReport } from '../../../core/services/cfdi.service';
import { ReportDownloadService } from '../../../core/services/report-download.service';


function makeReport(over: Partial<CfdiReport> = {}): CfdiReport {
  return {
    rows: [
      {
        order_id: 1, external_order_id: 'ML-1', issued_at: '2026-05-20T00:00:00Z',
        source: 'mercadolibre', currency: 'MXN',
        receiver_rfc: 'XAXX010101000', receiver_name: 'PÚBLICO EN GENERAL', cfdi_use: 'S01',
        concepts: [], subtotal: 100, iva_amount: 16, total: 116,
      },
    ],
    issuer: {
      rfc: 'AAA010101AAA', name: 'Tienda', tax_regime: '601', postal_code: '06000',
      default_product_key: '01010101', default_unit_key: 'H87', cfdi_use: 'S01',
      iva_rate: 0.16, is_configured: true,
    },
    start_date: '2026-04-20', end_date: '2026-05-20',
    order_count: 1, subtotal: 100, iva_amount: 16, total: 116,
    ...over,
  };
}


describe('CfdiPageComponent', () => {
  let fixture: ComponentFixture<CfdiPageComponent>;
  let component: CfdiPageComponent;
  let cfdiStub: { report: ReturnType<typeof vi.fn>; exportCsv: ReturnType<typeof vi.fn> };
  let downloadStub: { download: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    cfdiStub = {
      report: vi.fn().mockReturnValue(of(makeReport())),
      exportCsv: vi.fn().mockReturnValue(of(new Blob())),
    };
    downloadStub = { download: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [
        CfdiPageComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: CfdiService, useValue: cfdiStub },
        { provide: ReportDownloadService, useValue: downloadStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CfdiPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('fetches on init with a 30-day range', () => {
    expect(cfdiStub.report).toHaveBeenCalledTimes(1);
    const arg = cfdiStub.report.mock.calls[0][0];
    expect(arg.startDate).toBeTruthy();
    expect(arg.endDate).toBeTruthy();
  });

  it('populates rows + totals + issuer flag on success', () => {
    expect(component.rows.length).toBe(1);
    expect(component.orderCount).toBe(1);
    expect(component.subtotal).toBe(100);
    expect(component.ivaAmount).toBe(16);
    expect(component.total).toBe(116);
    expect(component.issuerConfigured).toBe(true);
  });

  it('reflects an unconfigured issuer', () => {
    cfdiStub.report.mockReturnValue(of(makeReport({
      issuer: { ...makeReport().issuer, is_configured: false },
    })));
    component.load();
    expect(component.issuerConfigured).toBe(false);
  });

  it('reloads when the window changes', () => {
    cfdiStub.report.mockClear();
    component.windowDays = 90;
    component.onFilterChange();
    expect(cfdiStub.report).toHaveBeenCalledTimes(1);
  });

  it('routes the CSV export through the download service', () => {
    component.exportCsv();
    expect(cfdiStub.exportCsv).toHaveBeenCalled();
    expect(downloadStub.download).toHaveBeenCalledWith(expect.anything(), 'fulcrum-cfdi', 'csv');
  });

  it('surfaces the error state on load failure', () => {
    cfdiStub.report.mockReturnValue(throwError(() => new Error('boom')));
    component.load();
    expect(component.errored).toBe(true);
    expect(component.rows).toEqual([]);
  });
});
