import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

import { AlertFormDialogComponent, AlertFormDialogData } from './alert-form-dialog.component';

describe('AlertFormDialogComponent', () => {
  let component: AlertFormDialogComponent;
  let fixture: ComponentFixture<AlertFormDialogComponent>;
  let closeSpy: ReturnType<typeof vi.fn>;

  async function setup(data: AlertFormDialogData) {
    closeSpy = vi.fn();
    await TestBed.configureTestingModule({
      imports: [
        AlertFormDialogComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: MatDialogRef, useValue: { close: closeSpy } },
        { provide: MAT_DIALOG_DATA, useValue: data },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(AlertFormDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  it('offers the ML Full stockout + reputation risk types in create mode', async () => {
    await setup({ mode: 'create' });
    expect(component.alertTypes).toContain('ml_full_stockout_risk');
    expect(component.alertTypes).toContain('reputation_risk');
  });

  it('maps each alert type to its own threshold hint key', async () => {
    await setup({ mode: 'create' });
    component.form.get('alert_type')?.setValue('ml_full_stockout_risk');
    expect(component.thresholdHintKey()).toBe('alerts.form.thresholdHintMlFullStockout');
    component.form.get('alert_type')?.setValue('reputation_risk');
    expect(component.thresholdHintKey()).toBe('alerts.form.thresholdHintReputation');
    component.form.get('alert_type')?.setValue('low_margin');
    expect(component.thresholdHintKey()).toBe('alerts.form.thresholdHintLowMargin');
    component.form.get('alert_type')?.setValue('stockout_risk');
    expect(component.thresholdHintKey()).toBe('alerts.form.thresholdHintStockoutRisk');
  });

  it('submits a create payload carrying the chosen alert type', async () => {
    await setup({ mode: 'create' });
    component.form.patchValue({
      alert_type: 'ml_full_stockout_risk', threshold: 3, window_days: 30,
      cooldown_minutes: 720, notify_email: 'ops@example.com', enabled: true,
    });
    component.submit();
    expect(closeSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        mode: 'create',
        payload: expect.objectContaining({ alert_type: 'ml_full_stockout_risk', threshold: 3 }),
      }),
    );
  });
});
