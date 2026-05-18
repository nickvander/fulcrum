import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { TranslocoTestingModule } from '@ngneat/transloco';

import { PaymentDetailDialogComponent } from './payment-detail-dialog.component';
import { Payment } from '../../services/payments.service';

function payment(overrides: Partial<Payment> = {}): Payment {
  return {
    id: 7,
    sales_order_id: 42,
    user_id: 1,
    provider: 'mercado_pago',
    external_payment_id: 'MP-PAY-9001',
    status: 'approved',
    amount: 199.0,
    currency: 'MXN',
    payer_email: 'alice@example.com',
    raw_response: null,
    last_webhook_payload: null,
    error_message: null,
    created_at: '2026-05-18T10:00:00Z',
    updated_at: '2026-05-18T10:01:00Z',
    ...overrides,
  };
}

describe('PaymentDetailDialogComponent', () => {
  let fixture: ComponentFixture<PaymentDetailDialogComponent>;
  let component: PaymentDetailDialogComponent;
  const dialogRefStub = { close: vi.fn() } as unknown as MatDialogRef<PaymentDetailDialogComponent>;

  async function setup(p: Payment): Promise<void> {
    // Each test reconfigures with a different MAT_DIALOG_DATA, so we
    // reset before reconfiguring or TestBed throws "module already
    // instantiated".
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [
        PaymentDetailDialogComponent,
        NoopAnimationsModule,
        MatDialogModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: MatDialogRef, useValue: dialogRefStub },
        { provide: MAT_DIALOG_DATA, useValue: { payment: p } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PaymentDetailDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  it('binds the payment from MAT_DIALOG_DATA onto the component', async () => {
    const p = payment();
    await setup(p);
    expect(component.payment).toBe(p);
  });

  it('renders the status chip', async () => {
    await setup(payment({ status: 'approved' }));
    const chip = fixture.debugElement.query(By.css('[data-testid="payment-detail-status"]'));
    expect(chip).not.toBeNull();
    expect(chip.nativeElement.classList.contains('status-approved')).toBe(true);
  });

  it('shows the error block only when an error_message is present', async () => {
    await setup(payment({ error_message: null }));
    expect(fixture.debugElement.query(By.css('[data-testid="payment-detail-error"]'))).toBeNull();

    await setup(payment({ error_message: 'cc_rejected_insufficient_amount' }));
    const err = fixture.debugElement.query(By.css('[data-testid="payment-detail-error"]'));
    expect(err).not.toBeNull();
    expect(err.nativeElement.textContent).toContain('cc_rejected_insufficient_amount');
  });

  it('shows the raw-response block only when a raw_response is present', async () => {
    await setup(payment({ raw_response: null }));
    expect(fixture.debugElement.query(By.css('[data-testid="payment-detail-raw"]'))).toBeNull();

    await setup(payment({ raw_response: { id: 'MP-PAY-9001', status: 'approved' } }));
    const raw = fixture.debugElement.query(By.css('[data-testid="payment-detail-raw"]'));
    expect(raw).not.toBeNull();
    expect(raw.nativeElement.textContent).toContain('MP-PAY-9001');
  });

  it('shows the last-webhook block only when a webhook payload is present', async () => {
    await setup(payment({ last_webhook_payload: null }));
    expect(fixture.debugElement.query(By.css('[data-testid="payment-detail-webhook"]'))).toBeNull();

    await setup(payment({ last_webhook_payload: { type: 'payment', data: { id: 'MP-PAY-9001' } } }));
    const wh = fixture.debugElement.query(By.css('[data-testid="payment-detail-webhook"]'));
    expect(wh).not.toBeNull();
  });

  it('close() delegates to the dialog ref', async () => {
    await setup(payment());
    component.close();
    expect(dialogRefStub.close).toHaveBeenCalled();
  });

  it('formatJson pretty-prints the object with 2-space indentation', async () => {
    await setup(payment());
    expect(component.formatJson({ a: 1 })).toBe('{\n  "a": 1\n}');
    expect(component.formatJson(null)).toBe('');
  });

  it('formatTimestamp returns em-dash for null', async () => {
    await setup(payment());
    expect(component.formatTimestamp(null)).toBe('—');
    expect(component.formatTimestamp(undefined)).toBe('—');
  });
});
