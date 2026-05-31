import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { HonestNumberDirective } from '../../directives/honest-number.directive';

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
  imports: [CommonModule, MatIconModule, HonestNumberDirective],
  template: `
    <div class="metric-card">
      <div class="metric-head">
        <span class="kpi-label">{{ label }}</span>
        <mat-icon *ngIf="icon" class="metric-icon">{{ icon }}</mat-icon>
      </div>
      <!-- Money headline → the shared honest-number primitive (moment C):
           muted unit + semantic tone. Other KPIs keep the plain kpi-value. -->
      <div
        *ngIf="honest; else plainValue"
        class="kpi-value kpi-value--honest"
        appHonestNumber
        [tone]="tone">{{ value }}</div>
      <ng-template #plainValue>
        <div class="kpi-value">{{ value }}</div>
      </ng-template>
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
    /* Honest-number variant pins the shared primitive to the KPI headline size
       (the .app-honest-number type rules come from styles/_honest-number.scss). */
    .kpi-value--honest {
      --honest-number-size: var(--font-display-size, 32px);
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

  /** Opt the headline value into the shared "honest MXN number" primitive
   *  (moment C): muted currency unit + semantic tone. Use for money headlines
   *  only — not percentages/counts. */
  @Input() honest = false;
  /** Semantic tone for the honest number. Default neutral (a plain money
   *  headline like inventory value). Never chile-red on money. */
  @Input() tone: 'profit' | 'loss' | 'neutral' = 'neutral';
}
