import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { PurchaseOrderEditComponent } from './purchase-order-edit.component';
import { SuppliersService } from '../../suppliers.service';
import { UserService } from '../../../users/services/user.service';
import { CommonModule } from '@angular/common';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ReactiveFormsModule, FormsModule, FormBuilder } from '@angular/forms';
import { MatDialogModule } from '@angular/material/dialog';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { RouterTestingModule } from '@angular/router/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';
import { ProductService } from '../../../products/services/product';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { vi, describe, it, expect, beforeEach, MockInstance } from 'vitest';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('PurchaseOrderEditComponent', () => {
  let component: PurchaseOrderEditComponent;
  let fixture: ComponentFixture<PurchaseOrderEditComponent>;
  let suppliersServiceSpy: { getSupplier: any, getSuppliers: any, getSuppliersForProduct: any };
  let productServiceSpy: { getProductById: any };
  let userServiceSpy: { getUsers: any };

  beforeEach(async () => {
    suppliersServiceSpy = {
      getSupplier: vi.fn(),
      getSuppliers: vi.fn(),
      getSuppliersForProduct: vi.fn()
    };
    productServiceSpy = {
      getProductById: vi.fn()
    };
    userServiceSpy = {
      getUsers: vi.fn()
    };

    await TestBed.configureTestingModule({
      declarations: [],
      imports: [
        PurchaseOrderEditComponent,
        CommonModule,
        HttpClientTestingModule,
        ReactiveFormsModule,
        FormsModule,
        MatDialogModule,
        MatSnackBarModule,
        MatSelectModule,
        MatInputModule,
        MatButtonModule,
        MatIconModule,
        MatCardModule,
        MatDatepickerModule,
        MatNativeDateModule,
        RouterTestingModule,
        NoopAnimationsModule,
        MatAutocompleteModule,
        TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } })
      ],
      providers: [
        { provide: SuppliersService, useValue: suppliersServiceSpy },
        { provide: ProductService, useValue: productServiceSpy },
        { provide: UserService, useValue: userServiceSpy },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: { get: () => null } },
            queryParamMap: of({ get: () => null }),
            paramMap: of({ get: () => null }),
            queryParams: of({})
          }
        },
        FormBuilder
      ],
      schemas: [CUSTOM_ELEMENTS_SCHEMA]
    })
      .compileComponents();

    fixture = TestBed.createComponent(PurchaseOrderEditComponent);
    component = fixture.componentInstance;
    // Mock initial data if necessary for component initialization
    suppliersServiceSpy.getSuppliersForProduct.mockReturnValue(of([]));
    suppliersServiceSpy.getSuppliers.mockReturnValue(of([]));
    userServiceSpy.getUsers.mockReturnValue(of([]));
    vi.spyOn(component, 'addLineItem'); // Spy on addLineItem for the 'should create' test
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
    expect(component.addLineItem).toHaveBeenCalled();
  });

  it('should unpack bundle and add components recursively', () => {
    const bundleProduct = {
      id: 99,
      name: 'Bundle Product',
      is_bundle: true,
      bundle_components: [
        { component_id: 101, quantity: 2 },
        { component_id: 102, quantity: 1 }
      ]
    };

    const component1 = { id: 101, name: 'Component 1', is_bundle: false, supplier_id: 1, cost_price: 10 };
    const component2 = { id: 102, name: 'Component 2', is_bundle: false, supplier_id: 1, cost_price: 20 };
    const supplierProducts = [{ supplier_id: 1, supplier_name: 'Sup 1', cost_price: 10, is_primary: true }];

    // Mock responses using mockReturnValue (Vitest syntax)
    productServiceSpy.getProductById.mockImplementation((id: number) => {
      if (id === 99) return of(bundleProduct as any);
      if (id === 101) return of(component1 as any);
      if (id === 102) return of(component2 as any);
      return of(null);
    });

    // Valid suppliers for components
    suppliersServiceSpy.getSuppliersForProduct.mockReturnValue(of(supplierProducts));

    vi.spyOn(component, 'finishAddingLineItem');
    vi.spyOn(component, 'handleProductAutofill');

    // Clear initial calls from ngOnInit
    vi.mocked(component.addLineItem).mockClear();

    component.handleProductAutofill(99);
    // tick(); // Removed because of behaves synchronously

    // Should call handleProductAutofill recursively for components
    expect(component.handleProductAutofill).toHaveBeenCalledWith(101, 2);
    expect(component.handleProductAutofill).toHaveBeenCalledWith(102, 1);

    // Should NOT add the bundle itself (finishAddingLineItem not called for bundle/id 99)
    // It WILL be called for components
    // We can check addLineItem calls
    const addLineItemSpy = vi.mocked(component.addLineItem);

    // Expect 2 calls (one for each component)
    expect(addLineItemSpy).toHaveBeenCalledTimes(2);
    expect(addLineItemSpy).toHaveBeenCalledWith(expect.objectContaining({ product_id: 101 })); // Component 1
    expect(addLineItemSpy).toHaveBeenCalledWith(expect.objectContaining({ product_id: 102 })); // Component 2
  });
});
