import { HttpErrorResponse } from '@angular/common/http';
import { translateApiError } from './translate-api-error';

describe('translateApiError', () => {
  function makeTransloco(translations: Record<string, (params?: Record<string, unknown>) => string>) {
    return {
      translate(key: string, params?: Record<string, unknown>): string {
        const fn = translations[key];
        return fn ? fn(params) : `[missing:${key}]`;
      },
    } as any;
  }

  it('translates code with params when payload has code', () => {
    const transloco = makeTransloco({
      'apiErrors.product.notFound': (p) => `No product ${p?.['id']}`,
    });
    const err = new HttpErrorResponse({
      status: 404,
      error: {
        detail: 'Product not found',
        code: 'apiErrors.product.notFound',
        params: { id: 7 },
      },
    });

    expect(translateApiError(err, transloco)).toBe('No product 7');
  });

  it('falls back to detail when code is absent (legacy endpoint)', () => {
    const transloco = makeTransloco({});
    const err = new HttpErrorResponse({
      status: 500,
      error: { detail: 'Something went wrong' },
    });

    expect(translateApiError(err, transloco)).toBe('Something went wrong');
  });

  it('falls back to err.message when neither code nor detail are present', () => {
    const transloco = makeTransloco({});
    const err = new HttpErrorResponse({ status: 0, statusText: 'Unknown', error: null });

    expect(translateApiError(err, transloco)).toBe(err.message);
  });

  it('falls back to fallbackKey translation when everything is empty', () => {
    const transloco = makeTransloco({
      'apiErrors.unknown': () => 'Algo salió mal',
    });
    const err = { error: null } as any;

    expect(translateApiError(err, transloco)).toBe('Algo salió mal');
  });

  it('honors a custom fallbackKey', () => {
    const transloco = makeTransloco({
      'users.errors.importFailed': () => 'Import failed',
    });
    const err = { error: null } as any;

    expect(translateApiError(err, transloco, 'users.errors.importFailed')).toBe('Import failed');
  });

  it('passes empty params object when payload omits params', () => {
    let received: Record<string, unknown> | undefined;
    const transloco = {
      translate(key: string, params?: Record<string, unknown>): string {
        received = params;
        return key;
      },
    } as any;
    const err = new HttpErrorResponse({
      status: 400,
      error: { code: 'apiErrors.something' },
    });

    translateApiError(err, transloco);
    expect(received).toEqual({});
  });
});
