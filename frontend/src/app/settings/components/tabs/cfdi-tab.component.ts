import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import { MaterialModule } from '../../../shared/material.module';
import { CfdiService } from '../../../core/services/cfdi.service';
import { NotificationService } from '../../../core/services/notification.service';

/**
 * Settings → CFDI: the seller's tax identity (emisor) used by the factura
 * export. Without RFC / razón social / régimen fiscal on file, the
 * `/reports/cfdi` export warns it isn't issuer-ready. Export-only — no
 * timbrado happens here.
 */
@Component({
  selector: 'app-cfdi-tab',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TranslocoModule,
    MaterialModule,
  ],
  templateUrl: './cfdi-tab.component.html',
  styleUrls: ['./cfdi-tab.component.scss'],
})
export class CfdiTabComponent implements OnInit {
  form: FormGroup;
  loading = false;
  saving = false;
  isConfigured = false;

  constructor(
    private fb: FormBuilder,
    private cfdi: CfdiService,
    private notify: NotificationService,
    private transloco: TranslocoService,
  ) {
    this.form = this.fb.group({
      rfc: [''],
      name: [''],
      tax_regime: [''],
      postal_code: [''],
      default_product_key: ['01010101'],
      default_unit_key: ['H87'],
      cfdi_use: ['S01'],
      iva_rate: [0.16],
    });
  }

  ngOnInit(): void {
    this.loading = true;
    this.cfdi
      .getConfig()
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (cfg) => {
          this.isConfigured = cfg.is_configured;
          this.form.patchValue({
            rfc: cfg.rfc ?? '',
            name: cfg.name ?? '',
            tax_regime: cfg.tax_regime ?? '',
            postal_code: cfg.postal_code ?? '',
            default_product_key: cfg.default_product_key,
            default_unit_key: cfg.default_unit_key,
            cfdi_use: cfg.cfdi_use,
            iva_rate: cfg.iva_rate,
          });
        },
        error: () => {},
      });
  }

  save(): void {
    if (this.saving) return;
    this.saving = true;
    this.cfdi
      .saveConfig(this.form.value)
      .pipe(finalize(() => (this.saving = false)))
      .subscribe({
        next: (cfg) => {
          this.isConfigured = cfg.is_configured;
          this.notify.showSuccess(this.transloco.translate('settings.cfdi.saved'));
        },
        error: (err) => {
          this.notify.showApiError(err, 'settings.cfdi.saveError');
        },
      });
  }
}
