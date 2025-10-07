import { Component, OnInit, ViewChild, AfterViewInit } from '@angular/core';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';
import { ProductService } from '../../services/product';
import { Product } from '../../models/product.model';

@Component({
  selector: 'app-product-list',
  templateUrl: './product-list.html',
  styleUrl: './product-list.scss'
})
export class ProductList implements OnInit, AfterViewInit {
  displayedColumns: string[] = ['name', 'sku', 'default_resale_price', 'actions'];
  dataSource: MatTableDataSource<Product> = new MatTableDataSource();

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  constructor(private productService: ProductService) {}

  ngOnInit(): void {
    this.productService.getProducts().subscribe((products) => {
      this.dataSource.data = products;
    });
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  deleteProduct(id: number): void {
    console.log(`TODO: Implement delete for product with id: ${id}`);
    // TODO: Call productService.deleteProduct(id) and refresh the table
  }

  onSearchQuery(query: string): void {
    console.log('Search query:', query);
    // TODO: Call a new method in productService to search products and update the dataSource
  }
}
