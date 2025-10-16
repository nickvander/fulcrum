export interface CustomFieldTemplate {
  id?: number;
  template_id: number;
  name: string;
  type?: string; // text, number, boolean, etc.
  default_value?: string;
  required?: boolean;
}

export interface ProductTemplate {
  id?: number;
  name: string;
  description?: string;
  category?: string;
  brand?: string;
  default_resale_price?: number;
  cost_price?: number;
  manufacturer?: string;
  width?: number;
  height?: number;
  depth?: number;
  weight?: number;
  properties?: string; // JSON string for additional properties
  created_at?: string;
  updated_at?: string;
  custom_fields?: CustomFieldTemplate[];
}