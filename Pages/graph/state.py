import operator
from typing import Sequence, TypedDict, Annotated, List
from langchain_core.messages import BaseMessage
from Pages.data_models import InputData
from typing import Dict


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    input_data: Annotated[List[InputData], operator.add]
    intermediate_outputs: Annotated[List[dict], operator.add]
    current_variables: dict
    output_image_paths: Annotated[List[str], operator.add]

