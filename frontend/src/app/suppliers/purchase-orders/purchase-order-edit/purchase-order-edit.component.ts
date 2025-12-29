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
import { UserService } from '../../../users/services/user.service'; // Import UserService
import { User } from '../../../shared/models/user.model'; // Import User model
import { Observable, Subject, of, zip } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, startWith, takeUntil, map, catchError } from 'rxjs/operators';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';
import { SupplierSelectionDialogComponent } from '../supplier-selection-dialog/supplier-selection-dialog.component';

@Component({
  selector: 'app-purchase-order-edit',
  templateUrl: './purchase-order-edit.component.html',
  styleUrls: ['./purchase-order-edit.component.scss'],
  standalone: false
})
export class PurchaseOrderEditComponent implements OnInit, OnDestroy {
  poForm: FormGroup;
  isEditMode = false;
  isLocked = false;
  poId: number | null = null;
  suppliers: Supplier[] = [];
  invoices: SupplierInvoice[] = [];
  users: User[] = []; // Store users for dropdown
  statusOptions = Object.values(PurchaseOrderStatus);
  paymentStatusOptions = ['unpaid', 'partial', 'paid'];
  paymentMethodOptions = ['Bank Transfer', 'Credit Card', 'Cash', 'Check', 'Other'];

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
    private snackBar: MatSnackBar,
    private userService: UserService // Inject UserService
  ) {
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
      console.log('PurchaseOrderEdit: Query Params received', params);
      if (params['product_id'] && !this.isEditMode) {
        console.log('PurchaseOrderEdit: Triggering autofill for product', params['product_id']);
        this.handleProductAutofill(+params['product_id']);
      }
    });
  }

  handleProductAutofill(productId: number): void {
    console.log('handleProductAutofill started for', productId);

    // Fetch Product AND its Supplier options
    zip(
      this.productService.getProductById(productId),
      this.suppliersService.getSuppliersForProduct(productId)
    ).subscribe(([product, supplierProducts]) => {
      if (product) {
        // Determine which supplier to use
        let selectedSupplierId = this.poForm.get('supplier_id')?.value;
        let selectedSupplierProduct: any = null;

        // If no supplier selected yet for the PO
        if (!selectedSupplierId) {
          if (supplierProducts.length === 1) {
            // Only 1 supplier source -> Auto select
            selectedSupplierId = supplierProducts[0].supplier_id;
            selectedSupplierProduct = supplierProducts[0];
            this.poForm.patchValue({ supplier_id: selectedSupplierId });
            this.snackBar.open(`Auto-selected supplier: ${supplierProducts[0].supplier_name}`, 'Close', { duration: 3000 });
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
                this.finishAddingLineItem(product, 1, result.cost_price);
              } else {
                // Cancelled or no selection, just add item with default cost
                this.finishAddingLineItem(product);
              }
            });
            return; // Exit here, finishAddingLineItem called in callback
          } else {
            // No supplier products found. Fallback to product.supplier_id
            if (product.supplier_id) {
              selectedSupplierId = product.supplier_id;
              this.poForm.patchValue({ supplier_id: selectedSupplierId });
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
        this.finishAddingLineItem(product, 1, cost);
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
      this.snackBar.open(`Incremented quantity for ${product.name}`, 'Close', { duration: 3000 });
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
      this.snackBar.open(`Added ${product.name} to order`, 'Close', { duration: 3000 });
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

  unlockOrder(): void {
    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: 'Unlock Order',
        message: 'This order is finalized. Unlocking it allows editing but may cause data inconsistencies if already processed. Are you sure?',
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.isLocked = false;
        this.poForm.enable();
        this.snackBar.open('Order unlocked for editing', 'Close', { duration: 3000 });
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
      this.snackBar.open('Please select a supplier first', 'Close', { duration: 3000 });
      return;
    }

    this.suppliersService.createPurchaseOrder(newPo).subscribe(po => {
      this.poId = po.id;
      this.isEditMode = true;
      sessionStorage.removeItem('fulcrum_po_create_draft');

      // Update URL without reloading
      window.history.replaceState({}, '', `/suppliers/po/${po.id}`);
      this.snackBar.open('Order saved as Draft', 'Close', { duration: 3000 });

      if (actionCallback) {
        actionCallback();
      }
    });
  }

  applyLandedCostToItems(): void {
    if (!this.isEditMode || !this.poId) {
      const dialogRef = this.dialog.open(ConfirmationDialog, {
        data: {
          title: 'Save Draft Required',
          message: 'To use the detailed cost allocation tool, we need to save this order as a Draft first. Continue?'
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
        title: 'Delete Purchase Order',
        message: 'Are you sure you want to delete this order? This action cannot be undone.',
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.suppliersService.deletePurchaseOrder(this.poId!).subscribe({
          next: () => {
            this.snackBar.open('Purchase Order deleted successfully', 'Close', { duration: 3000 });
            this.router.navigate(['/suppliers/po/list']);
          },
          error: (err) => {
            // Backend will send 400 if items are received
            const msg = err.error?.detail || 'Failed to delete order';
            this.snackBar.open(msg, 'Close', { duration: 5000 });
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
        title: 'Place Order',
        message: 'Are you sure you want to place this order? This will mark it as Ordered.'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.suppliersService.updatePurchaseOrderStatus(this.poId!, PurchaseOrderStatus.ORDERED).subscribe(() => {
          this.snackBar.open('Order placed successfully', 'Close', { duration: 3000 });
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
        this.snackBar.open('Order updated successfully', 'Close', { duration: 3000 });
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

        this.snackBar.open('Restored draft from previous session', 'Close', { duration: 3000 });
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
        title: 'Clear Draft',
        message: 'Are you sure you want to clear this draft? All entered data will be lost.'
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
        this.snackBar.open('Draft cleared', 'Close', { duration: 3000 });
      }
    });
  }

  cancel(): void {
    if (this.poForm.dirty) {
      const dialogRef = this.dialog.open(ConfirmationDialog, {
        data: {
          title: 'Unsaved Changes',
          message: 'You have unsaved changes. Are you sure you want to leave?'
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
}
