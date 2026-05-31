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
});
