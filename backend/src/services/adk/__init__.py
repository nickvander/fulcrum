"""
ADK (Agent Development Kit) Service

This module provides AI agent capabilities for the Fulcrum platform.

## Architecture

The agents are organized in a directory structure:
- `agents/` - Contains all agent implementations
  - `product_vision/` - Product identification from images
    - `prompts/` - Markdown prompt files
    - `agent.py` - Agent implementation

## Usage

```python
from src.services.adk.agents import ProductVisionAgent

agent = ProductVisionAgent(
    provider="google",
    api_key="your-api-key"
)

result = await agent.identify_product("/path/to/image.jpg")
```
"""
from .manager import ADKManager
from .agents import ProductVisionAgent

__all__ = ["ADKManager", "ProductVisionAgent"]
