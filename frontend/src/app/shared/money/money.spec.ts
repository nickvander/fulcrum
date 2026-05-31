import { describe, it, expect } from 'vitest';
import { formatMxn } from './money';

// Non-breaking-space and narrow-no-break-space tolerant compare: Intl may insert
// either between the symbol and the digits depending on the ICU build.
const normalize = (s: string) => s.replace(/ | /g, ' ');

describe('formatMxn', () => {
  it('formats a plain amount as MXN with $ symbol and 2 decimals', () => {
    expect(normalize(formatMxn(1234.5))).toBe('$1,234.50');
  });

  it('formats whole numbers with cents by default', () => {
    expect(normalize(formatMxn(1000))).toBe('$1,000.00');
  });

  it('drops cents for whole numbers when hideCents is set', () => {
    expect(normalize(formatMxn(1000, { hideCents: true }))).toBe('$1,000');
  });

  it('keeps cents for non-whole numbers even when hideCents is set', () => {
    expect(normalize(formatMxn(1000.25, { hideCents: true }))).toBe('$1,000.25');
  });

  it('formats zero', () => {
    expect(normalize(formatMxn(0))).toBe('$0.00');
  });

  it('appends the MXN code when showCode is set', () => {
    expect(normalize(formatMxn(50))).toBe('$50.00');
    expect(normalize(formatMxn(50, { showCode: true }))).toBe('$50.00 MXN');
  });

  it('returns a dash for null / undefined / NaN', () => {
    expect(formatMxn(null)).toBe('—');
    expect(formatMxn(undefined)).toBe('—');
    expect(formatMxn(NaN)).toBe('—');
  });

  it('never produces a USD-style or bare-$ output (guardrail)', () => {
    const out = formatMxn(99.99);
    expect(out).not.toContain('US$');
    expect(out).toContain('$');
  });
});
