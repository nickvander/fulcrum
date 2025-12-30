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
    template: `
    <mat-form-field appearance="outline" class="sleek-select status-filter-field" subscriptSizing="dynamic">
      <mat-label>{{ label }}</mat-label>
      <mat-select [ngModel]="selectedValue" (selectionChange)="onValueChange($event.value)">
        <mat-select-trigger>
          <div class="selected-option">
            <mat-icon *ngIf="getSelectedIcon()">{{ getSelectedIcon() }}</mat-icon>
            <span>{{ getSelectedLabel() }}</span>
          </div>
        </mat-select-trigger>
        <mat-option *ngFor="let option of options" [value]="option.value">
          <div class="option-content">
            <mat-icon *ngIf="option.icon">{{ option.icon }}</mat-icon>
            <span>{{ option.label }}</span>
          </div>
        </mat-option>
      </mat-select>
      <button *ngIf="selectedValue && selectedValue !== defaultValue" 
              mat-icon-button matSuffix 
              (click)="clearFilter($event)">
        <mat-icon class="clear-icon">close</mat-icon>
      </button>
    </mat-form-field>
  `,
    styles: [`
    :host {
      display: inline-block;
    }

    .status-filter-field {
      min-width: 140px;
    }

    .selected-option {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .selected-option mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      line-height: 18px;
      color: #666;
    }

    .option-content {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .option-content mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      line-height: 18px;
      color: #666;
    }

    .clear-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      line-height: 18px;
    }

    @media (max-width: 768px) {
      .status-filter-field {
        min-width: 120px;
      }
    }
  `]
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
