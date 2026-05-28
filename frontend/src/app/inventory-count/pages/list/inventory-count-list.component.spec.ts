import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslocoService, TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { InventoryCountListComponent } from './inventory-count-list.component';
import {
  InventoryCountService,
  InventoryCountSessionDetail,
  InventoryCountSessionHeader,
} from '../../services/inventory-count.service';


function makeHeader(over: Partial<InventoryCountSessionHeader> = {}): InventoryCountSessionHeader {
  return {
    id: 1,
    status: 'in_progress',
    location: 'default',
    notes: null,
    started_at: '2025-01-01T00:00:00Z',
    ended_at: null,
    started_by_user_id: 1,
    started_by_email: 'ops@example.com',
    item_count: 0,
    ...over,
  };
}


describe('InventoryCountListComponent', () => {
  let component: InventoryCountListComponent;
  let fixture: ComponentFixture<InventoryCountListComponent>;
  let svc: { list: ReturnType<typeof vi.fn>; start: ReturnType<typeof vi.fn> };
  let router: { navigate: ReturnType<typeof vi.fn> };
  let snack: { open: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    svc = {
      list: vi.fn().mockReturnValue(of([])),
      start: vi.fn(),
    };
    router = { navigate: vi.fn() };
    snack = { open: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [
        InventoryCountListComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: InventoryCountService, useValue: svc },
        { provide: Router, useValue: router },
      ],
    })
      // The standalone component imports MatSnackBarModule which provides
      // MatSnackBar in its own injector. Override at the component scope so
      // the test mock wins.
      .overrideComponent(InventoryCountListComponent, {
        set: {
          providers: [{ provide: MatSnackBar, useValue: snack }],
        },
      })
      .compileComponents();

    // Stub translate to be deterministic in tests.
    const transloco = TestBed.inject(TranslocoService);
    (transloco as any).translate = (k: string) => k;

    fixture = TestBed.createComponent(InventoryCountListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads sessions on init with no status filter', () => {
    expect(svc.list).toHaveBeenCalledWith({ status: null });
  });

  it('refresh() forwards the selected status filter', () => {
    svc.list.mockClear();
    component.statusFilter = 'committed';
    component.refresh();
    expect(svc.list).toHaveBeenCalledWith({ status: 'committed' });
  });

  it('refresh() coerces empty string filter to null (all)', () => {
    svc.list.mockClear();
    component.statusFilter = '';
    component.refresh();
    expect(svc.list).toHaveBeenCalledWith({ status: null });
  });

  it('start() navigates to the new session detail on success', () => {
    const created: InventoryCountSessionDetail = {
      ...makeHeader({ id: 42 }),
      items: [],
    };
    svc.start.mockReturnValue(of(created));
    component.newLocation = 'aisle-7';
    component.newNotes = 'spot check';
    component.start();
    expect(svc.start).toHaveBeenCalledWith({ location: 'aisle-7', notes: 'spot check' });
    expect(router.navigate).toHaveBeenCalledWith(['/inventory/count', 42]);
  });

  it('start() falls back to "default" location and undefined notes when blank', () => {
    svc.start.mockReturnValue(of({ ...makeHeader({ id: 1 }), items: [] }));
    component.newLocation = '';
    component.newNotes = '';
    component.start();
    expect(svc.start).toHaveBeenCalledWith({ location: 'default', notes: undefined });
  });

  it('start() surfaces an error snackbar on failure', () => {
    svc.start.mockReturnValue(throwError(() => new Error('boom')));
    component.start();
    expect(snack.open).toHaveBeenCalled();
    expect(component.starting).toBe(false);
  });

  it('statusChipClass() maps statuses to chip class names', () => {
    expect(component.statusChipClass('in_progress')).toBe('chip-progress');
    expect(component.statusChipClass('committed')).toBe('chip-committed');
    expect(component.statusChipClass('cancelled')).toBe('chip-cancelled');
  });

  it('clears sessions when the list call errors', () => {
    svc.list.mockReturnValue(throwError(() => new Error('boom')));
    component.sessions = [makeHeader()];
    component.refresh();
    expect(component.sessions).toEqual([]);
    expect(component.loading).toBe(false);
  });
});
