from typing import List, Optional, Annotated
import operator
from langgraph.graph import MessagesState
from pydantic import BaseModel, Field

class State(MessagesState):
    route: str
    rewritten: str
    pages: Annotated[List[int], operator.add]      # accumulate page hits
    hits:  Annotated[List[dict], operator.add]     # accumulate retrieval hits
    context: Optional[str]

class AgentInputState(MessagesState):
    """Public entry envelope: only incoming chat messages."""
    pass


# ===== STRUCTURED OUTPUT SCHEMAS =====

class ClarifyWithUser(BaseModel):
    """Schema for user clarification decision and questions."""
    
    need_clarification: bool = Field(
        description="Whether the user needs to be asked a clarifying question.",
    )
    question: str = Field(
        description="A question to ask the user to clarify the report scope",
    )
    verification: str = Field(
        description="Verify message that we will start research after the user has provided the necessary information.",
    )

class ResearchQuestion(BaseModel):
    """Schema for structured research brief generation."""
    
    research_brief: str = Field(
        description="A research question that will be used to guide the research.",
    )