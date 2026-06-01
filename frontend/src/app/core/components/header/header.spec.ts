import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { Header } from './header';
import { BrandPulseService } from '../../services/brand-pulse.service';

import { provideRouter } from '@angular/router';

describe('Header', () => {
  let pulse: BrandPulseService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        Header,
        HttpClientTestingModule,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' }
        })
      ],
      providers: [provideRouter([])]
    }).compileComponents();

    pulse = TestBed.inject(BrandPulseService);
  });

  it('should create the component', () => {
    const fixture = TestBed.createComponent(Header);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('toggles the syncing class on a brand pulse and clears it after the window', () => {
    vi.useFakeTimers();
    try {
      const fixture = TestBed.createComponent(Header);
      const app = fixture.componentInstance;
      fixture.detectChanges(); // ngOnInit → subscribe to pulse$

      expect(app.syncing).toBe(false);

      pulse.pulse();
      expect(app.syncing).toBe(true);

      vi.advanceTimersByTime(app.SYNC_PULSE_MS);
      expect(app.syncing).toBe(false);
    } finally {
      vi.useRealTimers();
    }
  });

  it('stops reacting to pulses after destroy', () => {
    vi.useFakeTimers();
    try {
      const fixture = TestBed.createComponent(Header);
      const app = fixture.componentInstance;
      fixture.detectChanges();
      fixture.destroy();

      pulse.pulse();
      expect(app.syncing).toBe(false);
    } finally {
      vi.useRealTimers();
    }
  });
});
