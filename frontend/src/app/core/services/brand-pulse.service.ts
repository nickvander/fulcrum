import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';

/**
 * Tiny app-wide signal that a *real* "synced to MercadoLibre" success just
 * happened, so the brand pivot-wedge mark (header + sidenav) can play its
 * subtle "tilt/settle" sync-pulse — a restrained signature moment of motion.
 *
 * Deliberately minimal: a single fire-and-forget Subject. There is no
 * app-wide event bus today (NotificationService only does snackbars), so this
 * stays scoped to the brand-pulse concern and mirrors the BehaviorSubject
 * pattern used by DateRangeService.
 *
 * Fire it ONLY on genuine ML pushes/syncs (not failures or reauth prompts):
 *   - an inbound shipped to ML Full (ship with pushToMarketplace=true),
 *   - a listing sync that did NOT need re-authorization.
 */
@Injectable({ providedIn: 'root' })
export class BrandPulseService {
  private readonly _pulse$ = new Subject<BrandPulseReason>();

  /** Emits each time a real ML sync success should pulse the brand wedge. */
  readonly pulse$: Observable<BrandPulseReason> = this._pulse$.asObservable();

  /**
   * Trigger one brand-wedge sync-pulse. `reason` is optional context kept for
   * future use (e.g. analytics or differentiated cues); it does not change the
   * motion today.
   */
  pulse(reason: BrandPulseReason = 'ml-sync'): void {
    this._pulse$.next(reason);
  }
}

/** Why the wedge pulsed. Open-ended string for future reasons. */
export type BrandPulseReason = 'ml-sync' | (string & {});
