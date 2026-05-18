import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { ReportDownloadService } from './report-download.service';

describe('ReportDownloadService', () => {
  let service: ReportDownloadService;
  let revokeSpy: ReturnType<typeof vi.fn>;
  let createObjectURLSpy: ReturnType<typeof vi.fn>;
  let clickSpy: ReturnType<typeof vi.fn>;
  let appendSpy: ReturnType<typeof vi.fn>;
  let removeSpy: ReturnType<typeof vi.fn>;
  let createdLinks: HTMLAnchorElement[];

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ReportDownloadService);

    createObjectURLSpy = vi.fn(() => 'blob:mock-url');
    revokeSpy = vi.fn();
    window.URL.createObjectURL = createObjectURLSpy as any;
    window.URL.revokeObjectURL = revokeSpy as any;

    createdLinks = [];
    const origCreate = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = origCreate(tag) as any;
      if (tag.toLowerCase() === 'a') {
        clickSpy = vi.fn();
        el.click = clickSpy;
        createdLinks.push(el);
      }
      return el;
    });
    appendSpy = vi.fn();
    removeSpy = vi.fn();
    vi.spyOn(document.body, 'appendChild').mockImplementation(appendSpy as any);
    vi.spyOn(document.body, 'removeChild').mockImplementation(removeSpy as any);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('creates a date-stamped anchor with the right filename + extension and clicks it', () => {
    const blob = new Blob(['data'], { type: 'text/csv' });
    service.download(of(blob), 'fulcrum-sales-by-channel', 'csv');

    expect(createObjectURLSpy).toHaveBeenCalledWith(blob);
    expect(createdLinks.length).toBe(1);
    const link = createdLinks[0];
    expect(link.href).toBe('blob:mock-url');
    expect(link.download).toMatch(/^fulcrum-sales-by-channel-\d{4}-\d{2}-\d{2}\.csv$/);
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(appendSpy).toHaveBeenCalledWith(link);
    expect(removeSpy).toHaveBeenCalledWith(link);
    expect(revokeSpy).toHaveBeenCalledWith('blob:mock-url');
  });

  it('uses the pdf extension when asked', () => {
    service.download(of(new Blob(['x'])), 'fulcrum-inventory-snapshot', 'pdf');
    expect(createdLinks[0].download).toMatch(/^fulcrum-inventory-snapshot-\d{4}-\d{2}-\d{2}\.pdf$/);
  });
});
