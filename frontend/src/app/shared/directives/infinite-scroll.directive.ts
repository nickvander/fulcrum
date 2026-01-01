import {
    Directive,
    ElementRef,
    Output,
    EventEmitter,
    OnInit,
    OnDestroy,
    Input,
} from '@angular/core';
import { fromEvent, Subscription } from 'rxjs';
import { throttleTime } from 'rxjs/operators';

/**
 * Directive that emits an event when the user scrolls near the bottom.
 *
 * Usage:
 *   - For window-based scrolling (default):
 *     `<div appInfiniteScroll (scrolled)="loadMore()"></div>`
 *
 *   - For container-based scrolling:
 *     `<div appInfiniteScroll [scrollContainer]="containerRef" (scrolled)="loadMore()"></div>`
 *
 * @example
 * ```html
 * <!-- Window scroll -->
 * <div class="grid">...</div>
 * <div appInfiniteScroll (scrolled)="onLoadMore()"></div>
 *
 * <!-- Container scroll -->
 * <div #container class="scrollable-container">
 *   <div class="content">...</div>
 *   <div appInfiniteScroll [scrollContainer]="container" (scrolled)="onLoadMore()"></div>
 * </div>
 * ```
 */
@Directive({
    selector: '[appInfiniteScroll]',
    standalone: true,
})
export class InfiniteScrollDirective implements OnInit, OnDestroy {
    /** Optional scroll container element. If not provided, uses window scroll. */
    @Input() scrollContainer: HTMLElement | null = null;

    /** Distance from bottom (in pixels) at which to trigger the scroll event. */
    @Input() scrollThreshold: number = 200;

    /** Throttle time in milliseconds between scroll checks. */
    @Input() scrollThrottleTime: number = 200;

    /** Emitted when user scrolls near the bottom of the container/window. */
    @Output() scrolled = new EventEmitter<void>();

    private scrollSubscription: Subscription | undefined;

    constructor(private elementRef: ElementRef) { }

    ngOnInit(): void {
        this.setupScrollListener();
    }

    ngOnDestroy(): void {
        if (this.scrollSubscription) {
            this.scrollSubscription.unsubscribe();
        }
    }

    private setupScrollListener(): void {
        if (this.scrollContainer) {
            // Container-based scrolling
            this.scrollSubscription = fromEvent(this.scrollContainer, 'scroll')
                .pipe(throttleTime(this.scrollThrottleTime))
                .subscribe(() => this.checkContainerScroll());
        } else {
            // Window-based scrolling (default)
            this.scrollSubscription = fromEvent(window, 'scroll')
                .pipe(throttleTime(this.scrollThrottleTime))
                .subscribe(() => this.checkWindowScroll());
        }
    }

    private checkWindowScroll(): void {
        const pos = window.innerHeight + window.scrollY;
        const max = document.documentElement.scrollHeight;

        if (pos >= max - this.scrollThreshold) {
            this.scrolled.emit();
        }
    }

    private checkContainerScroll(): void {
        if (!this.scrollContainer) return;

        const { scrollTop, scrollHeight, clientHeight } = this.scrollContainer;
        const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

        if (distanceFromBottom <= this.scrollThreshold) {
            this.scrolled.emit();
        }
    }
}
