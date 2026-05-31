import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { TranslocoModule } from '@ngneat/transloco';

/**
 * First-class error state — plain es-MX message + a single "Reintentar" CTA,
 * never a raw stack trace (Obsidian & Chile component language, see
 * work/redesign/05-design-system-and-plan.md §4 "Empty / loading / error").
 *
 * Pair with the existing app-empty-state / app-loading-spinner. The error
 * icon uses --error-color; the retry button emits (retry) for the caller.
 */
@Component({
  selector: 'app-error-state',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, TranslocoModule],
  template: `
    <div class="error-state">
      <mat-icon class="error-icon">{{ icon }}</mat-icon>
      <h3>{{ title || ('errors.generic.title' | transloco) }}</h3>
      <p *ngIf="message">{{ message }}</p>
      <button
        *ngIf="showRetry"
        mat-flat-button
        color="primary"
        (click)="retry.emit()">
        {{ retryLabel || ('errors.generic.retry' | transloco) }}
      </button>
    </div>
  `,
  styles: [`
    .error-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: var(--space-12, 48px) var(--space-6, 24px);
      text-align: center;
      color: var(--text-secondary);
    }
    .error-icon {
      font-size: 56px;
      width: 56px;
      height: 56px;
      margin-bottom: var(--space-4, 16px);
      color: var(--error-color);
    }
    h3 {
      margin: 0 0 var(--space-2, 8px);
      color: var(--text-main);
      font-family: var(--font-display);
    }
    p {
      margin: 0 0 var(--space-6, 24px);
      max-width: 420px;
    }
  `]
})
export class ErrorStateComponent {
  @Input() icon = 'error_outline';
  @Input() title?: string;
  @Input() message?: string;
  @Input() showRetry = true;
  @Input() retryLabel?: string;
  @Output() retry = new EventEmitter<void>();
}
