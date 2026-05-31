import { Pipe, PipeTransform } from '@angular/core';
import { formatMxn, MxnOptions } from '../money/money';

/**
 * Template-side wrapper around the shared MXN formatter.
 * Usage: {{ product.price | mxn }}  ·  {{ value | mxn:{ showCode: true } }}
 */
@Pipe({ name: 'mxn', standalone: true, pure: true })
export class MxnPipe implements PipeTransform {
  transform(value: number | null | undefined, options?: MxnOptions): string {
    return formatMxn(value, options);
  }
}
