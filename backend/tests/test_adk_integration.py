import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.services.adk.agents.product_vision.agent import ProductVisionAgent
from src.services.adk.orchestrator import AgentOrchestrator
from src.services.adk.manager import ADKManager

@pytest.mark.asyncio
async def test_product_vision_agent_fallback():
    """Test standard fallback behavior without ADK."""
    with patch('src.services.adk.agents.product_vision.agent.ADK_AVAILABLE', False):
        agent = ProductVisionAgent(model="gemini-2.0-flash")
        result = await agent.identify("fake_image.jpg")
        
        # Should return error since we didn't mock the internal fallback execution
        # but verifies the structure works
        assert "error" in result

@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """Test orchestrator initialization."""
    manager = MagicMock(spec=ADKManager)
    orchestrator = AgentOrchestrator(manager)
    assert orchestrator.manager == manager

@pytest.mark.asyncio
async def test_orchestrator_vision_flow():
    """Test the vision agent flow in orchestrator."""
    manager = MagicMock(spec=ADKManager)
    
    # Mock manager config
    # manager.get_active_config() returns a dict in the service code
    manager.get_active_config.return_value = {"model": "gemini-2.0-flash"}
    
    # Mock vision agent
    with patch('src.services.adk.orchestrator.ProductVisionAgent') as MockAgent:
        mock_instance = MockAgent.return_value
        mock_instance.identify = AsyncMock(return_value={"name": "Test Product", "category": "Test"})
        
        orchestrator = AgentOrchestrator(manager)
        result = await orchestrator.process_product_image("fake_path.jpg")
        
        assert result["name"] == "Test Product"
        MockAgent.assert_called_with(model="gemini-2.0-flash")
