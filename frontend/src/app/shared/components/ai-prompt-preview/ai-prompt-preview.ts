import { Component, Input, Output, EventEmitter, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';

/**
 * AiPromptPreviewComponent
 * 
 * A reusable, responsive component that displays AI prompt information
 * for transparency. Works with any ADK agent (Marketing, ProductVision, etc.)
 * 
 * Usage:
 * ```html
 * <app-ai-prompt-preview
 *   agentName="Marketing Content Generator"
 *   [tonePrompt]="selectedTone.prompt"
 *   [channelGuidelines]="currentChannelGuidelines"
 *   [customPrompt]="customPromptCtrl.value">
 * </app-ai-prompt-preview>
 * ```
 */
@Component({
    selector: 'app-ai-prompt-preview',
    standalone: true,
    imports: [
        CommonModule,
        MatIconModule,
        MatButtonModule,
        MatTooltipModule
    ],
    templateUrl: './ai-prompt-preview.html',
    styleUrls: ['./ai-prompt-preview.scss']
})
export class AiPromptPreviewComponent implements OnChanges {
    /** Name of the AI agent for display */
    @Input() agentName = 'AI Agent';

    /** The selected tone's full prompt text */
    @Input() tonePrompt = '';

    /** Channel-specific guidelines (e.g., Twitter vs Instagram) */
    @Input() channelGuidelines = '';

    /** User's custom additions to the prompt */
    @Input() customPrompt = '';

    /** Whether the preview panel is expanded */
    @Input() expanded = false;

    /** Emits when expand state changes (for two-way binding) */
    @Output() expandedChange = new EventEmitter<boolean>();

    /** Computed: whether there's any content to show */
    hasContent = false;

    ngOnChanges(changes: SimpleChanges): void {
        this.hasContent = !!(this.tonePrompt || this.channelGuidelines || this.customPrompt);
    }

    toggleExpanded(): void {
        this.expanded = !this.expanded;
        this.expandedChange.emit(this.expanded);
    }

    /** Get word count for a section */
    getWordCount(text: string): number {
        if (!text) return 0;
        return text.trim().split(/\s+/).filter(w => w.length > 0).length;
    }

    /** Get total token estimate (rough: 1 token ≈ 4 chars) */
    getTokenEstimate(): number {
        const totalChars = (this.tonePrompt?.length || 0) +
            (this.channelGuidelines?.length || 0) +
            (this.customPrompt?.length || 0);
        return Math.ceil(totalChars / 4);
    }
}
