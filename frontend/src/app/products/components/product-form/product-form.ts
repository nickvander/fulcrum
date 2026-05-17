import { Component, OnInit, OnDestroy, Input, Output, EventEmitter, ViewChild, ElementRef } from '@angular/core';
import { FormsModule, FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ProductService } from '../../services/product';
import { Product, ProductImage } from '../../models/product.model';
import { ProductVariant } from '../../models/product.model';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatDialog } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { ImageDialogComponent } from '../../../shared/components/image-dialog/image-dialog';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';
import { ProductFormImageGalleryComponent } from './product-form-image-gallery.component';
import { ProductVariantsComponent } from '../product-variants/product-variants';
import { switchMap, map, takeUntil, catchError, tap, distinctUntilChanged } from 'rxjs/operators';
import { forkJoin, of, Subject, Observable } from 'rxjs';
import { CustomField } from '../../../settings/models/custom-field.model';
import { NotificationService } from '../../../core/services/notification.service';
import { ProductFormInitializerService, ProductFormInitializationData } from '../../services/product-form-initializer.service';
import { AiService } from '../../../core/services/ai.service';
import { CustomFieldService } from '../../../settings/services/custom-field.service';
import * as QRCode from 'qrcode'; // Import qrcode library
import { TranslocoModule } from '@ngneat/transloco';

@Component({
  selector: 'app-product-form',
  templateUrl: './product-form.html',
  styleUrl: './product-form.scss',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatListModule,
    MatTooltipModule,
    ProductFormImageGalleryComponent,
    ProductVariantsComponent,
    MatTabsModule,
    MatSlideToggleModule,
    MatAutocompleteModule,
    TranslocoModule
  ],
})
export class ProductForm implements OnInit {
  @Input() product?: Product | null;
  @Input() isDialogMode: boolean = false;
  @Input() initialStagedImages: File[] = [];
  @Output() productSaved = new EventEmitter<void>();
  @Output() formClosed = new EventEmitter<void>();

  productForm: FormGroup;
  isEditMode = false;
  productId: number | null = null;
  customFields: CustomField[] = [];
  stagedImages: File[] = [];
  stagedImagePreviews: string[] = [];
  imagesToDelete: number[] = [];
  initialPrimaryImageId: number | null = null;
  originalValues: any = {};
  originalCustomFieldValues: any = {};
  productVariants: ProductVariant[] = [];
  bundleComponents: any[] = [];
  availableProducts: Product[] = [];
  returnToPO = false;
  isGeneratingDescription = false;
  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private productService: ProductService,
    private router: Router,
    private route: ActivatedRoute,
    private productFormInitializer: ProductFormInitializerService,
    private customFieldService: CustomFieldService,
    private notificationService: NotificationService,
    private dialog: MatDialog,
    private aiService: AiService
  ) {
    this.productForm = this.fb.group({
      id: [null],
      name: ['', Validators.required],
      sku: ['', Validators.required],
      description: [''],
      default_resale_price: [0, [Validators.required, Validators.min(0)]],
      cost_price: [0, [Validators.min(0)]],
      manufacturer: [''],
      brand: [''],
      category: [''],
      width: [0, [Validators.min(0)]],
      height: [0, [Validators.min(0)]],
      depth: [0, [Validators.min(0)]],
      weight: [0, [Validators.min(0)]],
      low_inventory_threshold: [null, [Validators.min(0)]],
      low_stock_quantity_threshold: [null, [Validators.min(0)]],
      is_bundle: [false],
      barcode_value: [''],
      qrcode_value: ['']
    });
  }

  ngOnInit(): void {
    console.log('ProductForm: ngOnInit started');

    // Initialize staged images if provided
    if (this.initialStagedImages && this.initialStagedImages.length > 0) {
      this.stagedImages = [...this.initialStagedImages];
      this.initialStagedImages.forEach(file => {
        const reader = new FileReader();
        reader.onload = (e: any) => {
          if (e.target?.result) {
            this.stagedImagePreviews.push(e.target.result);
          }
        };
        reader.readAsDataURL(file);
      });
    }

    // Check if we're coming from creating a product for a PO
    this.route.queryParams.pipe(takeUntil(this.destroy$)).subscribe(params => {
      if (params['returnTo'] === 'po') {
        this.returnToPO = true;
      }
    });

    // Check if product is passed via @Input (side panel mode)
    if (this.product) {
      console.log('ProductForm: Side panel mode');
      this.initializeSidePanelMode();
    } else {
      console.log('ProductForm: Route mode');
      this.initializeRouteMode();
    }

    // Auto-generate Barcode when SKU changes
    this.productForm.get('sku')?.valueChanges.pipe(
      takeUntil(this.destroy$),
      distinctUntilChanged()
    ).subscribe(sku => {
      // Only auto-generate if barcode is empty to avoid overwriting user data
      const currentBarcode = this.productForm.get('barcode_value')?.value;
      if (sku && (!currentBarcode || currentBarcode.trim() === '')) {
        const barcode = this.productService.generateBarcodeFromSku(sku);
        this.productForm.patchValue({ barcode_value: barcode }, { emitEvent: false });
      }
    });
  }

  returnToPurchaseOrder(): void {
    // Navigate back to PO creation with saved state
    this.router.navigate(['/suppliers/po/create']);
  }

  private initializeSidePanelMode(): void {
    console.log('ProductForm: initializeSidePanelMode');
    this.isEditMode = !!this.product!.id;
    this.productId = this.product!.id || null;

    // If we have an ID, load full details. If not (e.g. creating a bundle from existing), allow using passed product as is.
    const product$ = this.productId
      ? this.productService.getProductById(this.productId).pipe(
        catchError(error => {
          console.error('Error loading full product details:', error);
          return of(this.product!); // Fallback to partial product
        })
      )
      : of(this.product!);

    const customFields$ = this.customFieldService.getCustomFields().pipe(
      catchError(error => {
        console.error('Error getting custom fields:', error);
        return of([] as CustomField[]);
      })
    );

    const variants$ = this.productId
      ? this.productService.getProductVariants(this.productId).pipe(
        catchError(error => {
          console.error('Error loading product variants:', error);
          return of([] as ProductVariant[]);
        })
      )
      : of([] as ProductVariant[]);

    forkJoin({
      product: product$,
      customFields: customFields$,
      variants: variants$
    }).pipe(
      takeUntil(this.destroy$)
    ).subscribe({
      next: ({ product, customFields, variants }) => {
        console.log('ProductForm: Side panel data loaded');
        console.log('ProductForm: Received product:', product);
        console.log('ProductForm: Product identifiers:', {
          sku: product.sku,
          barcode_value: product.barcode_value,
          qrcode_value: product.qrcode_value
        });
        // Handle Product Data
        this.product = product;
        this.productId = product.id || null;

        if (product) {
          this.productForm.patchValue(product);
          console.log('ProductForm: After patchValue, form sku:', this.productForm.get('sku')?.value);

          // CRITICAL FIX: If we are in ADD mode (id=0) and SKU/Barcode/QR are missing, generate them NOW.
          // This handles cases where the data passing might have failed or been incomplete.
          if ((!this.productId || this.productId === 0) && !this.productForm.get('sku')?.value) {
            console.log('ProductForm: Detected new product with missing SKU - Auto-generating...');
            this.regenerateSku(); // Generates SKU and Barcode
            setTimeout(() => this.generateQRCode(), 100); // Generate QR after a tick
          } else if ((!this.productId || this.productId === 0)) {
            // If SKU exists but QR is missing (e.g. passed from scanner but QR not rendered)
            if (!this.productForm.get('qrcode_value')?.value) {
              console.log('ProductForm: SKU exists but QR missing - Generating QR...');
              this.generateQRCode();
            }
          } else if (this.productForm.get('qrcode_value')?.value) {
            // If QR exists (e.g. Edit mode), we must render the visual canvas
            setTimeout(() => this.renderQrCode(), 100);
          }

          if (this.isEditMode) {
            this.originalValues = { ...product };
            this.originalCustomFieldValues = {};
            if (product.custom_fields) {
              product.custom_fields.forEach(fieldValue => {
                this.originalCustomFieldValues[`custom_field_${fieldValue.custom_field_id}`] = fieldValue.value;
              });
            }
          }

          // Handle Bundles - Logic copied from handleInitializationData
          if (product.bundle_components) {
            this.bundleComponents = product.bundle_components.map(bc => {
              // If coming from backend, it might have nested component.
              // If coming from onCreateParentBundle, it matches the structure directly but 'component' inner obj might be missing or different.
              const component = (bc as any).component;
              let stock = 0;
              if (component && component.inventory_items) {
                stock = component.inventory_items.reduce((acc: any, item: any) => acc + item.quantity, 0);
              } else if ((bc as any).component_stock !== undefined) {
                // Fallback if stock is pre-calculated or passed
                stock = (bc as any).component_stock;
              }

              return {
                ...bc,
                component_name: component?.name || bc.component_name || 'Loading...',
                component_image: component?.primary_image?.image_path || bc.component_image,
                component_stock: stock,
                component_cost: component?.cost_price || (bc as any).component_cost || 0
              };
            });

            // If creating a bundle, update the cost if needed
            if (!this.isEditMode && product.is_bundle) {
              this.updateSuggestedBundleCost();
            }
          }
        }

        // Handle Custom Fields
        this.customFields = customFields;
        this.addCustomFieldControls();
        this.patchCustomFieldValues();

        // Handle Variants
        this.productVariants = variants;
      },
      error: (err) => console.error('Error initializing side panel', err)
    });
  }

  private initializeRouteMode(): void {
    console.log('ProductForm: initializeRouteMode');
    // Route-based mode - use existing routing logic
    const idParam = this.route.snapshot.params['id'];
    const isEditMode = !!idParam;
    const productId = idParam ? +idParam : null;

    console.log('ProductForm: calling initializeForm');
    // Use the initialization service instead of complex observables in component
    this.productFormInitializer.initializeForm(isEditMode, productId).pipe(
      takeUntil(this.destroy$)
    ).subscribe({
      next: (initializationData: ProductFormInitializationData) => {
        console.log('ProductForm: initializeForm next');
        this.handleInitializationData(initializationData);

        // Auto-Generate SKU for new products if missing (Manual Creation Flow)
        if (!this.isEditMode && !this.productForm.get('sku')?.value) {
          const newSku = this.productService.generateUniqueSku();
          console.log('Auto-generating SKU:', newSku);
          this.productForm.patchValue({ sku: newSku });
          // This will trigger the valueChanges subscription to generate the barcode
        }
      },
      error: (error) => {
        console.error('Error initializing form:', error);
        // Fallback to safe defaults
        this.handleInitializationData({
          customFields: [],
          isEditMode,
          initialPrimaryImageId: null
        });
      },
      complete: () => {
        console.log('ProductForm: initializeForm complete');
      }
    });
  }

  private handleInitializationData(data: ProductFormInitializationData): void {
    this.customFields = data.customFields;
    this.isEditMode = data.isEditMode;
    this.initialPrimaryImageId = data.initialPrimaryImageId;

    if (data.product) {
      this.product = data.product;
      this.productId = data.product.id || null;
      this.productForm.patchValue(data.product);

      // Store original values for dirty checking (only for edit mode)
      if (this.isEditMode) {
        this.originalValues = { ...data.product };
        this.patchCustomFieldValues();

        // Store original custom field values
        this.originalCustomFieldValues = {};
        if (data.product.custom_fields) {
          data.product.custom_fields.forEach(fieldValue => {
            this.originalCustomFieldValues[`custom_field_${fieldValue.custom_field_id}`] = fieldValue.value;
          });
        }
      }

      // Handle Bundles
      if (data.product.bundle_components) {
        this.bundleComponents = data.product.bundle_components.map(bc => {
          const component = (bc as any).component;
          let stock = 0;
          if (component && component.inventory_items) {
            stock = component.inventory_items.reduce((acc: any, item: any) => acc + item.quantity, 0);
          }
          return {
            ...bc,
            component_name: component?.name || bc.component_name || 'Loading...',
            component_image: component?.primary_image?.image_path || bc.component_image,
            component_stock: stock,
            component_cost: component?.cost_price || 0
          };
        });
      }
    }

    // Handle navigation state for pre-filled data
    const navigation = this.router.getCurrentNavigation();
    const navigationState = navigation?.extras?.state;
    if (navigationState && navigationState['productData']) {
      const productData = navigationState['productData'];
      const patchData: { [key: string]: any } = {};

      Object.keys(this.productForm.controls).forEach(key => {
        if (productData.hasOwnProperty(key)) {
          patchData[key] = productData[key];
        }
      });

      this.productForm.patchValue(patchData);
    }

    // Auto-Generate SKU, Barcode, and QR if missing for new products (e.g. from Scanner)
    if (!this.isEditMode && !this.productForm.get('sku')?.value) {
      const newSku = this.productService.generateUniqueSku();
      const newBarcode = this.productService.generateBarcodeFromSku(newSku);
      const newQrValue = `${window.location.origin}/products/view/${newSku}`;

      console.log('Auto-generating SKU/Barcode/QR in handleInitializationData:', { newSku, newBarcode, newQrValue });
      this.productForm.patchValue({
        sku: newSku,
        barcode_value: newBarcode,
        qrcode_value: newQrValue
      });

      // Render visual QR after patch
      setTimeout(() => this.renderQrCode(), 200);
    }

    // Add custom field controls after getting the data
    this.addCustomFieldControls();
  }

  addCustomFieldControls(): void {
    this.customFields.forEach(field => {
      this.productForm.addControl(`custom_field_${field.id}`, this.fb.control(''));
    });
  }

  patchCustomFieldValues(): void {
    if (this.product && this.product.custom_fields) {
      this.product.custom_fields.forEach(fieldValue => {
        const control = this.productForm.get(`custom_field_${fieldValue.custom_field_id}`);
        if (control) {
          control.patchValue(fieldValue.value);
        }
      });
    }
  }

  get isDirty(): boolean {
    const primaryImage = this.product?.images?.find(img => img.is_primary);
    const currentPrimaryId = primaryImage ? primaryImage.id : null;

    // Check if there are actual changes to form controls by comparing to original values
    let formControlsChanged = false;

    if (this.isEditMode) {
      // Compare current form values with original values for standard fields
      const standardFields = [
        'name', 'sku', 'description', 'default_resale_price', 'cost_price',
        'manufacturer', 'brand', 'category', 'width', 'height', 'depth', 'weight', 'low_inventory_threshold', 'low_stock_quantity_threshold'
      ];

      for (const key of standardFields) {
        const control = this.productForm.get(key);
        if (control) {
          // Convert values to the same type for comparison to avoid type mismatches
          const controlValue = control.value;
          const originalValue = this.originalValues[key];

          // Handle potential type differences (e.g., number vs string)
          if (String(controlValue) !== String(originalValue)) {
            formControlsChanged = true;
            break;
          }
        }
      }

      // Also check custom field values
      if (!formControlsChanged) {
        for (const key of Object.keys(this.productForm.controls)) {
          if (key.startsWith('custom_field_')) {
            const control = this.productForm.get(key);
            if (control) {
              const originalValue = this.originalCustomFieldValues[key];
              if (String(control.value) !== String(originalValue)) {
                formControlsChanged = true;
                break;
              }
            }
          }
        }
      }
    } else {
      // For create mode, check if any field has any value (indicating user input)
      for (const key of Object.keys(this.productForm.controls)) {
        const control = this.productForm.get(key);
        if (control && control.value && control.value !== '' && control.value !== null && control.value !== undefined) {
          formControlsChanged = true;
          break;
        }
      }
    }

    // Check if there are actual image changes (not just loading the form)
    const imageChanges = (
      this.stagedImages.length > 0 ||
      this.imagesToDelete.length > 0 ||
      (this.isEditMode && this.initialPrimaryImageId !== null && this.initialPrimaryImageId !== currentPrimaryId)
    );

    return formControlsChanged || imageChanges;
  }

  getImageUrl(imagePath: string): string {
    if (imagePath && imagePath.startsWith('http')) return imagePath;

    // Backend serves images from the 'uploads/product_images' directory.
    return `/uploads/product_images/${imagePath}`;
  }



  generateQRCode(): void {
    let sku = this.productForm.get('sku')?.value;
    const existingQR = this.productForm.get('qrcode_value')?.value;

    // Auto-generate SKU if missing
    if (!sku) {
      sku = this.productService.generateUniqueSku();
      this.productForm.patchValue({ sku: sku });
    }

    // Generate URL using current origin + SKU
    const qrValue = `${window.location.origin}/products/view/${sku}`;

    const applyQr = () => {
      this.productForm.patchValue({ qrcode_value: qrValue });
      this.productForm.markAsDirty();
      setTimeout(() => this.renderQrCode(), 100);
    };

    if (existingQR && existingQR.trim() !== '' && existingQR !== qrValue) {
      const dialogRef = this.dialog.open(ConfirmationDialog, {
        data: {
          title: 'Replace QR Code?',
          message: 'This will replace the existing QR code. Continue?'
        }
      });
      dialogRef.afterClosed().subscribe(result => {
        if (result) applyQr();
      });
    } else {
      applyQr();
    }
  }

  @ViewChild('qrCanvas') qrCanvas!: ElementRef<HTMLCanvasElement>;

  renderQrCode(): void {
    const qrValue = this.productForm.get('qrcode_value')?.value;
    if (qrValue && this.qrCanvas) {
      QRCode.toCanvas(this.qrCanvas.nativeElement, qrValue, {
        width: 128,
        margin: 1,
        color: {
          dark: '#000000',
          light: '#ffffff'
        }
      }, function (error: any) {
        if (error) console.error(error);
      });
    }
  }

  regenerateSku(): void {
    console.log('Regenerate SKU clicked');
    const newSku = this.productService.generateUniqueSku();
    console.log('Generated new SKU:', newSku);

    // Helper to sync barcode
    const syncBarcode = (sku: string) => {
      const newBarcode = this.productService.generateBarcodeFromSku(sku);
      this.productForm.patchValue({ barcode_value: newBarcode });
    };

    const currentSku = this.productForm.get('sku')?.value;

    if (currentSku && currentSku.trim() !== '') {
      const dialogRef = this.dialog.open(ConfirmationDialog, {
        data: {
          title: 'Regenerate SKU?',
          message: 'This will update both SKU and Barcode. Continue?'
        }
      });
      dialogRef.afterClosed().subscribe(result => {
        if (result) {
          console.log('User confirmed SKU regeneration');
          this.productForm.patchValue({ sku: newSku });
          syncBarcode(newSku); // Force sync
          this.productForm.markAsDirty();
        }
      });
    } else {
      console.log('Auto-patching SKU (no existing value)');
      this.productForm.patchValue({ sku: newSku });
      syncBarcode(newSku); // Force sync
      this.productForm.markAsDirty();
    }
  }

  regenerateBarcode(): void {
    const sku = this.productForm.get('sku')?.value;
    if (sku) {
      const barcode = this.productService.generateBarcodeFromSku(sku);
      this.productForm.patchValue({ barcode_value: barcode });
      this.productForm.markAsDirty();
    } else {
      this.notificationService.showError('Please enter a SKU first.');
    }
  }

  onSubmit(): void {
    if (this.productForm.invalid) {
      return;
    }

    const formValue = this.productForm.value;
    const productData: Partial<Product> = {
      name: formValue.name,
      sku: formValue.sku,
      description: formValue.description,
      default_resale_price: formValue.default_resale_price,
      cost_price: formValue.cost_price,
      manufacturer: formValue.manufacturer,
      brand: formValue.brand,
      category: formValue.category,
      width: formValue.width,
      height: formValue.height,
      depth: formValue.depth,
      weight: formValue.weight,
      low_inventory_threshold: formValue.low_inventory_threshold,
      low_stock_quantity_threshold: formValue.low_stock_quantity_threshold,
      is_bundle: formValue.is_bundle,
      bundle_components: formValue.is_bundle ? this.bundleComponents.map(bc => ({
        component_id: bc.component_id,
        quantity: bc.quantity
      })) : [],
      barcode_value: formValue.barcode_value,
      qrcode_value: formValue.qrcode_value
    };

    // Handle custom fields
    const customFieldValues: { [key: number]: any } = {};
    this.customFields.forEach(field => {
      const controlName = `custom_field_${field.id}`;
      if (formValue[controlName] !== undefined) {
        customFieldValues[field.id] = formValue[controlName];
      }
    });

    if (this.isEditMode && this.productId) {
      this.productService.updateProduct({ ...productData, id: this.productId } as Product).pipe(
        switchMap(updatedProduct => {
          // Save custom fields
          if (Object.keys(customFieldValues).length > 0) {
            return this.productService.saveCustomFieldValues(updatedProduct.id, customFieldValues).pipe(
              map(() => updatedProduct)
            );
          }
          return of(updatedProduct);
        }),
        switchMap(updatedProduct => {
          // Handle image deletions
          if (this.imagesToDelete.length > 0) {
            const deleteObservables = this.imagesToDelete.map(imageId =>
              this.productService.deleteProductImage(updatedProduct.id, imageId)
            );
            return forkJoin(deleteObservables).pipe(map(() => updatedProduct));
          }
          return of(updatedProduct);
        }),
        switchMap(updatedProduct => {
          // Handle new image uploads
          if (this.stagedImages.length > 0) {
            const uploadObservables = this.stagedImages.map(image =>
              this.productService.uploadProductImage(updatedProduct.id, image)
            );
            return forkJoin(uploadObservables).pipe(map(() => updatedProduct));
          }
          return of(updatedProduct);
        }),
        switchMap(updatedProduct => {
          // Handle primary image update
          const primaryImage = this.product?.images?.find(img => img.is_primary);
          if (primaryImage && primaryImage.id !== this.initialPrimaryImageId) {
            return this.productService.setPrimaryProductImage(updatedProduct.id, primaryImage.id).pipe(
              map(() => updatedProduct)
            );
          }
          return of(updatedProduct);
        })
      ).subscribe({
        next: () => {
          this.notificationService.showSuccess('Product updated successfully');
          // Emit event instead of navigating if in side panel mode
          if (this.product) {
            this.productSaved.emit();
          } else {
            this.router.navigate(['/products']);
          }
        },
        error: (error) => {
          console.error('Error updating product:', error);
          // HttpErrorInterceptor surfaces the localized backend message; no extra snackbar here.
        }
      });

    } else {
      this.productService.createProduct(productData as Product).pipe(
        switchMap(newProduct => {
          // Save custom fields
          if (Object.keys(customFieldValues).length > 0) {
            return this.productService.saveCustomFieldValues(newProduct.id, customFieldValues).pipe(
              map(() => newProduct)
            );
          }
          return of(newProduct);
        }),
        switchMap(newProduct => {
          // Handle image uploads
          if (this.stagedImages.length > 0) {
            const uploadObservables = this.stagedImages.map(image =>
              this.productService.uploadProductImage(newProduct.id, image)
            );
            return forkJoin(uploadObservables).pipe(map(() => newProduct));
          }
          return of(newProduct);
        })
      ).subscribe({
        next: () => {
          this.notificationService.showSuccess('Product created successfully');
          // Emit event instead of navigating if in side panel mode
          if (this.product) {
            this.productSaved.emit();
          } else {
            this.router.navigate(['/products']);
          }
        },
        error: (error) => {
          console.error('Error creating product:', error);
          // HttpErrorInterceptor surfaces the localized backend message; no extra snackbar here.
        }
      });
    }
  }

  onCancel(): void {
    if (this.isDirty) {
      const dialogRef = this.dialog.open(ConfirmationDialog, {
        data: {
          title: 'Discard changes?',
          message: 'You have unsaved changes. Are you sure you want to discard them?'
        }
      });
      dialogRef.afterClosed().subscribe(result => {
        if (result) {
          // Emit event instead of navigating if in side panel mode
          if (this.product) {
            this.formClosed.emit();
          } else {
            this.router.navigate(['/products']);
          }
        }
      });
    } else {
      // Emit event instead of navigating if in side panel mode
      if (this.product) {
        this.formClosed.emit();
      } else {
        this.router.navigate(['/products']);
      }
    }
  }

  // Methods to handle events from the child component
  onStagedImagesChange(images: File[]): void {
    this.stagedImages = images;
  }

  onStagedImagePreviewsChange(previews: string[]): void {
    this.stagedImagePreviews = previews;
  }

  onImagesToDelete(imageIds: number[]): void {
    this.imagesToDelete = [...this.imagesToDelete, ...imageIds];
    // Also remove from the product images if we have it
    if (this.product && this.product.images) {
      imageIds.forEach(id => {
        const index = this.product!.images!.findIndex(img => img.id === id);
        if (index > -1) {
          this.product!.images!.splice(index, 1);
        }
      });
    }
  }

  onPrimaryImageChange(imageId: number | null): void {
    if (imageId === null) {
      return; // Handle null case gracefully
    }
    if (this.product && this.product.images) {
      this.product.images.forEach(img => {
        img.is_primary = img.id === imageId ? 1 : 0;
      });
    }
  }

  onImageUpdated(event: { imageId: number, field: 'title' | 'description', value: string }): void {
    if (this.product && this.product.images) {
      const image = this.product.images.find(img => img.id === event.imageId);
      if (image) {
        image[event.field] = event.value;
      }
    }
  }

  onAddVariant(): void {
    // Create a new variant object with default values using the correct structure
    const newVariant: ProductVariant = {
      id: 0, // Temporary ID, will be set by backend when saved
      product_id: this.productId || 0,
      name: 'New Variant',
      sku: '',
      price: 0,
      stock_quantity: 0,
      attributes: {}
    };

    // Add the new variant to the list
    this.productVariants = [...this.productVariants, newVariant];
  }

  onExistingImagesOrderChange(orderedImages: ProductImage[]): void {
    if (this.product) {
      this.product.images = orderedImages;
      // Save the new order to the backend if the product already exists
      if (this.product.id) {
        const orderedImageIds = orderedImages.map(img => img.id!);
        this.productService.updateImageOrder(this.product.id, orderedImageIds).subscribe({
          next: () => {
            console.log('Image order updated successfully');
          },
          error: (error) => {
            console.error('Error updating image order:', error);
            this.notificationService.showError('Error updating image order');
            // Revert to the previous order
            // (In a real implementation, you might want to handle this differently)
          }
        });
      }
    }
  }

  onImageError(event: any): void {
    event.target.src = 'assets/placeholder.jpg';
  }

  onAddBundleComponent(product: Product): void {
    const existing = this.bundleComponents.find(c => c.component_id === product.id);
    if (existing) {
      existing.quantity++;
    } else {
      let stock = 0;
      if (product.inventory_items) {
        stock = product.inventory_items.reduce((acc, item) => acc + item.quantity, 0);
      }

      this.bundleComponents.push({
        component_id: product.id,
        component_name: product.name,
        component_image: product.primary_image?.image_path || (product.images && product.images.length > 0 ? product.images[0].image_path : undefined),
        quantity: 1,
        component_stock: stock,
        component_cost: product.cost_price || 0
      });
    }
    this.updateSuggestedBundleCost();
  }

  onRemoveBundleComponent(index: number): void {
    this.bundleComponents.splice(index, 1);
    this.updateSuggestedBundleCost();
  }

  updateSuggestedBundleCost(): void {
    if (this.productForm.get('is_bundle')?.value) {
      const totalCost = this.bundleComponents.reduce((acc, c) => acc + ((c.component_cost || 0) * c.quantity), 0);
      this.productForm.patchValue({ cost_price: totalCost });
    }
  }

  searchProducts(query: string): void {
    if (query.length < 2) return;
    this.productService.searchProductsIsolated(query).subscribe(res => {
      this.availableProducts = res.data.filter(p => p.id !== this.productId);
    });
  }

  getMarketplaceName(id: number): string {
    switch (id) {
      case 1: return 'Amazon';
      case 2: return 'eBay';
      case 3: return 'Shopify';
      case 4: return 'MercadoLibre';
      default: return 'Marketplace ' + id;
    }
  }

  generateAiDescription(): void {
    const productName = this.productForm.get('name')?.value;
    if (!productName) {
      this.notificationService.showError('Please enter a product name first.');
      return;
    }

    this.isGeneratingDescription = true;
    const context = [
      this.productForm.get('brand')?.value ? `Brand: ${this.productForm.get('brand')?.value}` : '',
      this.productForm.get('category')?.value ? `Category: ${this.productForm.get('category')?.value}` : '',
      this.productForm.get('manufacturer')?.value ? `Manufacturer: ${this.productForm.get('manufacturer')?.value}` : ''
    ].filter(Boolean).join(', ');

    this.aiService.generateDescription({
      product_name: productName,
      context: context || undefined,
      tone: 'Professional',
      length: 'medium'
    }).pipe(
      takeUntil(this.destroy$)
    ).subscribe({
      next: (response) => {
        this.isGeneratingDescription = false;
        if (response.error) {
          this.notificationService.showError(response.error);
          return;
        }
        if (response.description) {
          this.productForm.patchValue({ description: response.description });
          this.notificationService.showSuccess('AI description generated successfully!');
        }
      },
      error: (err) => {
        this.isGeneratingDescription = false;
        this.notificationService.showError('Failed to generate description: ' + (err.message || 'Unknown error'));
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
