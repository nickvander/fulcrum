import { TestBed } from '@angular/core/testing';
import { Sidenav } from './sidenav';
import { MatListModule } from '@angular/material/list';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('Sidenav', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [Sidenav],
      imports: [MatListModule, NoopAnimationsModule],
    }).compileComponents();
  });

  it('should create the component', () => {
    const fixture = TestBed.createComponent(Sidenav);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
