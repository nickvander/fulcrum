import { TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { Sidenav } from './sidenav';
import { MatListModule } from '@angular/material/list';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { getTranslocoTestingModule } from '../../../testing/transloco-testing';

describe('Sidenav', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        Sidenav,
        MatListModule,
        NoopAnimationsModule,
        HttpClientTestingModule,
        RouterTestingModule,
        getTranslocoTestingModule(),
      ],
    }).compileComponents();
  });

  it('should create the component', () => {
    const fixture = TestBed.createComponent(Sidenav);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should start with all nav groups collapsed', () => {
    const fixture = TestBed.createComponent(Sidenav);
    const app = fixture.componentInstance;
    expect(app.expanded.inventory).toBe(false);
    expect(app.expanded.purchasing).toBe(false);
    expect(app.expanded.marketplaces).toBe(false);
  });

  it('should toggle the inventory group open and closed', () => {
    const fixture = TestBed.createComponent(Sidenav);
    const app = fixture.componentInstance;
    fixture.detectChanges();

    app.toggleGroup('inventory');
    expect(app.expanded.inventory).toBe(true);

    app.toggleGroup('inventory');
    expect(app.expanded.inventory).toBe(false);
  });

  it('should render the Operations section heading (not the old Menu label)', () => {
    const fixture = TestBed.createComponent(Sidenav);
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Operations');
    expect(text).not.toContain('Menu');
  });

  it('should render the Inventory group header', () => {
    const fixture = TestBed.createComponent(Sidenav);
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Inventory');
  });
});
