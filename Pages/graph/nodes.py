import os
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    AIMessage,
    ToolMessage,
    HumanMessage,
)
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import ToolInvocation, ToolExecutor

from .state import AgentState
from .tools import complete_python_task


# Le POC attend que OPENAI_API_KEY soit déjà
# présente dans les variables d'environnement.
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
)

tools = [complete_python_task]

model = llm.bind_tools(tools)
tool_executor = ToolExecutor(tools)


# Chargement du prompt principal
prompt_path = os.path.join(
    os.path.dirname(__file__),
    "../prompts/main_prompt.md",
)

with open(prompt_path, "r") as file:
    prompt = file.read()


chat_template = ChatPromptTemplate.from_messages(
    [
        ("system", prompt),
        ("placeholder", "{messages}"),
    ]
)

model = chat_template | model


def create_data_summary(state: AgentState) -> str:
    """
    Construit un résumé des datasets et variables actuellement
    disponibles pour l'agent.
    """

    summary = ""
    variables = []

    input_data = state.get("input_data") or []

    for data in input_data:
        variables.append(data.variable_name)

        summary += f"\n\nVariable: {data.variable_name}\n"
        summary += f"Description: {data.data_description}"

    # Certaines versions de LangGraph créent la clé
    # avec la valeur None. On la normalise donc en dict vide.
    current_variables = state.get("current_variables") or {}

    remaining_variables = [
        variable
        for variable in current_variables
        if variable not in variables
    ]

    for variable in remaining_variables:
        summary += f"\n\nVariable: {variable}"

    return summary


def route_to_tools(
    state: AgentState,
) -> Literal["tools", "__end__"]:
    """
    Si le dernier message du modèle contient un appel d'outil,
    le workflow est envoyé vers le noeud 'tools'.

    Sinon, le workflow se termine.
    """

    messages = state.get("messages") or []

    if not messages:
        raise ValueError(
            f"No messages found in input state: {state}"
        )

    ai_message = messages[-1]

    if (
        hasattr(ai_message, "tool_calls")
        and ai_message.tool_calls
    ):
        return "tools"

    return "__end__"


def call_model(state: AgentState):
    """
    Appel du LLM avec les informations sur les datasets
    actuellement disponibles.
    """

    current_data_template = (
        "The following data is available:\n"
        "{data_summary}"
    )

    current_data_message = HumanMessage(
        content=current_data_template.format(
            data_summary=create_data_summary(state)
        )
    )

    messages = state.get("messages") or []

    # On construit une copie plutôt que de modifier directement
    # le state reçu par LangGraph.
    model_state = dict(state)

    model_state["messages"] = (
        [current_data_message] + list(messages)
    )

    llm_output = model.invoke(model_state)

    return {
        "messages": [llm_output],
        "intermediate_outputs": [
            current_data_message.content
        ],
    }


def call_tools(state: AgentState):
    """
    Exécute les appels d'outils demandés par le LLM.
    """

    messages = state.get("messages") or []

    if not messages:
        raise ValueError("No messages available for tool call")

    last_message = messages[-1]

    tool_invocations = []

    if (
        isinstance(last_message, AIMessage)
        and getattr(last_message, "tool_calls", None)
    ):
        tool_invocations = [
            ToolInvocation(
                tool=tool_call["name"],
                tool_input={
                    **tool_call["args"],

                    # L'état est injecté manuellement.
                    # On n'utilise donc pas InjectedState,
                    # incompatible avec cette version de LangGraph.
                    "graph_state": state,
                },
            )
            for tool_call in last_message.tool_calls
        ]

    responses = tool_executor.batch(
        tool_invocations,
        return_exceptions=True,
    )

    tool_messages = []
    state_updates = {}

    for tool_call, response in zip(
        last_message.tool_calls,
        responses,
    ):
        if isinstance(response, Exception):
            raise response

        message, updates = response

        tool_messages.append(
            ToolMessage(
                content=str(message),
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )

        if updates:
            state_updates.update(updates)

    state_updates["messages"] = tool_messages

    return state_updates