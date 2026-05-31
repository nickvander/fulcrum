import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';

/**
 * Metric / KPI card — Obsidian & Chile.
 *
 * Neutral surface with a 3px chile-red top accent and a big tabular display
 * number (NOT a painted gradient — the brand forbids large painted brand
 * regions; see work/redesign/05a-BRAND-LOCK.md and the re-pointed `kpi-card`
 * mixin in theme/mixins.scss). Optional delta chip reuses the semantic
 * success / error tokens.
 *
 *   <app-metric-card
 *     [label]="'dashboard.totalValue' | transloco"
 *     [value]="total | money"
 *     [delta]="'+12.4%'"
 *     deltaTone="positive">
 *   </app-metric-card>
 */
@Component({
  selector: 'app-metric-card',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  template: `
    <div class="metric-card">
      <div class="metric-head">
        <span class="kpi-label">{{ label }}</span>
        <mat-icon *ngIf="icon" class="metric-icon">{{ icon }}</mat-icon>
      </div>
      <div class="kpi-value">{{ value }}</div>
      <div
        *ngIf="delta"
        class="metric-delta"
        [class.positive]="deltaTone === 'positive'"
        [class.negative]="deltaTone === 'negative'">
        <mat-icon *ngIf="deltaTone !== 'neutral'">
          {{ deltaTone === 'positive' ? 'trending_up' : 'trending_down' }}
        </mat-icon>
        <span>{{ delta }}</span>
      </div>
    </div>
  `,
  styles: [`
    .metric-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-top: 3px solid var(--primary-color);
      border-radius: var(--border-radius);
      box-shadow: var(--shadow-sm);
      padding: var(--card-padding, 24px);
      display: flex;
      flex-direction: column;
      gap: var(--space-2, 8px);
    }
    .metric-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--space-2, 8px);
    }
    .kpi-label {
      color: var(--text-secondary);
      font-size: var(--font-overline-size, 11px);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }
    .metric-icon {
      color: var(--text-hint);
    }
    .kpi-value {
      font-family: var(--font-display);
      font-size: var(--font-display-size, 32px);
      line-height: 1.05;
      font-weight: 700;
      color: var(--text-main);
      font-variant-numeric: tabular-nums lining-nums;
      font-feature-settings: "tnum" 1, "lnum" 1;
    }
    .metric-delta {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: var(--font-caption-size, 12.5px);
      font-weight: 600;
      color: var(--text-secondary);
      font-variant-numeric: tabular-nums lining-nums;
    }
    .metric-delta mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }
    .metric-delta.positive { color: var(--success-color); }
    .metric-delta.negative { color: var(--error-color); }
  `]
})
export class MetricCardComponent {
  @Input() label = '';
  @Input() value: string | number = '';
  @Input() icon?: string;
  @Input() delta?: string;
  @Input() deltaTone: 'positive' | 'negative' | 'neutral' = 'neutral';
}
