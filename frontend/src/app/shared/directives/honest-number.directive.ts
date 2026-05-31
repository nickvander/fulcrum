import { Directive, HostBinding, Input } from '@angular/core';

/**
 * `appHonestNumber` — the "honest MXN number" primitive (signature moment C).
 *
 * Applies the ONE shared big-money treatment: Space Grotesk display face,
 * tabular lining figures, oversized headline, a muted currency unit, and a
 * SEMANTIC tone (profit = success, loss = danger). It NEVER paints chile-red on
 * a money number — that's the brand action color, not a money color (brand
 * lock). The visual rules live in `styles/_honest-number.scss`; this directive
 * is the single class-hook + tone driver so every call site shares one source
 * of truth.
 *
 * PRESENTATION ONLY. The amount must already be formatted by the shared
 * `money` / MoneyPipe formatter — the directive styles the formatted string; it
 * does NOT format, parse, or compute the number, and (deliberately) does NOT
 * rewrite the host's text node, so it never fights Angular's interpolation
 * binding. To mute the trailing currency code, wrap it in the partial's
 * `.app-honest-number__unit` span at the call site, e.g.
 *
 *   <span appHonestNumber [tone]="t">
 *     {{ amount | money }}<span class="app-honest-number__unit">MXN</span>
 *   </span>
 *
 * `tone`: 'profit' | 'loss' | 'neutral'. (For callers whose state is the
 * profit-summary verdict, map won→profit, lost→loss, even→neutral.)
 */
@Directive({
  selector: '[appHonestNumber]',
  standalone: true,
})
export class HonestNumberDirective {
  /** Semantic tone — drives the color token. Never chile-red on money. */
  @Input() tone: 'profit' | 'loss' | 'neutral' = 'neutral';

  @HostBinding('class.app-honest-number') readonly base = true;

  @HostBinding('class.app-honest-number--profit')
  get isProfit(): boolean {
    return this.tone === 'profit';
  }
  @HostBinding('class.app-honest-number--loss')
  get isLoss(): boolean {
    return this.tone === 'loss';
  }
  @HostBinding('class.app-honest-number--neutral')
  get isNeutral(): boolean {
    return this.tone === 'neutral';
  }
}
