import { TestBed } from '@angular/core/testing';
import { ProductComparisonService } from './product-comparison.service';
import { Product } from '../models/product.model';

describe('ProductComparisonService', () => {
    let service: ProductComparisonService;

    const mockProduct1: Product = {
        id: 1,
        name: 'Product 1',
        sku: 'P001',
        description: 'Description 1',
        default_resale_price: 100,
        cost_price: 50,
        is_bundle: false,
        images: [],
        inventory_items: [],
        inventory_adjustments: [],
        custom_fields: []
    };

    const mockProduct2: Product = {
        id: 2,
        name: 'Product 2',
        sku: 'P002',
        description: 'Description 2',
        default_resale_price: 200,
        cost_price: 100,
        is_bundle: false,
        images: [],
        inventory_items: [],
        inventory_adjustments: [],
        custom_fields: []
    };

    beforeEach(() => {
        TestBed.resetTestingModule();
        TestBed.configureTestingModule({
            providers: [ProductComparisonService]
        });
        service = TestBed.inject(ProductComparisonService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    it('should start with empty compared products', () => {
        expect(service.getProducts().length).toBe(0);
    });

    it('should add a product to comparison', () => {
        service.addProduct(mockProduct1);
        expect(service.getProducts().length).toBe(1);
        expect(service.getProducts()[0].id).toBe(1);
    });

    it('should not add duplicate products', () => {
        service.addProduct(mockProduct1);
        service.addProduct(mockProduct1); // Try to add the same product again
        expect(service.getProducts().length).toBe(1);
    });

    it('should remove a product from comparison', () => {
        service.addProduct(mockProduct1);
        service.addProduct(mockProduct2);
        expect(service.getProducts().length).toBe(2);

        service.removeProduct(1);
        expect(service.getProducts().length).toBe(1);
        expect(service.getProducts()[0].id).toBe(2);
    });

    it('should clear all products', () => {
        service.addProduct(mockProduct1);
        service.addProduct(mockProduct2);
        expect(service.getProducts().length).toBe(2);

        service.clearAll();
        expect(service.getProducts().length).toBe(0);
    });

    it('should check if a product is in comparison', () => {
        service.addProduct(mockProduct1);
        expect(service.isInComparison(1)).toBe(true);
        expect(service.isInComparison(2)).toBe(false);
    });

    it('should toggle product in comparison', () => {
        service.toggleProductInComparison(mockProduct1);
        expect(service.isInComparison(1)).toBe(true);

        service.toggleProductInComparison(mockProduct1);
        expect(service.isInComparison(1)).toBe(false);
    });
});
