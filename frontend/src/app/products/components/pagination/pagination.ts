import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';

import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-pagination',
  standalone: true,
  imports: [
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    FormsModule
],
  templateUrl: './pagination.html',
  styleUrls: ['./pagination.scss']
})
export class PaginationComponent implements OnInit {
  @Input() currentPage: number = 1;
  @Input() totalPages: number = 1;
  @Input() totalItems: number = 0;
  @Input() pageSize: number = 10;
  @Input() hasNextPage: boolean = false;
  @Input() hasPrevPage: boolean = false;
  
  @Output() pageChange = new EventEmitter<number>();
  @Output() pageSizeChange = new EventEmitter<number>();

  pages: number[] = [];
  displayedPage: number = 1;

  ngOnInit(): void {
    this.displayedPage = this.currentPage;
    this.generatePageNumbers();
  }

  ngOnChanges(): void {
    this.displayedPage = this.currentPage;
    this.generatePageNumbers();
  }

  onPageChange(page: number): void {
    if (page >= 1 && page <= this.totalPages && page !== this.currentPage) {
      this.currentPage = page;
      this.displayedPage = page;
      this.pageChange.emit(page);
    }
  }

  onNext(): void {
    if (this.currentPage < this.totalPages) {
      this.onPageChange(this.currentPage + 1);
    }
  }

  onPrev(): void {
    if (this.currentPage > 1) {
      this.onPageChange(this.currentPage - 1);
    }
  }

  onPageSizeChange(): void {
    this.pageSizeChange.emit(this.pageSize);
    // Reset to first page when page size changes
    this.onPageChange(1);
  }

  onDirectPageChange(): void {
    const page = parseInt(this.displayedPage.toString());
    if (!isNaN(page) && page >= 1 && page <= this.totalPages) {
      this.onPageChange(page);
    } else {
      this.displayedPage = this.currentPage; // Reset to current if invalid
    }
  }

  private generatePageNumbers(): void {
    const delta = 2; // Number of pages to show around current page
    const range = [];
    const rangeWithDots = [];

    for (let i = Math.max(2, this.currentPage - delta); i <= Math.min(this.totalPages - 1, this.currentPage + delta); i++) {
      range.push(i);
    }

    if (this.currentPage - delta > 2) {
      rangeWithDots.unshift('...');
    }
    rangeWithDots.unshift(1);

    if (this.currentPage + delta < this.totalPages - 1) {
      rangeWithDots.push('...');
    }
    if (this.totalPages > 1) {
      rangeWithDots.push(this.totalPages);
    }

    this.pages = rangeWithDots.map(p => typeof p === 'string' ? -1 : p);
  }
  
  calculateEndItem(): number {
    return Math.min(this.currentPage * this.pageSize, this.totalItems);
  }
}