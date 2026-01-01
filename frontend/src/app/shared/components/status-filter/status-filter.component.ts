import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

export interface StatusFilterOption {
  value: string;
  label: string;
  icon?: string;
}

@Component({
  selector: 'app-status-filter',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatSelectModule,
    MatIconModule,
    MatButtonModule
  ],
  templateUrl: './status-filter.component.html',
  styleUrls: ['./status-filter.component.scss']
})
export class StatusFilterComponent {
  @Input() options: StatusFilterOption[] = [];
  @Input() selectedValue: string = '';
  @Input() label: string = 'Status';
  @Input() defaultValue: string = 'all';
  @Output() valueChange = new EventEmitter<string>();

  getSelectedLabel(): string {
    const option = this.options.find(o => o.value === this.selectedValue);
    return option?.label || '';
  }

  getSelectedIcon(): string | undefined {
    const option = this.options.find(o => o.value === this.selectedValue);
    return option?.icon;
  }

  onValueChange(value: string): void {
    this.selectedValue = value;
    this.valueChange.emit(value);
  }

  clearFilter(event: Event): void {
    event.stopPropagation();
    this.selectedValue = this.defaultValue;
    this.valueChange.emit(this.defaultValue);
  }
}
