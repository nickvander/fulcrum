import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { TranslocoModule } from '@ngneat/transloco';
import { SettingsService, StoreSettings } from '../../../core/services/settings.service';
import { AiService } from '../../../core/services/ai.service';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
    selector: 'app-ai-tab',
    standalone: true,
    imports: [
        CommonModule,
        ReactiveFormsModule,
        MatFormFieldModule,
        MatInputModule,
        MatButtonModule,
        MatIconModule,
        MatSelectModule,
        MatSlideToggleModule,
        TranslocoModule
    ],
    templateUrl: './ai-tab.component.html',
    styleUrls: ['./ai-tab.component.scss']
})
export class AiTabComponent implements OnInit {
    aiForm: FormGroup;
    isLoading = false;
    showOtherKeys = false;
    aiConfig: StoreSettings['ai_config'];

    private providerNames: Record<string, string> = {
        google: 'Google Gemini',
        openai: 'OpenAI',
        anthropic: 'Anthropic Claude',
        qwen: 'Qwen (Alibaba)'
    };

    constructor(
        private fb: FormBuilder,
        private settingsService: SettingsService,
        private aiService: AiService,
        private snackBar: MatSnackBar
    ) {
        this.aiForm = this.fb.group({
            ai_enabled: [false],
            ai_provider: ['google'],
            ai_model: [''],
            ai_google_api_key: [''],
            ai_openai_api_key: [''],
            ai_anthropic_api_key: [''],
            ai_qwen_api_key: ['']
        });
    }

    ngOnInit(): void {
        this.settingsService.storeSettings$.subscribe(settings => {
            if (settings?.ai_config) {
                this.aiConfig = settings.ai_config;
                this.aiForm.patchValue({
                    ai_enabled: settings.ai_config.enabled,
                    ai_provider: settings.ai_config.provider,
                    ai_model: settings.ai_config.model
                }, { emitEvent: false });
            }
        });
    }

    getProviderName(provider: string): string {
        return this.providerNames[provider] || provider;
    }

    getActiveKeyControlName(): string {
        const provider = this.aiForm.get('ai_provider')?.value || 'google';
        return `ai_${provider}_api_key`;
    }

    getKeyControlName(provider: string): string {
        return `ai_${provider}_api_key`;
    }

    isActiveProviderConfigured(): boolean {
        if (!this.aiConfig) return false;
        const provider = this.aiForm.get('ai_provider')?.value || 'google';
        return this.isProviderConfigured(provider);
    }

    isProviderConfigured(provider: string): boolean {
        if (!this.aiConfig) return false;
        switch (provider) {
            case 'google': return this.aiConfig.google_configured;
            case 'openai': return this.aiConfig.openai_configured;
            case 'anthropic': return this.aiConfig.anthropic_configured;
            case 'qwen': return this.aiConfig.qwen_configured;
            default: return false;
        }
    }

    getOtherProviders(): string[] {
        const active = this.aiForm.get('ai_provider')?.value || 'google';
        return ['google', 'openai', 'anthropic', 'qwen'].filter(p => p !== active);
    }

    saveSettings(): void {
        this.isLoading = true;
        const formValue = this.aiForm.value;

        const updatePayload: Partial<StoreSettings> = {
            ai_enabled: formValue.ai_enabled,
            ai_provider: formValue.ai_provider,
            ai_model: formValue.ai_model || null
        };

        // Only include keys that have been entered (non-empty)
        if (formValue.ai_google_api_key?.trim()) {
            updatePayload.ai_google_api_key = formValue.ai_google_api_key;
        }
        if (formValue.ai_openai_api_key?.trim()) {
            updatePayload.ai_openai_api_key = formValue.ai_openai_api_key;
        }
        if (formValue.ai_anthropic_api_key?.trim()) {
            updatePayload.ai_anthropic_api_key = formValue.ai_anthropic_api_key;
        }
        if (formValue.ai_qwen_api_key?.trim()) {
            updatePayload.ai_qwen_api_key = formValue.ai_qwen_api_key;
        }

        this.settingsService.updateStoreSettings(updatePayload as StoreSettings).subscribe({
            next: () => {
                this.snackBar.open('AI Settings saved', 'Close', { duration: 3000 });
                // Drop the AiService capability cache so AI buttons across the
                // app reflect the new enabled/key state on next subscribe.
                this.aiService.invalidateCapabilities();
                this.aiService.getCapabilities(true).subscribe();
                // Clear key fields after save (keys are stored, not shown)
                this.aiForm.patchValue({
                    ai_google_api_key: '',
                    ai_openai_api_key: '',
                    ai_anthropic_api_key: '',
                    ai_qwen_api_key: ''
                });
                this.isLoading = false;
            },
            error: (err) => {
                console.error('Error saving AI settings', err);
                this.snackBar.open('Failed to save settings', 'Close', { duration: 3000 });
                this.isLoading = false;
            }
        });
    }
}
