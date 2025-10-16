import { Component, Input, Output, EventEmitter } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-batch-action-toolbar',
  templateUrl: './batch-action-toolbar.html',
  styleUrls: ['./batch-action-toolbar.scss'],
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule
  ]
})
export class BatchActionToolbarComponent {
  @Input() selectedCount: number = 0;
  @Output() deleteSelected = new EventEmitter<void>();
  @Output() selectAll = new EventEmitter<void>();
  @Output() deselectAll = new EventEmitter<void>();
  @Output() closeToolbar = new EventEmitter<void>();

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
}