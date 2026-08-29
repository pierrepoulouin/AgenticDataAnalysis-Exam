from typing import Any, Protocol

from backend.app.agent.state import AgentState


class Planner(Protocol):
    def __call__(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        ...


class MockPlanner:
    """
    Planner déterministe utilisé pour les tests.

    Il simule :
    Reason -> Tool -> Observe -> Final Answer
    sans appeler de LLM externe.
    """

    def __call__(
        self,
        state: AgentState,
    ) -> dict[str, Any]:

        tool_result = state.get("tool_result")

        if tool_result is None:
            return {
                "thought": (
                    "Je dois calculer le total des ventes "
                    "du dataset disponible."
                ),
                "tool_name": "execute_statistical_analysis",
                "python_code": """
total_sales = dataset_1["ventes"].sum()
print("Total :", total_sales)
""",
                "final_answer": None,
            }

        total_sales = state.get(
            "current_variables",
            {},
        ).get("total_sales")

        return {
            "thought": (
                "Le calcul est terminé, je peux répondre."
            ),
            "tool_name": None,
            "python_code": None,
            "final_answer": (
                f"Le total des ventes est de {total_sales}."
            ),
        }