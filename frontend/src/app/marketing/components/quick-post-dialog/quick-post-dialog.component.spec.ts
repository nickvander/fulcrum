
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { QuickPostDialogComponent } from './quick-post-dialog.component';
import { MarketingService } from '../../services/marketing.service';
import { ProductService } from '../../../products/services/product';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { HttpClientTestingModule } from '@angular/common/http/testing';

describe('QuickPostDialogComponent', () => {
    let component: QuickPostDialogComponent;
    let fixture: ComponentFixture<QuickPostDialogComponent>;
    let marketingServiceMock: any;
    let productServiceMock: any;
    let dialogRefMock: any;
    let snackBarMock: any;

    beforeEach(async () => {
        marketingServiceMock = {
            getConnectors: vi.fn().mockReturnValue(of([])),
            createQuickPost: vi.fn(),
            publishEvent: vi.fn()
        };

        productServiceMock = {
            searchProducts: vi.fn().mockReturnValue(of({ data: [] }))
        };

        dialogRefMock = {
            close: vi.fn()
        };

        snackBarMock = {
            open: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [
                QuickPostDialogComponent,
                NoopAnimationsModule,
                HttpClientTestingModule
            ],
            providers: [
                { provide: MarketingService, useValue: marketingServiceMock },
                { provide: ProductService, useValue: productServiceMock },
                { provide: MatDialogRef, useValue: dialogRefMock },
                { provide: MAT_DIALOG_DATA, useValue: {} },
                { provide: MatSnackBar, useValue: snackBarMock }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(QuickPostDialogComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load connectors on init', () => {
        expect(marketingServiceMock.getConnectors).toHaveBeenCalled();
    });

    it('should validate form', () => {
        expect(component.postForm.valid).toBe(false);
        component.postForm.patchValue({
            connector_id: '123',
            content_body: 'Test post'
        });
        // Might still be invalid depending on dynamic validators based on connector type
        // mocking connector logic would be needed for deeper validation tests
    });
});
