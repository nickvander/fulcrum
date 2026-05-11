
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SupplierProductManagerComponent } from './supplier-product-manager.component';
import { SuppliersService } from '../suppliers.service';
import { of } from 'rxjs';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterTestingModule } from '@angular/router/testing';

describe('SupplierProductManagerComponent', () => {
    let component: SupplierProductManagerComponent;
    let fixture: ComponentFixture<SupplierProductManagerComponent>;
    let suppliersServiceMock: any;

    beforeEach(async () => {
        suppliersServiceMock = {
            getSupplierProducts: vi.fn().mockReturnValue(of([])),
            deleteSupplierProductAlias: vi.fn().mockReturnValue(of({}))
        };

        await TestBed.configureTestingModule({
            imports: [
                SupplierProductManagerComponent,
                MatTableModule,
                MatButtonModule,
                MatIconModule,
                RouterTestingModule
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

    it('should remove a learned alias from the displayed supplier product', () => {
        const supplierProduct: any = {
            aliases: [
                { id: 1, alias_name: 'Alibaba Widget' },
                { id: 2, alias_name: 'Keep Me' }
            ]
        };
        const event = { stopPropagation: vi.fn() } as any;

        component.deleteAlias(event, supplierProduct, supplierProduct.aliases[0]);

        expect(event.stopPropagation).toHaveBeenCalled();
        expect(suppliersServiceMock.deleteSupplierProductAlias).toHaveBeenCalledWith(1);
        expect(supplierProduct.aliases).toEqual([{ id: 2, alias_name: 'Keep Me' }]);
    });
});
