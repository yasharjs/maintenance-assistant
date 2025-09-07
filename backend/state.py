from typing_extensions import TypedDict, Annotated, List, Sequence, Optional
from langgraph.graph.message import add_messages

import operator
from typing_extensions import TypedDict, Annotated, List, Sequence
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]
    route: str
    rewritten: str
    pages: List[int]
    hits: Optional[list]
    context: Optional[str]
    citations: Optional[List[dict]]


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


class ReasoningInputState(TypedDict):
    reasoning_messages: Annotated[List[BaseMessage], add_messages]
    tool_call_iterations: int
    citations: Optional[List[dict]]

class ReasoningOutputState(TypedDict):
    final_answer: str
    citations: Optional[List[dict]]