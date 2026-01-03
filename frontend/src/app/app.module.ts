import { NgModule, provideBrowserGlobalErrorListeners, isDevMode } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withInterceptors, HttpClientModule } from '@angular/common/http';
import { MatPaginatorIntl } from '@angular/material/paginator';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { CoreModule } from './core/core-module';
import { AuthModule } from './auth/auth-module';
import { AuthInterceptor } from './auth/interceptors/auth-interceptor';
import { ServiceWorkerModule } from '@angular/service-worker';
import { LoadingInterceptor } from './core/interceptors/loading.interceptor';
import { HttpErrorInterceptor } from './core/interceptors/http-error.interceptor';
import { MaterialModule } from './shared/material.module';

import { TranslocoRootModule } from './transloco-root.module';
import { TranslocoPaginatorIntl } from './shared/services/transloco-paginator-intl';

@NgModule({
  imports: [
    TranslocoRootModule,
    AppComponent,
    BrowserModule,
    BrowserAnimationsModule,
    HttpClientModule,
    CoreModule,
    AuthModule,
    MaterialModule,
    ServiceWorkerModule.register('ngsw-worker.js', {
      enabled: !isDevMode(),
      // Register the ServiceWorker as soon as the application is stable
      // or after 30 seconds (whichever comes first).
      registrationStrategy: 'registerWhenStable:30000'
    }),
    AppRoutingModule
  ],
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideAnimationsAsync(),
    provideHttpClient(withInterceptors([AuthInterceptor, LoadingInterceptor, HttpErrorInterceptor])),
    { provide: MatPaginatorIntl, useClass: TranslocoPaginatorIntl }
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
