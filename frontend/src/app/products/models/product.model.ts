export interface ProductImage {
  id: number;
  product_id: number;
  image_path: string;
  is_primary: number;
  source?: string;
}

export interface Product {
  id: number;
  name: string;
  description: string;
  sku: string;
  supplier_id?: number;
  default_resale_price: number;
  cost_price?: number;
  properties?: any;
  images?: ProductImage[];
}
