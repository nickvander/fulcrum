import { TestBed } from '@angular/core/testing';
import { BrandPulseService } from './brand-pulse.service';

describe('BrandPulseService', () => {
  let service: BrandPulseService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [BrandPulseService] });
    service = TestBed.inject(BrandPulseService);
  });

  it('emits on pulse$ when pulse() is called', () => {
    const seen: string[] = [];
    const sub = service.pulse$.subscribe(reason => seen.push(reason));

    service.pulse();

    expect(seen).toEqual(['ml-sync']);
    sub.unsubscribe();
  });

  it('passes through an explicit reason', () => {
    const seen: string[] = [];
    const sub = service.pulse$.subscribe(reason => seen.push(reason));

    service.pulse('custom-reason');

    expect(seen).toEqual(['custom-reason']);
    sub.unsubscribe();
  });

  it('does not emit before pulse() is called', () => {
    const spy = vi.fn();
    const sub = service.pulse$.subscribe(spy);

    expect(spy).not.toHaveBeenCalled();
    sub.unsubscribe();
  });

  it('emits once per pulse() call', () => {
    const spy = vi.fn();
    const sub = service.pulse$.subscribe(spy);

    service.pulse();
    service.pulse();

    expect(spy).toHaveBeenCalledTimes(2);
    sub.unsubscribe();
  });
});
