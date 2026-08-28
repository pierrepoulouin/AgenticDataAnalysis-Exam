import os
import pickle
import sys
import uuid
from io import StringIO
from typing import Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sklearn

from langchain_core.tools import tool


# ATTENTION :
# Ceci est volontairement conservé comme dans le POC.
# Cette variable globale est justement un des problèmes
# d'isolation multi-utilisateurs que l'examen demande d'identifier.
persistent_vars = {}


@tool
def complete_python_task(
    thought: str,
    python_code: str,
    graph_state: dict = None,
) -> Tuple[str, dict]:
    """
    Completes a python task.

    Args:
        thought:
            Internal thought about the next action to be taken.

        python_code:
            Python code to execute for analysis,
            transformation or visualization.

        graph_state:
            Current LangGraph state.
            It is injected manually by call_tools().
    """

    graph_state = graph_state or {}

    current_variables = (
        graph_state.get("current_variables") or {}
    )

    input_data = graph_state.get("input_data") or []

    # Charger les datasets CSV dans l'environnement Python.
    for input_dataset in input_data:
        if (
            input_dataset.variable_name
            not in current_variables
        ):
            current_variables[
                input_dataset.variable_name
            ] = pd.read_csv(
                input_dataset.data_path
            )

    output_directory = "images/plotly_figures/pickle"

    os.makedirs(
        output_directory,
        exist_ok=True,
    )

    existing_image_files = set(
        os.listdir(output_directory)
    )

    # Sauvegarde de stdout avant redirection.
    old_stdout = sys.stdout
    captured_stdout = StringIO()

    try:
        sys.stdout = captured_stdout

        # Environnement d'exécution Python.
        #
        # IMPORTANT :
        # globals().copy() est précisément une faiblesse
        # de sécurité du POC à analyser pendant l'examen.
        exec_globals = globals().copy()

        exec_globals.update(persistent_vars)
        exec_globals.update(current_variables)

        # Convention utilisée par le prompt :
        # les graphiques Plotly doivent être ajoutés ici.
        exec_globals["plotly_figures"] = []

        # Exécution du code produit par le LLM.
        exec(
            python_code,
            exec_globals,
        )

        output = captured_stdout.getvalue()

        # Sauvegarder les nouvelles variables Python.
        new_variables = {
            key: value
            for key, value in exec_globals.items()
            if key not in globals()
            and key != "__builtins__"
        }

        persistent_vars.update(new_variables)

        updated_state = {
            "intermediate_outputs": [
                {
                    "thought": thought,
                    "code": python_code,
                    "output": output,
                }
            ],
            "current_variables": persistent_vars,
        }

        # Sauvegarde des visualisations Plotly.
        figures = exec_globals.get(
            "plotly_figures",
            [],
        )

        for figure in figures:
            pickle_filename = (
                f"{uuid.uuid4()}.pickle"
            )

            pickle_path = os.path.join(
                output_directory,
                pickle_filename,
            )

            with open(
                pickle_path,
                "wb",
            ) as file:
                pickle.dump(
                    figure,
                    file,
                )

        new_image_files = [
            file
            for file in os.listdir(output_directory)
            if file not in existing_image_files
        ]

        if new_image_files:
            updated_state[
                "output_image_paths"
            ] = new_image_files

        # Éviter que les figures précédentes soient
        # considérées comme nouvelles au prochain appel.
        persistent_vars["plotly_figures"] = []

        return output, updated_state

    except Exception as exc:
        output = captured_stdout.getvalue()

        error_message = str(exc)

        if output:
            full_output = (
                f"{output}\nError: {error_message}"
            )
        else:
            full_output = error_message

        return (
            full_output,
            {
                "intermediate_outputs": [
                    {
                        "thought": thought,
                        "code": python_code,
                        "output": full_output,
                    }
                ]
            },
        )

    finally:
        # Très important :
        # stdout doit être restauré même si exec() plante.
        sys.stdout = old_stdout