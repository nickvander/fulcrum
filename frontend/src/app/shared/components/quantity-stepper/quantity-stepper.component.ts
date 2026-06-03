import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

/**
 * Touch-friendly numeric stepper: − / [n] / + with a numeric soft-keyboard.
 * Replaces raw `<input type="number">` (wrong mobile keyboard, spinner noise,
 * tiny tap targets) across the inventory operations (receive / count / adjust /
 * transfer). Value-based (no ControlValueAccessor) so it drops into both
 * reactive forms and ngModel via [value] / (valueChange).
 */
@Component({
  selector: 'app-quantity-stepper',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatButtonModule, MatIconModule],
  template: `
    <div class="qstepper">
      <button type="button" mat-icon-button class="step" (click)="dec()" [disabled]="atMin"
        [attr.aria-label]="'decrement'">
        <mat-icon>remove</mat-icon>
      </button>
      <input
        class="qval"
        type="text"
        inputmode="numeric"
        [value]="value"
        (input)="onInput($event)"
        (blur)="commit()"
        [attr.aria-label]="ariaLabel" />
      <button type="button" mat-icon-button class="step" (click)="inc()" [disabled]="atMax"
        [attr.aria-label]="'increment'">
        <mat-icon>add</mat-icon>
      </button>
    </div>
  `,
  styleUrl: './quantity-stepper.component.scss',
})
export class QuantityStepperComponent {
  @Input() value = 0;
  @Input() min: number | null = null;
  @Input() max: number | null = null;
  @Input() step = 1;
  @Input() ariaLabel = '';
  @Output() valueChange = new EventEmitter<number>();

  private draft: number = 0;

  get atMin(): boolean {
    return this.min !== null && this.value <= this.min;
  }
  get atMax(): boolean {
    return this.max !== null && this.value >= this.max;
  }

  private clamp(n: number): number {
    let v = Number.isFinite(n) ? n : 0;
    if (this.min !== null) v = Math.max(this.min, v);
    if (this.max !== null) v = Math.min(this.max, v);
    return v;
  }

  inc(): void {
    this.emit(this.clamp(this.value + this.step));
  }
  dec(): void {
    this.emit(this.clamp(this.value - this.step));
  }

  onInput(event: Event): void {
    // Allow a leading '-' for fields whose min is negative (e.g. adjustments).
    const raw = (event.target as HTMLInputElement).value.replace(/[^\d-]/g, '');
    this.draft = raw === '' || raw === '-' ? 0 : parseInt(raw, 10);
  }

  commit(): void {
    this.emit(this.clamp(this.draft));
  }

  private emit(v: number): void {
    if (v !== this.value) {
      this.value = v;
      this.valueChange.emit(v);
    }
    this.draft = v;
  }
}
