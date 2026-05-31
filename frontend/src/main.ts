import { provideZoneChangeDetection, isDevMode } from "@angular/core";
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

import { registerLocaleData } from '@angular/common';
import localeEsMx from '@angular/common/locales/es-MX';

registerLocaleData(localeEsMx, 'es-MX');

// Dev-only raw-stack overlay. Suppressed in production so end users never see
// the unstyled red stack dump; polished, translated error language is handled
// in-app (see core error handling / translate-api-error).
if (isDevMode()) {
  window.onerror = function (message, source, lineno, colno, error) {
    const errorDiv = document.createElement('div');
    errorDiv.style.color = 'red';
    errorDiv.style.padding = '20px';
    errorDiv.style.border = '2px solid red';
    errorDiv.style.margin = '20px';
    errorDiv.style.backgroundColor = '#fff0f0';
    errorDiv.style.fontFamily = 'monospace';
    errorDiv.innerHTML = `<h3>Runtime Error:</h3><p>${message}</p><pre>${error?.stack || ''}</pre>`;
    document.body.appendChild(errorDiv);
    return false;
  };
}

platformBrowserDynamic().bootstrapModule(AppModule, { applicationProviders: [provideZoneChangeDetection({ eventCoalescing: true })], })
  .catch(err => {
    console.error(err);
    const errorDiv = document.createElement('div');
    errorDiv.style.color = 'red';
    errorDiv.style.padding = '20px';
    errorDiv.innerHTML = `<h3>Bootstrap Error:</h3><pre>${err}</pre>`;
    document.body.appendChild(errorDiv);
  });
