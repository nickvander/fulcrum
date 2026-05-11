import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { OnboardingStatus, OnboardingStep } from '../../services/onboarding.service';

@Component({
    selector: 'app-onboarding-checklist',
    standalone: true,
    imports: [
        CommonModule,
        RouterModule,
        MatButtonModule,
        MatIconModule,
        MatProgressBarModule,
        MatTooltipModule
    ],
    templateUrl: './onboarding-checklist.component.html',
    styleUrls: ['./onboarding-checklist.component.scss']
})
export class OnboardingChecklistComponent {
    @Input() status: OnboardingStatus | null = null;

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
}
