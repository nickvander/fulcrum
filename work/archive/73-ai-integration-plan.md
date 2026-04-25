# Plan: AI Integration & ADK Agents

## Goal

Integrate a scalable, modular AI Agent architecture into Fulcrum using
**Google's Agent Development Kit (ADK)** capabilities. This enables "Bring Your
Own Key" (BYOK) for users to plug in their own model providers (Gemini, OpenAI,
etc.). The first implementation will be an **Intelligent Product Scanner Agent**
using **Gemini 3 Flash/Pro** to identify products and automated Barcode/QR
generation.

## Technology Stack

- **Agent Framework**: **Google ADK (Python SDK)** used as a **standalone
  library**.
  - _Why?_ It allows us to build structured, observable agents using a
    standardized pattern _without_ requiring Google Cloud Platform or Vertex AI
    infrastructure.
  - _BYOK Support_: **adk-python** natively supports `LiteLLM`, allowing us to
    plug in OpenAI (GPT-4o) and other providers easily by passing the user's API
    key.
  - _Future Scalability_: Since this is the same SDK used by **Vertex AI Agent
    Engine**, we can easily move these agents to the managed Vertex platform
    later (for enterprise scale/governance) without rewriting code—just by
    changing deployment config.
- **Models**:
  - **Primary**: **Gemini 3 Flash** (Fast, Free Tier, Multimodal).
  - **Secondary**: **Gemini 3 Pro** (Complex Reasoning).
  - **Fallback**: OpenAI GPT-4o (via `LiteLLM` in ADK).
- **Barcode/QR**: `python-barcode`, `qrcode[pil]`.
- **Backend**: FastAPI (Python).

## Phase 1: Foundation & "Vision Agent"

### 1. Unified AI Service Layer (ADK Integration)

Create a centralized service to manage ADK agents and model configuration.

- **Secure Key Storage**: Extend `StoreSettings` to store encrypted API keys
  (e.g., `ai_gemini_key_encrypted`, `ai_openai_key_encrypted`).
- **ADK Model Client**: A factory that initializes the correct model client
  based on user settings.
- **Location**: `backend/src/services/adk/` and
  `backend/src/api/v1/endpoints/ai.py`.

### 2. The "Vision Agent" (Product Identifier)

A specialized sequential agent designed to "see" and identify products.

- **Input**: Product Image.
- **Workflow (Sequential Agent)**:
  1.  **Analyst Step**: Uses **Gemini 3 Flash** to analyze the image and extract
      raw visual features (Brand, text, logos, potential category).
  2.  **Search Step**: Queries the Fulcrum database (Vector/Fuzzy search) to
      find potential matches based on Analyst output.
  3.  **Synthesizer Step**: Combines visual data + search results.
      - _If Match_: Returns "Product Found" with ID.
      - _If New_: Uses **Gemini 3 Pro** (or Flash) to suggest full product
        details (Title, Description, Attributes).
- **Output**: Structured JSON `ProductIdentificationResult`.

### 3. Barcode & QR Code Engine

- **Trigger**: Product Creation/Update.
- **Logic**:
  - Generate `CODE128` barcode for SKU.
  - Generate QR Code for Deep Link (`https://fulcrum.app/p/{id}`).
- **Storage**: Save to local `uploads/` (or S3), store URL in `Product` model.

### 4. Frontend Integration

- **Settings**: New "AI & Agents" tab for API Key management.
- **Scanner UI**:
  - Camera capture / File Upload widget.
  - Real-time feedback ("Agent Analyzing...", "Searching Inventory...").
  - "Create from Scan" flow.

## Implementation Steps

### Backend

1.  **Dependencies**: Add `google-adk` (core library), `google-generativeai`,
    `python-barcode`, `qrcode`.
    - _Note_: We do NOT need `google-cloud-aiplatform` unless we decide to
      deploy to Vertex AI later.
2.  **Schema**: Update `StoreSettings` model to include AI keys.
3.  **ADK Setup**:
    - Create `src/core/adk.py`: Setup ADK runtime/registry.
    - Implement `ProductVisionAgent` class.
4.  **API**: Update `POST /api/v1/ai/identify` to use the Agent.
5.  **Barcode**: Implement `src/services/barcode_service.py`.

### Frontend

1.  **AI Settings**: UI for inputting Gemini/OpenAI keys.
2.  **Scanner Component**: `ProductScannerComponent` (Camera/Upload).
3.  **Integration**: Accessible via "Scan" button in Product List.

## Verification

- **Unit Tests**: Mock ADK model responses to verify flow control.
- **Integration**: Functional test using a real (dev) key to verify Gemini API
  connectivity.
- **Manual**: Scan real objects (cereal box, book) and verify extraction.
