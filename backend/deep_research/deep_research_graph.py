from langgraph.graph import StateGraph, END, START
from backend.state import State, AgentInputState, ClarifyWithUser, ResearchQuestion
from backend.deep_research.prompt import clarify_with_user_instructions, transform_messages_into_research_topic_prompt
from langgraph.checkpoint.memory import InMemorySaver
from typing import Literal
from langgraph.types import Command 
from backend.client import get_llm
from langchain.schema import SystemMessage, HumanMessage, get_buffer_string, AIMessage
from datetime import datetime

llm = get_llm()

def get_today_str() -> str:
    dt = datetime.now()
    return f"{dt:%a} {dt:%b} {dt.day}, {dt:%Y}"

def clarify_with_user(state: State) -> Command:
    """
    Determine if the user's request contains sufficient information to proceed with research.
    
    Uses structured output to make deterministic decisions and avoid hallucination.
    Routes to either research brief generation or ends with a clarification question.
    """
    # Set up structured output model
    structured_output_model = llm.with_structured_output(ClarifyWithUser)

    # Invoke the model with clarification instructions
    response = structured_output_model.invoke([
        HumanMessage(content=clarify_with_user_instructions.format(
            messages=get_buffer_string(messages=state["messages"]), 
            date=get_today_str()
        ))
    ])
    
    # Route based on clarification need
    if response.need_clarification:
        return Command(
            goto=END, 
            update={"messages": [AIMessage(content=response.question)]}
        )
    else:
        return Command(
            goto="write_research_brief", 
            update={"messages": [AIMessage(content=response.verification)]}
        )


def write_research_brief(state: State):
    """
    Transform the conversation history into a comprehensive research brief.
    
    Uses structured output to ensure the brief follows the required format
    and contains all necessary details for effective research.
    """
    # Set up structured output model
    structured_output_model = llm.with_structured_output(ResearchQuestion)
    
    # Generate research brief from conversation history
    response = structured_output_model.invoke([
        HumanMessage(content=transform_messages_into_research_topic_prompt.format(
            messages=get_buffer_string(state.get("messages", [])),
            date=get_today_str()
        ))
    ])
    
    # Update state with generated research brief and pass it to the supervisor
    return {
        "research_brief": response.research_brief,
        "supervisor_messages": [HumanMessage(content=f"{response.research_brief}.")]
    }

deep_researcher_builder = StateGraph(State, input_schema=AgentInputState)
deep_researcher_builder.add_node("clarify_with_user", clarify_with_user)
deep_researcher_builder.add_node("write_research_brief", write_research_brief)

deep_researcher_builder.add_edge(START, "clarify_with_user")
deep_researcher_builder.add_edge("write_research_brief", END)

checkpointer = InMemorySaver()                     # lives only in-process
scope_research = deep_researcher_builder.compile(checkpointer=checkpointer)

__all__ = ["scope_research", "deep_researcher_builder"]