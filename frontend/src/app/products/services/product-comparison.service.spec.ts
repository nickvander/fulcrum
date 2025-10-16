import { TestBed } from '@angular/core/testing';
import { ProductComparisonService } from './product-comparison.service';
import { Product } from '../models/product.model';

describe('ProductComparisonService', () => {
  let service: ProductComparisonService;

  const mockProduct1: Product = {
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
  };

  const mockProduct2: Product = {
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
  };

  beforeEach(() => {
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
    expect(service.isInComparison(1)).toBeTrue();
    expect(service.isInComparison(2)).toBeFalse();
  });

  it('should toggle product in comparison', () => {
    service.toggleProductInComparison(mockProduct1);
    expect(service.isInComparison(1)).toBeTrue();

    service.toggleProductInComparison(mockProduct1);
    expect(service.isInComparison(1)).toBeFalse();
  });
});