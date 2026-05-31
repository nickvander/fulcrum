import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatNativeDateModule } from '@angular/material/core';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { MaterialModule } from '../../../shared/material.module';
import {
  CurrencyService,
  ExchangeRate,
} from '../../../core/services/currency.service';
import { NotificationService } from '../../../core/services/notification.service';

/**
 * Settings → Currency: record and review FX rates.
 *
 * Recorded rates power historical conversions — e.g. a USD order's
 * revenue is normalised to MXN at the rate that was true on the order
 * date. Without a rate on file, conversions fall back to 1.0 (an
 * estimate), so this screen is how an operator keeps margins honest.
 */
@Component({
  selector: 'app-currency-tab',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TranslocoModule,
    MaterialModule,
    MatDatepickerModule,
    MatNativeDateModule,
  ],
  templateUrl: './currency-tab.component.html',
  styleUrls: ['./currency-tab.component.scss'],
})
export class CurrencyTabComponent implements OnInit {
  form: FormGroup;
  rates: ExchangeRate[] = [];
  loading = false;
  saving = false;
  displayedColumns = ['pair', 'rate', 'date', 'source'];

  /** Upper bound for the rate-date picker — an FX rate can't be future-dated. */
  readonly today = new Date();

  /** Common currencies an MX operator sources/sells in. The pair fields
   *  are free-form too, but these cover the 99% case. */
  readonly currencyOptions = ['MXN', 'USD', 'EUR', 'GBP', 'CAD', 'BRL', 'JPY', 'CNY'];

  constructor(
    private fb: FormBuilder,
    private currency: CurrencyService,
    private notify: NotificationService,
    private transloco: TranslocoService,
  ) {
    this.form = this.fb.group({
      base_currency: ['USD', [Validators.required]],
      quote_currency: ['MXN', [Validators.required]],
      rate: [null, [Validators.required, Validators.min(0.0000001)]],
      rate_date: [null],
    });
  }

  ngOnInit(): void {
    this.loadRates();
  }

  loadRates(): void {
    this.loading = true;
    this.currency.listRates({ limit: 200 }).subscribe({
      next: (rows) => {
        this.rates = rows;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.notify.showApiError(err, 'settings.currency.loadError');
      },
    });
  }

  onSubmit(): void {
    if (!this.form.valid || this.saving) return;
    // Guard against a same-currency pair, which is a meaningless 1:1.
    const { base_currency, quote_currency } = this.form.value;
    if ((base_currency || '').toUpperCase() === (quote_currency || '').toUpperCase()) {
      this.notify.showError(this.transloco.translate('settings.currency.samePairError'));
      return;
    }

    this.saving = true;
    const v = this.form.value;
    this.currency
      .recordRate({
        base_currency: v.base_currency,
        quote_currency: v.quote_currency,
        rate: v.rate,
        // Normalise a Date (from the picker) or a string to YYYY-MM-DD.
        rate_date: this.toIsoDate(v.rate_date),
        source: 'manual',
      })
      .subscribe({
        next: (saved) => {
          this.saving = false;
          this.notify.showSuccess(
            this.transloco.translate('settings.currency.savedSnackbar', {
              base: saved.base_currency,
              quote: saved.quote_currency,
            }),
          );
          this.form.patchValue({ rate: null, rate_date: null });
          this.form.get('rate')?.markAsUntouched();
          this.loadRates();
        },
        error: (err) => {
          this.saving = false;
          this.notify.showApiError(err, 'settings.currency.saveError');
        },
      });
  }

  /** Accepts a Date (mat-datepicker) or an ISO string; returns YYYY-MM-DD
   *  or null. Uses local date parts so a picked day isn't shifted by the
   *  UTC offset. */
  private toIsoDate(value: unknown): string | null {
    if (!value) return null;
    if (value instanceof Date) {
      const y = value.getFullYear();
      const m = String(value.getMonth() + 1).padStart(2, '0');
      const d = String(value.getDate()).padStart(2, '0');
      return `${y}-${m}-${d}`;
    }
    return String(value).slice(0, 10);
  }
}
