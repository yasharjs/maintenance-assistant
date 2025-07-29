from unittest import result
from langgraph.graph import StateGraph
from typing import Optional, TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages
from backend.rag.test_rag import llm, rewrite_query 
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage

class State(TypedDict):
    messages: Annotated[list, add_messages]
    route: str
    rewritten: str

routing_descriptions = {
    "mechanical_drawing": (
        "Use this route for requests involving diagram illustrations, CAD drawings, BOMs, part numbers, component revisions, or references to drawing pages. "
        "Examples: locating a valve in the drawing set, identifying drawing numbers, part compatibility across revisions."
    ),
    "troubleshooting": (
        "Use this route for technical issues, alarms, calibration steps, faults, and setup procedures. "
        "Includes Moog servo valves, Rexroth pumps, amplifier cards, wiring diagnostics, jumper settings, and tuning."
    ),
    "general": (
        "Use this route for greetings, vague questions, or general inquiries not referencing machinery, setup, or technical drawings."
    ),
}

class RouteResponse(BaseModel):
    route: Literal["mechanical_drawing", "troubleshooting", "general", "uncertain"] = Field(
        ..., description="The best category match for the user's query."
    )
    follow_up: str = Field(
        default="", description="Follow-up question to ask if the route is uncertain."
    )

router_llm = llm.with_structured_output(RouteResponse)

def router_node(state: State) -> dict:
    history = state["messages"][-5:]
    query = history[-1].content
    options = "\n".join([f"{k}: {v}" for k, v in routing_descriptions.items()])

    # Build full message list
    message_list = [SystemMessage(content=(
        "You are a routing agent. Your job is to decide which category best matches the user's query, using the following routing options:\n\n"
        f"{options}\n\n"
        "If the user's query is vague, ambiguous, or underspecified — for example, it contains only a single term or lacks clear intent — then:\n"
        "- Set `route` to 'uncertain'\n"
        "- Provide a helpful clarifying `follow_up` question asking the user to be more specific.\n\n"
        "Only assign a route (mechanical_drawing, troubleshooting, general) if you are confident you understand the user's intent from the query and message history.\n\n"
        "Return structured output with two fields:\n"
        "- `route`: one of 'mechanical_drawing', 'troubleshooting', 'general', or 'uncertain'\n"
        "- `follow_up`: optional clarifying question if route is 'uncertain'"
    ))] + history

    result = router_llm.invoke(message_list)
    if result.route != "uncertain":
        return {"route": result.route}
    else:
        return {
            "messages": [{"role": "assistant", "content": result.follow_up}],
            "route": "uncertain",
        }

# ── Rewrite Node ────────────────────────────────────────────────────────
def rewriter_node(state: State) -> dict:
    last_message = state["messages"][-1]
    query = last_message.content if hasattr(last_message, "content") else last_message["content"]
    prompt = (
        "Rewrite the following query to be clearer and more specific, preserving technical accuracy:\n\n"
        f"{query}"
    )
    result = llm.invoke([{"role": "user", "content": prompt}])
    return {"rewritten": result.content.strip()}

def passthrough_node(state: State) -> dict:
    return {"rewritten": state["messages"][-1]["content"]}

# ── Graph Construction ──────────────────────────────────────────────────
def build_query_router_graph():
    graph = StateGraph(State)
    graph.add_node("router", router_node)
    # graph.add_node("rewriter", rewriter_node)
    # graph.add_node("passthrough", passthrough_node)

    graph.set_entry_point("router")
    graph.set_finish_point("router") 
    # graph.add_conditional_edges(
    #     "router",
    #     lambda state: "rewriter" if state["route"] in {"mechanical_drawing", "troubleshooting"} else "passthrough",
    #     {"rewriter": "rewriter", "passthrough": "passthrough"}
    # )
    # graph.set_finish_point("rewriter")
    # graph.set_finish_point("passthrough")

    return graph.compile()

query_router_graph = build_query_router_graph()