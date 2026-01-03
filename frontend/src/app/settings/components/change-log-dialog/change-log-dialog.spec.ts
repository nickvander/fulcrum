import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ChangeLogDialog } from './change-log-dialog';
import { IntegrationsService } from '../../services/integrations.service';
import { MatDialogRef } from '@angular/material/dialog';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of } from 'rxjs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';

describe('ChangeLogDialog', () => {
    let component: ChangeLogDialog;
    let fixture: ComponentFixture<ChangeLogDialog>;
    let mockIntegrationsService: any;
    let mockDialogRef: any;

    beforeEach(async () => {
        mockIntegrationsService = {
            getChangeLogs: vi.fn().mockReturnValue(of({ entries: [], total: 0 }))
        };

        mockDialogRef = {
            close: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [
                ChangeLogDialog, // Standalone
                TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } }),
                NoopAnimationsModule,
                HttpClientTestingModule
            ],
            providers: [
                { provide: IntegrationsService, useValue: mockIntegrationsService },
                { provide: MatDialogRef, useValue: mockDialogRef }
            ]
        }).compileComponents();
    });

    beforeEach(() => {
        fixture = TestBed.createComponent(ChangeLogDialog);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load change logs on init', () => {
        expect(mockIntegrationsService.getChangeLogs).toHaveBeenCalled();
    });

    it('should close dialog when close is called', () => {
        component.close();
        expect(mockDialogRef.close).toHaveBeenCalled();
    });
});
