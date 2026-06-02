import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { CfdiTabComponent } from './cfdi-tab.component';
import { CfdiService, CfdiIssuerConfig } from '../../../core/services/cfdi.service';
import { NotificationService } from '../../../core/services/notification.service';


const CONFIG: CfdiIssuerConfig = {
  rfc: 'AAA010101AAA', name: 'Tienda', tax_regime: '601', postal_code: '06000',
  default_product_key: '01010101', default_unit_key: 'H87', cfdi_use: 'S01',
  iva_rate: 0.16, is_configured: true,
};


describe('CfdiTabComponent', () => {
  let component: CfdiTabComponent;
  let fixture: ComponentFixture<CfdiTabComponent>;
  let cfdiStub: { getConfig: ReturnType<typeof vi.fn>; saveConfig: ReturnType<typeof vi.fn> };
  let notifyStub: {
    showSuccess: ReturnType<typeof vi.fn>;
    showError: ReturnType<typeof vi.fn>;
    showApiError: ReturnType<typeof vi.fn>;
  };

  async function setup(cfg: CfdiIssuerConfig = CONFIG) {
    cfdiStub = {
      getConfig: vi.fn().mockReturnValue(of(cfg)),
      saveConfig: vi.fn().mockReturnValue(of(cfg)),
    };
    notifyStub = { showSuccess: vi.fn(), showError: vi.fn(), showApiError: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [
        CfdiTabComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: CfdiService, useValue: cfdiStub },
        { provide: NotificationService, useValue: notifyStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CfdiTabComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  it('loads and patches the issuer config on init', async () => {
    await setup();
    expect(cfdiStub.getConfig).toHaveBeenCalled();
    expect(component.form.value.rfc).toBe('AAA010101AAA');
    expect(component.isConfigured).toBe(true);
  });

  it('saves the config and notifies on success', async () => {
    await setup();
    component.form.patchValue({ rfc: 'BBB020202BBB' });
    component.save();
    expect(cfdiStub.saveConfig).toHaveBeenCalled();
    expect(notifyStub.showSuccess).toHaveBeenCalled();
  });

  it('surfaces an API error on save failure', async () => {
    await setup();
    cfdiStub.saveConfig.mockReturnValue(throwError(() => new Error('boom')));
    component.save();
    expect(notifyStub.showApiError).toHaveBeenCalled();
  });

  it('reflects an incomplete issuer config', async () => {
    await setup({ ...CONFIG, is_configured: false });
    expect(component.isConfigured).toBe(false);
  });
});
