# Progress Log: AI Integration & Intelligent Agents

## Status: Planning

### Objective
Integrate modular AI architecture, Vision Agent for product scanning, and Barcode/QR generation.

### Work Log
- [ ] **Phase 1: Foundation & Vision Agent**
    - [ ] **Dependencies & Configuration**
        - [ ] Add `pydantic-ai`, `google-generativeai`, `openai`, `qrcode`, `python-barcode` to backend requirements.
        - [ ] Update `Settings` model/schema to support multiple AI Provider API Keys (Gemini, OpenAI, Claude).
    - [ ] **AI Service Module (`backend/src/services/ai/`)**
        - [ ] Create `AIService` abstract base and specific implementations.
        - [ ] Implement BYOK key retrieval from Settings.
    - [ ] **Barcode Engines (`backend/src/services/barcode/`)**
        - [ ] Create `BarcodeGenerator` service (EAN/Code128).
        - [ ] Create `QRCodeGenerator` service.
        - [ ] Add DB columns for `barcode_image_url` and `qrcode_image_url` to `Product`.
    - [ ] **Vision Agent API**
        - [ ] Create `POST /api/v1/ai/products/identify` endpoint.
        - [ ] Implement Vision Logic: Image -> Gemini Flash -> JSON Data.
        - [ ] Implement Search Logic: Match AI data against existing DB products.
    - [ ] **Frontend: Settings**
        - [ ] Add "AI Integration" tab in Settings Dialog.
        - [ ] Inputs for Gemini API Key, OpenAI Key, etc.
    - [ ] **Frontend: Product Scanner**
        - [ ] Build `CameraCaptureComponent` (or reuse existing if avail).
        - [ ] Implement "Scan Product" UI in Product List.
        - [ ] Handle "New Product" flow with pre-filled data.

### Notes
- **ADK Choice**: Using **PydanticAI** for type-safe agent definitions.
- **Model Standard**: Gemini 1.5 Flash recommended for default "Vision" tasks due to speed/free-tier/multimodal capabilities.
