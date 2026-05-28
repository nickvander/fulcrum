import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { ActivatedRoute } from '@angular/router';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslocoService, TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { InventoryCountDetailComponent } from './inventory-count-detail.component';
import {
  InventoryCountCommitResult,
  InventoryCountItem,
  InventoryCountService,
  InventoryCountSessionDetail,
} from '../../services/inventory-count.service';


function makeItem(over: Partial<InventoryCountItem> = {}): InventoryCountItem {
  return {
    id: 1,
    session_id: 100,
    product_id: 10,
    variant_id: null,
    product_sku: 'SKU-1',
    product_name: 'Widget',
    expected_quantity: 5,
    counted_quantity: null,
    added_at: '2025-01-01T00:00:00Z',
    updated_at: null,
    ...over,
  };
}

function makeSession(over: Partial<InventoryCountSessionDetail> = {}): InventoryCountSessionDetail {
  return {
    id: 100,
    status: 'in_progress',
    location: 'default',
    notes: null,
    started_at: '2025-01-01T00:00:00Z',
    ended_at: null,
    started_by_user_id: 1,
    started_by_email: 'ops@example.com',
    item_count: 0,
    items: [],
    ...over,
  };
}


describe('InventoryCountDetailComponent', () => {
  let component: InventoryCountDetailComponent;
  let fixture: ComponentFixture<InventoryCountDetailComponent>;
  let svc: any;
  let dialog: { open: ReturnType<typeof vi.fn> };
  let snack: any;

  function stubDialogConfirm(ok: boolean): void {
    dialog.open.mockReturnValue({ afterClosed: () => of(ok) } as unknown as MatDialogRef<unknown>);
  }

  beforeEach(async () => {
    svc = {
      get: vi.fn().mockReturnValue(of(makeSession())),
      addItem: vi.fn(),
      updateCount: vi.fn(),
      removeItem: vi.fn(),
      commit: vi.fn(),
      cancel: vi.fn(),
    };
    snack = { open: vi.fn() };
    dialog = { open: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [
        NoopAnimationsModule,
        RouterTestingModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
        InventoryCountDetailComponent,
      ],
      providers: [
        { provide: InventoryCountService, useValue: svc },
        { provide: MatSnackBar, useValue: snack },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => '100' } } },
        },
      ],
    })
      // The standalone component imports MatDialogModule + MatSnackBarModule
      // which provide their own MatDialog / MatSnackBar in the component-level
      // injector. Override at the component scope so the test mocks win.
      .overrideComponent(InventoryCountDetailComponent, {
        set: {
          providers: [
            { provide: MatDialog, useValue: dialog },
            { provide: MatSnackBar, useValue: snack },
          ],
        },
      })
      .compileComponents();

    // Stub translate so we don't depend on translation files in tests.
    const transloco = TestBed.inject(TranslocoService);
    (transloco as any).translate = (k: string) => k;

    stubDialogConfirm(true);
    fixture = TestBed.createComponent(InventoryCountDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads the session on init using the :id route param', () => {
    expect(svc.get).toHaveBeenCalledWith(100);
    expect(component.session).not.toBeNull();
  });

  it('isInProgress reflects the session status', () => {
    expect(component.isInProgress).toBe(true);
    component.session!.status = 'committed';
    expect(component.isInProgress).toBe(false);
  });

  it('addItem() appends the new item locally and clears the input', () => {
    const item = makeItem({ id: 7 });
    svc.addItem.mockReturnValue(of(item));
    component.addingSku = '  SKU-1  ';
    component.addItem();
    expect(svc.addItem).toHaveBeenCalledWith(100, 'SKU-1');
    expect(component.session!.items.length).toBe(1);
    expect(component.session!.item_count).toBe(1);
    expect(component.addingSku).toBe('');
  });

  it('addItem() shows skuNotFound on missing SKU', () => {
    svc.addItem.mockReturnValue(throwError(() => ({ error: { code: 'apiErrors.product.notFoundBySku' } })));
    component.addingSku = 'NOPE';
    component.addItem();
    expect(snack.open).toHaveBeenCalled();
  });

  it('addItem() shows already-added error when SKU is duplicate', () => {
    svc.addItem.mockReturnValue(throwError(() => ({ error: { code: 'apiErrors.inventoryCount.skuAlreadyInSession' } })));
    component.addingSku = 'DUPE';
    component.addItem();
    expect(snack.open).toHaveBeenCalled();
  });

  it('saveCount() sends the floored numeric value and persists it locally', () => {
    const item = makeItem();
    component.session!.items = [item];
    svc.updateCount.mockReturnValue(of({ ...item, counted_quantity: 7 }));
    component.saveCount(item, '7');
    expect(svc.updateCount).toHaveBeenCalledWith(100, 1, 7);
    expect(item.counted_quantity).toBe(7);
  });

  it('saveCount() floors decimal entries', () => {
    const item = makeItem();
    component.session!.items = [item];
    svc.updateCount.mockReturnValue(of({ ...item, counted_quantity: 7 }));
    component.saveCount(item, '7.9');
    expect(svc.updateCount).toHaveBeenCalledWith(100, 1, 7);
  });

  it('saveCount() passes null when the input is cleared', () => {
    const item = makeItem();
    component.session!.items = [item];
    svc.updateCount.mockReturnValue(of({ ...item, counted_quantity: null }));
    component.saveCount(item, '');
    expect(svc.updateCount).toHaveBeenCalledWith(100, 1, null);
  });

  it('removeItem() drops the row from the local items list on success', () => {
    const item = makeItem({ id: 42 });
    component.session!.items = [item];
    component.session!.item_count = 1;
    svc.removeItem.mockReturnValue(of(undefined));
    component.removeItem(item);
    expect(svc.removeItem).toHaveBeenCalledWith(100, 42);
    expect(component.session!.items).toEqual([]);
    expect(component.session!.item_count).toBe(0);
  });

  it('delta() returns null when counted is missing, otherwise counted - expected', () => {
    const skipped = makeItem({ counted_quantity: null, expected_quantity: 5 });
    const equal = makeItem({ counted_quantity: 5, expected_quantity: 5 });
    const over = makeItem({ counted_quantity: 7, expected_quantity: 5 });
    const under = makeItem({ counted_quantity: 2, expected_quantity: 5 });
    expect(component.delta(skipped)).toBeNull();
    expect(component.delta(equal)).toBe(0);
    expect(component.delta(over)).toBe(2);
    expect(component.delta(under)).toBe(-3);
  });

  it('deltaClass() distinguishes positive / negative / zero / skipped', () => {
    expect(component.deltaClass(makeItem({ counted_quantity: null }))).toBe('');
    expect(component.deltaClass(makeItem({ counted_quantity: 5, expected_quantity: 5 }))).toBe('delta-zero');
    expect(component.deltaClass(makeItem({ counted_quantity: 7, expected_quantity: 5 }))).toBe('delta-positive');
    expect(component.deltaClass(makeItem({ counted_quantity: 2, expected_quantity: 5 }))).toBe('delta-negative');
  });

  it('pendingAdjustmentCount() counts only counted-and-differing rows', () => {
    component.session!.items = [
      makeItem({ id: 1, counted_quantity: null, expected_quantity: 5 }),   // skipped
      makeItem({ id: 2, counted_quantity: 5, expected_quantity: 5 }),       // matches → 0 delta
      makeItem({ id: 3, counted_quantity: 7, expected_quantity: 5 }),       // +2
      makeItem({ id: 4, counted_quantity: 0, expected_quantity: 3 }),       // -3
    ];
    expect(component.pendingAdjustmentCount()).toBe(2);
  });

  it('commit() opens the confirmation dialog then POSTs to the service', () => {
    component.session!.items = [makeItem({ counted_quantity: 7, expected_quantity: 5 })];
    const result: InventoryCountCommitResult = {
      adjustments_created: 1,
      items_skipped: 0,
      session: makeSession({ status: 'committed' }),
    };
    svc.commit.mockReturnValue(of(result));
    component.commit();
    expect(dialog.open).toHaveBeenCalled();
    expect(svc.commit).toHaveBeenCalledWith(100);
    expect(component.session!.status).toBe('committed');
    expect(snack.open).toHaveBeenCalled();
  });

  it('commit() short-circuits when the operator rejects the dialog', () => {
    stubDialogConfirm(false);
    component.commit();
    expect(svc.commit).not.toHaveBeenCalled();
  });

  it('cancelSession() POSTs to /cancel and updates local state', () => {
    const cancelled = makeSession({ status: 'cancelled' });
    svc.cancel.mockReturnValue(of(cancelled));
    component.cancelSession();
    expect(svc.cancel).toHaveBeenCalledWith(100);
    expect(component.session!.status).toBe('cancelled');
  });

  it('cancelSession() short-circuits when the operator rejects the dialog', () => {
    stubDialogConfirm(false);
    component.cancelSession();
    expect(svc.cancel).not.toHaveBeenCalled();
  });

  it('load() errored path sets the errored flag', () => {
    svc.get.mockReturnValue(throwError(() => new Error('boom')));
    component.session = null;
    component.load(999);
    expect(component.errored).toBe(true);
    expect(component.session).toBeNull();
  });
});
