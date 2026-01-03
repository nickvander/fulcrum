# Plan: AI Integration & Intelligent Product Agents

## Goal
Integrate a modular AI Agent architecture into Fulcrum to enable "Bring Your Own Key" (BYOK) AI features. The first major feature is an **Intelligent Product Scanner** that uses multimodal AI (Vision) to identify products from images, check for existence in the database, or suggest details for new products. Additionally, implement automated Barcode/QR code generation for all products.

## Technology Stack Recommendation
*   **Agent Framework**: **PydanticAI** (or a lightweight custom service using `google-generativeai` and `openai` SDKs directly). PydanticAI is recommended for its seamless integration with FastAPI, Pydantic models, and type safety.
*   **Models**: 
    *   **Primary**: Google Gemini 1.5 Flash (Best for speed, cost, and multimodal vision).
    *   **Secondary/User Option**: OpenAI GPT-4o, Claude 3.5 Sonnet.
*   **Barcode/QR**: `python-barcode`, `qrcode[pil]`.

## Phase 1: Foundation & "Vision Agent"

### 1. Unified AI Service Layer
Create a modular backend service to handle API keys and model abstraction.
*   **Secure Key Storage**: Update `Settings` model to store encrypted API keys for providers (Gemini, OpenAI, Anthropic).
*   **Model Provider Factory**: A service that initializes the correct client based on user settings.
*   **Location**: `backend/src/services/ai/`

### 2. The "Vision Agent" (Product Identifier)
A specialized agent designed to "see" products.
*   **Input**: Image (uploaded or camera capture).
*   **Capability**:
    *   Analyze image using Multimodal LLM (Gemini Flash).
    *   Extract structured data: `ProductMetadata` (Brand, Name, SKU/Barcode if visible, Description, Category, Estimated Price).
    *   **Agent Logic**:
        *   *Step 1*: Identify product features.
        *   *Step 2*: Search existing database (using Vector Utils or Fuzzy Search) for matches.
        *   *Step 3 (Result)*: Return structured response: `{ match_found: bool, existing_product_id: UUID, suggested_details: ProductSchema }`.

### 3. Barcode & QR Code Engine
Enhance product identification in the physical world.
*   **Signal**: On `Product` create/update.
*   **Action**: 
    *   Generate standard Barcode (EAN-13 or Code-128) if SKU allows, or auto-generate internal barcode.
    *   Generate QR Code containing a deep link (e.g., `https://fulcrum.app/products/{id}`).
*   **Storage**: Save images to object storage (or local `static/` for now) and link URL in DB.
*   **UI**: Display codes in Product Details with "Print" option.

### 4. Frontend Integration
*   **Scanner Interface**:
    *   New "Scan Product" button in global nav or Product List.
    *   Camera view (using HTML5 Media Devices API) + File Upload.
    *   "Analyzing..." animation.
*   **Result Modal**:
    *   If Found: "Is this the product?" -> Redirect to Product Details.
    *   If New: "New Product Detected" -> Pre-fill `ProductFormComponent` with AI suggestions.

## Implementation Steps

### Backend
1.  **Dependencies**: Add `google-generativeai`, `openai`, `pydantic-ai`, `python-barcode`, `qrcode`, `pillow`.
2.  **Settings**: Add `ai_provider_config` to `Settings` schema.
3.  **Core AI Service**: Implement `AIService` class with `get_vision_model()`.
4.  **Vision Endpoint**: `POST /api/v1/ai/identify-product`
    *   Accepts `UploadFile`.
    *   Runs Agent pipeline.
5.  **Barcode Service**: Implement `BarcodeGenerator` and add hooks to `ProductService`.

### Frontend
1.  **Settings UI**: Add "AI Integrations" tab in Settings to input API Keys.
2.  **Camera Component**: Create `CameraCaptureComponent` for handling video stream and image capture.
3.  **Scan Logic**: Service to upload image to `identify-product` endpoint.
4.  **Product Form**: Logic to accept "pre-filled" data from the AI scan.

## Verification
*   **Unit Tests**: Mock AI responses to test extraction logic and JSON parsing.
*   **Integration Tests**: Test end-to-end flow with real (or recorded) API calls if possible.
*   **Manual**: Test with various physical products.

## Future Agents (Roadmap)
*   **Marketing Agent**: Generate newsletters/social posts (Planned Phase 4).
*   **Support Agent**: Chat interface for user queries.
