
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SupplierProductManagerComponent } from './supplier-product-manager.component';
import { SuppliersService } from '../suppliers.service';
import { of } from 'rxjs';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

describe('SupplierProductManagerComponent', () => {
    let component: SupplierProductManagerComponent;
    let fixture: ComponentFixture<SupplierProductManagerComponent>;
    let suppliersServiceMock: any;

    beforeEach(async () => {
        suppliersServiceMock = {
            getSupplierProducts: vi.fn().mockReturnValue(of([]))
        };

        await TestBed.configureTestingModule({
            imports: [
                SupplierProductManagerComponent,
                MatTableModule,
                MatButtonModule,
                MatIconModule
            ],
            providers: [
                { provide: SuppliersService, useValue: suppliersServiceMock }
            ]
        })
            .compileComponents();

        fixture = TestBed.createComponent(SupplierProductManagerComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load products on init if supplierId is present', () => {
        component.supplierId = 1;
        component.ngOnInit();
        expect(suppliersServiceMock.getSupplierProducts).toHaveBeenCalledWith(1);
    });
});
