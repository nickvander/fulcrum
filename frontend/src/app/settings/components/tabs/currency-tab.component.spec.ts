import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { of, throwError } from 'rxjs';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { CurrencyTabComponent } from './currency-tab.component';
import { CurrencyService, ExchangeRate } from '../../../core/services/currency.service';
import { NotificationService } from '../../../core/services/notification.service';

describe('CurrencyTabComponent', () => {
  let component: CurrencyTabComponent;
  let fixture: ComponentFixture<CurrencyTabComponent>;
  let currencyStub: {
    listRates: ReturnType<typeof vi.fn>;
    recordRate: ReturnType<typeof vi.fn>;
  };
  let notifyStub: {
    showSuccess: ReturnType<typeof vi.fn>;
    showError: ReturnType<typeof vi.fn>;
    showApiError: ReturnType<typeof vi.fn>;
  };

  const rate: ExchangeRate = {
    id: 1, base_currency: 'USD', quote_currency: 'MXN',
    rate: 18.5, rate_date: '2026-03-01', source: 'manual',
  };

  async function setup(rates: ExchangeRate[] = [rate]) {
    currencyStub = {
      listRates: vi.fn().mockReturnValue(of(rates)),
      recordRate: vi.fn().mockReturnValue(of(rate)),
    };
    notifyStub = {
      showSuccess: vi.fn(),
      showError: vi.fn(),
      showApiError: vi.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [
        CurrencyTabComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: CurrencyService, useValue: currencyStub },
        { provide: NotificationService, useValue: notifyStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CurrencyTabComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  it('loads rates on init and renders them', async () => {
    await setup();
    expect(currencyStub.listRates).toHaveBeenCalled();
    expect(component.rates.length).toBe(1);
    const table = fixture.debugElement.query(By.css('[data-testid="rates-table"]'));
    expect(table).not.toBeNull();
  });

  it('shows the empty state when no rates exist', async () => {
    await setup([]);
    expect(
      fixture.debugElement.query(By.css('[data-testid="rates-empty"]')),
    ).not.toBeNull();
  });

  it('records a rate, reloads the list, and notifies success', async () => {
    await setup();
    component.form.patchValue({
      base_currency: 'USD', quote_currency: 'MXN', rate: 18.5, rate_date: '2026-03-01',
    });
    component.onSubmit();
    expect(currencyStub.recordRate).toHaveBeenCalledWith({
      base_currency: 'USD', quote_currency: 'MXN', rate: 18.5,
      rate_date: '2026-03-01', source: 'manual',
    });
    expect(notifyStub.showSuccess).toHaveBeenCalled();
    // listRates called once on init + once after save.
    expect(currencyStub.listRates).toHaveBeenCalledTimes(2);
    // The rate field is cleared for the next entry.
    expect(component.form.value.rate).toBeNull();
  });

  it('omits rate_date when none is picked (server defaults to today)', async () => {
    await setup();
    component.form.patchValue({ base_currency: 'EUR', quote_currency: 'MXN', rate: 20, rate_date: null });
    component.onSubmit();
    expect(currencyStub.recordRate).toHaveBeenCalledWith(
      expect.objectContaining({ rate_date: null }),
    );
  });

  it('refuses a same-currency pair without calling the service', async () => {
    await setup();
    component.form.patchValue({ base_currency: 'MXN', quote_currency: 'MXN', rate: 1 });
    component.onSubmit();
    expect(currencyStub.recordRate).not.toHaveBeenCalled();
    expect(notifyStub.showError).toHaveBeenCalled();
  });

  it('does nothing while a save is already in flight', async () => {
    await setup();
    component.saving = true;
    component.form.patchValue({ base_currency: 'USD', quote_currency: 'MXN', rate: 18 });
    component.onSubmit();
    expect(currencyStub.recordRate).not.toHaveBeenCalled();
  });

  it('an invalid (empty rate) form does not submit', async () => {
    await setup();
    component.form.patchValue({ base_currency: 'USD', quote_currency: 'MXN', rate: null });
    component.onSubmit();
    expect(currencyStub.recordRate).not.toHaveBeenCalled();
  });

  it('surfaces a load failure via the notifier without crashing', async () => {
    currencyStub = {
      listRates: vi.fn().mockReturnValue(throwError(() => new Error('boom'))),
      recordRate: vi.fn(),
    };
    notifyStub = { showSuccess: vi.fn(), showError: vi.fn(), showApiError: vi.fn() };
    await TestBed.configureTestingModule({
      imports: [
        CurrencyTabComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: CurrencyService, useValue: currencyStub },
        { provide: NotificationService, useValue: notifyStub },
      ],
    }).compileComponents();
    const fresh = TestBed.createComponent(CurrencyTabComponent);
    fresh.detectChanges();
    expect(fresh.componentInstance.rates).toEqual([]);
    expect(fresh.componentInstance.loading).toBe(false);
    expect(notifyStub.showApiError).toHaveBeenCalled();
  });

  it('a save failure clears the saving flag and notifies', async () => {
    await setup();
    currencyStub.recordRate.mockReturnValueOnce(throwError(() => new Error('boom')));
    component.form.patchValue({ base_currency: 'USD', quote_currency: 'MXN', rate: 18 });
    component.onSubmit();
    expect(component.saving).toBe(false);
    expect(notifyStub.showApiError).toHaveBeenCalled();
  });
});
