import { TestBed } from '@angular/core/testing';
import { App } from './app';
import { RouterTestingModule } from '@angular/router/testing';
import { AppRoutingModule } from './app-routing-module';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { CoreModule } from './core/core-module';
import { CommonModule } from '@angular/common';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App, RouterTestingModule, NoopAnimationsModule],
    })
    .overrideComponent(App, {
      set: {
        imports: [CommonModule, CoreModule, RouterTestingModule],
      },
    })
    .compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
