
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ConnectorSettingsComponent } from './connector-settings.component';
import { MarketingService } from '../../services/marketing.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ActivatedRoute } from '@angular/router';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('ConnectorSettingsComponent', () => {
    let component: ConnectorSettingsComponent;
    let fixture: ComponentFixture<ConnectorSettingsComponent>;
    let marketingServiceMock: any;
    let snackBarMock: any;
    let dialogMock: any;

    beforeEach(async () => {
        marketingServiceMock = {
            getConnectors: vi.fn().mockReturnValue(of([])),
            createConnector: vi.fn(),
            updateConnector: vi.fn(),
            testConnector: vi.fn(),
            deleteConnector: vi.fn()
        };

        snackBarMock = {
            open: vi.fn()
        };

        dialogMock = {
            open: vi.fn().mockReturnValue({
                afterClosed: () => of(true)
            })
        };

        await TestBed.configureTestingModule({
            imports: [
                ConnectorSettingsComponent,
                NoopAnimationsModule,
                HttpClientTestingModule,
                TranslocoTestingModule.forRoot({
                    langs: { en: {}, 'es-MX': {} },
                    translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' }
                })
            ],
            providers: [
                { provide: MarketingService, useValue: marketingServiceMock },
                { provide: MatSnackBar, useValue: snackBarMock },
                { provide: MatDialog, useValue: dialogMock },
                {
                    provide: ActivatedRoute,
                    useValue: {
                        snapshot: { paramMap: { get: () => null } }
                    }
                }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(ConnectorSettingsComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load connectors on init', () => {
        expect(marketingServiceMock.getConnectors).toHaveBeenCalled();
    });

    it('should open email setup', () => {
        component.openEmailSetup('gmail');
        expect(component.showEmailSetup).toBe(true);
        expect(component.emailForm.get('provider')?.value).toBe('gmail');
    });

    it('should open social setup', () => {
        component.openSocialSetup('instagram');
        expect(component.showSocialSetup).toBe(true);
        expect(component.selectedProviderKey).toBe('instagram');
    });
});
