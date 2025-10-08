import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';

@Pipe({
  name: 'safeUrl',
})
export class SafeUrlPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(value: Blob | null): SafeUrl | null {
    if (!value) {
      return null;
    }
    const url = URL.createObjectURL(value);
    return this.sanitizer.bypassSecurityTrustUrl(url);
  }
}