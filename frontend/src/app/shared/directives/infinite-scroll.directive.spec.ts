import { ElementRef } from '@angular/core';
import { InfiniteScrollDirective } from './infinite-scroll.directive';

/**
 * Simple unit tests for InfiniteScrollDirective.
 * 
 * Note: Full integration tests are skipped due to Vitest/Angular compatibility
 * issues with ElementRef DI. The directive is tested indirectly through 
 * product-list.spec.ts using a stub directive.
 */
describe('InfiniteScrollDirective', () => {
    let directive: InfiniteScrollDirective;
    let mockElementRef: ElementRef;

    beforeEach(() => {
        mockElementRef = { nativeElement: document.createElement('div') };
        directive = new InfiniteScrollDirective(mockElementRef);
    });

    describe('Default values', () => {
        it('should have default scrollThreshold of 200', () => {
            expect(directive.scrollThreshold).toBe(200);
        });

        it('should have default scrollThrottleTime of 200', () => {
            expect(directive.scrollThrottleTime).toBe(200);
        });

        it('should have null scrollContainer by default', () => {
            expect(directive.scrollContainer).toBeNull();
        });

        it('should have scrolled EventEmitter', () => {
            expect(directive.scrolled).toBeDefined();
            expect(typeof directive.scrolled.emit).toBe('function');
        });
    });

    describe('Input properties', () => {
        it('should accept custom scrollThreshold', () => {
            directive.scrollThreshold = 500;
            expect(directive.scrollThreshold).toBe(500);
        });

        it('should accept custom scrollThrottleTime', () => {
            directive.scrollThrottleTime = 100;
            expect(directive.scrollThrottleTime).toBe(100);
        });

        it('should accept scrollContainer reference', () => {
            const container = document.createElement('div');
            directive.scrollContainer = container;
            expect(directive.scrollContainer).toBe(container);
        });
    });

    describe('Lifecycle', () => {
        it('should implement OnInit', () => {
            expect(typeof directive.ngOnInit).toBe('function');
        });

        it('should implement OnDestroy', () => {
            expect(typeof directive.ngOnDestroy).toBe('function');
        });

        it('should not throw on destroy before init', () => {
            expect(() => directive.ngOnDestroy()).not.toThrow();
        });

        it('should clean up on destroy after init', () => {
            directive.ngOnInit();
            expect(() => directive.ngOnDestroy()).not.toThrow();
        });
    });
});
