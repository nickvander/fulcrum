import { MoneyPipe } from './money.pipe';

describe('MoneyPipe', () => {
  let pipe: MoneyPipe;

  beforeEach(() => {
    pipe = new MoneyPipe();
  });

  it('defaults to MXN with the MX$ symbol', () => {
    expect(pipe.transform(1234.5)).toBe('MX$1,234.50');
  });

  it('renders USD as US$ so it is distinct from pesos', () => {
    expect(pipe.transform(50, 'USD')).toBe('US$50.00');
    // The whole point: MXN and USD never both collapse to a bare "$".
    expect(pipe.transform(50, 'MXN')).toBe('MX$50.00');
  });

  it('lower-cases input codes are normalized', () => {
    expect(pipe.transform(10, 'usd')).toBe('US$10.00');
  });

  it('renders € / £ / R$ for known symbols', () => {
    expect(pipe.transform(10, 'EUR')).toBe('€10.00');
    expect(pipe.transform(10, 'GBP')).toBe('£10.00');
    expect(pipe.transform(10, 'BRL')).toBe('R$10.00');
  });

  it('JPY has no decimals', () => {
    expect(pipe.transform(1500, 'JPY')).toBe('¥1,500');
  });

  it('unknown currency codes render the code after the number', () => {
    expect(pipe.transform(50, 'AUD')).toBe('50.00 AUD');
  });

  it('optionally appends the code for extra clarity', () => {
    expect(pipe.transform(50, 'USD', { showCode: true })).toBe('US$50.00 USD');
  });

  it('renders an em-dash for null / undefined / NaN', () => {
    expect(pipe.transform(null)).toBe('—');
    expect(pipe.transform(undefined)).toBe('—');
    expect(pipe.transform(NaN)).toBe('—');
  });

  it('handles zero and negatives', () => {
    expect(pipe.transform(0, 'MXN')).toBe('MX$0.00');
    expect(pipe.transform(-12.3, 'USD')).toBe('US$-12.30');
  });
});
