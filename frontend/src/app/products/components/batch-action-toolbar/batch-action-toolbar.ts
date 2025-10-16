import { Component, Input, Output, EventEmitter } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-batch-action-toolbar',
  templateUrl: './batch-action-toolbar.html',
  styleUrls: ['./batch-action-toolbar.scss'],
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule
  ]
})
export class BatchActionToolbarComponent {
  @Input() selectedCount: number = 0;
  @Output() deleteSelected = new EventEmitter<void>();
  @Output() selectAll = new EventEmitter<void>();
  @Output() deselectAll = new EventEmitter<void>();
  @Output() closeToolbar = new EventEmitter<void>();
  @Output() batchPriceUpdate = new EventEmitter<{productIds: number[], price: number}>();
  @Output() batchCategoryUpdate = new EventEmitter<{productIds: number[], category: string}>();
  @Output() batchCustomFieldUpdate = new EventEmitter<{productIds: number[], updates: {[key: string]: any}}>();

  onDeleteSelected(): void {
    this.deleteSelected.emit();
  }

  onSelectAll(): void {
    this.selectAll.emit();
  }

  onDeselectAll(): void {
    this.deselectAll.emit();
  }

  onClose(): void {
    this.closeToolbar.emit();
  }
  
  onBatchPriceUpdate(): void {
    // This would open a dialog for price update
    // For now, emit an event that the parent component handles
    this.batchPriceUpdate.emit({ productIds: [], price: 0 }); // Placeholder values
  }
  
  onBatchCategoryUpdate(): void {
    // This would open a dialog for category update
    this.batchCategoryUpdate.emit({ productIds: [], category: '' }); // Placeholder values
  }
  
  onBatchCustomFieldUpdate(): void {
    // This would open a dialog for custom field updates
    this.batchCustomFieldUpdate.emit({ productIds: [], updates: {} }); // Placeholder values
  }
}