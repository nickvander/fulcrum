import { TestBed } from '@angular/core/testing';
import { AiSearchBar } from './ai-search-bar';
import { getTranslocoTestingModule } from '../../../testing/transloco-testing';

describe('AiSearchBar', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AiSearchBar, getTranslocoTestingModule()],
    }).compileComponents();
  });

  it('should create the component', () => {
    const fixture = TestBed.createComponent(AiSearchBar);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('tints the search_spark prefix icon with the shared AI gold class (moment B)', () => {
    const fixture = TestBed.createComponent(AiSearchBar);
    fixture.detectChanges();
    const icon: HTMLElement = fixture.nativeElement.querySelector('.search-icon');
    expect(icon).not.toBeNull();
    expect(icon.textContent?.trim()).toBe('search_spark');
    expect(icon.classList.contains('ai-accent')).toBe(true);
  });
});
