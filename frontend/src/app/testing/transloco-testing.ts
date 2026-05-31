import { TranslocoTestingModule, TranslocoTestingOptions } from '@ngneat/transloco';
import en from '../../assets/i18n/en.json';
import esMX from '../../assets/i18n/es-MX.json';

/**
 * Shared TranslocoTestingModule that loads the REAL translation files so that
 * a transloco.translate(key) call returns the actual English copy in specs
 * (default lang is 'en' here, even though the app default is 'es-MX'). This lets
 * component specs keep asserting on the English strings they were written against.
 */
export function getTranslocoTestingModule(options: TranslocoTestingOptions = {}) {
  return TranslocoTestingModule.forRoot({
    langs: { en, 'es-MX': esMX },
    translocoConfig: {
      availableLangs: ['en', 'es-MX'],
      defaultLang: 'en',
    },
    preloadLangs: true,
    ...options,
  });
}
