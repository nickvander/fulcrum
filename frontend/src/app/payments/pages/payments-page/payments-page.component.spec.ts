import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { PaymentsPageComponent } from './payments-page.component';
import {
  Payment,
  PaymentsService,
} from '../../services/payments.service';

function payment(overrides: Partial<Payment> = {}): Payment {
  return {
    id: 1,
    sales_order_id: null,
    user_id: 1,
    provider: 'mercado_pago',
    external_payment_id: 'MP-1',
    status: 'approved',
    amount: 199.0,
    currency: 'MXN',
    payer_email: 'alice@example.com',
    raw_response: null,
    last_webhook_payload: null,
    error_message: null,
    created_at: '2026-05-18T10:00:00Z',
    updated_at: null,
    ...overrides,
  };
}

describe('PaymentsPageComponent', () => {
  let fixture: ComponentFixture<PaymentsPageComponent>;
  let component: PaymentsPageComponent;
  let paymentsStub: {
    list: ReturnType<typeof vi.fn>;
    get: ReturnType<typeof vi.fn>;
  };
  let dialogStub: { open: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    paymentsStub = {
      list: vi.fn().mockReturnValue(of({ items: [], total: 0 })),
      get: vi.fn().mockReturnValue(of(payment())),
    };
    dialogStub = {
      open: vi.fn().mockReturnValue({
        afterClosed: () => of(null),
      } as MatDialogRef<unknown>),
    };

    await TestBed.configureTestingModule({
      imports: [
        PaymentsPageComponent,
        NoopAnimationsModule,
        MatDialogModule,
        MatSnackBarModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: PaymentsService, useValue: paymentsStub },
        { provide: MatDialog, useValue: dialogStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PaymentsPageComponent);
    component = fixture.componentInstance;
    // Standalone MatDialogModule provides its own MatDialog after our
    // root-level override. Replace the private field directly — same
    // pattern AlertsPageComponentSpec uses.
    (component as unknown as { dialog: typeof dialogStub }).dialog = dialogStub;
    fixture.detectChanges();
  });

  it('loads on init and renders the empty state when no payments exist', () => {
    expect(paymentsStub.list).toHaveBeenCalledTimes(1);
    expect(paymentsStub.list).toHaveBeenCalledWith({
      status: null, skip: 0, limit: 25,
    });
    const empty = fixture.debugElement.query(By.css('[data-testid="payments-empty-state"]'));
    expect(empty).not.toBeNull();
  });

  it('renders one table row per payment + the total count from the envelope', () => {
    paymentsStub.list.mockReturnValue(of({
      items: [payment({ id: 1 }), payment({ id: 2, status: 'pending' })],
      total: 12,
    }));
    component.refresh();
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('[data-testid="payment-row-1"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="payment-row-2"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="payments-empty-state"]'))).toBeNull();
    expect(component.total).toBe(12);
  });

  it('onStatusChange resets the page index and re-fetches with the new status', () => {
    component.pageIndex = 4;
    component.selectedStatus = 'rejected';
    paymentsStub.list.mockClear();
    component.onStatusChange();

    expect(component.pageIndex).toBe(0);
    expect(paymentsStub.list).toHaveBeenCalledWith({
      status: 'rejected', skip: 0, limit: 25,
    });
  });

  it("onStatusChange treats 'all' as no filter (sends status=null)", () => {
    component.selectedStatus = 'all';
    paymentsStub.list.mockClear();
    component.onStatusChange();
    expect(paymentsStub.list).toHaveBeenCalledWith({
      status: null, skip: 0, limit: 25,
    });
  });

  it('onPage updates page index + size and re-fetches with the right skip', () => {
    paymentsStub.list.mockClear();
    component.onPage({ pageIndex: 3, pageSize: 50, length: 200 });
    expect(component.pageIndex).toBe(3);
    expect(component.pageSize).toBe(50);
    expect(paymentsStub.list).toHaveBeenCalledWith({
      status: null, skip: 150, limit: 50,
    });
  });

  it('openDetail opens the dialog with the payment in its data', () => {
    const p = payment({ id: 77 });
    component.openDetail(p);
    expect(dialogStub.open).toHaveBeenCalled();
    const args = dialogStub.open.mock.calls[0];
    expect(args[1].data.payment).toBe(p);
  });

  it('failed list() leaves payments empty and stops loading', () => {
    paymentsStub.list.mockReturnValueOnce(throwError(() => new Error('boom')));
    component.refresh();
    fixture.detectChanges();
    expect(component.payments.length).toBe(0);
    expect(component.loading).toBe(false);
  });

  it('formatAmount renders amount with two decimals + currency', () => {
    expect(component.formatAmount(payment({ amount: 199, currency: 'MXN' }))).toBe('199.00 MXN');
    expect(component.formatAmount(payment({ amount: 12.5, currency: 'USD' }))).toBe('12.50 USD');
  });

  it('formatTimestamp returns em-dash for null', () => {
    expect(component.formatTimestamp(null)).toBe('—');
    expect(component.formatTimestamp('2026-05-18T10:00:00Z')).not.toBe('—');
  });

  it('statusClass returns a CSS-prefixed class', () => {
    expect(component.statusClass('approved')).toBe('status-approved');
    expect(component.statusClass('rejected')).toBe('status-rejected');
  });
});
