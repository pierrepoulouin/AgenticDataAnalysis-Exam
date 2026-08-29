import json
import os
from typing import Any, Protocol

from langchain_core.messages import HumanMessage, SystemMessage

from backend.app.agent.state import AgentState


ALLOWED_TOOLS = {
    "execute_data_cleaning",
    "execute_statistical_analysis",
    "execute_visualization",
}


class Planner(Protocol):
    def __call__(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        ...


class MockPlanner:
    """
    Planner déterministe utilisé pour les tests locaux.

    Aucun appel à une API LLM externe n'est effectué.
    """

    def __call__(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        tool_result = state.get("tool_result")

        user_query = state.get(
            "user_query",
            "",
        ).lower()

        wants_visualization = any(
            keyword in user_query
            for keyword in (
                "graphique",
                "visualisation",
                "visualise",
                "diagramme",
                "barres",
            )
        )

        # ---------------------------------------------------------------
        # Premier passage : Reason -> choix d'un outil
        # ---------------------------------------------------------------

        if tool_result is None:
            if wants_visualization:
                return {
                    "thought": (
                        "Créer un graphique des ventes "
                        "par mois."
                    ),
                    "tool_name": "execute_visualization",
                    "python_code": """
fig = px.bar(
    dataset_1,
    x="mois",
    y="ventes",
    title="Ventes 2026",
)
""",
                    "final_answer": None,
                }

            return {
                "thought": (
                    "Calculer le total des ventes "
                    "avec l'outil statistique."
                ),
                "tool_name": "execute_statistical_analysis",
                "python_code": """
total_sales = dataset_1["ventes"].sum()
print("Total :", total_sales)
""",
                "final_answer": None,
            }

        # ---------------------------------------------------------------
        # Deuxième passage : Observation -> réponse finale
        # ---------------------------------------------------------------

        if (
            tool_result.get("tool")
            == "execute_visualization"
        ):
            return {
                "thought": (
                    "La visualisation a été créée."
                ),
                "tool_name": None,
                "python_code": None,
                "final_answer": (
                    "Voici la visualisation "
                    "des ventes par mois."
                ),
            }

        total_sales = state.get(
            "current_variables",
            {},
        ).get("total_sales")

        return {
            "thought": (
                "Le résultat nécessaire "
                "est disponible."
            ),
            "tool_name": None,
            "python_code": None,
            "final_answer": (
                f"Le total des ventes est "
                f"de {total_sales}."
            ),
        }


class LLMPlanner:
    """
    Planner utilisant un LLM externe.

    Le provider n'est utilisé que lorsque
    AGENT_PLANNER=llm.
    """

    def __init__(self) -> None:
        from langchain_openai import ChatOpenAI

        model_name = os.getenv("OPENAI_MODEL")

        if not model_name:
            raise RuntimeError(
                "OPENAI_MODEL must be configured "
                "when AGENT_PLANNER=llm"
            )

        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0,
        )

    def __call__(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        user_query = state.get(
            "user_query",
            "",
        )

        data_context = state.get(
            "data_context",
            {},
        )

        tool_result = state.get(
            "tool_result"
        )

        observation = None

        if tool_result:
            observation = {
                "tool": tool_result.get("tool"),
                "stdout": tool_result.get("stdout"),
            }

        system_prompt = """
You are a data analysis agent.

You may use only these tools:
- execute_data_cleaning
- execute_statistical_analysis
- execute_visualization

Available Python libraries are already exposed:
pd, np, px, go, stats, sklearn.

Do not write import statements.

Return ONLY valid JSON.

If an action is required, return:
{
  "thought": "short action rationale",
  "tool_name": "one allowed tool",
  "python_code": "python code",
  "final_answer": null
}

If the task is complete, return:
{
  "thought": "short completion rationale",
  "tool_name": null,
  "python_code": null,
  "final_answer": "answer for the user"
}

Do not invent dataset columns or results.
Use observations from executed tools.
"""

        human_prompt = json.dumps(
            {
                "user_query": user_query,
                "data_context": data_context,
                "observation": observation,
            },
            default=str,
            ensure_ascii=False,
        )

        response = self.llm.invoke(
            [
                SystemMessage(
                    content=system_prompt
                ),
                HumanMessage(
                    content=human_prompt
                ),
            ]
        )

        try:
            decision = json.loads(
                response.content
            )

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Planner returned invalid JSON"
            ) from exc

        tool_name = decision.get(
            "tool_name"
        )

        final_answer = decision.get(
            "final_answer"
        )

        if tool_name is not None:
            if tool_name not in ALLOWED_TOOLS:
                raise ValueError(
                    "Planner selected forbidden "
                    f"tool: {tool_name}"
                )

            if not decision.get(
                "python_code"
            ):
                raise ValueError(
                    "Planner selected a tool "
                    "without Python code"
                )

        elif not final_answer:
            raise ValueError(
                "Planner returned neither "
                "a tool nor a final answer"
            )

        return {
            "thought": decision.get(
                "thought",
                "",
            ),
            "tool_name": tool_name,
            "python_code": decision.get(
                "python_code"
            ),
            "final_answer": final_answer,
        }


def get_planner() -> Planner:
    """
    Sélectionne le planner à partir
    de la configuration d'environnement.
    """

    planner_type = os.getenv(
        "AGENT_PLANNER",
        "mock",
    ).lower()

    if planner_type == "mock":
        return MockPlanner()

    if planner_type == "llm":
        return LLMPlanner()

    raise ValueError(
        f"Unsupported AGENT_PLANNER: "
        f"{planner_type}"
    )