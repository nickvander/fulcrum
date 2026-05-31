import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../material.module';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  imports: [CommonModule, MaterialModule],
  templateUrl: './empty-state.component.html',
  styleUrls: ['./empty-state.component.scss']
})
export class EmptyStateComponent {
  @Input() icon: string = 'info';
  @Input() title: string = '';
  @Input() description: string = '';

  /**
   * Presentation tone (signature moment E):
   *  - 'neutral' (default): the existing muted, generic empty state.
   *  - 'peer': warm, first-run peer-voice framing — a softer, more inviting
   *    layout. Pair it with `tú`-voice es-MX copy in the caller's i18n.
   * Existing call sites are untouched (default stays 'neutral').
   */
  @Input() tone: 'neutral' | 'peer' = 'neutral';

  /**
   * Render the chile-red pivot-wedge brand glyph instead of a Material icon
   * (reuses the header/rail clip-path motif). Defaults on for the peer tone so
   * first-run empties carry the brand mark; pass a Material `icon` to override.
   */
  @Input() useWedge: boolean | null = null;

  /** True when the wedge glyph should render (peer tone unless icon-overridden). */
  get showWedge(): boolean {
    if (this.useWedge !== null) {
      return this.useWedge;
    }
    return this.tone === 'peer';
  }
}
