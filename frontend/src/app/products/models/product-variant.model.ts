export interface ProductVariant {
  id?: number;
  product_id: number;
  name: string;
  sku: string;
  description?: string;
  price?: number;
  cost_price?: number;
  attributes?: string; // JSON string containing variant attributes
  created_at?: string;
  updated_at?: string;
}