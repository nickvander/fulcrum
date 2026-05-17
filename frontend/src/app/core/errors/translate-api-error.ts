import { HttpErrorResponse } from '@angular/common/http';
import { TranslocoService } from '@ngneat/transloco';

/**
 * Resolves an API error to a localized, user-facing string.
 *
 * Wire shape from `LocalizedHTTPException`:
 *   { detail: "Product 7 not found", code: "apiErrors.product.notFound", params: { id: 7 } }
 *
 * If `code` is present we translate it; otherwise we fall back to `detail`
 * (legacy endpoints), then `err.message`, then the supplied `fallbackKey`.
 */
export function translateApiError(
  err: unknown,
  transloco: TranslocoService,
  fallbackKey = 'apiErrors.unknown',
): string {
  const body = (err instanceof HttpErrorResponse ? err.error : (err as { error?: unknown })?.error) as
    | { code?: string; params?: Record<string, unknown>; detail?: unknown }
    | undefined
    | null;

  if (body && typeof body.code === 'string' && body.code.length > 0) {
    return transloco.translate(body.code, body.params ?? {});
  }

  if (body && typeof body.detail === 'string' && body.detail.length > 0) {
    return body.detail;
  }

  const message = (err as { message?: unknown })?.message;
  if (typeof message === 'string' && message.length > 0) {
    return message;
  }

  return transloco.translate(fallbackKey);
}
