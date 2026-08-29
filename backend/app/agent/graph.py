from langgraph.graph import END, StateGraph

from backend.app.agent.manager import AgentManager
from backend.app.agent.nodes import make_tool_execution_node
from backend.app.agent.state import AgentState


def create_agent_graph(
    manager: AgentManager,
):
    workflow = StateGraph(AgentState)

    tool_execution_node = make_tool_execution_node(
        manager
    )

    workflow.add_node(
        "tool_execution",
        tool_execution_node,
    )

    workflow.set_entry_point(
        "tool_execution"
    )

    workflow.add_edge(
        "tool_execution",
        END,
    )

    return workflow.compile()