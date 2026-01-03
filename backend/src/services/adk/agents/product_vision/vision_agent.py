from backend.src.services.adk.tools.search_tool import SearchTool
from backend.src.services.adk.tools.fulcrum_tool import TOOL_DEFINITION as FulcrumTool

class VisionAnalysisAgent:
    """
    Specialized agent for analyzing product images.
    """
    
    def __init__(self, model: str):
        self.model = model
        self.system_prompt = load_prompt("system.md")
        self._agent = None
        self._init_agent()
        
    def _init_agent(self):
        try:
            tools = []
            
            # Add Search Tool if available
            search = SearchTool()
            if search.is_available and search.tool:
                tools.append(search.tool)
                
            # Add Fulcrum DB Tool
            tools.append(FulcrumTool)
            
            self._agent = LlmAgent(
                name="vision_analysis",
                model=self.model,
                instruction=self.system_prompt,
                description="Analyzes product images to extract attributes.",
                tools=tools if tools else None
            )
        except Exception as e:
            print(f"VisionAnalysisAgent init failed: {e}")
            self._agent = None

    @property
    def adk_agent(self):
        return self._agent
