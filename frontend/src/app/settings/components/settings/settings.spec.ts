import { TestBed } from '@angular/core/testing';
import { Settings } from './settings';

describe('Settings', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [Settings],
    }).compileComponents();
  });

  it('should create the component', () => {
    const fixture = TestBed.createComponent(Settings);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
