import { Directive, ElementRef, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { fromEvent, Subscription } from 'rxjs';
import { throttleTime } from 'rxjs/operators';

@Directive({
  selector: '[appInfiniteScroll]'
})
export class InfiniteScrollDirective implements OnInit, OnDestroy {
  @Output() scrolled = new EventEmitter<void>();

  private scrollSubscription: Subscription | undefined;

  constructor(private elementRef: ElementRef) {}

  ngOnInit(): void {
    this.scrollSubscription = fromEvent(window, 'scroll')
      .pipe(throttleTime(200))
      .subscribe(() => {
        const pos = window.innerHeight + window.scrollY;
        const max = document.documentElement.scrollHeight;
        
        // Trigger when we're within 100px of the bottom
        if (pos >= max - 100) {
          this.scrolled.emit();
        }
      });
  }

  ngOnDestroy(): void {
    if (this.scrollSubscription) {
      this.scrollSubscription.unsubscribe();
    }
  }
}