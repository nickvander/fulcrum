
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { QuickPostDetailDialogComponent } from './quick-post-detail-dialog.component';
import { MarketingService } from '../../services/marketing.service';
import { ProductService } from '../../../products/services/product';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { of } from 'rxjs';

describe('QuickPostDetailDialogComponent', () => {
    let component: QuickPostDetailDialogComponent;
    let fixture: ComponentFixture<QuickPostDetailDialogComponent>;
    let marketingServiceMock: any;
    let productServiceMock: any;
    let dialogRefMock: any;
    let dialogMock: any;
    let snackBarMock: any;

    const mockPost = {
        id: '1',
        name: 'Test Post',
        channel_type: 'social',
        status: 'draft',
        content_body: 'Body',
        created_at: new Date().toISOString()
    };

    beforeEach(async () => {
        marketingServiceMock = {
            updateEvent: vi.fn().mockReturnValue(of({})),
            publishEvent: vi.fn(),
        };

        productServiceMock = {
            getProductById: vi.fn().mockReturnValue(of({ data: [] }))
        };

        dialogRefMock = {
            close: vi.fn()
        };

        dialogMock = {
            open: vi.fn()
        };

        snackBarMock = {
            open: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [
                QuickPostDetailDialogComponent,
                NoopAnimationsModule,
                HttpClientTestingModule
            ],
            providers: [
                { provide: MarketingService, useValue: marketingServiceMock },
                { provide: ProductService, useValue: productServiceMock },
                { provide: MatDialogRef, useValue: dialogRefMock },
                { provide: MAT_DIALOG_DATA, useValue: { post: mockPost } },
                { provide: MatDialog, useValue: dialogMock },
                { provide: MatSnackBar, useValue: snackBarMock }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(QuickPostDetailDialogComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize content from data', () => {
        expect(component.post.name).toBe('Test Post');
        expect(component.editForm.get('name')?.value).toBe('Test Post');
    });

    it('should toggle edit mode', () => {
        expect(component.isEditing).toBe(false);
        component.startEdit();
        expect(component.isEditing).toBe(true);
        component.cancelEdit();
        expect(component.isEditing).toBe(false);
    });

    it('should call updateEvent on save', () => {
        component.startEdit();
        component.editForm.patchValue({ name: 'Updated' });
        component.saveChanges();
        expect(marketingServiceMock.updateEvent).toHaveBeenCalled();
    });
});
