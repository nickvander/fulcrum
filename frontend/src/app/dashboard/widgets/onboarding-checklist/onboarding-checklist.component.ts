import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';
import { OnboardingStatus, OnboardingStep } from '../../services/onboarding.service';

const DISMISSED_KEY = 'fulcrum_onboarding_dismissed';

@Component({
    selector: 'app-onboarding-checklist',
    standalone: true,
    imports: [
        CommonModule,
        RouterModule,
        MatButtonModule,
        MatIconModule,
        MatProgressBarModule,
        MatTooltipModule,
        TranslocoModule
    ],
    templateUrl: './onboarding-checklist.component.html',
    styleUrls: ['./onboarding-checklist.component.scss']
})
export class OnboardingChecklistComponent implements OnChanges {
    @Input() status: OnboardingStatus | null = null;
    @Input() creatingDemo = false;
    @Output() createDemoWorkspace = new EventEmitter<void>();

    /** When true the operator clicked "dismiss" on the success banner.
     *  Persisted in localStorage so a page refresh keeps it hidden. */
    dismissed = false;

    /** Operator clicked "View details" on the success banner to temporarily
     *  re-expand the checklist even after completing setup. */
    expanded = false;

    ngOnChanges(changes: SimpleChanges): void {
        if (changes['status'] && this.status?.complete) {
            this.dismissed = localStorage.getItem(DISMISSED_KEY) === 'true';
        }
    }

    get showFull(): boolean {
        // Show the full grid when: setup isn't complete yet, OR the operator
        // explicitly re-expanded it.
        if (!this.status?.complete) return true;
        return this.expanded;
    }

    get showBanner(): boolean {
        // Show the compact success banner when: complete AND not dismissed
        // AND not expanded (expanded replaces banner with the full grid).
        return !!(this.status?.complete && !this.dismissed && !this.expanded);
    }

    dismiss(): void {
        this.dismissed = true;
        this.expanded = false;
        localStorage.setItem(DISMISSED_KEY, 'true');
    }

    toggleExpand(): void {
        this.expanded = !this.expanded;
    }

    trackStep(_: number, step: OnboardingStep): string {
        return step.key;
    }

    progressValue(): number {
        if (!this.status || this.status.total_required === 0) return 0;
        return Math.round((this.status.completed_required / this.status.total_required) * 100);
    }

    stateIcon(step: OnboardingStep): string {
        if (step.complete) return 'check_circle';
        if (step.optional) return 'radio_button_unchecked';
        return 'error';
    }

    requestDemoWorkspace(): void {
        if (this.creatingDemo) return;
        this.createDemoWorkspace.emit();
    }
}
