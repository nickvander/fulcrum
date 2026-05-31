import { Directive, HostBinding, Input } from '@angular/core';

/**
 * Dense-table wrapper directive — Obsidian & Chile.
 *
 * Apply to a mat-table (or its wrapper) to opt into the cockpit dense style:
 * sticky header, hairline rows, tabular right-aligned money cells, and a
 * persisted compact-density toggle. Presentation is driven entirely by the
 * `.app-dense-table` class hook in styles so it tracks the token contract.
 *
 *   <table mat-table appDenseTable [compact]="densityCompact"> ... </table>
 *
 * Mark numeric columns with the `.numeric` / `.money` cell classes (defined
 * globally in styles.scss) to get tabular lining figures + right alignment.
 */
@Directive({
  selector: '[appDenseTable]',
  standalone: true,
})
export class DenseTableDirective {
  /** When true, rows tighten further (compact density). Persist via settings. */
  @Input() compact = false;

  @HostBinding('class.app-dense-table') readonly base = true;

  @HostBinding('class.app-dense-table--compact')
  get isCompact(): boolean {
    return this.compact;
  }
}
