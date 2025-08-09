from typing import List, TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]
    route: str
    rewritten: str
    pages: List[int]
    hits: Optional[list]
    context: Optional[str]