# Progress Log: AI Integration & Intelligent Agents

## Status: In Progress

### Objective
Integrate modular AI architecture using Google ADK & Gemini 3, Vision Agent, and Barcode/QR generation.

### Work Log
- [x] **Phase 1: Foundation & Vision Agent**
    - [x] **Dependencies & Configuration**
        - [x] Add AI libraries to backend requirements
        - [x] Update `StoreSettings` model/schema (Encrypted keys, Store Domain)
    - [x] **AI Service Module (`backend/src/services/adk/`)**
        - [x] Create `ADKManager` class
        - [x] Implement BYOK key retrieval
        - [x] Implement `AgentOrchestrator`
        - [x] Implement `ProductVisionAgent` (Model agnostic, ADK pattern)
    - [x] **Barcode Engines (`backend/src/services/barcode/`)**
        - [x] Create `BarcodeService`
        - [x] Add columns `barcode_image_url`, `qrcode_image_url` to `Product`
    - [x] **Vision Agent API**
        - [x] Create `POST /api/v1/ai/identify-product` endpoint
        - [x] Create tests for ADK integration (`tests/test_adk_integration.py`)
    - [x] **Frontend: Settings**
        - [x] Add "AI & Agents" tab in Settings
        - [x] Add "Marketing > Store Brand" section (Store Name, Domain)
        - [x] Inputs for Multi-Provider API Keys
    - [x] **Frontend: Product Scanner**
        - [x] Build `ProductScannerComponent` (Camera + Upload + Bluetooth)
        - [x] Integrate Scanner into "Add Product" flow

### Notes
- **Architecture**: Modular ADK design with `LlmAgent`, `Runner`, and `Orchestrator`.
- **Agents**: Currently implemented `ProductVisionAgent` (Vision -> JSON).
- **Providers**: Supports Google Gemini, OpenAI, Anthropic, Qwen.
- **QR Codes**: Uses `StoreSettings.store_domain` for public URLs.
