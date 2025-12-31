import { Injectable, inject } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Observable, map, shareReplay } from 'rxjs';

/**
 * Service to detect current device/screen size.
 * Uses Angular CDK BreakpointObserver for responsive layouts.
 */
@Injectable({
    providedIn: 'root'
})
export class ScreenService {
    private breakpointObserver = inject(BreakpointObserver);

    /**
     * Breakpoint definitions based on common device widths
     */
    private static readonly BREAKPOINTS = {
        mobile: '(max-width: 767px)',
        tablet: '(min-width: 768px) and (max-width: 1023px)',
        desktop: '(min-width: 1024px)',
    };

    /**
     * True when viewport is phone-sized (< 768px)
     */
    readonly isMobile$: Observable<boolean> = this.breakpointObserver
        .observe(ScreenService.BREAKPOINTS.mobile)
        .pipe(
            map(result => result.matches),
            shareReplay(1)
        );

    /**
     * True when viewport is tablet-sized (768px - 1023px)
     */
    readonly isTablet$: Observable<boolean> = this.breakpointObserver
        .observe(ScreenService.BREAKPOINTS.tablet)
        .pipe(
            map(result => result.matches),
            shareReplay(1)
        );

    /**
     * True when viewport is desktop-sized (>= 1024px)
     */
    readonly isDesktop$: Observable<boolean> = this.breakpointObserver
        .observe(ScreenService.BREAKPOINTS.desktop)
        .pipe(
            map(result => result.matches),
            shareReplay(1)
        );

    /**
     * True when viewport is NOT desktop (mobile or tablet)
     */
    readonly isMobileOrTablet$: Observable<boolean> = this.breakpointObserver
        .observe([ScreenService.BREAKPOINTS.mobile, ScreenService.BREAKPOINTS.tablet])
        .pipe(
            map(result => result.matches),
            shareReplay(1)
        );

    /**
     * Current device type as a string
     */
    readonly deviceType$: Observable<'mobile' | 'tablet' | 'desktop'> = this.breakpointObserver
        .observe([
            ScreenService.BREAKPOINTS.mobile,
            ScreenService.BREAKPOINTS.tablet,
            ScreenService.BREAKPOINTS.desktop
        ])
        .pipe(
            map(result => {
                if (result.breakpoints[ScreenService.BREAKPOINTS.mobile]) return 'mobile' as const;
                if (result.breakpoints[ScreenService.BREAKPOINTS.tablet]) return 'tablet' as const;
                return 'desktop' as const;
            }),
            shareReplay(1)
        );
}
