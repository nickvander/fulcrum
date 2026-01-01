import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LowStockListWidgetComponent } from './low-stock-list.component';
import { RouterTestingModule } from '@angular/router/testing';
import { By } from '@angular/platform-browser';
import { Product } from '../../../products/models/product.model';

describe('LowStockListWidgetComponent', () => {
    let component: LowStockListWidgetComponent;
    let fixture: ComponentFixture<LowStockListWidgetComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                LowStockListWidgetComponent,
                RouterTestingModule
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(LowStockListWidgetComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should display empty state when no products', () => {
        component.products = [];
        fixture.detectChanges();
        const emptyState = fixture.debugElement.query(By.css('.empty-state'));
        expect(emptyState).toBeTruthy();
        expect(emptyState.nativeElement.textContent).toContain('All stock levels healthy');
    });

    it('should display products when provided', () => {
        const mockProduct: Product = {
            id: 1,
            name: 'Test Product',
            sku: 'SKU-123',
            description: 'Test Desc',
            default_resale_price: 10,
            is_bundle: false,
            inventory_items: [
                { id: 1, product_id: 1, quantity: 5 }
            ]
        };

        component.products = [mockProduct];
        fixture.detectChanges();

        const listItems = fixture.debugElement.queryAll(By.css('a[mat-list-item]'));
        expect(listItems.length).toBe(1);
        expect(listItems[0].nativeElement.textContent).toContain('Test Product');
        expect(listItems[0].nativeElement.textContent).toContain('5 units');
    });
});
