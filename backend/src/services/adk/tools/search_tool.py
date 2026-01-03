"""
Search Tool for ADK Agents.
Wraps the ADK built-in Google Search tool.
"""
try:
    from google.adk.tools import google_search
    ADK_SEARCH_AVAILABLE = True
except ImportError:
    ADK_SEARCH_AVAILABLE = False
    google_search = None

class SearchTool:
    """Wrapper for ADK native search."""
    
    @property
    def tool(self):
        """Returns the ADK tool definition."""
        return google_search if ADK_SEARCH_AVAILABLE else None

    @property
    def is_available(self):
        return ADK_SEARCH_AVAILABLE
