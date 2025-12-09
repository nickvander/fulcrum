import type { MockedObject } from "vitest";
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ProductsComponent } from './products';
import { ProductList } from '../product-list/product-list';
import { ProductForm } from '../product-form/product-form';
import { ProductService } from '../../services/product';
import { of } from 'rxjs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Component } from '@angular/core';
import { By } from '@angular/platform-browser';

// Create stub components for testing
@Component({
    selector: 'app-product-list',
    template: '<div>Product List Stub</div>',
    standalone: true
})
class ProductListStubComponent {
    // Stub the editProduct output
    editProduct = { emit: vi.fn() };
}

@Component({
    selector: 'app-product-form',
    template: '<div>Product Form Stub</div>',
    standalone: true
})
class ProductFormStubComponent {
}

describe('ProductsComponent', () => {
    let component: ProductsComponent;
    let fixture: ComponentFixture<ProductsComponent>;
    let productServiceSpy: MockedObject<ProductService>;

    beforeEach(async () => {
        const spy = {
            getProducts: vi.fn().mockName("ProductService.getProducts")
        };
        spy.getProducts.mockReturnValue(of([]));

        await TestBed.configureTestingModule({
            imports: [
                ProductsComponent,
                NoopAnimationsModule,
                MatSidenavModule,
                MatButtonModule,
                MatIconModule,
                ProductList,
                ProductForm
            ],
            providers: [
                { provide: ProductService, useValue: spy }
            ]
        })
            // Override the imports to use stubs for complex components
            .overrideComponent(ProductsComponent, {
            remove: {
                imports: [ProductList, ProductForm]
            },
            add: {
                imports: [ProductListStubComponent, ProductFormStubComponent]
            }
        })
            .compileComponents();

        fixture = TestBed.createComponent(ProductsComponent);
        component = fixture.componentInstance;
        productServiceSpy = TestBed.inject(ProductService) as MockedObject<ProductService>;
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should call productService.getProducts on init', () => {
        fixture.detectChanges(); // This triggers ngOnInit
        expect(productServiceSpy.getProducts).toHaveBeenCalled();
    });

    it('should open edit panel when openEditPanel is called', () => {
        const mockProduct = { id: 1, name: 'Test Product', sku: 'TEST001', description: '', default_resale_price: 10, images: [] } as any;

        component.openEditPanel(mockProduct);

        expect(component.selectedProduct).toEqual(mockProduct);
        expect(component.isEditing).toBe(true);
    });

    it('should close edit panel when closeEditPanel is called', () => {
        component.closeEditPanel();

        expect(component.selectedProduct).toBeNull();
        expect(component.isEditing).toBe(false);
    });

    it('should call productService.getProducts and close panel when onProductSaved is called', () => {
        component.selectedProduct = { id: 1, name: 'Test Product', sku: 'TEST001', description: '', default_resale_price: 10, images: [] };
        component.isEditing = true;

        component.onProductSaved();

        expect(productServiceSpy.getProducts).toHaveBeenCalled();
        expect(component.selectedProduct).toBeNull();
        expect(component.isEditing).toBe(false);
    });
});
