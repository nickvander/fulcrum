import { Component, Output, EventEmitter, Input, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { Subject, takeUntil } from 'rxjs';
import { DateRangeService, DateRangePreset, DateRange } from '../../services/date-range.service';

@Component({
    selector: 'app-date-range-presets',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        MatButtonToggleModule,
        MatFormFieldModule,
        MatDatepickerModule,
        MatNativeDateModule,
        MatInputModule,
        MatIconModule,
        MatButtonModule
    ],
    template: `
        <div class="date-range-container">
            <mat-button-toggle-group [value]="selectedPreset" (change)="onPresetChange($event.value)">
                <mat-button-toggle value="day">Today</mat-button-toggle>
                <mat-button-toggle value="week">Week</mat-button-toggle>
                <mat-button-toggle value="month">Month</mat-button-toggle>
                <mat-button-toggle value="3months">3 Mo</mat-button-toggle>
                <mat-button-toggle value="6months">6 Mo</mat-button-toggle>
                <mat-button-toggle value="year">Year</mat-button-toggle>
                <mat-button-toggle value="custom">Custom</mat-button-toggle>
            </mat-button-toggle-group>

            @if (selectedPreset === 'custom') {
                <div class="custom-range">
                    <mat-form-field appearance="outline" class="date-field">
                        <mat-label>Start</mat-label>
                        <input matInput [matDatepicker]="startPicker" [(ngModel)]="customStart" (dateChange)="onCustomChange()">
                        <mat-datepicker-toggle matIconSuffix [for]="startPicker"></mat-datepicker-toggle>
                        <mat-datepicker #startPicker></mat-datepicker>
                    </mat-form-field>
                    <span class="range-separator">to</span>
                    <mat-form-field appearance="outline" class="date-field">
                        <mat-label>End</mat-label>
                        <input matInput [matDatepicker]="endPicker" [(ngModel)]="customEnd" (dateChange)="onCustomChange()">
                        <mat-datepicker-toggle matIconSuffix [for]="endPicker"></mat-datepicker-toggle>
                        <mat-datepicker #endPicker></mat-datepicker>
                    </mat-form-field>
                </div>
            }
        </div>
    `,
    styles: [`
        .date-range-container {
            display: flex;
            align-items: center;
            gap: 16px;
            flex-wrap: wrap;
        }

        mat-button-toggle-group {
            height: 32px; /* Slightly smaller for sleekness */
            border: none;
            gap: 8px;
            background: transparent;
            align-items: center;
        }

        mat-button-toggle {
            font-size: 0.85rem;
            border-radius: 8px !important; /* Soft rect/pill */
            border: none;
            background-color: #f5f5f5; /* Light gray default */
            color: #424242; /* Dark gray text */
            transition: all 0.2s ease;
            line-height: 32px;
            padding: 0 12px;
            
            /* Remove default indicator if present in Mat3 */
            ::ng-deep .mat-button-toggle-label-content {
                line-height: 32px;
                padding: 0;
            }

            &.mat-button-toggle-checked {
                background-color: #263238 !important; /* Dark Blue-Grey (Sleek) */
                color: white !important;
                font-weight: 500;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }

            &:hover:not(.mat-button-toggle-checked) {
                background-color: #e0e0e0;
            }
        }

        /* Hide the checkmark icon if Material adds one */
        ::ng-deep mat-button-toggle .mat-pseudo-checkbox {
            display: none !important;
        }

        .custom-range {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-left: 8px;
        }

        .date-field {
            width: 130px;
        }

        /* Override date field wrapper to be cleaner if needed */
        ::ng-deep .custom-range .mat-mdc-text-field-wrapper {
             background-color: white;
             border-radius: 8px;
        }

        .range-separator {
            color: #757575;
            font-size: 0.9rem;
            font-weight: 500;
        }

        @media (max-width: 768px) {
            .date-range-container {
                flex-direction: column;
                align-items: flex-start;
                gap: 12px;
            }
            .custom-range {
                 margin-left: 0;
            }
        }
    `]
})
export class DateRangePresetsComponent implements OnInit, OnDestroy {
    @Input() useGlobalService = true;  // If true, syncs with global DateRangeService
    @Output() rangeChange = new EventEmitter<DateRange>();

    selectedPreset: DateRangePreset = 'week';
    customStart: Date = new Date();
    customEnd: Date = new Date();

    private destroy$ = new Subject<void>();

    constructor(private dateRangeService: DateRangeService) { }

    ngOnInit(): void {
        if (this.useGlobalService) {
            // Subscribe to global date range
            this.dateRangeService.dateRange$
                .pipe(takeUntil(this.destroy$))
                .subscribe(range => {
                    this.selectedPreset = range.preset;
                    this.customStart = range.startDate;
                    this.customEnd = range.endDate;
                });
        }
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    onPresetChange(preset: DateRangePreset): void {
        this.selectedPreset = preset;

        if (preset !== 'custom') {
            if (this.useGlobalService) {
                this.dateRangeService.setPreset(preset);
            }
            const range = this.dateRangeService.getDateRangeFromPreset(preset);
            this.rangeChange.emit(range);
        }
    }

    onCustomChange(): void {
        if (this.customStart && this.customEnd) {
            if (this.useGlobalService) {
                this.dateRangeService.setCustomRange(this.customStart, this.customEnd);
            }
            this.rangeChange.emit({
                preset: 'custom',
                startDate: this.customStart,
                endDate: this.customEnd
            });
        }
    }
}
