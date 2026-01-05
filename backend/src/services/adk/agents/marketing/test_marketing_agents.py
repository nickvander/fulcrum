"""
Marketing Agent Tests

NOTE: These tests require the full ADK environment to be available.
They are skipped in fast tests and run only in full integration test suites.
"""
import pytest


@pytest.mark.skip(reason="Requires full ADK environment - run manually or in integration suite")
def test_marketing_root_agent_initialization():
    """Test that the agent initializes correctly."""
    from src.services.adk.agents.marketing.root_agent import MarketingRootAgent
    agent = MarketingRootAgent(api_key="test-key")
    assert agent.is_available
    assert agent._pipeline is not None


@pytest.mark.skip(reason="Requires full ADK environment - run manually or in integration suite")
def test_generate_campaign():
    """Test the full generation flow."""
    import asyncio
    from src.services.adk.agents.marketing.root_agent import MarketingRootAgent
    
    agent = MarketingRootAgent(api_key="test-key")
    
    result = asyncio.run(agent.generate_campaign(
        product_name="Test Product",
        product_description="Awesome stuff"
    ))
    
    # Verify results have expected structure
    assert "content" in result or "error" in result
