
from langgraph.graph import END, StateGraph

from backend.app.agent.manager import AgentManager
from backend.app.agent.nodes import (
    make_reason_node,
    make_tool_execution_node,
)
from backend.app.agent.state import AgentState
from backend.app.agent.planner import Planner



def route_after_reason(state: AgentState) -> str:
    if state.get("final_answer"):
        return "end"

    if state.get("tool_name"):
        return "tool"

    raise ValueError(
        "Reason node produced neither a tool nor a final answer"
    )


def create_agent_graph(
    manager: AgentManager,
    planner: Planner,
):
    workflow = StateGraph(AgentState)

    workflow.add_node(
        "reason",
        make_reason_node(planner),
    )

    workflow.add_node(
        "tool_execution",
        make_tool_execution_node(manager),
    )

    workflow.set_entry_point("reason")

    workflow.add_conditional_edges(
        "reason",
        route_after_reason,
        {
            "tool": "tool_execution",
            "end": END,
        },
    )

    workflow.add_edge(
        "tool_execution",
        "reason",
    )

    return workflow.compile()