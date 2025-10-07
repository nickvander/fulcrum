import { TestBed } from '@angular/core/testing';
import { Sidenav } from './sidenav';

describe('Sidenav', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [Sidenav],
    }).compileComponents();
  });

  it('should create the component', () => {
    const fixture = TestBed.createComponent(Sidenav);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
