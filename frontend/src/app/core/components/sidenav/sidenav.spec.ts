import { TestBed } from '@angular/core/testing';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { RouterTestingModule } from '@angular/router/testing';
import { Sidenav } from './sidenav';
import { MatListModule } from '@angular/material/list';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';

describe('Sidenav', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        Sidenav,
        MatListModule,
        NoopAnimationsModule,
        HttpClientTestingModule,
        RouterTestingModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, es: {} },
          translocoConfig: { availableLangs: ['en', 'es'], defaultLang: 'en' }
        })
      ],
    }).compileComponents();
  });

  it('should create the component', () => {
    const fixture = TestBed.createComponent(Sidenav);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
