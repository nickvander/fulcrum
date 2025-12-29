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
            height: 36px;
        }

        mat-button-toggle {
            font-size: 0.8rem;
        }

        .custom-range {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .date-field {
            width: 140px;
        }

        .range-separator {
            color: #666;
            font-size: 0.9rem;
        }

        @media (max-width: 768px) {
            .date-range-container {
                flex-direction: column;
                align-items: flex-start;
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
