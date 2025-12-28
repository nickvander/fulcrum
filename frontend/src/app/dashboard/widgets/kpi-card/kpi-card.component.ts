import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-kpi-card',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatTooltipModule, RouterModule],
  template: `
    <mat-card class="kpi-card h-full cursor-pointer transition-shadow hover:shadow-lg" 
              [routerLink]="link"
              [matTooltip]="tooltip || ''">
      <mat-card-content class="flex flex-col justify-between p-4 h-full">
        <div class="flex justify-between items-start mb-2">
          <div class="icon-container p-2 rounded-lg" [style.background-color]="color + '20'">
            <mat-icon [style.color]="color">{{ icon }}</mat-icon>
          </div>
          <div class="status-indicator" *ngIf="status">
             <span class="text-xs font-medium px-2 py-1 rounded-full" 
                   [style.background-color]="statusColor + '20'"
                   [style.color]="statusColor">
               {{ status }}
             </span>
          </div>
        </div>
        <div>
          <h3 class="text-sm font-medium text-gray-500 uppercase tracking-wider">{{ title }}</h3>
          <p class="text-3xl font-bold mt-1">{{ value }}</p>
        </div>
      </mat-card-content>
    </mat-card>
  `,
  styles: [`
    :host { display: block; height: 100%; }
    .flex { display: flex; }
    .flex-col { flex-direction: column; }
    .justify-between { justify-content: space-between; }
    .items-start { align-items: flex-start; }
    .p-4 { padding: 1rem; }
    .h-full { height: 100%; }
    .text-sm { font-size: 0.875rem; }
    .text-3xl { font-size: 1.875rem; }
    .font-bold { font-weight: 700; }
    .font-medium { font-weight: 500; }
    .text-gray-500 { color: #6b7280; }
    .uppercase { text-transform: uppercase; }
    .tracking-wider { letter-spacing: 0.05em; }
    .mt-1 { margin-top: 0.25rem; }
    .mb-2 { margin-bottom: 0.5rem; }
    .rounded-lg { border-radius: 0.5rem; }
    .rounded-full { border-radius: 9999px; }
    .px-2 { padding-left: 0.5rem; padding-right: 0.5rem; }
    .py-1 { padding-top: 0.25rem; padding-bottom: 0.25rem; }
    .text-xs { font-size: 0.75rem; }
    .transition-shadow { transition: box-shadow 0.3s ease; }
    .hover\:shadow-lg:hover { box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); }
  `]
})
export class KpiCardComponent {
  @Input() title: string = '';
  @Input() value: string | number = 0;
  @Input() icon: string = 'show_chart';
  @Input() color: string = '#3f51b5';
  @Input() link: string | any[] = '/';
  @Input() status?: string;
  @Input() statusColor: string = '#10b981';
  @Input() tooltip?: string;
}
