import { Component, Input } from '@angular/core';
import { Product } from '../../../products/models/product.model';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-low-stock-list',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    RouterModule
  ],
  templateUrl: './low-stock-list.component.html',
  styleUrls: ['./low-stock-list.component.scss']
})
export class LowStockListWidgetComponent {
  @Input() products: Product[] = [];

  getTotalStock(product: Product): number {
    return product.inventory_items?.reduce((acc, item) => acc + item.quantity, 0) || 0;
  }
}
