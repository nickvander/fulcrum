import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AiTabComponent } from './ai-tab.component';
import { SettingsService } from '../../../core/services/settings.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ReactiveFormsModule } from '@angular/forms';

// Mock Transloco if specific module helper not available
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('AiTabComponent', () => {
    let component: AiTabComponent;
    let fixture: ComponentFixture<AiTabComponent>;
    let settingsServiceSpy: any;
    let snackBarSpy: any;

    beforeEach(async () => {
        settingsServiceSpy = {
            updateStoreSettings: vi.fn(),
            storeSettings$: of({
                ai_config: {
                    enabled: true,
                    provider: 'google',
                    model: '',
                    google_configured: true,
                    openai_configured: false,
                    anthropic_configured: false,
                    qwen_configured: false
                }
            })
        };
        snackBarSpy = {
            open: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [
                AiTabComponent,
                NoopAnimationsModule,
                ReactiveFormsModule,
                TranslocoTestingModule.forRoot({
                    langs: {
                        en: {},
                        es: {}
                    },
                    translocoConfig: {
                        availableLangs: ['en', 'es'],
                        defaultLang: 'en',
                        reRenderOnLangChange: true
                    }
                })
            ],
            providers: [
                { provide: SettingsService, useValue: settingsServiceSpy },
                { provide: MatSnackBar, useValue: snackBarSpy }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(AiTabComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should display configured status based on settings', () => {
        expect(component.aiConfig?.google_configured).toBe(true);
        expect(component.aiConfig?.openai_configured).toBe(false);
        expect(component.aiConfig?.enabled).toBe(true);
    });

    it('should call updateStoreSettings when saving', () => {
        component.aiForm.patchValue({
            ai_google_api_key: 'new-key',
            ai_provider: 'openai'
        });
        settingsServiceSpy.updateStoreSettings.mockReturnValue(of({}));

        component.saveSettings();

        expect(settingsServiceSpy.updateStoreSettings).toHaveBeenCalledWith(expect.objectContaining({
            ai_google_api_key: 'new-key',
            ai_provider: 'openai',
            ai_enabled: true // from initialization
        }));
        expect(snackBarSpy.open).toHaveBeenCalled();
    });
});
