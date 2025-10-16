import { Product } from './product.model';

export interface PaginatedProducts {
  data: Product[];
  currentPage: number;
  totalPages: number;
  totalItems: number;
  pageSize: number;
  hasNextPage: boolean;
  hasPrevPage: boolean;
}