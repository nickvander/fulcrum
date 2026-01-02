import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { Settings } from './settings';

describe('Settings', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        Settings,
        HttpClientTestingModule,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: {
            availableLangs: ['en', 'es-MX'],
            defaultLang: 'en',
          },
        }),
      ],
    }).compileComponents();
  });

  it('should create the component', () => {
    const fixture = TestBed.createComponent(Settings);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});

