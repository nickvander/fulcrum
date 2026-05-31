import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MetricCardComponent } from './metric-card.component';

describe('MetricCardComponent', () => {
  let fixture: ComponentFixture<MetricCardComponent>;
  let component: MetricCardComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MetricCardComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(MetricCardComponent);
    component = fixture.componentInstance;
  });

  it('renders a plain kpi value by default (no honest-number primitive)', () => {
    component.label = 'Inventory value';
    component.value = 'MX$525.00';
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const value = root.querySelector('.kpi-value');
    expect(value?.textContent).toContain('MX$525.00');
    expect(value?.classList.contains('app-honest-number')).toBe(false);
  });

  it('opts the money headline into the honest-number primitive when honest=true (moment C)', () => {
    component.label = 'Inventory value';
    component.value = 'MX$525.00';
    component.honest = true;
    fixture.detectChanges();
    const value = (fixture.nativeElement as HTMLElement).querySelector('.kpi-value');
    expect(value?.classList.contains('kpi-value--honest')).toBe(true);
    // Directive applies the shared primitive class + neutral tone (no chile-red).
    expect(value?.classList.contains('app-honest-number')).toBe(true);
    expect(value?.classList.contains('app-honest-number--neutral')).toBe(true);
    expect(value?.className).not.toMatch(/primary/);
  });
});
