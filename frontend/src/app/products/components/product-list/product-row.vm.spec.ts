import { toRowVM } from './product-row.vm';
import { Product } from '../../models/product.model';

function product(overrides: Partial<Product> = {}): Product {
  return {
    id: 1,
    name: 'Test',
    description: '',
    sku: 'SKU-1',
    default_resale_price: 100,
    is_bundle: false,
    ...overrides,
  } as Product;
}

describe('toRowVM', () => {
  it('computes current stock from the default location, ignoring others', () => {
    const vm = toRowVM(product({
      inventory_items: [
        { id: 1, product_id: 1, location: 'default', quantity: 30 },
        { id: 2, product_id: 1, location: 'ml-full', quantity: 5 },
      ],
    }));
    expect(vm.currentStock).toBe(30);
  });

  it('hides the Amazon FBA bucket but keeps default + ml-full', () => {
    const vm = toRowVM(product({
      inventory_items: [
        { id: 1, product_id: 1, location: 'default', quantity: 10 },
        { id: 2, product_id: 1, location: 'ml-full', quantity: 4 },
        { id: 3, product_id: 1, location: 'amazon-fba', quantity: 7 },
      ],
    }));
    const locations = vm.buckets.map(b => b.location);
    expect(locations).toContain('default');
    expect(locations).toContain('ml-full');
    expect(locations).not.toContain('amazon-fba');
    expect(vm.hasMlFullBucket).toBe(true);
  });

  it('classifies stock health against the reorder/low threshold', () => {
    const out = toRowVM(product({ inventory_items: [] }));
    expect(out.stockHealth).toBe('out');
    expect(out.showWhyZero).toBe(true);

    const low = toRowVM(product({
      low_stock_quantity_threshold: 10,
      inventory_items: [{ id: 1, product_id: 1, location: 'default', quantity: 5 }],
    }));
    expect(low.stockHealth).toBe('low');

    const healthy = toRowVM(product({
      low_stock_quantity_threshold: 10,
      inventory_items: [{ id: 1, product_id: 1, location: 'default', quantity: 50 }],
    }));
    expect(healthy.stockHealth).toBe('healthy');
  });

  it('computes margin band from cost vs price', () => {
    const healthy = toRowVM(product({ default_resale_price: 100, cost_price: 50 }));
    expect(healthy.marginPct).toBe(50);
    expect(healthy.marginBand).toBe('healthy');

    const thin = toRowVM(product({ default_resale_price: 100, cost_price: 85 }));
    expect(thin.marginBand).toBe('thin');

    const negative = toRowVM(product({ default_resale_price: 100, cost_price: 95 }));
    expect(negative.marginBand).toBe('negative');
  });

  it('derives ML listing status from marketplace listings', () => {
    expect(toRowVM(product()).mlStatus).toBe('unlisted');
    expect(
      toRowVM(product({ marketplace_listings: [{ id: 1, product_id: 1, marketplace_id: 1, marketplace_price: 100, status: 'active' }] })).mlStatus,
    ).toBe('active');
    expect(
      toRowVM(product({ marketplace_listings: [{ id: 1, product_id: 1, marketplace_id: 1, marketplace_price: 100, status: 'paused' }] })).mlStatus,
    ).toBe('paused');
  });

  it('flags reorder when stock is at/below the reorder point', () => {
    const vm = toRowVM(product({
      reorder_point: 10,
      inventory_items: [{ id: 1, product_id: 1, location: 'default', quantity: 8 }],
    }));
    expect(vm.reorderTriggered).toBe(true);
  });
});
