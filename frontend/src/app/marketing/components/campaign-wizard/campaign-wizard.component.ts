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
  templateUrl: './campaign-wizard.component.html',
  styleUrls: ['./campaign-wizard.component.scss']
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
