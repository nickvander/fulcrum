import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, forkJoin, map, catchError, of } from 'rxjs';
import { ProductService } from '../../products/services/product';
import { SuppliersService } from '../../suppliers/suppliers.service';
import { PurchaseOrderStatus } from '../../shared/models/purchase-order.model';
import { Product } from '../../products/models/product.model';

export interface DashboardStats {
    totalProducts: number;
    lowStockCount: number;
    pendingOrdersCount: number;
    totalSuppliers: number;
    lowStockProducts: Product[];
    totalInventoryValue: number;
    stockHealthPercentage: number;
}

@Injectable({
    providedIn: 'root'
})
export class DashboardStatsService {
    constructor(
        private productService: ProductService,
        private suppliersService: SuppliersService
    ) { }

    getStats(): Observable<DashboardStats> {
        return forkJoin({
            products: this.productService.getProducts(1, 1000), // Get a large batch for counting
            purchaseOrders: this.suppliersService.getPurchaseOrders(0, 1000),
            suppliers: this.suppliersService.getSuppliers(0, 1000)
        }).pipe(
            map(({ products, purchaseOrders, suppliers }) => {
                const productList = products.data || [];

                let totalInventoryValue = 0;
                let healthyCount = 0;

                const lowStockProducts = productList.filter(p => {
                    const totalStock = p.inventory_items?.reduce((acc, item) => acc + item.quantity, 0) || 0;

                    // Value calculation
                    totalInventoryValue += totalStock * (p.cost_price || 0);

                    // Reorder point check
                    const isLow = totalStock < 5;
                    if (!isLow) healthyCount++;
                    return isLow;
                });

                const totalProducts = products.totalItems || productList.length;
                const stockHealthPercentage = totalProducts > 0
                    ? Math.round((healthyCount / totalProducts) * 100)
                    : 100;

                const pendingOrdersCount = purchaseOrders.filter(po =>
                    po.status === PurchaseOrderStatus.ORDERED || po.status === PurchaseOrderStatus.PARTIALLY_RECEIVED
                ).length;

                return {
                    totalProducts,
                    lowStockCount: lowStockProducts.length,
                    pendingOrdersCount,
                    totalSuppliers: suppliers.length,
                    lowStockProducts: lowStockProducts.slice(0, 5),
                    totalInventoryValue,
                    stockHealthPercentage
                };
            }),
            catchError(error => {
                return of({
                    totalProducts: 0,
                    lowStockCount: 0,
                    pendingOrdersCount: 0,
                    totalSuppliers: 0,
                    lowStockProducts: [],
                    totalInventoryValue: 0,
                    stockHealthPercentage: 0
                });
            })
        );
    }
}
