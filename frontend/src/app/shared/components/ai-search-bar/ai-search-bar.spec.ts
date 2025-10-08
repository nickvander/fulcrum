import { TestBed } from '@angular/core/testing';
import { AiSearchBar } from './ai-search-bar';

describe('AiSearchBar', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AiSearchBar],
    }).compileComponents();
  });

  it('should create the component', () => {
    const fixture = TestBed.createComponent(AiSearchBar);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
