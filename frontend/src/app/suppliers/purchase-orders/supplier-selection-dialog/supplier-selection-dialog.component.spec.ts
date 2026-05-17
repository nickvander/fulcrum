
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SupplierSelectionDialogComponent } from './supplier-selection-dialog.component';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('SupplierSelectionDialogComponent', () => {
    let component: SupplierSelectionDialogComponent;
    let fixture: ComponentFixture<SupplierSelectionDialogComponent>;
    let dialogRefMock: any;

    const mockData = {
        productName: 'Test Product',
        suppliers: []
    };

    beforeEach(async () => {
        dialogRefMock = {
            close: vi.fn()
        };

        await TestBed.configureTestingModule({
            declarations: [],
            imports: [
        TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } }),SupplierSelectionDialogComponent, MatDialogModule, MatListModule, MatIconModule, MatButtonModule, NoopAnimationsModule],
            providers: [
                { provide: MatDialogRef, useValue: dialogRefMock },
                { provide: MAT_DIALOG_DATA, useValue: mockData }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(SupplierSelectionDialogComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should close dialog when cancel is called', () => {
        component.cancel();
        expect(dialogRefMock.close).toHaveBeenCalledWith(null);
    });
});
