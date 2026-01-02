import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SupplierListComponent } from './supplier-list.component';
import { SuppliersService } from '../suppliers.service';
import { RouterTestingModule } from '@angular/router/testing';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { vi } from 'vitest';
import { CommonModule } from '@angular/common';
import { CUSTOM_ELEMENTS_SCHEMA, NO_ERRORS_SCHEMA } from '@angular/core';

import { TranslocoTestingModule } from '@ngneat/transloco';

describe('SupplierListComponent', () => {
    let component: SupplierListComponent;
    let fixture: ComponentFixture<SupplierListComponent>;
    let suppliersServiceMock: any;
    let routerMock: any;

    beforeEach(async () => {
        suppliersServiceMock = {
            getSuppliers: vi.fn(),
            getPurchaseOrders: vi.fn()
        };
        routerMock = {
            navigate: vi.fn()
        };

        suppliersServiceMock.getSuppliers.mockReturnValue(of([
            { id: 1, name: 'Supplier A', contact_person: 'John', email: 'john@a.com' }
        ] as any[]));
        suppliersServiceMock.getPurchaseOrders.mockReturnValue(of([]));

        await TestBed.configureTestingModule({
            declarations: [],
            imports: [
                SupplierListComponent,
                CommonModule,
                MatTableModule,
                MatPaginatorModule,
                MatSortModule,
                MatIconModule,
                MatButtonModule,
                BrowserAnimationsModule,
                RouterTestingModule,
                TranslocoTestingModule.forRoot({
                    langs: { en: {}, es: {} },
                    translocoConfig: { availableLangs: ['en', 'es'], defaultLang: 'en' }
                })
            ],
            providers: [
                { provide: SuppliersService, useValue: suppliersServiceMock }
            ],
            schemas: [CUSTOM_ELEMENTS_SCHEMA, NO_ERRORS_SCHEMA]
        })
            .compileComponents();

        fixture = TestBed.createComponent(SupplierListComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load data on init', () => {
        expect(suppliersServiceMock.getSuppliers).toHaveBeenCalled();
        expect(suppliersServiceMock.getPurchaseOrders).toHaveBeenCalled();
    });
});
