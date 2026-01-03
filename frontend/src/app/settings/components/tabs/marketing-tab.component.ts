import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { TranslocoModule } from '@ngneat/transloco';
import { MaterialModule } from '../../../shared/material.module';
import { NotificationService } from '../../../core/services/notification.service';
import { environment } from '../../../../environments/environment';

@Component({
    selector: 'app-marketing-tab',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, TranslocoModule, MaterialModule],
    templateUrl: './marketing-tab.component.html',
    styleUrls: ['./marketing-tab.component.scss']
})
export class MarketingTabComponent implements OnInit {
    smtpForm: FormGroup;
    smtpConfigured = false;
    testingSmtp = false;
    savingSmtp = false;
    private readonly apiUrl = environment.apiUrl;

    constructor(
        private fb: FormBuilder,
        private http: HttpClient,
        private notificationService: NotificationService
    ) {
        this.smtpForm = this.fb.group({
            provider: ['gmail'],
            host: [''],
            port: [587],
            username: ['', [Validators.required, Validators.email]],
            password: [''],
            from_name: [''],
        });
    }

    ngOnInit(): void {
        this.loadSmtpSettings();
    }

    loadSmtpSettings(): void {
        this.http.get<any>(`${this.apiUrl}/settings/smtp`).subscribe({
            next: (config) => {
                this.smtpForm.patchValue({
                    provider: config.provider || 'gmail',
                    host: config.host || '',
                    port: config.port || 587,
                    username: config.username || '',
                    from_name: config.from_name || '',
                }, { emitEvent: false });
                this.smtpConfigured = config.is_configured;
            },
            error: (err) => console.error('Failed to load SMTP settings', err)
        });
    }

    onProviderChange(provider: string): void {
        if (provider !== 'custom') {
            this.smtpForm.patchValue({ host: '', port: 587 });
        }
    }

    onSmtpSubmit(): void {
        if (!this.smtpForm.valid) return;
        this.savingSmtp = true;
        this.http.post<any>(`${this.apiUrl}/settings/smtp`, this.smtpForm.value).subscribe({
            next: () => {
                this.savingSmtp = false;
                this.smtpConfigured = true;
                this.notificationService.showSuccess('Email settings saved!');
            },
            error: (err) => {
                this.savingSmtp = false;
                this.notificationService.showError('Failed to save email settings');
            }
        });
    }

    testSmtp(): void {
        this.testingSmtp = true;
        this.http.post<any>(`${this.apiUrl}/settings/smtp/test`, {}).subscribe({
            next: (result) => {
                this.testingSmtp = false;
                if (result.success) this.notificationService.showSuccess('SMTP connection successful!');
                else this.notificationService.showError(result.error || 'Connection failed');
            },
            error: (err) => { this.testingSmtp = false; this.notificationService.showError('Connection test failed'); }
        });
    }
}
