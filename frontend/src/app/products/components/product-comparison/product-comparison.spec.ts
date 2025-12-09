import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ProductComparisonComponent } from './product-comparison';
import { Product } from '../../models/product.model';

describe('ProductComparisonComponent', () => {
    let component: ProductComparisonComponent;
    let fixture: ComponentFixture<ProductComparisonComponent>;

    const mockProducts: Product[] = [
        {
            id: 1,
            name: 'Product A',
            sku: 'SKU-A-001',
            description: 'Description A',
            default_resale_price: 19.99,
            cost_price: 10.99,
            images: [],
            inventory_items: [],
            inventory_adjustments: [],
            custom_fields: []
        },
        {
            id: 2,
            name: 'Product B',
            sku: 'SKU-B-001',
            description: 'Description B',
            default_resale_price: 29.99,
            cost_price: 15.99,
            images: [],
            inventory_items: [],
            inventory_adjustments: [],
            custom_fields: []
        }
    ];

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                MatIconModule,
                MatButtonModule,
                MatCardModule,
                MatTableModule,
                MatTooltipModule,
                ProductComparisonComponent
            ]
        })
            .compileComponents();

        fixture = TestBed.createComponent(ProductComparisonComponent);
        component = fixture.componentInstance;
        component.products = [...mockProducts];
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize with provided products', () => {
        expect(component.products.length).toBe(2);
        expect(component.products[0].name).toBe('Product A');
    });

    it('should emit closeComparison event when onClose is called', () => {
        vi.spyOn(component.closeComparison, 'emit');
        component.onClose();
        expect(component.closeComparison.emit).toHaveBeenCalled();
    });

    it('should emit exportComparison event when onExportComparison is called', () => {
        vi.spyOn(component.exportComparison, 'emit');
        component.onExportComparison();
        expect(component.exportComparison.emit).toHaveBeenCalledWith(mockProducts);
    });

    it('should remove a product when removeProduct is called', () => {
        expect(component.products.length).toBe(2);
        component.removeProduct(0);
        expect(component.products.length).toBe(1);
    });

    it('should format currency values correctly', () => {
        const formatted = component.formatValue(29.99, 'currency');
        expect(formatted).toBe('$29.99');
    });

    it('should format number values correctly', () => {
        const formatted = component.formatValue(123, 'number');
        expect(formatted).toBe('123');
    });

    it('should format text values correctly', () => {
        const formatted = component.formatValue('Test Value', 'text');
        expect(formatted).toBe('Test Value');
    });

    it('should return "N/A" for null or undefined values', () => {
        const formattedNull = component.formatValue(null, 'text');
        const formattedUndefined = component.formatValue(undefined, 'text');
        expect(formattedNull).toBe('N/A');
        expect(formattedUndefined).toBe('N/A');
    });

    it('should update comparison data when products change', () => {
        component.products = [...mockProducts];
        component.ngOnChanges();
        expect(component.displayedColumns.length).toBe(3); // attribute + 2 products
    });
});
