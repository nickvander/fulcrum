
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { QuickPostDialogComponent } from './quick-post-dialog.component';
import { MarketingService, TonePreset } from '../../services/marketing.service';
import { ProductService } from '../../../products/services/product';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { HttpClientTestingModule } from '@angular/common/http/testing';

describe('QuickPostDialogComponent', () => {
    let component: QuickPostDialogComponent;
    let fixture: ComponentFixture<QuickPostDialogComponent>;
    let marketingServiceMock: any;
    let productServiceMock: any;
    let dialogRefMock: any;
    let snackBarMock: any;

    const mockTonePresets: TonePreset[] = [
        { id: 'professional', name: 'Professional', prompt: 'Write professional content', description: 'Formal tone' },
        { id: 'casual', name: 'Casual', prompt: 'Write casual content', description: 'Friendly tone' },
        { id: 'custom', name: 'Custom', prompt: '', description: 'Custom prompt' }
    ];

    beforeEach(async () => {
        marketingServiceMock = {
            getConnectors: vi.fn().mockReturnValue(of([])),
            getTonePresets: vi.fn().mockReturnValue(of(mockTonePresets)),
            createQuickPost: vi.fn().mockReturnValue(of({ id: 1 })),
            publishEvent: vi.fn(),
            generateContent: vi.fn().mockReturnValue(of({
                content: { content: 'Generated text' },
                research: { hashtags: ['#test'] },
                generated_image_url: 'http://example.com/image.png'
            }))
        };

        productServiceMock = {
            searchProducts: vi.fn().mockReturnValue(of({ data: [] }))
        };

        dialogRefMock = {
            close: vi.fn()
        };

        snackBarMock = {
            open: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [
                QuickPostDialogComponent,
                NoopAnimationsModule,
                HttpClientTestingModule
            ],
            providers: [
                { provide: MarketingService, useValue: marketingServiceMock },
                { provide: ProductService, useValue: productServiceMock },
                { provide: MatDialogRef, useValue: dialogRefMock },
                { provide: MAT_DIALOG_DATA, useValue: {} },
                { provide: MatSnackBar, useValue: snackBarMock }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(QuickPostDialogComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load connectors on init', () => {
        expect(marketingServiceMock.getConnectors).toHaveBeenCalled();
    });

    it('should load tone presets on init', () => {
        expect(marketingServiceMock.getTonePresets).toHaveBeenCalled();
    });

    it('should validate form', () => {
        expect(component.postForm.valid).toBe(false);
        component.postForm.patchValue({
            connector_id: '123',
            content_body: 'Test post'
        });
    });

    // AI Content Helper Tests
    describe('AI Content Helpers', () => {
        it('hasContent should return false when content_body is empty', () => {
            component.postForm.patchValue({ content_body: '' });
            expect(component.hasContent()).toBe(false);
        });

        it('hasContent should return true when content_body has text', () => {
            component.postForm.patchValue({ content_body: 'Some content' });
            expect(component.hasContent()).toBe(true);
        });

        it('hasImage should return false when content_image_url is empty', () => {
            component.postForm.patchValue({ content_image_url: '' });
            expect(component.hasImage()).toBe(false);
        });

        it('hasImage should return true when content_image_url has value', () => {
            component.postForm.patchValue({ content_image_url: 'http://example.com/img.jpg' });
            expect(component.hasImage()).toBe(true);
        });

        it('hasBoth should return true only when both content and image exist', () => {
            component.postForm.patchValue({ content_body: '', content_image_url: '' });
            expect(component.hasBoth()).toBe(false);

            component.postForm.patchValue({ content_body: 'Text', content_image_url: '' });
            expect(component.hasBoth()).toBe(false);

            component.postForm.patchValue({ content_body: 'Text', content_image_url: 'http://img.jpg' });
            expect(component.hasBoth()).toBe(true);
        });
    });

    // Tone Selection Tests
    describe('Tone Selection', () => {
        it('should select a tone and populate customPromptCtrl', () => {
            const professionalTone = mockTonePresets[0];
            component.tonePresets = mockTonePresets;
            component.selectTone(professionalTone);

            expect(component.selectedTone).toBe(professionalTone);
            expect(component.customPromptCtrl.value).toBe(professionalTone.prompt);
        });

        it('should clear customPromptCtrl for custom tone', () => {
            const customTone = mockTonePresets[2]; // Custom has empty prompt
            component.tonePresets = mockTonePresets;
            component.selectTone(customTone);

            expect(component.selectedTone).toBe(customTone);
            expect(component.customPromptCtrl.value).toBe('');
        });
    });

    // Image Filename Extraction
    describe('getImageFilename', () => {
        it('should extract filename from URL', () => {
            component.postForm.patchValue({ content_image_url: 'http://example.com/uploads/product_123.png' });
            const result = component.getImageFilename();
            expect(result).toBe('product_123.png');
        });

        it('should return empty string for empty URL', () => {
            component.postForm.patchValue({ content_image_url: '' });
            const result = component.getImageFilename();
            expect(result).toBe('');
        });
    });
});
