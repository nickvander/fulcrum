export interface ProductImage {
  id: number;
  product_id: number;
  image_path: string;
  is_primary: number;
  source?: string;
  title?: string;
  description?: string;
}

export interface InventoryItem {
  id: number;
  product_id: number;
  quantity: number;
  location?: string;
}

export interface InventoryAdjustment {
  id: number;
  product_id: number;
  adjustment: number;
  reason: string | null;
  timestamp: string;
  created_by: string | null;
}

export interface ProductCustomField {
  id: number;
  product_id: number;
  custom_field_id: number;
  value: string;
}

export interface ProductVariant {
  id: number;
  product_id: number;
  name: string;
  sku: string;
  price: number;
  stock_quantity: number;
  attributes: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface MarketplaceListing {
  id: number;
  product_id: number;
  marketplace_id: number;
  external_listing_id?: string;
  listing_url?: string;
  status?: string;
}

export interface Product {
  id: number;
  name: string;
  description: string;
  sku: string;
  supplier_id?: number;
  default_resale_price: number;
  cost_price?: number;
  average_cost?: number;
  properties?: any;
  images?: ProductImage[];
  inventory_items?: InventoryItem[];
  inventory_adjustments?: InventoryAdjustment[];
  manufacturer?: string;
  brand?: string;
  category?: string;
  width?: number;
  height?: number;
  depth?: number;
  weight?: number;
  primary_image?: ProductImage;
  custom_fields?: ProductCustomField[];
  variants?: ProductVariant[];
  marketplace_listings?: MarketplaceListing[];
  is_bundle: boolean;
  bundle_components?: BundleComponent[];
  part_of_bundles?: BundleComponent[];
}

export interface BundleComponent {
  id?: number;
  bundle_id?: number;
  component_id: number;
  quantity: number;
  component_name?: string;
  component_image?: string;
  bundle_name?: string;
  bundle_image?: string;
  bundle_stock?: number;
  component_stock?: number;
  component_cost?: number;
}