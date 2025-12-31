import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterModule } from '@angular/router';

@Component({
    selector: 'app-stat-card',
    standalone: true,
    imports: [CommonModule, MatCardModule, MatIconModule, MatTooltipModule, RouterModule],
    template: `
    <div class="stat-card"
         [class.gradient-primary]="colorType === 'primary'"
         [class.gradient-accent]="colorType === 'accent'"
         [class.gradient-success]="colorType === 'success'"
         [class.gradient-warn]="colorType === 'warn'"
         [class.gradient-error]="colorType === 'error'"
         [routerLink]="link"
         [matTooltip]="tooltip || ''">
        <div class="kpi-value">{{ value }}</div>
        <div class="kpi-label">{{ title }}</div>
        <mat-icon class="kpi-icon">{{ icon }}</mat-icon>
    </div>
  `,
    styles: [`
    @use '../../../../theme/variables' as v;

    :host { display: block; height: 100%; }

    .stat-card {
        border-radius: var(--border-radius);
        box-shadow: var(--shadow-sm);
        overflow: hidden;
        transition: box-shadow 0.2s ease, transform 0.2s ease;
        color: white;
        padding: 20px 24px;
        position: relative;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        cursor: pointer;
    }

    .stat-card:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }

    .kpi-value {
        font-size: 1.5rem;
        font-weight: 700;
        line-height: 1.2;
    }

    .kpi-label {
        opacity: 0.9;
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }

    .kpi-icon {
        position: absolute;
        top: 16px;
        right: 16px;
        opacity: 0.3;
        font-size: 40px;
        width: 40px;
        height: 40px;
    }

    .gradient-primary {
        background: var(--gradient-primary);
    }

    .gradient-accent {
        background: var(--gradient-accent);
    }

    .gradient-success {
        background: var(--gradient-success);
    }

    .gradient-warn {
        background: var(--gradient-warn);
    }

    .gradient-error {
        background: linear-gradient(135deg, #EF5350 0%, #C62828 100%);
    }
  `]
})
export class StatCardComponent {
    @Input() title: string = '';
    @Input() value: string | number = 0;
    @Input() icon: string = 'show_chart';
    @Input() colorType: 'primary' | 'accent' | 'success' | 'warn' | 'error' = 'primary';
    @Input() link: string | any[] | null = null;
    @Input() tooltip?: string;

    // Legacy inputs for backward compatibility
    @Input() gradient?: string;
    @Input() color?: string;
    @Input() iconColor?: string;
    @Input() iconBgColor?: string;
    @Input() status?: string;
    @Input() statusColor?: string;
}
