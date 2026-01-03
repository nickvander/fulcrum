import { TestBed } from '@angular/core/testing';
import { AppComponent } from './app.component';
import { RouterTestingModule } from '@angular/router/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatNativeDateModule } from '@angular/material/core';
import { CoreModule } from './core/core-module';
import { CommonModule } from '@angular/common';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('AppComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        AppComponent,
        RouterTestingModule,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: {
            availableLangs: ['en', 'es-MX'],
            defaultLang: 'en',
          },
        }),
        MatNativeDateModule,
      ],
    })
      .overrideComponent(AppComponent, {
        set: {
          imports: [CommonModule, CoreModule, RouterTestingModule],
        },
      })
      .compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});

