import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, FormArray, FormControl, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { PurchaseOrderCreate, PurchaseOrderStatus } from '../../../shared/models/purchase-order.model';
import { Supplier } from '../../../shared/models/supplier.model';
import { Product } from '../../../products/models/product.model';
import { SuppliersService, DocumentParseResult } from '../../suppliers.service';
import { ProductService } from '../../../products/services/product';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { ReceivingDialogComponent } from '../receiving-dialog/receiving-dialog.component';
import { QuickProductDialogComponent } from '../quick-product-dialog/quick-product-dialog.component';
import { CostAllocationDialogComponent } from '../cost-allocation-dialog/cost-allocation-dialog.component';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatCardModule } from '@angular/material/card';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { SupplierInvoice } from '../../suppliers.service';
import { UserService } from '../../../users/services/user.service';
import { User } from '../../../shared/models/user.model';
import { Observable, Subject, of, zip } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, startWith, takeUntil, map, catchError } from 'rxjs/operators';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';
import { SupplierSelectionDialogComponent } from '../supplier-selection-dialog/supplier-selection-dialog.component';
import { InvoiceMatchDialogComponent } from '../invoice-match-dialog/invoice-match-dialog.component';
import { TranslocoService, TranslocoModule } from '@ngneat/transloco';
import { SettingsService } from '../../../core/services/settings.service';

@Component({
  selector: 'app-purchase-order-edit',
  templateUrl: './purchase-order-edit.component.html',
  styleUrls: ['./purchase-order-edit.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    RouterModule,
    MatDialogModule,
    MatSnackBarModule,
    MatAutocompleteModule,
    MatInputModule,
    MatFormFieldModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatCardModule,
    MatTooltipModule,
    MatTableModule,
    MatProgressSpinnerModule,
    TranslocoModule
  ]
})
export class PurchaseOrderEditComponent implements OnInit, OnDestroy {
  poForm: FormGroup;
  isEditMode = false;
  isLocked = false;
  poId: number | null = null;
  suppliers: Supplier[] = [];
  invoices: SupplierInvoice[] = [];
  isParsingInvoice = false;
  isDraggingInvoice = false;
  aiEnabled = false;
  users: User[] = [];
  statusOptions = Object.values(PurchaseOrderStatus);
  paymentStatusOptions = ['unpaid', 'partial', 'paid'];

  // Map backend values to translation keys
  paymentMethodOptions = [
    { value: 'Bank Transfer', labelKey: 'purchaseOrders.paymentMethod.bankTransfer' },
    { value: 'Credit Card', labelKey: 'purchaseOrders.paymentMethod.creditCard' },
    { value: 'Cash', labelKey: 'purchaseOrders.paymentMethod.cash' },
    { value: 'Check', labelKey: 'purchaseOrders.paymentMethod.check' },
    { value: 'Other', labelKey: 'purchaseOrders.paymentMethod.other' }
  ];

  // Product autocomplete
  productSearchControls: FormControl[] = [];
  filteredProducts$: Observable<Product[]>[] = [];
  private destroy$ = new Subject<void>();
  currentLang: string;

  constructor(
    private fb: FormBuilder,
    private suppliersService: SuppliersService,
    private productService: ProductService,
    private route: ActivatedRoute,
    private router: Router,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private userService: UserService,
    private translocoService: TranslocoService,
    private settingsService: SettingsService
  ) {
    this.currentLang = this.translocoService.getActiveLang();

    this.poForm = this.fb.group({
      supplier_id: [null, Validators.required],
      status: [PurchaseOrderStatus.DRAFT],
      currency: ['USD'],
      notes: [''],
      shipping_cost: [0],
      import_cost: [0],
      other_costs: [0],
      payment_status: ['unpaid'],
      payment_method: [null],
      paid_by_user_id: [null],
      custom_payer_name: [null], // Optional
      ordered_at: [null],
      received_at: [null],
      items: this.fb.array([])
    });
  }

  ngOnInit(): void {
    // Subscribe to language changes for date pipe
    this.translocoService.langChanges$.pipe(takeUntil(this.destroy$)).subscribe(lang => {
      this.currentLang = lang;
    });

    // Check if AI is enabled
    this.settingsService.storeSettings$.pipe(takeUntil(this.destroy$)).subscribe(settings => {
      this.aiEnabled = settings?.ai_config?.enabled || false;
    });

    this.loadSuppliers();
    this.loadUsers(); // Load users

    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam && idParam !== 'create') {
      this.isEditMode = true;
      this.poId = +idParam;
      this.loadPurchaseOrder(this.poId);
      this.loadInvoices();
    } else {
      this.loadDraft();
    }

    // Auto-save draft changes
    this.poForm.valueChanges.pipe(
      debounceTime(2000),
      takeUntil(this.destroy$)
    ).subscribe(val => {
      if (!this.isEditMode) {
        sessionStorage.setItem('fulcrum_po_create_draft', JSON.stringify(val));
      }
    });

    // Check for product_id query param for autofill
    this.route.queryParams.pipe(takeUntil(this.destroy$)).subscribe(params => {
      if (params['product_id'] && !this.isEditMode) {
        this.handleProductAutofill(+params['product_id']);
      }
    });
  }

  handleProductAutofill(productId: number, quantityToAdd: number = 1): void {
    console.log('handleProductAutofill started for', productId);

    // Fetch Product AND its Supplier options
    zip(
      this.productService.getProductById(productId),
      this.suppliersService.getSuppliersForProduct(productId)
    ).subscribe(([product, supplierProducts]) => {
      if (product) {
        // --- Bundle Handling ---
        if (product.is_bundle && product.bundle_components && product.bundle_components.length > 0) {
          const msg = this.translocoService.translate('purchaseOrders.messages.unpackingBundle', { name: product.name });
          this.snackBar.open(msg, this.translocoService.translate('common.close'), { duration: 2000 });
          product.bundle_components.forEach(component => {
            // Recursively add each component
            // Note: Component logic assumes component_id is a valid Product ID
            this.handleProductAutofill(component.component_id, component.quantity * quantityToAdd);
          });
          return; // Stop here, do not add the bundle itself
        }

        // --- Standard Product Handling ---
        let selectedSupplierId = this.poForm.get('supplier_id')?.value;
        let selectedSupplierProduct: any = null;
        let unitCost = 0;

        // If no supplier selected yet for the PO
        if (!selectedSupplierId) {
          if (supplierProducts.length === 1) {
            // Only 1 supplier source -> Auto select
            selectedSupplierId = supplierProducts[0].supplier_id;
            selectedSupplierProduct = supplierProducts[0];
            this.poForm.patchValue({ supplier_id: selectedSupplierId });
            const msg = this.translocoService.translate('purchaseOrders.messages.autoSelectedSupplier', { name: supplierProducts[0].supplier_name });
            this.snackBar.open(msg, this.translocoService.translate('common.close'), { duration: 3000 });
          } else if (supplierProducts.length > 1) {
            // Multiple sources -> Ask user
            const dialogRef = this.dialog.open(SupplierSelectionDialogComponent, {
              width: '500px',
              data: { productName: product.name, suppliers: supplierProducts }
            });

            dialogRef.afterClosed().subscribe(result => {
              if (result) {
                // User picked one
                selectedSupplierId = result.supplier_id;
                selectedSupplierProduct = result;
                this.poForm.patchValue({ supplier_id: selectedSupplierId });
                this.finishAddingLineItem(product, quantityToAdd, result.cost_price);
              } else {
                // Cancelled or no selection, just add item with default cost
                this.finishAddingLineItem(product, quantityToAdd);
              }
            });
            return; // Exit here, finishAddingLineItem called in callback
          } else {
            // No supplier products found. Fallback to product.supplier_id
            if (product.supplier_id) {
              selectedSupplierId = product.supplier_id;
              this.poForm.patchValue({ supplier_id: selectedSupplierId });
              const msg = this.translocoService.translate('purchaseOrders.messages.defaultSupplier');
              this.snackBar.open(msg, this.translocoService.translate('common.close'), { duration: 3000 });
            }
          }
        } else {
          // Supplier ALREADY selected for PO. Check if this product is from them.
          const match = supplierProducts.find(sp => sp.supplier_id === selectedSupplierId);
          if (match) {
            selectedSupplierProduct = match;
          }
        }

        const cost = selectedSupplierProduct ? selectedSupplierProduct.cost_price : (product.cost_price || 0);
        this.finishAddingLineItem(product, quantityToAdd, cost);
      }
    });
  }

  finishAddingLineItem(product: Product, quantity: number = 1, unitCost: number = 0): void {
    // Check if already added to avoid duplicates
    const existing = this.items.controls.find(ctrl => ctrl.get('product_id')?.value === product.id);

    if (existing) {
      const currentQty = existing.get('quantity_ordered')?.value || 0;
      existing.patchValue({ quantity_ordered: currentQty + quantity });
      // Also update cost if it was 0? No, keep existing price if set.
      const msg = this.translocoService.translate('purchaseOrders.messages.incrementedQty', { name: product.name });
      this.snackBar.open(msg, this.translocoService.translate('common.close'), { duration: 3000 });
    } else {
      // Remove empty first item if it's the only one and has no product_id
      const firstItem = this.items.at(0);
      if (this.items.length === 1 && !firstItem.get('product_id')?.value) {
        this.removeItem(0);
      }

      this.addLineItem({
        product_id: product.id,
        product_name: product.name,
        quantity_ordered: quantity,
        unit_cost: unitCost || product.cost_price || 0
      });
      const msg = this.translocoService.translate('purchaseOrders.messages.addedProduct', { name: product.name });
      this.snackBar.open(msg, this.translocoService.translate('common.close'), { duration: 3000 });
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

  loadUsers(): void {
    this.userService.getUsers().subscribe((users: User[]) => {
      this.users = users;
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
        other_costs: po.other_costs || 0,
        payment_status: po.payment_status || 'unpaid',
        payment_method: po.payment_method,
        paid_by_user_id: po.paid_by_user_id,
        custom_payer_name: po.custom_payer_name,
        ordered_at: po.ordered_at,
        received_at: po.received_at
      });

      this.items.clear();
      this.productSearchControls = [];
      this.filteredProducts$ = [];

      if (po.items) {
        po.items.forEach(item => {
          this.addLineItem(item);
        });
      }

      // Lock if not in DRAFT status
      this.checkLockStatus();
    });
  }

  checkLockStatus(): void {
    const status = this.poForm.get('status')?.value;
    this.isLocked = status !== PurchaseOrderStatus.DRAFT;

    if (this.isLocked) {
      this.poForm.disable();
    } else {
      this.poForm.enable();
    }
  }

  getStatusTranslationKey(status: string): string {
    if (!status) return '';
    const camelCaseStatus = status.toLowerCase().replace(/_([a-z])/g, (g) => g[1].toUpperCase());
    return `purchaseOrders.${camelCaseStatus}`;
  }

  unlockOrder(): void {
    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: this.translocoService.translate('purchaseOrders.messages.unlockConfirm.title'),
        message: this.translocoService.translate('purchaseOrders.messages.unlockConfirm.message'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.isLocked = false;
        this.poForm.enable();
        this.snackBar.open(this.translocoService.translate('purchaseOrders.messages.unlocked'), this.translocoService.translate('common.close'), { duration: 3000 });
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
      product_name: [item?.product_name || item?.product?.name || ''],
      quantity_ordered: [item?.quantity_ordered || 1, [Validators.required, Validators.min(1)]],
      unit_cost: [item?.unit_cost || 0, [Validators.required, Validators.min(0)]]
    });
    this.items.push(itemGroup);

    // Setup autocomplete for this line
    const searchControl = new FormControl(item?.product_name || item?.product?.name || '');
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

  calculateItemsSubtotal(): number {
    return this.items.controls.reduce((sum, item) => {
      const qty = item.get('quantity_ordered')?.value || 0;
      const cost = item.get('unit_cost')?.value || 0;
      return sum + (qty * cost);
    }, 0);
  }

  calculateGrandTotal(): number {
    const itemsSubtotal = this.calculateItemsSubtotal();
    const additionalCosts = this.calculateTotalAdditionalCosts();
    return itemsSubtotal + additionalCosts;
  }

  getEstimatedAllocatedCost(unitCost: number): number {
    return Number(unitCost || 0) + this.calculatePerUnitLandedCost();
  }

  saveAsDraft(actionCallback?: () => void): void {
    if (this.poForm.invalid && this.items.length === 0) return;

    const formValue = this.poForm.value;
    const newPo: PurchaseOrderCreate = {
      supplier_id: formValue.supplier_id,
      status: PurchaseOrderStatus.DRAFT,
      currency: formValue.currency,
      exchange_rate: 1.0,
      notes: formValue.notes,
      shipping_cost: formValue.shipping_cost,
      tax_amount: formValue.import_cost,
      other_costs: formValue.other_costs,
      items: formValue.items.map((item: any) => ({
        product_id: item.product_id,
        quantity_ordered: item.quantity_ordered,
        unit_cost: item.unit_cost
      })),
      payment_status: formValue.payment_status,
      payment_method: formValue.payment_method,
      paid_by_user_id: formValue.paid_by_user_id,
      custom_payer_name: formValue.custom_payer_name,
      ordered_at: formValue.ordered_at,
      received_at: formValue.received_at
    };

    if (!newPo.supplier_id) {
      this.snackBar.open(this.translocoService.translate('purchaseOrders.messages.selectSupplierFirst'), this.translocoService.translate('common.close'), { duration: 3000 });
      return;
    }

    this.suppliersService.createPurchaseOrder(newPo).subscribe(po => {
      this.poId = po.id;
      this.isEditMode = true;
      sessionStorage.removeItem('fulcrum_po_create_draft');

      // Update URL without reloading
      window.history.replaceState({}, '', `/suppliers/po/${po.id}`);
      this.snackBar.open(this.translocoService.translate('purchaseOrders.messages.savedDraft'), this.translocoService.translate('common.close'), { duration: 3000 });

      if (actionCallback) {
        actionCallback();
      }
    });
  }

  applyLandedCostToItems(): void {
    if (!this.isEditMode || !this.poId) {
      const dialogRef = this.dialog.open(ConfirmationDialog, {
        data: {
          title: this.translocoService.translate('purchaseOrders.messages.saveDraftRequired.title'),
          message: this.translocoService.translate('purchaseOrders.messages.saveDraftRequired.message')
        }
      });

      dialogRef.afterClosed().subscribe(result => {
        if (result) {
          this.saveAsDraft(() => this.applyLandedCostToItems());
        }
      });
      return;
    }

    const formValue = this.poForm.value;
    const overrides = {
      shipping_cost: formValue.shipping_cost,
      tax_amount: formValue.import_cost,
      other_costs: formValue.other_costs
    };

    this.openCostAllocationDialog(overrides);
  }

  openCostAllocationDialog(overrides?: any): void {
    const dialogRef = this.dialog.open(CostAllocationDialogComponent, {
      width: '900px',
      data: { poId: this.poId, overrides }
    });

    dialogRef.afterClosed().subscribe(applied => {
      if (applied) {
        // Reload PO to get updated costs
        this.loadPurchaseOrder(this.poId!);
      }
    });
  }

  updateOrder(): Observable<any> {
    if (!this.poId) return of(null);
    const formValue = this.poForm.value;
    const updateData: any = {
      supplier_id: formValue.supplier_id,
      status: formValue.status,
      currency: formValue.currency,
      notes: formValue.notes,
      shipping_cost: formValue.shipping_cost,
      tax_amount: formValue.import_cost,
      other_costs: formValue.other_costs,
      payment_status: formValue.payment_status,
      payment_method: formValue.payment_method,
      paid_by_user_id: formValue.paid_by_user_id,
      custom_payer_name: formValue.custom_payer_name,
      ordered_at: formValue.ordered_at,
      received_at: formValue.received_at,
      items: formValue.items.map((item: any) => ({
        product_id: item.product_id,
        quantity_ordered: item.quantity_ordered,
        unit_cost: item.unit_cost
      }))
    };
    return this.suppliersService.updatePurchaseOrder(this.poId, updateData);
  }

  deleteOrder(): void {
    if (!this.poId) return;

    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: this.translocoService.translate('purchaseOrders.messages.deleteConfirm.title'),
        message: this.translocoService.translate('purchaseOrders.messages.deleteConfirm.message'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.suppliersService.deletePurchaseOrder(this.poId!).subscribe({
          next: () => {
            this.snackBar.open(this.translocoService.translate('purchaseOrders.messages.deleteSuccess'), this.translocoService.translate('common.close'), { duration: 3000 });
            this.router.navigate(['/suppliers/po/list']);
          },
          error: (err) => {
            // Backend will send 400 if items are received
            const msg = err.error?.detail || this.translocoService.translate('purchaseOrders.messages.deleteFailed');
            this.snackBar.open(msg, this.translocoService.translate('common.close'), { duration: 5000 });
          }
        });
      }
    });
  }

  placeOrder(): void {
    if (this.poForm.invalid && this.items.length === 0) return;

    // If it's a new PO, create it with ORDERED status
    if (!this.poId) {
      this.poForm.patchValue({ status: PurchaseOrderStatus.ORDERED });
      this.onSubmit();
      return;
    }

    // If existing, update status
    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: this.translocoService.translate('purchaseOrders.messages.placeOrderConfirm.title'),
        message: this.translocoService.translate('purchaseOrders.messages.placeOrderConfirm.message')
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.suppliersService.updatePurchaseOrderStatus(this.poId!, PurchaseOrderStatus.ORDERED).subscribe(() => {
          this.snackBar.open(this.translocoService.translate('purchaseOrders.messages.placed'), this.translocoService.translate('common.close'), { duration: 3000 });
          this.loadPurchaseOrder(this.poId!);
          this.router.navigate(['/suppliers/po/list']);
        });
      }
    });
  }

  onSubmit(): void {
    if (this.poForm.invalid) return;

    const formValue = this.poForm.value;

    if (this.isEditMode && this.poId) {
      this.updateOrder().subscribe(() => {
        this.snackBar.open(this.translocoService.translate('purchaseOrders.messages.updated'), this.translocoService.translate('common.close'), { duration: 3000 });
        this.router.navigate(['/suppliers/po/list']);
      });
    } else {
      const newPo: PurchaseOrderCreate = {
        supplier_id: formValue.supplier_id,
        status: formValue.status, // Uses form value which defaults to draft
        currency: formValue.currency,
        exchange_rate: 1.0,
        notes: formValue.notes,
        shipping_cost: formValue.shipping_cost,
        tax_amount: formValue.import_cost,
        other_costs: formValue.other_costs,
        items: formValue.items.map((item: any) => ({
          product_id: item.product_id,
          quantity_ordered: item.quantity_ordered,
          unit_cost: item.unit_cost
        })),
        payment_status: formValue.payment_status,
        payment_method: formValue.payment_method,
        paid_by_user_id: formValue.paid_by_user_id,
        custom_payer_name: formValue.custom_payer_name,
        ordered_at: formValue.ordered_at,
        received_at: formValue.received_at
      };

      this.suppliersService.createPurchaseOrder(newPo).subscribe(po => {
        sessionStorage.removeItem('fulcrum_po_create_draft');
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

  // --- Draft Management ---

  loadDraft(): void {
    const saved = sessionStorage.getItem('fulcrum_po_create_draft');
    if (saved) {
      try {
        const data = JSON.parse(saved);

        // Patch simple fields
        this.poForm.patchValue({
          supplier_id: data.supplier_id,
          currency: data.currency,
          notes: data.notes,
          shipping_cost: data.shipping_cost,
          import_cost: data.import_cost,
          other_costs: data.other_costs,
          payment_status: data.payment_status,
          payment_method: data.payment_method,
          paid_by_user_id: data.paid_by_user_id,
          custom_payer_name: data.custom_payer_name
        });

        // Rebuild items array
        this.items.clear();
        this.productSearchControls = [];
        this.filteredProducts$ = [];

        if (data.items && Array.isArray(data.items)) {
          data.items.forEach((item: any) => {
            this.addLineItem(item);
          });
        }

        if (this.items.length === 0) {
          this.addLineItem();
        }

        this.snackBar.open(this.translocoService.translate('purchaseOrders.messages.restoredDraft'), this.translocoService.translate('common.close'), { duration: 3000 });
      } catch (e) {
        console.error('Failed to parse draft', e);
        this.addLineItem();
      }
    } else {
      this.addLineItem();
    }
  }

  clearDraft(): void {
    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: this.translocoService.translate('purchaseOrders.messages.clearDraftConfirm.title'),
        message: this.translocoService.translate('purchaseOrders.messages.clearDraftConfirm.message')
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        sessionStorage.removeItem('fulcrum_po_create_draft');
        // Reset form
        this.poForm.reset({
          supplier_id: null,
          status: 'draft',
          currency: 'USD',
          notes: '',
          shipping_cost: 0,
          import_cost: 0,
          other_costs: 0,
          payment_status: 'unpaid',
          payment_method: null,
          paid_by_user_id: null,
          custom_payer_name: null
        });
        this.items.clear();
        this.productSearchControls = [];
        this.filteredProducts$ = [];
        this.addLineItem(); // Add one empty row
        this.snackBar.open(this.translocoService.translate('purchaseOrders.messages.clearedDraft'), this.translocoService.translate('common.close'), { duration: 3000 });
      }
    });
  }

  cancel(): void {
    if (this.poForm.dirty) {
      const dialogRef = this.dialog.open(ConfirmationDialog, {
        data: {
          title: this.translocoService.translate('purchaseOrders.messages.unsavedChanges.title'),
          message: this.translocoService.translate('purchaseOrders.messages.unsavedChanges.message')
        }
      });
      dialogRef.afterClosed().subscribe(result => {
        if (result) {
          this.router.navigate(['/suppliers/po/list']);
        }
      });
    } else {
      this.router.navigate(['/suppliers/po/list']);
    }
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
    if (!file) return;

    if (!this.poId) {
      const dialogRef = this.dialog.open(ConfirmationDialog, {
        data: {
          title: 'Save Draft Required',
          message: 'To upload an invoice, we need to save this order as a Draft first. Continue?'
        }
      });

      dialogRef.afterClosed().subscribe(result => {
        if (result) {
          // Must clone logic because event.target.files might be lost? 
          // Actually it persists in closure but let's be safe
          this.saveAsDraft(() => this.uploadFileInternal(file));
        } else {
          // Reset file input
          event.target.value = '';
        }
      });
      return;
    } else {
      this.uploadFileInternal(file);
    }
  }

  private uploadFileInternal(file: File): void {
    if (file.size > 10 * 1024 * 1024) {
      this.snackBar.open('File too large. Max 10MB.', 'Close', { duration: 3000 });
      return;
    }
    this.suppliersService.uploadInvoice(this.poId!, file).subscribe({
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

  deleteInvoice(id: number): void {
    if (!this.poId) return;

    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: 'Delete Invoice',
        message: 'Are you sure you want to delete this invoice?'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.suppliersService.deleteInvoice(id).subscribe(() => {
          this.snackBar.open('Invoice deleted', 'Close', { duration: 3000 });
          this.loadInvoices();
        });
      }
    });
  }

  getInvoiceFileUrl(path: string): string {
    return this.suppliersService.getInvoiceFileUrl(path);
  }

  onParseAndMatchSelected(event: any): void {
    const file = event.target.files[0];
    if (!file || !this.poId) return;
    event.target.value = ''; // Reset input
    this.parseAndMatchInvoice(file);
  }

  parseAndMatchInvoice(file: File): void {
    // When creating new PO with AI enabled, allow extraction
    if (!this.poId && !this.aiEnabled) {
      this.snackBar.open(this.translocoService.translate('purchaseOrders.messages.saveFirst'),
        this.translocoService.translate('common.close'), { duration: 3000 });
      return;
    }

    this.isParsingInvoice = true;

    // Use unified parseDocument endpoint - pass poId if we have one
    this.suppliersService.parseDocument(file, this.poId || undefined).subscribe({
      next: (result) => {
        this.isParsingInvoice = false;

        if (result.mode === 'match') {
          // Check if matched a DIFFERENT PO
          if (result.matched_po_id && result.matched_po_id !== this.poId) {
            // Show warning: invoice matches different PO
            this.dialog.open(ConfirmationDialog, {
              data: {
                title: this.translocoService.translate('purchaseOrders.invoiceMatching.differentPoTitle'),
                message: this.translocoService.translate('purchaseOrders.invoiceMatching.differentPoMessage', {
                  poNumber: result.matched_po_number,
                  supplier: result.matched_supplier_name
                }),
                confirmText: this.translocoService.translate('purchaseOrders.invoiceMatching.goToPo'),
                cancelText: this.translocoService.translate('purchaseOrders.invoiceMatching.scanAnother')
              }
            }).afterClosed().subscribe((goToPo) => {
              if (goToPo) {
                this.router.navigate(['/suppliers/po', result.matched_po_id]);
              }
              // Otherwise just close, user can try another document
            });
            return;
          }

          // Matched this PO - show comparison dialog
          const dialogRef = this.dialog.open(InvoiceMatchDialogComponent, {
            width: '900px',
            data: {
              matchResult: {
                invoice_number: result.invoice_number,
                invoice_date: result.document_date,
                vendor_name: result.vendor_name,
                matches: result.matches,
                unmatched_po_items: result.unmatched_po_items,
                unmatched_invoice_items: result.unmatched_invoice_items,
                total_discrepancy: result.total_discrepancy,
                overall_confidence: result.match_confidence,
                extraction_confidence: result.confidence
              },
              poId: this.poId
            }
          });

          dialogRef.afterClosed().subscribe((dialogResult) => {
            if (dialogResult?.action === 'apply') {
              this.applyInvoiceValuesToItems(dialogResult.matchResult);
            }
          });
        } else {
          // Mode: create - populate form with extracted data
          this.populateFormFromExtraction(result);
        }
      },
      error: (err) => {
        this.isParsingInvoice = false;
        const msg = err.error?.detail || this.translocoService.translate('purchaseOrders.invoiceMatching.parseFailed');
        this.snackBar.open(msg, this.translocoService.translate('common.close'), { duration: 5000 });
      }
    });
  }

  private applyInvoiceValuesToItems(matchResult: any): void {
    // Apply matched invoice values to PO items
    let updatedCount = 0;

    for (const match of matchResult.matches || []) {
      if (match.po_item_id && match.match_status !== 'unmatched') {
        // Find the corresponding item in the form array
        const itemIndex = this.items.controls.findIndex(
          (ctrl) => ctrl.get('id')?.value === match.po_item_id
        );

        if (itemIndex >= 0) {
          const item = this.items.at(itemIndex);
          // Update unit cost from invoice
          if (match.invoice_unit_cost && match.invoice_unit_cost !== item.get('unitCost')?.value) {
            item.patchValue({ unitCost: match.invoice_unit_cost });
            updatedCount++;
          }
        }
      }
    }

    if (updatedCount > 0) {
      this.snackBar.open(
        this.translocoService.translate('purchaseOrders.invoiceMatching.valuesApplied', { count: updatedCount }),
        this.translocoService.translate('common.close'),
        { duration: 3000 }
      );
    } else {
      this.snackBar.open(
        this.translocoService.translate('purchaseOrders.invoiceMatching.noChanges'),
        this.translocoService.translate('common.close'),
        { duration: 3000 }
      );
    }
  }

  private populateFormFromExtraction(result: DocumentParseResult): void {
    let changesApplied = false;

    // Try to match and set supplier
    if (result.vendor_name && this.suppliers.length > 0) {
      const matchedSupplier = this.suppliers.find(s =>
        s.name.toLowerCase().includes(result.vendor_name!.toLowerCase()) ||
        result.vendor_name!.toLowerCase().includes(s.name.toLowerCase())
      );
      if (matchedSupplier && !this.poForm.get('supplierId')?.value) {
        this.poForm.patchValue({ supplierId: matchedSupplier.id });
        this.snackBar.open(
          this.translocoService.translate('purchaseOrders.messages.autoSelectedSupplier', { name: matchedSupplier.name }),
          this.translocoService.translate('common.close'),
          { duration: 3000 }
        );
        changesApplied = true;
      }
    }

    // Set currency if extracted
    if (result.currency && result.currency !== 'USD') {
      this.poForm.patchValue({ currency: result.currency });
    }

    // Set shipping cost
    if (result.shipping_cost > 0) {
      this.poForm.patchValue({ shippingCost: result.shipping_cost });
      changesApplied = true;
    }

    // Set tax amount
    if (result.tax_amount > 0) {
      this.poForm.patchValue({ taxAmount: result.tax_amount });
      changesApplied = true;
    }

    // Add extracted items to the form
    if (result.items && result.items.length > 0) {
      for (const item of result.items) {
        // Add item to form - will have product_id if matched
        this.addLineItem({
          product_id: item.matched_product_id || null,
          product_name: item.description || item.sku || '',
          quantity_ordered: item.quantity,
          unit_cost: item.unit_cost
        });
        changesApplied = true;
      }
    }

    if (!changesApplied) {
      this.snackBar.open(
        this.translocoService.translate('purchaseOrders.invoiceMatching.noPoMatch'),
        this.translocoService.translate('common.close'),
        { duration: 5000 }
      );
    }
  }

  // Drag & Drop handlers for invoice zone
  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    // Allow drag when we have poId OR when AI is enabled for create flow
    if ((this.poId || this.aiEnabled) && !this.isParsingInvoice) {
      this.isDraggingInvoice = true;
    }
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDraggingInvoice = false;
  }

  onInvoiceDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDraggingInvoice = false;

    // Allow drop when we have poId OR when AI is enabled for create flow
    if ((!this.poId && !this.aiEnabled) || this.isParsingInvoice) return;

    const files = event.dataTransfer?.files;
    if (files?.length) {
      this.parseAndMatchInvoice(files[0]);
    }
  }
}
