import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

export type DateRangePreset = 'day' | 'week' | 'month' | '3months' | '6months' | 'year' | 'custom';

export interface DateRange {
    preset: DateRangePreset;
    startDate: Date;
    endDate: Date;
}

/**
 * Global date range service for app-wide date filtering.
 * Components subscribe to changes and apply consistent filtering.
 */
@Injectable({
    providedIn: 'root'
})
export class DateRangeService {
    private readonly defaultPreset: DateRangePreset = 'week';

    private dateRangeSubject = new BehaviorSubject<DateRange>(
        this.getDateRangeFromPreset(this.defaultPreset)
    );

    /** Observable for components to subscribe to date range changes (debounced) */
    dateRange$: Observable<DateRange> = this.dateRangeSubject.pipe(
        debounceTime(150),  // Debounce for smoother UI
        distinctUntilChanged((a, b) =>
            a.preset === b.preset &&
            a.startDate.getTime() === b.startDate.getTime() &&
            a.endDate.getTime() === b.endDate.getTime()
        )
    );

    /** Get current date range (immediate, for initial loads) */
    get currentRange(): DateRange {
        return this.dateRangeSubject.value;
    }

    /** Set date range from a preset */
    setPreset(preset: DateRangePreset): void {
        const range = this.getDateRangeFromPreset(preset);
        this.dateRangeSubject.next(range);
    }

    /** Set a custom date range */
    setCustomRange(startDate: Date, endDate: Date): void {
        this.dateRangeSubject.next({
            preset: 'custom',
            startDate,
            endDate
        });
    }

    /** Convert preset to actual dates */
    getDateRangeFromPreset(preset: DateRangePreset): DateRange {
        const now = new Date();
        const endDate = new Date(now);
        endDate.setHours(23, 59, 59, 999);

        let startDate = new Date(now);
        startDate.setHours(0, 0, 0, 0);

        switch (preset) {
            case 'day':
                // Today (start of day to end of day)
                startDate.setHours(0, 0, 0, 0);
                break;
            case 'week':
                // Last 7 Days
                startDate.setDate(now.getDate() - 7);
                break;
            case 'month':
                // Last 30 Days
                startDate.setMonth(now.getMonth() - 1);
                break;
            case '3months':
                // Last 90 Days
                startDate.setMonth(now.getMonth() - 3);
                break;
            case '6months':
                // Last 180 Days
                startDate.setMonth(now.getMonth() - 6);
                break;
            case 'year':
                // Last 365 Days
                startDate.setFullYear(now.getFullYear() - 1);
                break;
            case 'custom':
                // Custom range, use current values
                return this.dateRangeSubject.value;
        }

        return { preset, startDate, endDate };
    }

    /** Returns a human-readable range for a preset (e.g., "Oct 29 - Dec 29") */
    getRangeDescription(preset: DateRangePreset): string {
        const range = this.getDateRangeFromPreset(preset);
        const options: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' };

        if (preset === 'day') {
            return `Today (${range.startDate.toLocaleDateString(undefined, options)})`;
        }

        const startStr = range.startDate.toLocaleDateString(undefined, options);
        const endStr = range.endDate.toLocaleDateString(undefined, options);
        return `${startStr} - ${endStr}`;
    }

    /** Format date as YYYY-MM-DD for API calls */
    formatDateForApi(date: Date): string {
        return date.toISOString().split('T')[0];
    }

    /** Get formatted start/end for current range */
    getApiDates(): { startDate: string; endDate: string } {
        const range = this.currentRange;
        return {
            startDate: this.formatDateForApi(range.startDate),
            endDate: this.formatDateForApi(range.endDate)
        };
    }

    /**
     * Smart default: Find smallest range with sufficient data.
     * Call this with a data count check function.
     */
    async findSmartDefault(
        checkDataCount: (startDate: string, endDate: string) => Promise<number>,
        minCount: number = 5
    ): Promise<DateRangePreset> {
        const presets: DateRangePreset[] = ['week', 'month', '3months', '6months', 'year'];

        for (const preset of presets) {
            const range = this.getDateRangeFromPreset(preset);
            const startStr = this.formatDateForApi(range.startDate);
            const endStr = this.formatDateForApi(range.endDate);

            const count = await checkDataCount(startStr, endStr);
            if (count >= minCount) {
                return preset;
            }
        }

        return 'year'; // Fallback to max range
    }
}
