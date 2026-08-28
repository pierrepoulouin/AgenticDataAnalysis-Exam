from typing import List

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph

from Pages.data_models import InputData
from Pages.graph.nodes import call_model, call_tools, route_to_tools
from Pages.graph.state import AgentState


class PythonChatbot:
    def __init__(self):
        self.reset_chat()
        self.graph = self.create_graph()

    def create_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("agent", call_model)
        workflow.add_node("tools", call_tools)

        workflow.add_conditional_edges("agent", route_to_tools)
        workflow.add_edge("tools", "agent")

        workflow.set_entry_point("agent")

        return workflow.compile()

    def user_sent_message(
        self,
        user_query: str,
        input_data: List[InputData],
    ):
        starting_image_paths_set = set(
            sum(self.output_image_paths.values(), [])
        )

        input_state = {
            "messages": self.chat_history
            + [HumanMessage(content=user_query)],
            "output_image_paths": list(starting_image_paths_set),
            "input_data": input_data,

            # Initialisation explicite pour éviter
            # current_variables=None avec certaines versions de LangGraph
            "current_variables": {},
            "intermediate_outputs": [],
        }

        result = self.graph.invoke(
            input_state,
            {"recursion_limit": 25},
        )

        self.chat_history = result["messages"]

        new_image_paths = (
            set(result.get("output_image_paths") or [])
            - starting_image_paths_set
        )

        self.output_image_paths[
            len(self.chat_history) - 1
        ] = list(new_image_paths)

        if result.get("intermediate_outputs"):
            self.intermediate_outputs.extend(
                result["intermediate_outputs"]
            )

    def reset_chat(self):
        self.chat_history = []
        self.intermediate_outputs = []
        self.output_image_paths = {}