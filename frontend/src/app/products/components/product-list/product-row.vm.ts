import { Product, MarketplaceListing } from '../../models/product.model';

/**
 * Flat, presentation-ready view of a Product for the product-list table + grid.
 *
 * Built ONCE per fetch (see {@link toRowVM}) so the template does pure property
 * reads instead of calling getCurrentStock()/getPrimaryImage()/getEffectiveCost()
 * per row per change-detection tick. It is also the single source of truth for
 * stock + status, which removes the old grid (`stock_quantity`) vs table
 * (`getCurrentStock()`) disagreement.
 */
export type StockHealth = 'healthy' | 'low' | 'out';
export type MarginBand = 'healthy' | 'thin' | 'negative';
export type MlStatus = 'active' | 'paused' | 'unlisted' | 'closed';

export interface StockBucket {
  /** Raw inventory location key (e.g. 'default', 'ml-full', 'amazon-fba'). */
  location: string;
  /** i18n key for the human label, resolved in the template. */
  labelKey: string;
  quantity: number;
}

export interface ProductRowVM {
  id: number;
  name: string;
  sku: string;
  brand: string | null;
  description: string;

  isBundle: boolean;
  bundleCount: number;
  bundlePreview: { qty: number; name: string }[];

  // image
  primaryImagePath: string; // '' when none
  hasImage: boolean;

  // money (MXN-native)
  price: number;
  effectiveCost: number;
  avgCost: number;
  showAvgCost: boolean;
  margin: number; // price - effectiveCost
  marginPct: number; // 0..100 (rounded)
  marginBand: MarginBand;
  currency: string;
  showCurrencyCode: boolean;

  // stock (location-aware)
  currentStock: number;
  buckets: StockBucket[]; // non-zero buckets, for the expander
  hasMlFullBucket: boolean;
  stockHealth: StockHealth;
  lowStockThreshold: number;
  showWhyZero: boolean;
  daysOfInventory: number | null;
  daysWarning: boolean;
  reorderTriggered: boolean;

  // ML listing
  mlStatus: MlStatus;
  isListed: boolean;
  marketplaceListings: MarketplaceListing[];
  activeCampaignCount: number;
  adjustmentCount: number;

  /** Original product, for dialogs / actions / deep links. */
  product: Product;
}

/** Inventory locations we recognise as MercadoLibre Full. */
const ML_FULL_LOCATIONS = new Set(['ml-full', 'ml_full', 'mercadolibre-full', 'mercadolibre', 'full']);

/** Amazon FBA is hidden for now (ML-Full is the only active fulfillment channel). */
const HIDDEN_LOCATIONS = new Set(['amazon-fba', 'amazon_fba', 'fba']);

const BUCKET_LABEL_KEYS: Record<string, string> = {
  default: 'products.bucketDefault',
  'ml-full': 'products.bucketMlFull',
  ml_full: 'products.bucketMlFull',
  full: 'products.bucketMlFull',
  mercadolibre: 'products.bucketMlFull',
  'amazon-fba': 'products.bucketAmazonFba',
  amazon_fba: 'products.bucketAmazonFba',
  fba: 'products.bucketAmazonFba',
};

function sumInventory(product: Product): { total: number; byLocation: Map<string, number> } {
  const byLocation = new Map<string, number>();
  let total = 0;
  for (const item of product.inventory_items ?? []) {
    const loc = (item.location || 'default').toLowerCase();
    byLocation.set(loc, (byLocation.get(loc) ?? 0) + item.quantity);
    total += item.quantity;
  }
  return { total, byLocation };
}

/** Total stock, location-aware. Bundles report assembled (physical) stock. */
function computeCurrentStock(product: Product, byLocation: Map<string, number>, total: number): number {
  if (byLocation.size === 0) return 0;
  // Prefer an explicit 'default' location, else fall back to the full sum.
  return byLocation.has('default') ? (byLocation.get('default') ?? 0) : total;
}

function computeEffectiveCost(product: Product): number {
  if (product.is_bundle && (!product.cost_price || product.cost_price === 0)) {
    const comps = product.bundle_components ?? [];
    if (comps.length > 0) {
      return comps.reduce((sum, bc) => sum + (bc.component_cost || 0) * bc.quantity, 0);
    }
  }
  return product.cost_price || 0;
}

function computeBundleAvgCost(product: Product): number {
  if (product.is_bundle && product.bundle_components && product.bundle_components.length > 0) {
    return product.bundle_components.reduce((sum, bc) => sum + (bc.component_cost || 0) * bc.quantity, 0);
  }
  return product.average_cost || 0;
}

function computeMlStatus(listings: MarketplaceListing[]): MlStatus {
  if (!listings || listings.length === 0) return 'unlisted';
  const statuses = listings.map((l) => (l.status || '').toLowerCase());
  if (statuses.some((s) => s === 'active' || s === 'published' || s === 'live')) return 'active';
  if (statuses.some((s) => s === 'paused' || s === 'inactive')) return 'paused';
  if (statuses.some((s) => s === 'closed' || s === 'finished' || s === 'ended')) return 'closed';
  // Listings exist but no recognised status → treat as active (listed).
  return 'active';
}

/** Pure factory: Product → ProductRowVM. No side effects, no DI. */
export function toRowVM(product: Product): ProductRowVM {
  const { total, byLocation } = sumInventory(product);
  const currentStock = computeCurrentStock(product, byLocation, total);

  const buckets: StockBucket[] = [];
  let hasMlFullBucket = false;
  for (const [location, quantity] of byLocation) {
    if (HIDDEN_LOCATIONS.has(location)) continue; // Amazon FBA hidden for now
    if (ML_FULL_LOCATIONS.has(location)) hasMlFullBucket = true;
    if (quantity !== 0) {
      buckets.push({
        location,
        labelKey: BUCKET_LABEL_KEYS[location] ?? 'products.bucketDefault',
        quantity,
      });
    }
  }

  const lowStockThreshold =
    product.reorder_point ?? product.low_stock_quantity_threshold ?? product.low_inventory_threshold ?? 10;

  let stockHealth: StockHealth;
  if (currentStock === 0) stockHealth = 'out';
  else if (currentStock <= lowStockThreshold) stockHealth = 'low';
  else stockHealth = 'healthy';

  const price = product.default_resale_price || 0;
  const effectiveCost = computeEffectiveCost(product);
  const margin = price - effectiveCost;
  const marginPct = price > 0 ? Math.round((margin / price) * 100) : 0;
  let marginBand: MarginBand;
  if (effectiveCost <= 0) marginBand = 'healthy'; // no cost recorded → don't flag
  else if (marginPct < 10) marginBand = 'negative';
  else if (marginPct < 20) marginBand = 'thin';
  else marginBand = 'healthy';

  const avgCost = product.is_bundle ? computeBundleAvgCost(product) : product.average_cost || 0;

  const listings = product.marketplace_listings ?? [];
  const mlStatus = computeMlStatus(listings);

  const days =
    product.days_of_inventory !== undefined && product.days_of_inventory < 999
      ? product.days_of_inventory
      : null;

  const reorderPoint = product.reorder_point ?? product.low_stock_quantity_threshold ?? 0;

  return {
    id: product.id,
    name: product.name,
    sku: product.sku,
    brand: product.brand ?? null,
    description: product.description ?? '',

    isBundle: !!product.is_bundle,
    bundleCount: product.bundle_components?.length ?? 0,
    bundlePreview: (product.bundle_components ?? []).slice(0, 3).map((c) => ({
      qty: c.quantity,
      name: c.component_name ?? '',
    })),

    primaryImagePath: product.primary_image?.image_path || product.images?.[0]?.image_path || '',
    hasImage: !!(product.primary_image?.image_path || product.images?.[0]?.image_path),

    price,
    effectiveCost,
    avgCost,
    showAvgCost: avgCost > 0,
    margin,
    marginPct,
    marginBand,
    currency: product.currency ?? 'MXN',
    showCurrencyCode: !!product.currency && product.currency !== 'MXN',

    currentStock,
    buckets,
    hasMlFullBucket,
    stockHealth,
    lowStockThreshold,
    showWhyZero: currentStock === 0,
    daysOfInventory: days,
    daysWarning: days !== null && days < (product.low_inventory_threshold ?? 30),
    reorderTriggered: reorderPoint > 0 && currentStock <= reorderPoint,

    mlStatus,
    isListed: mlStatus !== 'unlisted',
    marketplaceListings: listings,
    activeCampaignCount: product.active_campaign_count ?? 0,
    adjustmentCount: product.inventory_adjustment_count ?? 0,

    product,
  };
}
