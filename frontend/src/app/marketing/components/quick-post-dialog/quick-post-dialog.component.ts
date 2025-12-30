import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';

import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatChipsModule } from '@angular/material/chips';
import { debounceTime, distinctUntilChanged, switchMap, startWith, map } from 'rxjs/operators';
import { Observable, of } from 'rxjs';

import { MarketingService, MarketingConnector, CampaignProductSummary } from '../../services/marketing.service';
import { ProductService } from '../../../products/services/product';
import { Product } from '../../../products/models/product.model';

@Component({
  selector: 'app-quick-post-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatAutocompleteModule,
    MatChipsModule
  ],
  template: `
    <header class="dialog-header">
      <h2>Create Quick Post</h2>
    </header>
    <form [formGroup]="postForm" (ngSubmit)="onSubmit()">
      <mat-dialog-content>
        <p class="intro-text">
          Publish a one-off update to your social channels.
        </p>

        <!-- Connector Selection -->
        <mat-form-field appearance="fill" class="full-width">
          <mat-label>Select Channel</mat-label>
          <mat-select formControlName="connector_id">
            <mat-option *ngFor="let connector of connectors" [value]="connector.id">
              {{ connector.name }} ({{ connector.connector_type | titlecase }})
            </mat-option>
            <mat-option *ngIf="connectors.length === 0" disabled>
              No active connectors found
            </mat-option>
          </mat-select>
        </mat-form-field>

        <!-- Product Linking -->
        <mat-form-field appearance="fill" class="full-width">
          <mat-label>Link Products (Leave empty for General/Store Post)</mat-label>
          <mat-chip-grid #chipGrid aria-label="Product selection">
            <mat-chip-row *ngFor="let product of selectedProducts" (removed)="removeProduct(product)">
              <img matChipAvatar [src]="product.primary_image?.image_path" 
                   onerror="this.src='assets/placeholder.jpg'" 
                   *ngIf="product.primary_image?.image_path"/>
              {{product.name}}
              <button matChipRemove [attr.aria-label]="'remove ' + product.name">
                <mat-icon>cancel</mat-icon>
              </button>
            </mat-chip-row>
          </mat-chip-grid>
          <input placeholder="Search products..." #productInput [formControl]="productSearchCtrl"
            [matChipInputFor]="chipGrid" [matAutocomplete]="auto">
          <mat-autocomplete #auto="matAutocomplete" (optionSelected)="productSelected($event)">
            <mat-option *ngFor="let product of filteredProducts$ | async" [value]="product">
               <img [src]="product.primary_image?.image_path || ''" class="option-img" onerror="this.style.display='none'">
               <span>{{product.name}}</span>
            </mat-option>
          </mat-autocomplete>
        </mat-form-field>

        <!-- Email Subject -->
        <mat-form-field *ngIf="isChannel('email')" appearance="fill" class="full-width">
           <mat-label>Subject Line</mat-label>
           <input matInput formControlName="content_subject">
        </mat-form-field>

        <!-- Content -->
        <mat-form-field appearance="fill" class="full-width">
          <mat-label>Post Content</mat-label>
          <textarea matInput formControlName="content_body" rows="4" placeholder="What's happening?"></textarea>
          <mat-hint align="end" *ngIf="isChannel('twitter')">{{postForm.get('content_body')?.value?.length || 0}} / 280</mat-hint>
        </mat-form-field>

        <!-- Image URL -->
        <mat-form-field appearance="fill" class="full-width">
          <mat-label>Image URL {{ isChannel('instagram') ? '(Required)' : '(Optional)' }}</mat-label>
          <input matInput formControlName="content_image_url" placeholder="https://...">
          <button mat-icon-button matSuffix type="button" (click)="fileInput.click()">
            <mat-icon>attach_file</mat-icon>
          </button>
        </mat-form-field>
        <input #fileInput type="file" style="display:none">

        <!-- Preview -->
        <div class="preview-box" *ngIf="postForm.get('content_image_url')?.value || selectedProducts.length > 0">
          <h4 *ngIf="selectedProducts.length > 0">Linked Products:</h4>
          <div class="product-preview-list" *ngIf="selectedProducts.length > 0">
              <div *ngFor="let p of selectedProducts" class="product-chip">
                  <img [src]="p.primary_image?.image_path" onerror="this.style.display='none'">
                  <span>{{p.name}}</span>
                  <a [href]="'/products/' + p.id" target="_blank" class="link-icon"><mat-icon>open_in_new</mat-icon></a>
              </div>
          </div>

          <img [src]="postForm.get('content_image_url')?.value" alt="Preview" 
               onerror="this.style.display='none'" *ngIf="postForm.get('content_image_url')?.value">
        </div>

      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button type="button" mat-dialog-close>Cancel</button>
        <button mat-raised-button color="primary" type="submit" 
                [disabled]="!postForm.valid || submitting">
          <mat-spinner diameter="20" *ngIf="submitting"></mat-spinner>
          <span *ngIf="!submitting">Post Now</span>
        </button>
      </mat-dialog-actions>
    </form>
  `,
  styles: [`
    .dialog-header {
      background: #263238;
      color: white;
      padding: 16px 24px;
      margin: 0 !important;
      display: flex;
      justify-content: space-between;
      align-items: center;
      width: 100%;
      box-sizing: border-box;
    }
    .dialog-header h2 {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 500;
    }
    .full-width {
      width: 100%;
      margin-bottom: 16px;
    }
    .intro-text {
      color: #666;
      margin-bottom: 24px;
    }
    .preview-box {
        border: 1px solid #ddd;
        padding: 10px;
        border-radius: 4px;
        margin-top: 10px;
    }
    .preview-box img {
      max-width: 100%;
      max-height: 200px;
      border-radius: 8px;
    }
    .option-img {
        width: 30px;
        height: 30px;
        border-radius: 4px;
        margin-right: 10px;
        vertical-align: middle;
    }
    .product-preview-list {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 10px;
    }
    .product-chip {
        display: flex;
        align-items: center;
        background: #f0f0f0;
        padding: 4px 8px;
        border-radius: 16px;
        font-size: 12px;
    }
    .product-chip img {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        margin-right: 5px;
    }
    .link-icon {
        margin-left: 5px;
        color: #666;
        text-decoration: none;
        display: flex;
    }
    .link-icon mat-icon {
        font-size: 14px;
        width: 14px;
        height: 14px;
    }
    mat-spinner {
      display: inline-block;
      margin-right: 8px;
    }
  `]
})
export class QuickPostDialogComponent implements OnInit {
  postForm: FormGroup;
  connectors: MarketingConnector[] = [];
  submitting = false;

  // Product Linking
  productSearchCtrl = new FormControl<string | Product>('');
  filteredProducts$: Observable<Product[]>;
  selectedProducts: Product[] = [];

  // View element ref
  @ViewChild('productInput') productInput: any;

  constructor(
    private fb: FormBuilder,
    private marketingService: MarketingService,
    private productService: ProductService,
    private dialogRef: MatDialogRef<QuickPostDialogComponent>,
    private snackBar: MatSnackBar
  ) {
    this.postForm = this.fb.group({
      connector_id: ['', Validators.required],
      content_body: ['', Validators.required],
      content_image_url: [''],
      content_subject: [''],
      // Hidden fields
      name: ['Quick Post ' + new Date().toLocaleDateString()],
      channel_type: ['social'],
    });

    // Search logic
    this.filteredProducts$ = this.productSearchCtrl.valueChanges.pipe(
      startWith(''),
      debounceTime(300),
      switchMap(value => {
        const query = typeof value === 'string' ? value : value?.name;
        return query ? this.productService.searchProducts(query).pipe(map(res => res.data)) : of([]);
      })
    );
  }

  ngOnInit(): void {
    this.loadConnectors();

    // Update channel type and validators when connector changes
    this.postForm.get('connector_id')?.valueChanges.subscribe(id => {
      const connector = this.connectors.find(c => c.id === id);
      if (connector) {
        const type = connector.channel_type || 'social';
        const provider = connector.config_json?.provider;

        this.postForm.patchValue({
          channel_type: type
        }, { emitEvent: false });

        // Dynamic Validators
        const bodyCtrl = this.postForm.get('content_body');
        const imageCtrl = this.postForm.get('content_image_url');
        const subjectCtrl = this.postForm.get('content_subject');

        // Reset validators
        bodyCtrl?.clearValidators();
        imageCtrl?.clearValidators();
        subjectCtrl?.clearValidators();

        if (type === 'email') {
          subjectCtrl?.setValidators(Validators.required);
          bodyCtrl?.setValidators(Validators.required); // Email body needed
        } else if (provider === 'twitter') {
          bodyCtrl?.setValidators([Validators.required, Validators.maxLength(280)]);
        } else {
          bodyCtrl?.setValidators(Validators.required);
        }

        if (provider === 'instagram') {
          imageCtrl?.setValidators(Validators.required);
        }

        bodyCtrl?.updateValueAndValidity();
        imageCtrl?.updateValueAndValidity();
        subjectCtrl?.updateValueAndValidity();
      }
    });
  }

  isChannel(typeOrProvider: string): boolean {
    const id = this.postForm.get('connector_id')?.value;
    const connector = this.connectors.find(c => c.id === id);
    if (!connector) return false;
    return connector.channel_type === typeOrProvider || connector.config_json?.provider === typeOrProvider;
  }

  loadConnectors(): void {
    this.marketingService.getConnectors(true).subscribe({
      next: (data) => {
        this.connectors = data;
        // Auto-select first if available
        if (this.connectors.length > 0) {
          this.postForm.patchValue({ connector_id: this.connectors[0].id });
        }
      },
      error: (err) => console.error('Failed to load connectors', err)
    });
  }

  // Product Selection
  removeProduct(product: Product): void {
    const index = this.selectedProducts.indexOf(product);
    if (index >= 0) {
      this.selectedProducts.splice(index, 1);
    }
  }

  productSelected(event: any): void {
    const product = event.option.value;
    if (!this.selectedProducts.find(p => p.id === product.id)) {
      this.selectedProducts.push(product);
    }
    if (this.productInput) {
      this.productInput.nativeElement.value = '';
    }
    this.productSearchCtrl.setValue(null);
  }

  onSubmit(): void {
    if (this.postForm.invalid) return;

    this.submitting = true;
    const formValue = this.postForm.value;

    // payload
    const payload: any = {
      ...formValue,
      product_ids: this.selectedProducts.map(p => p.id)
    };

    // First create the event (as draft/quick post) without campaign
    this.marketingService.createQuickPost(payload).subscribe({
      next: (event) => {
        // Then immediately publish it
        this.publishEvent(event.id);
      },
      error: (err) => {
        this.submitting = false;
        this.snackBar.open('Failed to create post', 'Close', { duration: 3000 });
        console.error(err);
      }
    });
  }

  publishEvent(eventId: number): void {
    this.marketingService.publishEvent(eventId).subscribe({
      next: (result) => {
        this.submitting = false;
        this.snackBar.open('Posted successfully!', 'Close', { duration: 3000 });
        this.dialogRef.close(true);
      },
      error: (err) => {
        this.submitting = false;
        // Even if publish fails, the event exists.
        console.error('Publish failed', err);
        const msg = err.error?.detail || 'Failed to publish post';
        this.snackBar.open(msg, 'Close', { duration: 5000 });
        this.dialogRef.close(false);
      }
    });
  }

  close(): void {
    this.dialogRef.close();
  }
}
