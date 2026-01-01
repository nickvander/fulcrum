
import { Component, OnInit, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ProductService } from '../../../products/services/product';
import { Product } from '../../../products/models/product.model';
import { RouterModule } from '@angular/router';

@Component({
    selector: 'app-inventory-health-widget',
    standalone: true,
    imports: [
        CommonModule,
        MatCardModule,
        MatButtonModule,
        MatIconModule,
        MatListModule,
        MatProgressBarModule,
        MatProgressSpinnerModule,
        MatTooltipModule,
        RouterModule
    ],
    templateUrl: './inventory-health-widget.component.html',
    styleUrls: ['./inventory-health-widget.component.scss']
})
export class InventoryHealthWidgetComponent implements OnInit {
    @Input() products: Product[] | null = null;
    @Input() title: string = 'Inventory Health';

    lowStockItems: Product[] = [];
    loading = true;

    constructor(private productService: ProductService) { }

    ngOnInit(): void {
        this.loadData();
    }

    isQtyLow(item: Product): boolean {
        return (item.stock_quantity || 0) < (item.low_stock_quantity_threshold || 10);
    }

    loadData() {
        this.loading = true;

        if (this.products) {
            this.processProducts(this.products);
            this.loading = false;
        } else {
            this.productService.getProducts(1, 100).subscribe(response => {
                this.processProducts(response.data);
                this.loading = false;
            });
        }
    }

    private processProducts(products: Product[]) {
        this.lowStockItems = products
            .map(p => ({
                ...p,
                days_of_inventory: p.days_of_inventory !== undefined ? p.days_of_inventory : 0
            }))
            .filter(p => {
                const daysLow = p.days_of_inventory !== undefined && p.days_of_inventory < (p.low_inventory_threshold || 30) && p.days_of_inventory >= 0;
                const qtyLow = (p.stock_quantity || 0) < (p.low_stock_quantity_threshold || 10);
                return daysLow || qtyLow;
            })
            .sort((a, b) => (a.days_of_inventory || 0) - (b.days_of_inventory || 0))
            .slice(0, 5);
    }
}
