import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { HttpErrorResponse } from '@angular/common/http';
import { of, throwError } from 'rxjs';

import { CfdiOrderCardComponent } from './cfdi-order-card.component';
import { CfdiDocument, CfdiService } from '../../../core/services/cfdi.service';


function makeDoc(over: Partial<CfdiDocument> = {}): CfdiDocument {
  return {
    id: 1, order_id: 7, kind: 'ingreso', status: 'stamped', invoicing_source: 'self',
    uuid: 'AAA-BBB', receiver_rfc: 'XAXX010101000', receiver_name: 'PÚBLICO EN GENERAL',
    cfdi_use: 'S01', currency: 'MXN', subtotal_cents: 10000, iva_cents: 1600,
    total_cents: 11600, pac_vendor: 'mock', ...over,
  };
}


describe('CfdiOrderCardComponent', () => {
  let fixture: ComponentFixture<CfdiOrderCardComponent>;
  let component: CfdiOrderCardComponent;
  let cfdiStub: {
    getOrderDocument: ReturnType<typeof vi.fn>;
    stampOrder: ReturnType<typeof vi.fn>;
    linkExternal: ReturnType<typeof vi.fn>;
  };

  function notFound() {
    return throwError(() => new HttpErrorResponse({ status: 404 }));
  }

  async function setup() {
    cfdiStub = {
      getOrderDocument: vi.fn().mockReturnValue(notFound()),
      stampOrder: vi.fn().mockReturnValue(of(makeDoc())),
      linkExternal: vi.fn().mockReturnValue(of(makeDoc({ invoicing_source: 'marketplace_handled' }))),
    };

    await TestBed.configureTestingModule({
      imports: [
        CfdiOrderCardComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [{ provide: CfdiService, useValue: cfdiStub }],
    }).compileComponents();

    fixture = TestBed.createComponent(CfdiOrderCardComponent);
    component = fixture.componentInstance;
    component.orderId = 7;
    fixture.detectChanges(); // triggers ngOnChanges via initial binding? set manually
    component.ngOnChanges();
  }

  it('loads the document on init; 404 => no document', async () => {
    await setup();
    expect(cfdiStub.getOrderDocument).toHaveBeenCalledWith(7);
    expect(component.doc).toBeNull();
  });

  it('shows an existing document when present', async () => {
    await setup();
    cfdiStub.getOrderDocument.mockReturnValue(of(makeDoc()));
    component.load();
    expect(component.doc?.uuid).toBe('AAA-BBB');
  });

  it('stamps and shows the resulting document', async () => {
    await setup();
    component.stamp();
    expect(cfdiStub.stampOrder).toHaveBeenCalledWith(7);
    expect(component.doc?.status).toBe('stamped');
  });

  it('on 409 offers the link path (marketplace handled)', async () => {
    await setup();
    cfdiStub.stampOrder.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 409, error: { code: 'apiErrors.cfdi.marketplaceHandled' } })),
    );
    component.stamp();
    expect(component.marketplaceHandled).toBe(true);
    expect(component.showLink).toBe(true);
    expect(component.doc).toBeNull();
  });

  it('flags issuer-not-configured', async () => {
    await setup();
    cfdiStub.stampOrder.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 400, error: { code: 'apiErrors.cfdi.issuerNotConfigured' } })),
    );
    component.stamp();
    expect(component.issuerMissing).toBe(true);
  });

  it('links an external UUID', async () => {
    await setup();
    component.linkUuid = '11111111-2222-3333-4444-555555555555';
    component.link();
    expect(cfdiStub.linkExternal).toHaveBeenCalledWith(7, '11111111-2222-3333-4444-555555555555', undefined);
    expect(component.doc?.invoicing_source).toBe('marketplace_handled');
    expect(component.showLink).toBe(false);
  });

  it('does not link an empty UUID', async () => {
    await setup();
    component.linkUuid = '   ';
    component.link();
    expect(cfdiStub.linkExternal).not.toHaveBeenCalled();
  });
});
