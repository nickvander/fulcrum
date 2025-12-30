import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule, FormsModule, FormControl } from '@angular/forms';
import { MatStepperModule } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatChipsModule } from '@angular/material/chips';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router, ActivatedRoute } from '@angular/router';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { Observable, of } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, startWith, map } from 'rxjs/operators';

import { MarketingService, CampaignCreate, CampaignEventCreate, MarketingConnector } from '../../services/marketing.service';
import { ProductService } from '../../../products/services/product';
import { Product } from '../../../products/models/product.model';

@Component({
  selector: 'app-campaign-wizard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    ReactiveFormsModule,
    FormsModule,
    MatStepperModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSelectModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatChipsModule,
    MatCardModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatAutocompleteModule,
  ],
  template: `
    <div class="wizard-container">
      <div class="wizard-header">
        <button mat-icon-button routerLink="/marketing">
          <mat-icon>arrow_back</mat-icon>
        </button>
        <h1>{{ isEditMode ? 'Edit Campaign' : 'Create Campaign' }}</h1>
      </div>

      <mat-stepper #stepper linear class="campaign-stepper">
        <!-- Step 1: Campaign Details -->
        <mat-step [stepControl]="campaignForm">
          <ng-template matStepLabel>Campaign Details</ng-template>
          <form [formGroup]="campaignForm" class="step-content">
            <mat-card class="form-card">
              <mat-card-content>
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Campaign Name</mat-label>
                  <input matInput formControlName="name" placeholder="e.g., Summer Sale 2024">
                  <mat-error *ngIf="campaignForm.get('name')?.hasError('required')">
                    Name is required
                  </mat-error>
                </mat-form-field>

                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Description</mat-label>
                  <textarea matInput formControlName="description" rows="3" 
                            placeholder="Describe the purpose and goals of this campaign"></textarea>
                </mat-form-field>

                <div class="date-range">
                  <mat-form-field appearance="outline">
                    <mat-label>Start Date</mat-label>
                    <input matInput [matDatepicker]="startPicker" formControlName="start_date">
                    <mat-datepicker-toggle matIconSuffix [for]="startPicker"></mat-datepicker-toggle>
                    <mat-datepicker #startPicker></mat-datepicker>
                  </mat-form-field>

                  <mat-form-field appearance="outline">
                    <mat-label>End Date</mat-label>
                    <input matInput [matDatepicker]="endPicker" formControlName="end_date">
                    <mat-datepicker-toggle matIconSuffix [for]="endPicker"></mat-datepicker-toggle>
                    <mat-datepicker #endPicker></mat-datepicker>
                  </mat-form-field>
                </div>

                <mat-form-field appearance="outline">
                  <mat-label>Budget (Optional)</mat-label>
                  <span matPrefix>$ </span>
                  <input matInput type="number" formControlName="budget" placeholder="0.00">
                </mat-form-field>
              </mat-card-content>
            </mat-card>

            <div class="step-actions">
              <button mat-stroked-button routerLink="/marketing">Cancel</button>
              <button mat-raised-button color="primary" matStepperNext [disabled]="campaignForm.invalid">
                Next
                <mat-icon>arrow_forward</mat-icon>
              </button>
            </div>
          </form>
        </mat-step>

        <!-- Step 2: Product Linking -->
        <mat-step>
          <ng-template matStepLabel>Link Products</ng-template>
          <div class="step-content">
              <mat-card class="form-card">
                  <mat-card-content>
                      <h3>Select Products</h3>
                      <p class="help-text">Link products to this campaign to easily create content.</p>
                      
                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>Search Products</mat-label>
                        <mat-chip-grid #chipGrid aria-label="Product selection">
                            <mat-chip-row *ngFor="let product of selectedProducts" (removed)="removeProduct(product)">
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
                  </mat-card-content>
              </mat-card>
              <div class="step-actions">
                  <button mat-stroked-button matStepperPrevious>Back</button>
                  <button mat-raised-button color="primary" matStepperNext>
                    Next
                    <mat-icon>arrow_forward</mat-icon>
                  </button>
              </div>
          </div>
        </mat-step>

        <!-- Step 2: Channel Selection -->
        <mat-step>
          <ng-template matStepLabel>Choose Channels</ng-template>
          <div class="step-content">
            <mat-card class="form-card">
              <mat-card-content>
                <h3>Select Marketing Channels</h3>
                <p class="help-text">Choose the channels you want to use for this campaign</p>

                <div class="channel-grid">
                  <mat-card class="channel-card" [class.selected]="selectedChannels.includes('email')"
                            (click)="toggleChannel('email')">
                    <mat-icon>email</mat-icon>
                    <span>Email</span>
                    <small>Send newsletters & promos</small>
                  </mat-card>

                  <mat-card class="channel-card" [class.selected]="selectedChannels.includes('social')"
                            (click)="toggleChannel('social')">
                    <mat-icon>share</mat-icon>
                    <span>Social Media</span>
                    <small>Post to Instagram, Facebook, etc.</small>
                  </mat-card>

                  <mat-card class="channel-card" [class.selected]="selectedChannels.includes('paid_ad')"
                            (click)="toggleChannel('paid_ad')">
                    <mat-icon>trending_up</mat-icon>
                    <span>Paid Ads</span>
                    <small>Google Ads, Meta Ads</small>
                  </mat-card>
                </div>

                <div class="connector-info" *ngIf="selectedChannels.length > 0">
                  <h4>Connected Platforms</h4>
                  <p *ngIf="connectors.length === 0" class="no-connectors">
                    No connectors configured yet. 
                    <a routerLink="/marketing/connectors">Set up connectors</a>
                  </p>
                  <div class="connector-list" *ngIf="connectors.length > 0">
                    <mat-chip *ngFor="let connector of getConnectorsForChannels()" 
                              color="primary">
                      {{ connector.name }}
                    </mat-chip>
                  </div>
                </div>
              </mat-card-content>
            </mat-card>

            <div class="step-actions">
              <button mat-stroked-button matStepperPrevious>Back</button>
              <button mat-raised-button color="primary" matStepperNext 
                      [disabled]="selectedChannels.length === 0">
                Next
                <mat-icon>arrow_forward</mat-icon>
              </button>
            </div>
          </div>
        </mat-step>

        <!-- Step 3: Create Events -->
        <mat-step>
          <ng-template matStepLabel>Schedule Events</ng-template>
          <div class="step-content">
            <mat-card class="form-card">
              <mat-card-content>
                <div class="events-header">
                  <h3>Campaign Events</h3>
                  <button mat-stroked-button (click)="addEvent()">
                    <mat-icon>add</mat-icon>
                    Add Event
                  </button>
                </div>

                <div class="events-list" *ngIf="events.length > 0">
                  <mat-card class="event-card" *ngFor="let event of events; let i = index">
                    <div class="event-header">
                      <div class="event-info">
                        <mat-icon>{{ getChannelIcon(event.channel_type) }}</mat-icon>
                        <span class="event-name">{{ event.name || 'Untitled Event' }}</span>
                      </div>
                      <button mat-icon-button (click)="removeEvent(i)">
                        <mat-icon>close</mat-icon>
                      </button>
                    </div>
                    <div class="event-form">
                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>Event Name</mat-label>
                        <input matInput [(ngModel)]="event.name" placeholder="e.g., Launch Email">
                      </mat-form-field>

                      <mat-form-field appearance="outline">
                        <mat-label>Channel</mat-label>
                        <mat-select [(ngModel)]="event.channel_type">
                          <mat-option *ngFor="let ch of selectedChannels" [value]="ch">
                            {{ ch | titlecase }}
                          </mat-option>
                        </mat-select>
                      </mat-form-field>

                      <mat-form-field appearance="outline">
                        <mat-label>Scheduled Time</mat-label>
                        <input matInput type="datetime-local" [(ngModel)]="event.scheduled_at">
                      </mat-form-field>

                      <mat-form-field appearance="outline" class="full-width" *ngIf="isChannelType(event, 'email')">
                         <mat-label>Subject Line</mat-label>
                         <input matInput [(ngModel)]="event.content_subject">
                      </mat-form-field>

                      <mat-form-field appearance="outline" class="full-width">
                         <mat-label>Content</mat-label>
                         <textarea matInput [(ngModel)]="event.content_body" rows="3"></textarea>
                      </mat-form-field>
                      
                      <mat-form-field appearance="outline" class="full-width">
                         <mat-label>Image URL</mat-label>
                         <input matInput [(ngModel)]="event.content_image_url">
                      </mat-form-field>
                    </div>
                  </mat-card>
                </div>

                <div class="empty-events" *ngIf="events.length === 0">
                  <mat-icon>event</mat-icon>
                  <p>No events yet. Add events to schedule your campaign activities.</p>
                </div>
              </mat-card-content>
            </mat-card>

            <div class="step-actions">
              <button mat-stroked-button matStepperPrevious>Back</button>
              <button mat-raised-button color="primary" (click)="onSubmit()" [disabled]="saving">
                <mat-spinner diameter="20" *ngIf="saving"></mat-spinner>
                <span *ngIf="!saving">{{ isEditMode ? 'Update Campaign' : 'Create Campaign' }}</span>
              </button>
            </div>
          </div>
        </mat-step>
      </mat-stepper>
    </div>
  `,
  styles: [`
    .wizard-container {
      padding: 24px;
      max-width: 800px;
      margin: 0 auto;
    }

    .wizard-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 24px;
    }

    .wizard-header h1 {
      margin: 0;
      font-size: 24px;
      font-weight: 500;
    }

    .campaign-stepper {
      background: transparent;
    }

    .step-content {
      padding: 24px 0;
    }

    .form-card {
      border-radius: 12px;
      margin-bottom: 24px;
    }

    .full-width {
      width: 100%;
    }

    .date-range {
      display: flex;
      gap: 16px;
    }

    .date-range mat-form-field {
      flex: 1;
    }

    .step-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }

    .channel-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }

    .channel-card {
      padding: 24px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
      border: 2px solid transparent;
    }

    .channel-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    .channel-card.selected {
      border-color: #1976d2;
      background: #e3f2fd;
    }

    .channel-card mat-icon {
      font-size: 40px;
      width: 40px;
      height: 40px;
      color: #1976d2;
      display: block;
      margin: 0 auto 12px;
    }

    .channel-card span {
      display: block;
      font-weight: 500;
      margin-bottom: 4px;
    }

    .channel-card small {
      color: #666;
    }

    .help-text {
      color: #666;
      margin-bottom: 16px;
    }

    .connector-info h4 {
      margin-bottom: 8px;
    }

    .no-connectors {
      color: #666;
    }

    .no-connectors a {
      color: #1976d2;
    }

    .events-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .event-card {
      margin-bottom: 16px;
      border-radius: 8px;
    }

    .event-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      background: #f5f5f5;
      border-radius: 8px 8px 0 0;
    }

    .event-info {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .event-name {
      font-weight: 500;
    }

    .event-form {
      padding: 16px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    .event-form .full-width {
      grid-column: 1 / -1;
    }

    .empty-events {
      text-align: center;
      padding: 48px;
      color: #999;
    }

    .empty-events mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
    }

    .option-img {
      width: 30px;
      height: 30px;
      border-radius: 4px;
      margin-right: 10px;
      vertical-align: middle;
    }
  `]
})
export class CampaignWizardComponent implements OnInit {
  campaignForm: FormGroup;
  selectedChannels: string[] = [];
  events: CampaignEventCreate[] = [];
  connectors: MarketingConnector[] = [];
  saving = false;
  isEditMode = false;
  campaignId: number | null = null;

  // Product Selection
  productSearchCtrl = new FormControl<string | Product>('');
  filteredProducts$: Observable<Product[]>;
  selectedProducts: Product[] = [];

  @ViewChild('productInput') productInput: any;

  constructor(
    private fb: FormBuilder,
    private marketingService: MarketingService,
    private productService: ProductService,
    private router: Router,
    private route: ActivatedRoute,
    private snackBar: MatSnackBar
  ) {
    this.campaignForm = this.fb.group({
      name: ['', Validators.required],
      description: [''],
      start_date: [null],
      end_date: [null],
      budget: [null],
    });

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
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditMode = true;
      this.campaignId = +id;
      this.loadCampaign(+id);
    }
  }

  loadCampaign(id: number): void {
    this.marketingService.getCampaign(id).subscribe({
      next: (campaign) => {
        this.campaignForm.patchValue({
          name: campaign.name,
          description: campaign.description,
          start_date: campaign.start_date,
          end_date: campaign.end_date,
          budget: campaign.budget
        });

        // Map products
        this.selectedProducts = (campaign.products || []).map(p => ({
          id: p.id,
          name: p.name,
          sku: p.sku || '',
          primary_image: p.image_url ? { image_path: p.image_url } : undefined,
          description: '',
          default_resale_price: 0,
          is_bundle: false
        } as any));

        // Note: Existing events are not loaded for editing in this wizard as they require complex sync.
        // Users should edit events in the detail view.
      },
      error: (err) => {
        console.error('Failed to load campaign', err);
        this.snackBar.open('Error loading campaign', 'Close');
      }
    });
  }

  loadConnectors(): void {
    this.marketingService.getConnectors().subscribe({
      next: (connectors) => this.connectors = connectors,
      error: (err) => console.error('Failed to load connectors', err)
    });
  }

  toggleChannel(channel: string): void {
    const index = this.selectedChannels.indexOf(channel);
    if (index > -1) {
      this.selectedChannels.splice(index, 1);
    } else {
      this.selectedChannels.push(channel);
    }
  }

  getConnectorsForChannels(): MarketingConnector[] {
    return this.connectors.filter(c => this.selectedChannels.includes(c.channel_type));
  }

  // Product Methods
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

  addEvent(): void {
    this.events.push({
      name: '',
      channel_type: this.selectedChannels[0] || 'email',
      content_subject: '',
      content_body: '',
      content_image_url: '',
      product_ids: [] // Can link specific subset if needed, or backend uses main list
    });
  }

  removeEvent(index: number): void {
    this.events.splice(index, 1);
  }

  getChannelIcon(channel: string): string {
    const icons: Record<string, string> = {
      email: 'email',
      social: 'share',
      paid_ad: 'trending_up',
    };
    return icons[channel] || 'campaign';
  }

  isChannelType(event: CampaignEventCreate, type: string): boolean {
    return event.channel_type === type;
  }

  onSubmit(): void {
    if (this.campaignForm.invalid) return;

    this.saving = true;
    const formValue = this.campaignForm.value;

    const payload: any = {
      name: formValue.name,
      description: formValue.description,
      start_date: formValue.start_date ? new Date(formValue.start_date).toISOString().split('T')[0] : null,
      end_date: formValue.end_date ? new Date(formValue.end_date).toISOString().split('T')[0] : null,
      budget: formValue.budget,
      product_ids: this.selectedProducts.map(p => p.id)
    };

    if (this.isEditMode && this.campaignId) {
      this.marketingService.updateCampaign(this.campaignId, payload).subscribe({
        next: () => {
          this.saving = false;
          this.snackBar.open('Campaign updated!', 'View', { duration: 3000 })
            .onAction().subscribe(() => this.router.navigate(['/marketing', this.campaignId]));
          this.router.navigate(['/marketing']);
        },
        error: (err) => {
          this.saving = false;
          console.error('Failed to update campaign', err);
          this.snackBar.open('Failed to update campaign', 'Close', { duration: 3000 });
        }
      });
    } else {
      payload.events = this.events;
      this.marketingService.createCampaign(payload).subscribe({
        next: (created) => {
          this.saving = false;
          this.snackBar.open('Campaign created!', 'View', { duration: 3000 })
            .onAction().subscribe(() => this.router.navigate(['/marketing', created.id]));
          this.router.navigate(['/marketing']);
        },
        error: (err) => {
          this.saving = false;
          console.error('Failed to create campaign', err);
          this.snackBar.open('Failed to create campaign', 'Close', { duration: 3000 });
        }
      });
    }
  }
}
