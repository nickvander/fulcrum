# Task 75: AI Content Generation & Marketing Agent

## Goal

Implement a comprehensive AI-powered marketing content generation system using
ADK. Users can:

1. Generate social media content (Twitter/X, Instagram) based on product data
2. Generate photorealistic product images for marketing campaigns
3. Manually or automatically create marketing content via dedicated UI

---

## Architecture

### Agent Structure (ADK)

**MarketingRootAgent** orchestrates specialized sub-agents:

1. **ResearchAgent**: Search current trends, hashtags, viral angles
2. **ContentAgent**: Draft platform-specific posts (Twitter 280 chars, Instagram
   with hashtags)
3. **ImageAgent**: Generate product images using Gemini's native image output

### Backend Implementation

- `src/services/adk/agents/marketing/` - Agent service directory
  - `root_agent.py` - Orchestrator
  - `research_agent.py` - Trend search
  - `content_agent.py` - Text generation
  - `image_agent.py` - Image generation
- `src/api/v1/endpoints/marketing_ai.py` - API endpoints
  - `GET /tone-presets` - Available tone presets
  - `POST /generate-content` - Full generation pipeline

### Frontend Implementation

- **Quick Post Dialog** with AI Content Assistant panel
- Tone chips with editable prompts
- Split generation (Text / Image / Both)
- Product image URL support for style reference

---

## Completed (2026-01-05)

- ✅ Implemented AI Content Generation pipeline with ADK
- ✅ Created `MarketingRootAgent` with research, content, and image agents
- ✅ Image generation working via `gemini-2.0-flash-exp`
- ✅ Quick Post Dialog UI with product linking, tone selection, image preview
- ✅ Default image toggle set to OFF
- ✅ Added `/tone-presets` API endpoint (backend)
- ✅ Injected SettingsService for AI enabled check
- ✅ Tone chips UI with editable prompt (Content + Image prompts)
- ✅ Image URL displayed as chip with clear button
- ✅ Fixed saveDraft with content_json AI metadata
- ✅ Split generation buttons (Generate Text / Image / Both)
- ✅ Overwrite confirmation dialogs
- ✅ Product image URL passed to AI for style reference
- ✅ Updated `ai-integration.md` with Marketing Agent diagram
- ✅ Updated `marketing.md` user guide

---

## Future Enhancements

- [ ] Frontend unit tests for QuickPostDialogComponent
- [x] Refactor tone prompts to `.md` files for easier maintenance
- [x] Channel-aware prompt modifications (Instagram = more hashtags)
- [x] UI to preview active tone + channel prompts before generating

## Prompt File Structure (Added 2026-01-05)

```
prompts/
├── content.md           # Main ContentAgent system prompt
├── research.md          # ResearchAgent system prompt
├── image_generation.md  # ImageAgent system prompt
├── channels/
│   ├── twitter.md       # Twitter/X guidelines (280 chars, 1-2 hashtags)
│   └── instagram.md     # Instagram guidelines (5-10 hashtags, line breaks)
└── tones/
    ├── professional.md  # Formal business voice
    ├── casual.md        # Friendly conversational
    ├── viral.md         # High-energy, FOMO-driven
    └── luxury.md        # Elegant, aspirational
```

**API Endpoints:**
- `GET /tone-presets` - Returns tone presets (prompts loaded from .md files)
- `GET /channel-guidelines/{channel}` - Returns channel-specific guidelines
