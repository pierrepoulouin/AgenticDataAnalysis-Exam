import json
import os
from typing import Any, Protocol

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
)

from backend.app.agent.state import (
    AgentState,
)


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
    Planner déterministe pour les tests locaux.

    Il permet de tester toute l'architecture
    sans consommer d'API LLM.
    """

    def _get_dataset(
        self,
        state: AgentState,
    ):
        variables = state.get(
            "current_variables",
            {},
        )

        dataset_names = sorted(
            name
            for name in variables
            if name.startswith(
                "dataset_"
            )
        )

        if not dataset_names:
            return None, None

        dataset_name = (
            dataset_names[0]
        )

        return (
            dataset_name,
            variables[dataset_name],
        )

    def __call__(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        tool_result = state.get(
            "tool_result"
        )

        user_query = state.get(
            "user_query",
            "",
        ).lower()

        (
            dataset_name,
            dataframe,
        ) = self._get_dataset(
            state
        )

        if dataset_name is None:
            return {
                "thought": (
                    "Aucun dataset n'est "
                    "disponible."
                ),
                "tool_name": None,
                "python_code": None,
                "final_answer": (
                    "Aucun dataset n'est "
                    "associé à cette session."
                ),
            }

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

        if tool_result is None:
            columns = list(
                dataframe.columns
            )

            numeric_columns = list(
                dataframe.select_dtypes(
                    include="number"
                ).columns
            )

            if wants_visualization:
                if (
                    "mois" in columns
                    and "ventes" in columns
                ):
                    x_column = "mois"
                    y_column = "ventes"

                    python_code = f"""
fig = px.bar(
    {dataset_name},
    x={x_column!r},
    y={y_column!r},
    title="Ventes par mois",
)
"""

                elif (
                    columns
                    and numeric_columns
                ):
                    x_column = columns[0]
                    y_column = (
                        numeric_columns[0]
                    )

                    python_code = f"""
fig = px.bar(
    {dataset_name},
    x={x_column!r},
    y={y_column!r},
    title="Visualisation des données",
)
"""

                elif columns:
                    x_column = columns[0]

                    python_code = f"""
fig = px.histogram(
    {dataset_name},
    x={x_column!r},
    title="Distribution des données",
)
"""

                else:
                    return {
                        "thought": (
                            "Le dataset ne contient "
                            "aucune colonne."
                        ),
                        "tool_name": None,
                        "python_code": None,
                        "final_answer": (
                            "Le dataset est vide."
                        ),
                    }

                return {
                    "thought": (
                        "Créer une visualisation "
                        "du dataset."
                    ),
                    "tool_name": (
                        "execute_visualization"
                    ),
                    "python_code": python_code,
                    "final_answer": None,
                }

            if (
                "ventes"
                in numeric_columns
            ):
                target_column = (
                    "ventes"
                )

            elif numeric_columns:
                target_column = (
                    numeric_columns[0]
                )

            else:
                return {
                    "thought": (
                        "Aucune colonne numérique "
                        "n'est disponible."
                    ),
                    "tool_name": None,
                    "python_code": None,
                    "final_answer": (
                        "Je ne trouve aucune "
                        "colonne numérique à analyser."
                    ),
                }

            return {
                "thought": (
                    "Calculer la somme d'une "
                    "colonne numérique."
                ),
                "tool_name": (
                    "execute_statistical_analysis"
                ),
                "python_code": f"""
analysis_value = {dataset_name}[{target_column!r}].sum()
print("Total :", analysis_value)
""",
                "final_answer": None,
            }

        if (
            tool_result.get("tool")
            == "execute_visualization"
        ):
            return {
                "thought": (
                    "La visualisation "
                    "a été créée."
                ),
                "tool_name": None,
                "python_code": None,
                "final_answer": (
                    "Voici la visualisation "
                    "des données."
                ),
            }

        analysis_value = state.get(
            "current_variables",
            {},
        ).get(
            "analysis_value"
        )

        return {
            "thought": (
                "Le calcul est terminé."
            ),
            "tool_name": None,
            "python_code": None,
            "final_answer": (
                f"Le résultat du calcul "
                f"est de {analysis_value}."
            ),
        }


class LLMPlanner:
    """
    Planner utilisant un vrai LLM lorsque
    AGENT_PLANNER=llm.
    """

    def __init__(self) -> None:
        from langchain_openai import (
            ChatOpenAI,
        )

        model_name = os.getenv(
            "OPENAI_MODEL"
        )

        if not model_name:
            raise RuntimeError(
                "OPENAI_MODEL must be "
                "configured when "
                "AGENT_PLANNER=llm"
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
                "tool": tool_result.get(
                    "tool"
                ),
                "stdout": tool_result.get(
                    "stdout"
                ),
            }

        system_prompt = """
You are a data analysis agent.

You may use only these tools:
- execute_data_cleaning
- execute_statistical_analysis
- execute_visualization

Available Python libraries:
pd, np, px, go, stats, sklearn.

Do not write import statements.

Return ONLY valid JSON.

For a tool action:
{
  "thought": "short rationale",
  "tool_name": "allowed tool",
  "python_code": "python code",
  "final_answer": null
}

For a final response:
{
  "thought": "short rationale",
  "tool_name": null,
  "python_code": null,
  "final_answer": "answer"
}

Do not invent columns or results.
"""

        human_prompt = json.dumps(
            {
                "user_query": (
                    user_query
                ),
                "data_context": (
                    data_context
                ),
                "observation": (
                    observation
                ),
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
                "Planner returned "
                "invalid JSON"
            ) from exc

        tool_name = decision.get(
            "tool_name"
        )

        final_answer = decision.get(
            "final_answer"
        )

        if tool_name is not None:
            if (
                tool_name
                not in ALLOWED_TOOLS
            ):
                raise ValueError(
                    "Planner selected "
                    "forbidden tool: "
                    f"{tool_name}"
                )

            if not decision.get(
                "python_code"
            ):
                raise ValueError(
                    "Planner selected a "
                    "tool without Python code"
                )

        elif not final_answer:
            raise ValueError(
                "Planner returned neither "
                "tool nor final answer"
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
    planner_type = os.getenv(
        "AGENT_PLANNER",
        "mock",
    ).lower()

    if planner_type == "mock":
        return MockPlanner()

    if planner_type == "llm":
        return LLMPlanner()

    raise ValueError(
        "Unsupported AGENT_PLANNER: "
        f"{planner_type}"
    )