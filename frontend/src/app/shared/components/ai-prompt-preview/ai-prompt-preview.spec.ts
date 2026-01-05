import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AiPromptPreviewComponent } from './ai-prompt-preview';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('AiPromptPreviewComponent', () => {
    let component: AiPromptPreviewComponent;
    let fixture: ComponentFixture<AiPromptPreviewComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                AiPromptPreviewComponent,
                NoopAnimationsModule
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(AiPromptPreviewComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    describe('hasContent', () => {
        it('should be false when no inputs are set', () => {
            component.tonePrompt = '';
            component.channelGuidelines = '';
            component.customPrompt = '';
            component.ngOnChanges({});
            expect(component.hasContent).toBe(false);
        });

        it('should be true when tonePrompt is set', () => {
            component.tonePrompt = 'Write professional content';
            component.ngOnChanges({});
            expect(component.hasContent).toBe(true);
        });

        it('should be true when channelGuidelines is set', () => {
            component.channelGuidelines = '280 character limit';
            component.ngOnChanges({});
            expect(component.hasContent).toBe(true);
        });

        it('should be true when customPrompt is set', () => {
            component.customPrompt = 'Focus on eco-friendly features';
            component.ngOnChanges({});
            expect(component.hasContent).toBe(true);
        });
    });

    describe('toggleExpanded', () => {
        it('should toggle expanded state', () => {
            expect(component.expanded).toBe(false);
            component.toggleExpanded();
            expect(component.expanded).toBe(true);
            component.toggleExpanded();
            expect(component.expanded).toBe(false);
        });

        it('should emit expandedChange event', () => {
            const spy = vi.spyOn(component.expandedChange, 'emit');
            component.toggleExpanded();
            expect(spy).toHaveBeenCalledWith(true);
        });
    });

    describe('getWordCount', () => {
        it('should return 0 for empty string', () => {
            expect(component.getWordCount('')).toBe(0);
        });

        it('should count words correctly', () => {
            expect(component.getWordCount('hello world')).toBe(2);
            expect(component.getWordCount('one two three four five')).toBe(5);
        });
    });

    describe('getTokenEstimate', () => {
        it('should return 0 when no content', () => {
            component.tonePrompt = '';
            component.channelGuidelines = '';
            component.customPrompt = '';
            expect(component.getTokenEstimate()).toBe(0);
        });

        it('should estimate tokens (1 token ≈ 4 chars)', () => {
            component.tonePrompt = 'twelve chars'; // 12 chars = 3 tokens
            component.channelGuidelines = '';
            component.customPrompt = '';
            expect(component.getTokenEstimate()).toBe(3);
        });
    });
});
