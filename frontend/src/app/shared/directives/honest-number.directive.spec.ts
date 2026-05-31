import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import { HonestNumberDirective } from './honest-number.directive';

@Component({
  standalone: true,
  imports: [HonestNumberDirective],
  template: `<div appHonestNumber [tone]="tone">{{ text }}</div>`,
})
class HostComponent {
  tone: 'profit' | 'loss' | 'neutral' = 'neutral';
  text = 'MX$1,234.50 MXN';
}

describe('HonestNumberDirective', () => {
  let fixture: ComponentFixture<HostComponent>;
  let host: HostComponent;

  function el(): HTMLElement {
    return fixture.debugElement.query(By.directive(HonestNumberDirective))
      .nativeElement as HTMLElement;
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    host = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('applies the shared primitive class hook', () => {
    expect(el().classList.contains('app-honest-number')).toBe(true);
  });

  it('renders the profit tone (success) — never the chile-red primary', () => {
    host.tone = 'profit';
    fixture.detectChanges();
    const node = el();
    expect(node.classList.contains('app-honest-number--profit')).toBe(true);
    expect(node.classList.contains('app-honest-number--loss')).toBe(false);
    expect(node.classList.contains('app-honest-number--neutral')).toBe(false);
    // No brand/primary class is ever placed on a money number.
    expect(node.className).not.toMatch(/primary|result-won/);
  });

  it('renders the loss tone (danger) — never the chile-red primary', () => {
    host.tone = 'loss';
    fixture.detectChanges();
    const node = el();
    expect(node.classList.contains('app-honest-number--loss')).toBe(true);
    expect(node.classList.contains('app-honest-number--profit')).toBe(false);
    expect(node.className).not.toMatch(/primary/);
  });

  it('defaults to the neutral tone', () => {
    expect(el().classList.contains('app-honest-number--neutral')).toBe(true);
  });

  it('leaves the formatted amount text untouched (presentation only, no rewrite)', () => {
    expect(el().textContent).toContain('MX$1,234.50 MXN');
  });
});
