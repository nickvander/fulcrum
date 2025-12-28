import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormBuilder, FormGroup, Validators, FormArray, FormControl } from '@angular/forms';
import { PurchaseOrderCreate, PurchaseOrderStatus } from '../../../shared/models/purchase-order.model';
import { Supplier } from '../../../shared/models/supplier.model';
import { Product } from '../../../products/models/product.model';
import { SuppliersService } from '../../suppliers.service';
import { ProductService } from '../../../products/services/product';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { ReceivingDialogComponent } from '../receiving-dialog/receiving-dialog.component';
import { QuickProductDialogComponent } from '../quick-product-dialog/quick-product-dialog.component';
import { CostAllocationDialogComponent } from '../cost-allocation-dialog/cost-allocation-dialog.component';
import { MatSnackBar } from '@angular/material/snack-bar';
import { SupplierInvoice } from '../../suppliers.service';
import { Observable, Subject, of } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, startWith, takeUntil, map, catchError } from 'rxjs/operators';

@Component({
  selector: 'app-purchase-order-edit',
  templateUrl: './purchase-order-edit.component.html',
  styleUrls: ['./purchase-order-edit.component.scss'],
  standalone: false
})
export class PurchaseOrderEditComponent implements OnInit, OnDestroy {
  poForm: FormGroup;
  isEditMode = false;
  poId: number | null = null;
  suppliers: Supplier[] = [];
  invoices: SupplierInvoice[] = [];
  statusOptions = Object.values(PurchaseOrderStatus);

  // Product autocomplete
  productSearchControls: FormControl[] = [];
  filteredProducts$: Observable<Product[]>[] = [];
  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private suppliersService: SuppliersService,
    private productService: ProductService,
    private route: ActivatedRoute,
    private router: Router,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {
    this.poForm = this.fb.group({
      supplier_id: [null, Validators.required],
      status: [PurchaseOrderStatus.DRAFT],
      currency: ['USD'],
      notes: [''],
      shipping_cost: [0],
      import_cost: [0],
      other_costs: [0],
      items: this.fb.array([])
    });
  }

  ngOnInit(): void {
    this.loadSuppliers();

    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam && idParam !== 'create') {
      this.isEditMode = true;
      this.poId = +idParam;
      this.loadPurchaseOrder(this.poId);
      this.loadInvoices();
    } else {
      this.addLineItem();
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadSuppliers(): void {
    this.suppliersService.getSuppliers().subscribe(suppliers => {
      this.suppliers = suppliers;
    });
  }

  loadPurchaseOrder(id: number): void {
    this.suppliersService.getPurchaseOrder(id).subscribe(po => {
      this.poForm.patchValue({
        supplier_id: po.supplier_id,
        status: po.status,
        currency: po.currency,
        notes: po.notes,
        shipping_cost: po.shipping_cost || 0,
        import_cost: po.tax_amount || 0, // Using tax_amount as import_cost for now
        other_costs: po.other_costs || 0
      });

      this.items.clear();
      this.productSearchControls = [];
      this.filteredProducts$ = [];

      if (po.items) {
        po.items.forEach(item => {
          this.addLineItem(item);
        });
      }
    });
  }

  get items(): FormArray {
    return this.poForm.get('items') as FormArray;
  }

  addLineItem(item: any = null): void {
    const index = this.items.length;

    const itemGroup = this.fb.group({
      product_id: [item?.product_id || null, Validators.required],
      product_name: [item?.product_name || ''],
      quantity_ordered: [item?.quantity_ordered || 1, [Validators.required, Validators.min(1)]],
      unit_cost: [item?.unit_cost || 0, [Validators.required, Validators.min(0)]]
    });
    this.items.push(itemGroup);

    // Setup autocomplete for this line
    const searchControl = new FormControl(item?.product_name || '');
    this.productSearchControls.push(searchControl);

    // Use getProducts with name filter for search
    const filtered$ = searchControl.valueChanges.pipe(
      startWith(''),
      debounceTime(300),
      distinctUntilChanged(),
      switchMap(term => {
        // If term is an object (selected product), extract name
        const searchTerm = typeof term === 'string' ? term : term?.name || '';

        if (!searchTerm || searchTerm.length < 2) {
          return of([]);
        }
        // Use getProducts with name filter
        return this.productService.getProducts(1, 20, { name: searchTerm }).pipe(
          map(response => response.data || []),
          catchError(() => of([]))
        );
      }),
      takeUntil(this.destroy$)
    );
    this.filteredProducts$.push(filtered$);
  }

  removeItem(index: number): void {
    this.items.removeAt(index);
    this.productSearchControls.splice(index, 1);
    this.filteredProducts$.splice(index, 1);
  }

  selectProduct(product: Product, index: number): void {
    const itemGroup = this.items.at(index) as FormGroup;
    itemGroup.patchValue({
      product_id: product.id,
      product_name: product.name,
      unit_cost: product.cost_price || 0
    });
    // Update the search control to show selected product name
    this.productSearchControls[index].setValue(product.name, { emitEvent: false });
  }

  displayProductFn(product: Product | string): string {
    if (!product) return '';
    if (typeof product === 'string') return product;
    return product.name ? `${product.name} (${product.sku || 'No SKU'})` : '';
  }

  openQuickAddProduct(index: number): void {
    const searchTerm = this.productSearchControls[index]?.value || '';
    const suggestedName = typeof searchTerm === 'string' ? searchTerm : '';

    // Pass current PO form state so it can be saved if user navigates away
    const dialogRef = this.dialog.open(QuickProductDialogComponent, {
      width: '520px',
      data: {
        suggestedName,
        poFormState: this.poForm.getRawValue(),
        lineItemIndex: index
      }
    });

    dialogRef.afterClosed().subscribe((result: any) => {
      if (result?.action === 'navigateToProduct') {
        // User is navigating to create product with variants
        // State is already saved to sessionStorage by the dialog
        return;
      }
      if (result && result.id) {
        // Product was created, select it
        this.selectProduct(result, index);
      }
    });
  }

  // Landed Cost Calculations
  calculateTotalAdditionalCosts(): number {
    const shipping = this.poForm.get('shipping_cost')?.value || 0;
    const importCost = this.poForm.get('import_cost')?.value || 0;
    const other = this.poForm.get('other_costs')?.value || 0;
    return Number(shipping) + Number(importCost) + Number(other);
  }

  getTotalQuantity(): number {
    return this.items.controls.reduce((sum, item) => {
      return sum + (item.get('quantity_ordered')?.value || 0);
    }, 0);
  }

  calculatePerUnitLandedCost(): number {
    const totalQty = this.getTotalQuantity();
    if (totalQty === 0) return 0;
    return this.calculateTotalAdditionalCosts() / totalQty;
  }

  applyLandedCostToItems(): void {
    if (!this.isEditMode || !this.poId) {
      // For new POs, apply locally (old behavior as fallback)
      const perUnitCost = this.calculatePerUnitLandedCost();
      if (perUnitCost === 0) return;
      this.items.controls.forEach(item => {
        const currentCost = item.get('unit_cost')?.value || 0;
        item.patchValue({ unit_cost: Number(currentCost) + perUnitCost });
      });
      this.snackBar.open('Costs applied locally. Save order to see detailed preview.', 'Close', { duration: 3000 });
      return;
    }

    // For existing POs, open the preview dialog
    const dialogRef = this.dialog.open(CostAllocationDialogComponent, {
      width: '800px',
      data: { poId: this.poId }
    });

    dialogRef.afterClosed().subscribe(applied => {
      if (applied) {
        // Reload PO to get updated costs
        this.loadPurchaseOrder(this.poId!);
      }
    });
  }

  onSubmit(): void {
    if (this.poForm.invalid) return;

    const formValue = this.poForm.value;

    if (this.isEditMode && this.poId) {
      this.suppliersService.updatePurchaseOrderStatus(this.poId, formValue.status).subscribe(() => {
        this.router.navigate(['/suppliers/po/list']);
      });
    } else {
      const newPo: PurchaseOrderCreate = {
        supplier_id: formValue.supplier_id,
        status: formValue.status,
        currency: formValue.currency,
        exchange_rate: 1.0,
        notes: formValue.notes,
        shipping_cost: formValue.shipping_cost,
        tax_amount: formValue.import_cost, // Map import_cost to tax_amount
        other_costs: formValue.other_costs,
        items: formValue.items.map((item: any) => ({
          product_id: item.product_id,
          quantity_ordered: item.quantity_ordered,
          unit_cost: item.unit_cost
        }))
      };

      this.suppliersService.createPurchaseOrder(newPo).subscribe(po => {
        this.router.navigate(['/suppliers/po', po.id]);
      });
    }
  }

  openReceivingDialog(): void {
    if (!this.poId) return;

    this.suppliersService.getPurchaseOrder(this.poId).subscribe(po => {
      const dialogRef = this.dialog.open(ReceivingDialogComponent, {
        width: '800px',
        data: { po: po }
      });

      dialogRef.afterClosed().subscribe(result => {
        if (result) {
          this.loadPurchaseOrder(this.poId!);
        }
      });
    });
  }

  // --- Invoice Management ---

  loadInvoices(): void {
    if (!this.poId) return;
    this.suppliersService.getInvoices(this.poId).subscribe(invoices => {
      this.invoices = invoices;
    });
  }

  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (file && this.poId) {
      if (file.size > 10 * 1024 * 1024) {
        this.snackBar.open('File too large. Max 10MB.', 'Close', { duration: 3000 });
        return;
      }
      this.suppliersService.uploadInvoice(this.poId, file).subscribe({
        next: () => {
          this.snackBar.open('Invoice uploaded successfully', 'Close', { duration: 3000 });
          this.loadInvoices();
        },
        error: (err) => {
          console.error('Upload failed', err);
          this.snackBar.open('Upload failed', 'Close', { duration: 3000 });
        }
      });
    }
  }

  deleteInvoice(id: number): void {
    if (!this.poId) return;
    if (confirm('Are you sure you want to delete this invoice?')) {
      this.suppliersService.deleteInvoice(id).subscribe(() => {
        this.snackBar.open('Invoice deleted', 'Close', { duration: 3000 });
        this.loadInvoices();
      });
    }
  }

  getInvoiceFileUrl(path: string): string {
    return this.suppliersService.getInvoiceFileUrl(path);
  }
}
