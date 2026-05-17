import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CostAllocationDialogComponent } from './cost-allocation-dialog.component';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { SuppliersService } from '../../suppliers.service';
import { of } from 'rxjs';
import { MatTableModule } from '@angular/material/table';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { FormsModule } from '@angular/forms';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { vi } from 'vitest';
import { CommonModule } from '@angular/common';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('CostAllocationDialogComponent', () => {
    let component: CostAllocationDialogComponent;
    let fixture: ComponentFixture<CostAllocationDialogComponent>;
    let suppliersServiceMock: any;
    let dialogRefMock: any;

    beforeEach(async () => {
        suppliersServiceMock = {
            getCostAllocationPreview: vi.fn().mockReturnValue(of({
                total_shipping: 100,
                total_taxes: 50,
                total_other: 0,
                allocations: []
            })),
            applyCostAllocation: vi.fn().mockReturnValue(of(true))
        };

        dialogRefMock = {
            close: vi.fn()
        };

        await TestBed.configureTestingModule({
            declarations: [],
            imports: [
                CostAllocationDialogComponent,
                CommonModule,
                MatDialogModule,
                MatTableModule,
                MatCheckboxModule,
                MatButtonModule,
                MatIconModule,
                MatProgressSpinnerModule,
                FormsModule,
                BrowserAnimationsModule,
                TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } }),
            ],
            providers: [
                { provide: MAT_DIALOG_DATA, useValue: { poId: 1, overrides: {} } },
                { provide: MatDialogRef, useValue: dialogRefMock },
                { provide: SuppliersService, useValue: suppliersServiceMock }
            ],
            schemas: [CUSTOM_ELEMENTS_SCHEMA]
        })
            .compileComponents();

        fixture = TestBed.createComponent(CostAllocationDialogComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load preview on init', () => {
        expect(suppliersServiceMock.getCostAllocationPreview).toHaveBeenCalledWith(1, [], {});
    });

    it('should apply cost allocation', () => {
        component.apply();
        expect(suppliersServiceMock.applyCostAllocation).toHaveBeenCalledWith(1, []);
        expect(dialogRefMock.close).toHaveBeenCalledWith(true);
    });
});
