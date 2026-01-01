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
    templateUrl: './stat-card.component.html',
    styleUrls: ['./stat-card.component.scss']
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
