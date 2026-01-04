"""
ADK Integration Tests.

Tests for the ADK agent architecture without requiring actual API calls.
"""
from unittest.mock import MagicMock


class TestProductVisionAgent:
    """Tests for the ProductVisionAgent."""

    def test_agent_fallback_when_adk_unavailable(self):
        """Test standard fallback behavior without ADK."""
        from src.services.adk.agents.product_vision import root_agent
        
        # Temporarily disable ADK
        original_value = root_agent.ADK_AVAILABLE
        root_agent.ADK_AVAILABLE = False
        
        try:
            from src.services.adk.agents.product_vision.agent import ProductVisionAgent
            agent = ProductVisionAgent(model="gemini-3.0-flash")
            assert agent.is_available is False
        finally:
            root_agent.ADK_AVAILABLE = original_value

    def test_vision_agent_initialization(self):
        """Test VisionAnalysisAgent initializes correctly."""
        from src.services.adk.agents.product_vision.vision_agent import VisionAnalysisAgent
        
        agent = VisionAnalysisAgent(model="gemini-3.0-flash")
        # May or may not be available depending on ADK installation
        assert hasattr(agent, 'is_available')
        assert hasattr(agent, 'adk_agent')


class TestAgentOrchestrator:
    """Tests for the AgentOrchestrator."""

    def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        from src.services.adk.orchestrator import AgentOrchestrator
        from src.services.adk.manager import ADKManager
        
        manager = MagicMock(spec=ADKManager)
        orchestrator = AgentOrchestrator(manager)
        assert orchestrator.manager == manager

    def test_orchestrator_get_vision_agent(self):
        """Test getting vision agent from orchestrator."""
        from src.services.adk.orchestrator import AgentOrchestrator
        from src.services.adk.manager import ADKManager
        
        manager = MagicMock(spec=ADKManager)
        manager.get_active_config.return_value = {"model": "gemini-3.0-flash"}
        
        orchestrator = AgentOrchestrator(manager)
        agent = orchestrator._get_vision_agent()
        
        assert agent is not None
        assert hasattr(agent, 'is_available')


class TestRootAgent:
    """Tests for ProductVisionRootAgent."""

    def test_root_agent_initialization(self):
        """Test root agent initializes correctly."""
        from src.services.adk.agents.product_vision.root_agent import ProductVisionRootAgent
        
        agent = ProductVisionRootAgent(model="gemini-3.0-flash")
        assert hasattr(agent, 'is_available')
        assert hasattr(agent, '_vision_agent')
