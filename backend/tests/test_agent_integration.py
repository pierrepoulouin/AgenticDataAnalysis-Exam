"""
Integration tests for the agent system with PostgreSQL checkpointer.
Run with: docker exec agentic-backend python -m pytest backend/tests/test_agent_integration.py -v
"""
import pytest
import pandas as pd
import asyncio
import os

# NOTE: Import will work after backend implementation
# from backend.agents.agent_manager import AgentManager
# from backend.models.database import get_db


@pytest.fixture
def sample_dataframe():
    """Create a sample census-like dataframe for testing."""
    return pd.DataFrame({
        'age': [25, 30, 35, 40, 45, 50, 55, 60],
        'income': [30000, 45000, 55000, 65000, 75000, 85000, 95000, 105000],
        'education': ['HS', 'BS', 'BS', 'MS', 'MS', 'PhD', 'PhD', 'PhD'],
        'workclass': ['Private', 'Private', 'Gov', 'Private', 'Gov', 'Private', 'Self', 'Self']
    })


@pytest.fixture
def context(sample_dataframe):
    """Create context for agent manager."""
    return {
        'df': sample_dataframe,
        'dataset_id': 1,
        'dataset_name': 'test_census.csv',
        'columns': sample_dataframe.columns.tolist(),
        'shape': sample_dataframe.shape,
        'dtypes': sample_dataframe.dtypes.astype(str).to_dict()
    }


@pytest.fixture
def agent_manager():
    """Get agent manager instance with PostgreSQL checkpointer."""
    # TODO: Implement after backend migration
    pass


@pytest.mark.asyncio
@pytest.mark.integration
async def test_describe_dataset(agent_manager, context):
    """
    Test: Agent can describe the dataset
    Expected: Agent returns accurate description
    """
    # TODO: Implement after backend migration
    
    # result = await agent_manager.process_query(
    #     query="describe the dataset",
    #     context=context,
    #     session_id="test-session-1"
    # )
    
    # assert result['success'] == True, f"Query failed: {result.get('error')}"
    # assert len(result['synthesis']) > 0, "No synthesis generated"
    
    pytest.skip("Backend not implemented yet - students will complete this")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_histogram(agent_manager, context):
    """
    Test: Agent can create histogram visualization
    Expected: Figure is generated and saved as JSON
    """
    pytest.skip("Backend not implemented yet - students will complete this")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_calculate_mean(agent_manager, context):
    """
    Test: Agent can calculate statistics
    Expected: Correct mean age returned
    """
    pytest.skip("Backend not implemented yet - students will complete this")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_scatter_plot(agent_manager, context):
    """
    Test: Agent can create scatter plot
    Expected: Figure is generated with correct data
    """
    pytest.skip("Backend not implemented yet - students will complete this")


@pytest.mark.asyncio
@pytest.mark.persistence
async def test_session_persistence(agent_manager, context):
    """
    CRITICAL TEST: Test that agent remembers conversation after restart
    Steps:
    1. Query 1: "Calculate mean age"
    2. Checkpoint saved to PostgreSQL
    3. Simulate restart: Create new agent_manager instance
    4. Query 2: "What was the mean age we calculated?"
    Expected: Agent remembers from checkpoint
    """
    pytest.skip("Backend not implemented yet - students will implement this")


@pytest.mark.asyncio
@pytest.mark.security
async def test_code_execution_sandbox(agent_manager, context):
    """
    CRITICAL TEST: Test that malicious code is blocked
    Steps:
    1. Query with malicious code
    2. Verify execution is blocked/sandboxed
    Expected: Security breach prevented
    """
    pytest.skip("Backend not implemented yet - students will implement this")
