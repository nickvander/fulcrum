import { ComponentFixture, TestBed } from '@angular/core/testing';
import { QuickProductDialogComponent } from './quick-product-dialog.component';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule, MatDialog } from '@angular/material/dialog';
import { ProductService } from '../../../products/services/product';
import { Router } from '@angular/router';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { of } from 'rxjs';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatButtonModule } from '@angular/material/button';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { vi } from 'vitest';
import { CommonModule } from '@angular/common';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';

describe('QuickProductDialogComponent', () => {
    let component: QuickProductDialogComponent;
    let fixture: ComponentFixture<QuickProductDialogComponent>;
    let productServiceMock: any;
    let dialogRefMock: any;
    let routerMock: any;

    beforeEach(async () => {
        productServiceMock = {
            createProduct: vi.fn()
        };
        dialogRefMock = {
            close: vi.fn()
        };
        routerMock = {
            navigate: vi.fn()
        };

        await TestBed.configureTestingModule({
            declarations: [QuickProductDialogComponent],
            imports: [
                CommonModule,
                ReactiveFormsModule,
                MatDialogModule,
                MatFormFieldModule,
                MatInputModule,
                MatCheckboxModule,
                MatButtonModule,
                BrowserAnimationsModule
            ],
            providers: [
                FormBuilder,
                { provide: MAT_DIALOG_DATA, useValue: { suggestedName: 'Test Product' } },
                { provide: MatDialogRef, useValue: dialogRefMock },
                { provide: ProductService, useValue: productServiceMock },
                { provide: Router, useValue: routerMock },
                { provide: MatDialog, useValue: {} }
            ],
            schemas: [CUSTOM_ELEMENTS_SCHEMA]
        })
            .compileComponents();

        fixture = TestBed.createComponent(QuickProductDialogComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize form with data', () => {
        expect(component.productForm.get('name')?.value).toBe('Test Product');
    });

    it('should call createProduct on submit', () => {
        component.productForm.patchValue({ name: 'New Product', cost_price: 10 });
        productServiceMock.createProduct.mockReturnValue(of({ id: 123, name: 'New Product' }));

        component.onSubmit(false);
        expect(productServiceMock.createProduct).toHaveBeenCalled();
        expect(dialogRefMock.close).toHaveBeenCalled();
    });
});
