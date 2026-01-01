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
import { MatTooltipModule } from '@angular/material/tooltip';
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
        MatButtonModule,
        MatTooltipModule
    ],
    templateUrl: './date-range-presets.component.html',
    styleUrls: ['./date-range-presets.component.scss']
})
export class DateRangePresetsComponent implements OnInit, OnDestroy {
    @Input() useGlobalService = true;  // If true, syncs with global DateRangeService
    @Input() showAllOption = false;    // If true, shows "All" as first option
    @Input() defaultPreset: DateRangePreset | 'all' = 'week';
    @Output() rangeChange = new EventEmitter<DateRange | null>();

    selectedPreset: DateRangePreset | 'all' = 'week';
    customStart: Date = new Date();
    customEnd: Date = new Date();

    private destroy$ = new Subject<void>();

    constructor(private dateRangeService: DateRangeService) { }

    ngOnInit(): void {
        // Set default preset
        if (this.showAllOption && this.defaultPreset === 'all') {
            this.selectedPreset = 'all';
        } else {
            this.selectedPreset = this.defaultPreset as DateRangePreset;
        }

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

    onPresetChange(preset: DateRangePreset | 'all'): void {
        this.selectedPreset = preset;

        if (preset === 'all') {
            // Emit null to indicate no date filter
            this.rangeChange.emit(null);
        } else if (preset !== 'custom') {
            if (this.useGlobalService) {
                this.dateRangeService.setPreset(preset as DateRangePreset);
            }
            const range = this.dateRangeService.getDateRangeFromPreset(preset as DateRangePreset);
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

    getTooltip(preset: DateRangePreset): string {
        return this.dateRangeService.getRangeDescription(preset);
    }
}
