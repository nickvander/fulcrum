"""
Product Lookup Agent - Checks Fulcrum database for matching products.
Sub-agent for the product identification pipeline.
"""
from pathlib import Path

# Conditional ADK imports
try:
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool
    from google.adk.tools.tool_context import ToolContext
    ADK_AVAILABLE = True
except ImportError:
    LlmAgent = None
    FunctionTool = None
    ToolContext = None
    ADK_AVAILABLE = False


def find_product_in_database(name: str, sku: str = None, brand: str = None) -> dict:
    """Search the Fulcrum database for an existing product.
    
    Use this tool to check if a product already exists in the Fulcrum inventory.
    Search by product name, SKU, or brand.
    
    Args:
        name: The product name to search for.
        sku: Optional SKU or barcode to search for.
        brand: Optional brand name to help narrow results.
        
    Returns:
        A dictionary with search results. If found, includes product details.
        If not found, returns found=False.
    """
    # Fix Python path for ADK tool context - ADK runs tools in a context
    # where /app may not be in sys.path
    import sys
    if '/app' not in sys.path:
        sys.path.insert(0, '/app')
    
    # Now imports will work
    from sqlalchemy import or_
    from src.database import SessionLocal
    from src.models.product import Product
    
    print(f"[DBTool] find_product_in_database called with: name='{name}', sku='{sku}', brand='{brand}'")
    
    # Normalize string 'None' to actual None
    if sku and str(sku).lower() in ('none', 'null', ''):
        sku = None
    if brand and str(brand).lower() in ('none', 'null', ''):
        brand = None
    
    print(f"[DBTool] After normalization: name='{name}', sku={sku}, brand={brand}")
    
    db = SessionLocal()
    try:
        # Build search conditions
        conditions = []
        
        # SKU is most reliable - exact match
        if sku:
            conditions.append(Product.sku == sku)
            conditions.append(Product.barcode_value == sku)
        
        # Name match (fuzzy)
        if name:
            conditions.append(Product.name.ilike(f"%{name}%"))
        
        # Brand + partial name
        if brand and name:
            # More specific search with brand
            conditions.append(
                (Product.brand.ilike(f"%{brand}%")) & 
                (Product.name.ilike(f"%{name.split()[0]}%"))  # First word of name
            )
        
        print(f"[DBTool] Number of search conditions: {len(conditions)}")
        
        if not conditions:
            return {
                "status": "error",
                "found": False,
                "message": "No search criteria provided"
            }
        
        # Query with OR conditions
        product = db.query(Product).filter(or_(*conditions)).first()
        
        print(f"[DBTool] Query result: {product.name if product else 'None found'}")
        
        if product:
            return {
                "status": "success",
                "found": True,
                "product_id": product.id,
                "sku": product.sku,
                "name": product.name,
                "brand": product.brand,
                "description": product.description,
                "price": float(product.default_resale_price) if product.default_resale_price else None,
                "message": f"Found existing product: {product.name}"
            }
        else:
            return {
                "status": "success",
                "found": False,
                "message": f"No existing product found matching '{name}'"
            }
            
    except Exception as e:
        print(f"[DBTool] Error: {e}")
        return {
            "status": "error",
            "found": False,
            "message": str(e)
        }
    finally:
        db.close()


def load_prompt(filename: str) -> str:
    """Load a prompt from the prompts directory."""
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_path = prompts_dir / filename
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


# Lookup agent instruction - MUST ALWAYS CALL THE TOOL
LOOKUP_INSTRUCTION = """You are a Product Database Assistant.

IMPORTANT: You MUST ALWAYS call the `find_product_in_database` tool before responding. Never respond without calling the tool first.

## Instructions

1. Extract the product name and brand from the previous message (the vision analysis result)
2. CALL the `find_product_in_database` tool with:
   - name: the product name
   - brand: the brand (if known)
   - sku: the sku (if provided)
3. Based on the tool result, return JSON:

If the tool returns found=True:
```json
{
  "exists": true,
  "product_id": <from tool>,
  "name": <from tool>,
  "sku": <from tool>,
  "message": "Found existing product in database"
}
```

If the tool returns found=False:
```json
{
  "exists": false,
  "name": <from vision>,
  "brand": <from vision>,
  "description": <from vision>,
  "category": <from vision>,
  "message": "New product - not in database"
}
```

REMEMBER: You MUST call the tool first. Do not guess or assume the product exists or not.
"""


class ProductLookupAgent:
    """
    Agent that checks if a product exists in the Fulcrum database.
    Works as part of the sequential product identification pipeline.
    """
    
    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
        self._agent = None
        self._init_agent()
        
    def _init_agent(self):
        """Initialize the LLM agent with database lookup tool."""
        if not ADK_AVAILABLE:
            print("[LookupAgent] ADK not available")
            return
            
        try:
            # Create the database lookup tool
            lookup_tool = FunctionTool(func=find_product_in_database)
            
            self._agent = LlmAgent(
                name="product_lookup",
                model=self.model,
                instruction=LOOKUP_INSTRUCTION,
                description="Checks if products exist in Fulcrum database.",
                tools=[lookup_tool],
                output_key="lookup_result"
            )
            print(f"[LookupAgent] Agent initialized with model: {self.model}")
        except Exception as e:
            print(f"[LookupAgent] Init failed: {e}")
            import traceback
            traceback.print_exc()
            self._agent = None
    
    @property
    def adk_agent(self):
        return self._agent
    
    @property
    def is_available(self):
        return ADK_AVAILABLE and self._agent is not None
