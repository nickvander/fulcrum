# AI Integration Guide

Fulcrum leverages AI to streamline product management using multiple AI
providers (Google Gemini, OpenAI, Anthropic Claude, Alibaba Qwen).

## Features

### 1. Product Scanner (Vision Agent)

The product scanner allows users to capture photos of products and
automatically identify details like Name, Description, Brand, and Category.

**Modes:**

- **AI Mode (Configured):** Captures image, analyzes it with the configured AI
  provider, and pre-fills the "Add Product" form.
- **Manual Mode (Not Configured):** Standard camera to capture a product image
  and attach it to a blank form for manual entry.
- **Barcode Scanner:** Use a Bluetooth scanner or camera to scan barcodes.

### 2. Barcode & QR Code Generation

Automatically generates CODE128 barcodes and QR codes for products:

- **Barcode:** Format `STORE-{SKU}` for internal tracking
- **QR Code:** Links to your store domain (configured in Settings > Marketing)

## Configuration

AI features are "Bring Your Own Key" (BYOK).

### Setting Up AI

1. Navigate to **Settings > AI & Agents**
2. Toggle **Enable AI Features** ON
3. Select your **Active Provider** (Google, OpenAI, Anthropic, or Qwen)
4. Enter the API key for your selected provider
5. Optionally override the model name
6. Click **Save**

### Supported Providers

| Provider   | Default Model               | API Key Source                |
|------------|-------------------------------|-------------------------------|
| Google     | gemini-2.0-flash             | [AI Studio](https://aistudio.google.com/) |
| OpenAI     | gpt-4o                       | [OpenAI](https://platform.openai.com/) |
| Anthropic  | claude-3-5-sonnet-20240620   | [Anthropic](https://console.anthropic.com/) |
| Qwen       | qwen-vl-max                  | [DashScope](https://dashscope.console.aliyun.com/) |

### Store Domain (QR Codes)

Configure your store's public domain in **Settings > Marketing > Store Brand**:

- **Store Name:** Your store's display name
- **Store Domain:** Base URL for QR codes (e.g., `https://mystore.com`)

QR codes will generate URLs like: `https://mystore.com/qr/{product_id}`

## Architecture

### ADK Agent Structure

```
backend/src/services/adk/
├── __init__.py           # Package exports
├── manager.py            # ADKManager - settings & key management
├── agents/               # All agent implementations
│   ├── __init__.py
│   └── product_vision/   # Product identification agent
│       ├── __init__.py
│       ├── agent.py      # ProductVisionAgent class
│       └── prompts/
│           └── system.md # Agent instructions (editable)
```

### Key Design Decisions

1. **Prompts in Markdown:** Agent instructions are stored in `.md` files for
   easy editing without code changes.

2. **Multi-Provider Support:** The `ProductVisionAgent` supports multiple AI
   providers with automatic fallback.

3. **ADK Compatibility:** Designed to work with Google ADK when available,
   with fallback to direct API calls.

4. **Modular Design:** Each agent is self-contained in its own directory with
   prompts and tools.

### Adding New Agents

Create a new directory in `agents/`:

```
agents/new_agent/
├── __init__.py
├── agent.py
└── prompts/
    └── system.md
```

Export from `agents/__init__.py` and use in your service.

## Testing

To test AI features without cost:

1. Use **Gemini 1.5 Flash** (free tier available)
2. Use "Manual Mode" of the scanner if you don't have an API key
3. Run the test script: `python -m pytest tests/test_ai_service.py`
