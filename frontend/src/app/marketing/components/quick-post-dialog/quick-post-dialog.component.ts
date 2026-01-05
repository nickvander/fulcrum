import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatDialogRef, MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';

import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatChipsModule } from '@angular/material/chips';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';
import { debounceTime, switchMap, startWith, map } from 'rxjs/operators';
import { Observable, of } from 'rxjs';

import { MarketingService, MarketingConnector, TonePreset } from '../../services/marketing.service';
import { ProductService } from '../../../products/services/product';
import { Product } from '../../../products/models/product.model';
import { SettingsService } from '../../../core/services/settings.service';
import { AiPromptPreviewComponent } from '../../../shared/components/ai-prompt-preview/ai-prompt-preview';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';

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
    MatChipsModule,
    MatSlideToggleModule,
    MatTooltipModule,
    AiPromptPreviewComponent
  ],
  templateUrl: './quick-post-dialog.component.html',
  styleUrls: ['./quick-post-dialog.component.scss']
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
    private settingsService: SettingsService,
    private dialogRef: MatDialogRef<QuickPostDialogComponent>,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
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
    this.loadAiSettings();

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

        // Manual/Simulated Options if no connectors
        if (this.connectors.length === 0) {
          this.connectors = [
            { id: -1, name: 'Twitter / X', connector_type: 'social', config_json: { provider: 'twitter' } } as any,
            { id: -2, name: 'Instagram', connector_type: 'social', config_json: { provider: 'instagram' } } as any
          ];
        }

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


  // AI Controls
  showAiPanel = true;
  aiEnabled = false; // Controlled by settings
  generating = false;
  tonePresets: TonePreset[] = [];
  selectedTone: TonePreset | null = null;
  customPromptCtrl = new FormControl('');
  imagePromptCtrl = new FormControl('Create a photorealistic product image with natural lighting and clean composition.');
  aiImageCtrl = new FormControl(false); // Default OFF
  aiResult: any = null;
  draftEventId: number | null = null; // If AI generated, we have a draft event ID
  channelGuidelines = ''; // For prompt preview

  toggleAiPanel() {
    this.showAiPanel = !this.showAiPanel;
  }

  loadAiSettings() {
    // Check if AI is enabled in store settings
    this.settingsService.storeSettings$.subscribe(settings => {
      this.aiEnabled = settings?.ai_config?.enabled || false;
    });

    // Load tone presets
    this.marketingService.getTonePresets().subscribe({
      next: (presets) => {
        this.tonePresets = presets;
        // Auto-select first non-custom preset
        const defaultPreset = presets.find(p => p.id === 'professional');
        if (defaultPreset) {
          this.selectTone(defaultPreset);
        }
      },
      error: (err) => console.error('Failed to load tone presets', err)
    });
  }

  selectTone(preset: TonePreset) {
    this.selectedTone = preset;
    // Pre-fill the custom prompt with the preset's prompt (user can edit)
    if (preset.id !== 'custom') {
      this.customPromptCtrl.setValue(preset.prompt);
    } else {
      this.customPromptCtrl.setValue('');
    }
  }

  clearImage() {
    this.postForm.patchValue({ content_image_url: '' });
  }

  getImageFilename(): string {
    const url = this.postForm.get('content_image_url')?.value || '';
    if (!url) return '';
    // Extract filename from URL path
    const parts = url.split('/');
    return parts[parts.length - 1] || 'image';
  }

  generateContent() {
    if (this.selectedProducts.length === 0) return;

    this.generating = true;
    const product = this.selectedProducts[0]; // Use first product
    const platform = this.postForm.get('channel_type')?.value === 'social' ? 'Twitter' : 'Instagram'; // Simple mapping

    const tone = this.selectedTone?.name || 'Professional';
    const customPrompt = this.customPromptCtrl.value || undefined;

    this.marketingService.generateContent(
      product.id,
      platform,
      tone,
      this.aiImageCtrl.value || false,
      customPrompt
    ).subscribe({
      next: (result) => {
        this.generating = false;
        this.aiResult = result;
        this.draftEventId = result.event_id || null;

        // Auto-fill form
        if (result.content && result.content.content) {
          this.postForm.patchValue({
            content_body: result.content.content
          });
        }
        if (result.generated_image_url) {
          this.postForm.patchValue({
            content_image_url: result.generated_image_url
          });
        }

        this.snackBar.open('Content generated!', 'Close', { duration: 3000 });
      },
      error: (err) => {
        this.generating = false;
        console.error(err);
        // Extract meaningful error message for user
        let errorMsg = 'Generation failed';
        if (err?.error?.detail) {
          errorMsg = err.error.detail;
        } else if (err?.error?.message) {
          errorMsg = err.error.message;
        } else if (err?.message?.includes('quota') || err?.message?.includes('429')) {
          errorMsg = 'API quota exceeded. Please try again later.';
        }
        this.snackBar.open(errorMsg, 'Close', { duration: 5000 });
      }
    });
  }

  // Helper methods for button labels
  hasContent(): boolean {
    return !!this.postForm.get('content_body')?.value?.trim();
  }

  hasImage(): boolean {
    return !!this.postForm.get('content_image_url')?.value?.trim();
  }

  hasBoth(): boolean {
    return this.hasContent() && this.hasImage();
  }

  // Generate text only
  generateText(): void {
    if (this.hasContent()) {
      const dialogRef = this.dialog.open(ConfirmationDialog, {
        data: {
          title: 'Overwrite Content?',
          message: 'This will replace your existing text content. Continue?'
        }
      });
      dialogRef.afterClosed().subscribe(confirmed => {
        if (confirmed) {
          this.aiImageCtrl.setValue(false);
          this.generateContent();
        }
      });
    } else {
      this.aiImageCtrl.setValue(false);
      this.generateContent();
    }
  }

  // Generate image only
  generateImage(): void {
    if (this.hasImage()) {
      const dialogRef = this.dialog.open(ConfirmationDialog, {
        data: {
          title: 'Overwrite Image?',
          message: 'This will replace your existing image. Continue?'
        }
      });
      dialogRef.afterClosed().subscribe(confirmed => {
        if (confirmed) {
          this.aiImageCtrl.setValue(true);
          this.generateContentImageOnly();
        }
      });
    } else {
      this.aiImageCtrl.setValue(true);
      this.generateContentImageOnly();
    }
  }

  // Generate both text and image
  generateBoth(): void {
    if (this.hasBoth()) {
      const dialogRef = this.dialog.open(ConfirmationDialog, {
        data: {
          title: 'Overwrite All?',
          message: 'This will replace your existing text and image. Continue?'
        }
      });
      dialogRef.afterClosed().subscribe(confirmed => {
        if (confirmed) {
          this.aiImageCtrl.setValue(true);
          this.generateContent();
        }
      });
    } else {
      this.aiImageCtrl.setValue(true);
      this.generateContent();
    }
  }

  // Image-only generation - runs full pipeline but only applies image
  private generateContentImageOnly(): void {
    if (this.selectedProducts.length === 0) return;

    this.generating = true;
    const product = this.selectedProducts[0];
    const platform = this.postForm.get('channel_type')?.value === 'social' ? 'Twitter' : 'Instagram';
    const tone = this.selectedTone?.name || 'Professional';
    const customPrompt = this.customPromptCtrl.value || undefined;

    this.marketingService.generateContent(
      product.id,
      platform,
      tone,
      true, // Always generate image
      customPrompt
    ).subscribe({
      next: (result) => {
        this.generating = false;
        this.aiResult = result;

        // Only apply image, not text
        if (result.generated_image_url) {
          this.postForm.patchValue({
            content_image_url: result.generated_image_url
          });
          this.snackBar.open('Image generated!', 'Close', { duration: 3000 });
        } else {
          this.snackBar.open('No image was generated', 'Close', { duration: 3000 });
        }
      },
      error: (err) => {
        this.generating = false;
        console.error(err);
        // Extract meaningful error message for user
        let errorMsg = 'Image generation failed';
        if (err?.error?.detail) {
          errorMsg = err.error.detail;
        } else if (err?.error?.message) {
          errorMsg = err.error.message;
        } else if (err?.message?.includes('quota') || err?.message?.includes('429')) {
          errorMsg = 'API quota exceeded. Please try again later.';
        }
        this.snackBar.open(errorMsg, 'Close', { duration: 5000 });
      }
    });
  }

  saveDraft() {
    if (this.postForm.invalid) return;
    this.submitting = true;

    // Build AI metadata for content_json
    const aiMetadata = {
      ai_tone: this.selectedTone?.name || null,
      ai_prompt: this.customPromptCtrl.value || null,
      ai_model: 'gemini-2.0-flash-exp', // Track the model used
      generated_at: this.aiResult ? new Date().toISOString() : null,
    };

    const payload = {
      ...this.postForm.value,
      product_ids: this.selectedProducts.map(p => p.id),
      content_json: aiMetadata,
    };

    if (this.draftEventId) {
      // Update existing draft
      this.marketingService.updateEvent(this.draftEventId, {
        content_body: payload.content_body,
        content_image_url: payload.content_image_url,
        content_json: aiMetadata,
        name: payload.name
      }).subscribe({
        next: () => {
          this.submitting = false;
          this.snackBar.open('Draft updated', 'Close', { duration: 2000 });
          this.dialogRef.close(true);
        },
        error: (err) => {
          this.submitting = false;
          console.error(err);
          this.snackBar.open('Failed to save draft', 'Close', { duration: 2000 });
        }
      });
    } else {
      // Create new draft
      this.marketingService.createQuickPost(payload).subscribe({
        next: (event) => {
          this.submitting = false;
          this.snackBar.open('Draft saved', 'Close', { duration: 2000 });
          this.dialogRef.close(true);
        },
        error: (err) => {
          this.submitting = false;
          console.error(err);
          this.snackBar.open('Failed to save draft', 'Close', { duration: 2000 });
        }
      });
    }
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

    if (this.draftEventId) {
      // Update draft then publish
      this.marketingService.updateEvent(this.draftEventId, payload).subscribe({
        next: () => {
          this.publishEvent(this.draftEventId!);
        },
        error: (err) => {
          this.submitting = false;
          console.error(err);
        }
      });
    } else {
      // Create and publish
      this.marketingService.createQuickPost(payload).subscribe({
        next: (event) => {
          this.publishEvent(event.id);
        },
        error: (err) => {
          this.submitting = false;
          this.snackBar.open('Failed to create post', 'Close', { duration: 3000 });
          console.error(err);
        }
      });
    }
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

