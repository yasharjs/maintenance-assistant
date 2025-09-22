from typing_extensions import TypedDict, Annotated, List, Sequence, Optional
from langgraph.graph.message import add_messages

import operator
from typing_extensions import TypedDict, Annotated, List, Literal, NotRequired
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

class Todo(TypedDict):
    """A structured task item for tracking progress through complex workflows.

    Attributes:
        content: Short, specific description of the task
        status: Current state - pending, in_progress, or completed
    """

    content: str
    status: Literal["pending", "in_progress", "completed"]

class ReasoningInputState(TypedDict):
    reasoning_messages: Annotated[List[BaseMessage], add_messages]
    tool_call_iterations: int
    citations: Optional[List[dict]]
    todos: NotRequired[list[Todo]]

class ReasoningOutputState(TypedDict):
    final_answer: str
    citations: Optional[List[dict]]