import asyncio
from unittest import result
from langgraph.graph import StateGraph
from typing import Dict, Any, Tuple, Optional, Literal
from langgraph.graph.message import add_messages
from backend.rag.test_rag import llm
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import spacy
import uuid, time
from types import SimpleNamespace
from langgraph.types import StreamWriter 
nlp = spacy.load("en_core_web_sm")
from backend.custom_langgraph.troubleshoot_graph import State
import re
from langchain_core.prompts import ChatPromptTemplate ,  MessagesPlaceholder


few_shots = [
    # Single-turn examples
    HumanMessage(content="stroke manifold assembly drawing item numbers"),
    AIMessage(content="mechanical_drawing"),

    HumanMessage(content="servo valve not working?"),
    AIMessage(content="troubleshooting"),

    HumanMessage(content="explain what is a servo valve?"),
    AIMessage(content="troubleshooting"),

    HumanMessage(content="what are the assembly parts of a servo valve"),
    AIMessage(content="troubleshooting"),
    
    # HumanMessage(content="what are the main components of a filter o-ring "),
    # AIMessage(content="troubleshooting"),

    HumanMessage(content="can you give me a list of valve drawings available?"),
    AIMessage(content="mechanical_drawing"),

    HumanMessage(content="green enabled light at the front of card is off, what do I do?"),
    AIMessage(content="troubleshooting"),

    HumanMessage(content="what are the components of a typical servo "),
    AIMessage(content="troubleshooting"),

    # Multi-turn: follow-up question continues same context
    HumanMessage(content="what causes not mechanically centered fault?"),
    AIMessage(content="troubleshooting"),
    HumanMessage(content="what about step 2?"),
    AIMessage(content="troubleshooting"),

    HumanMessage(content="show me stroke manifold assembly drawing"),
    AIMessage(content="mechanical_drawing"),
    HumanMessage(content="can you zoom into item 6?"),
    AIMessage(content="mechanical_drawing"),

    # Multi-turn: new query switches context
    HumanMessage(content="my pump isn’t calibrating properly"),
    AIMessage(content="troubleshooting"),
    HumanMessage(content="can you show me the wiring diagram for the pump area?"),
    AIMessage(content="mechanical_drawing"),

    # Vague user question relying on previous context
    HumanMessage(content="explain briefly how to calibrate"),
    AIMessage(content="troubleshooting"),
    HumanMessage(content="and what if it fails?"),
    AIMessage(content="troubleshooting"),
]


routing_descriptions = {
    "mechanical_drawing": (
        "Route queries asking for static info: part numbers, BOM entries, drawing locations, or diagram details. "
        "Intent is to find or describe document content, not fix issues."
    ),
    "troubleshooting": (
        "Route queries about operational problems: faults, alarms, calibration, diagnostics, or performance. "
        "Intent is to solve issues or adjust systems, not just locate parts."
    ),
    "general": (
        "Route greetings, chit-chat"
    )
}

class RouteResponse(BaseModel):
    route: Literal["mechanical_drawing", "troubleshooting", "general", "uncertain"] = Field(
        ..., description="The best category match for the user's query."
    )
    follow_up: str = Field(
        default="", description="Follow-up question to ask if the route is uncertain."
    )

router_llm = llm.with_structured_output(RouteResponse)

def normalize_query_to_lemmas(query: str) -> list[str]:
    doc = nlp(query.lower())
    return [token.lemma_ for token in doc if not token.is_stop and token.is_alpha]

# --- Normalization ---
_word = re.compile(r"[A-Za-z0-9]+")

# Normalize: lowercase, remove punctuation, extra spaces
def normalize(text: str) -> str:
    return " ".join(_word.findall(text.lower()))

# Tokenize: simple whitespace split 
def tokenize(text: str):
    return normalize(text).split()

# --- Deterministic keyword sets (high-precision) ---
# keep these tight and explicit; expand gradually based on failures
TROUBLE_HARD = tuple([
    "breakout box", "break out box",
    "pinout", "pin value", "pin values", "pin", "pins",
    "ready signal", "valve ready", "enable",
    "fault", "alarm", "error",
    "voltage", "values", "reading", "measure",
    "proxy", "pilot unlock",
])

DRAWING_HARD = tuple([
    "drawing", "diagram", "schematic",
    "bom", "bill of materials",
    "item number", "position", "item position",
    "exploded", "rev", "revision",
    "zoom", "zoom into", "zoom in",
])

SHORT_UTTERANCE_TOKENS = 2  # guard: 1-2 tokens w/out hard keywords => uncertain


def hit_any(text: str, phrases: Tuple[str, ...]) -> bool:
    t = " " + normalize(text) + " "
    for ph in phrases:
        if " " + normalize(ph) + " " in t:
            return True
    return False

def deterministic_gate(query: str) -> Optional[str]:
    # 1) Short utterance guard
    toks = tokenize(query)
    if len(toks) <= SHORT_UTTERANCE_TOKENS:
        # unless it clearly mentions a drawing or troubleshooting hard keyword
        if hit_any(query, DRAWING_HARD):
            return "mechanical_drawing"
        if hit_any(query, TROUBLE_HARD):
            return "troubleshooting"
        return "uncertain"

    # 2) High-precision keyword overrides
    if hit_any(query, TROUBLE_HARD):
        return "troubleshooting"

    if hit_any(query, DRAWING_HARD):
        # only if it doesn't also strongly suggest troubleshooting
        if not hit_any(query, TROUBLE_HARD):
            return "mechanical_drawing"

    return None  # let LLM decide
async def _hybrid_route_with_followup(query: str, history_msgs):
    # 1) deterministic gates first
    det = deterministic_gate(query)
    if det in {"troubleshooting", "mechanical_drawing", "general"}:
        print(f"Deterministic route for '{query}': {det}")
        return {"route": det, "follow_up": ""}

    # 2) LLM structured fallback
    llm_resp = await classify_structured(query, history_msgs)
    route = llm_resp["route"]
    follow_up = llm_resp["follow_up"]

    # 3) Tie-breaker: if LLM says uncertain but we see a clear domain hint
    if route == "uncertain":
        print(f"LLM uncertain for '{query}', checking keywords...")
        if hit_any(query, TROUBLE_HARD):
            return {"route": "troubleshooting", "follow_up": ""}
        if hit_any(query, DRAWING_HARD):
            return {"route": "mechanical_drawing", "follow_up": ""}
        # still uncertain → keep LLM follow-up (and ensure there is one)
        if not follow_up:
            follow_up = "Can you clarify if you want electrical pin/values or drawing/BOM details?"
        return {"route": "uncertain", "follow_up": follow_up}

    # Normal case
    return {"route": route, "follow_up": ""}

async def classify_structured(query: str, history_msgs):
    """
    Calls the LLM and returns a RouteResponse-like dict:
      {"route": "...", "follow_up": "..."}
    """
    # We’ll reuse your existing few_shots and pass a compact history
    prompt_msgs = [
        SystemMessage(content=(
            "You are a routing agent for an enterprise maintenance assistant. "
            "Your task is to classify the current user query into one of the following categories:\n"
            "- mechanical_drawing: for diagrams, drawings, drawing item position, drawing item position number, item numbers,BOMs\n"
            "- troubleshooting: for issues, alarms, errors, calibration, fixing steps, diagnostic procedures, electrical values, pin/pinout, breakout box, alarms/faults, enable/ready signals,\n"
            "If a query mentions components or parts but does not clearly request a drawing, list, or part number, classify as 'troubleshooting'.\n\n"
            "- uncertain: if the intent is unclear or ambiguous\n\n"
            "provide a helpful follow-up question.if the query is uncertain, to clarify the user's intent.\n\n"
            "- general: for greetings, chit-chat, or unrelated queries\n\n"
            "Use conversation history (last 5 messages) to help resolve vague follow-ups like 'what about step 2?'. "
            "Continue the previous intent unless there is a clear switch in topic.\n\n"
            "Return a JSON object with fields: route, follow_up." 
        ))
    ] + few_shots + history_msgs + [HumanMessage(content=query)]

    resp = await router_llm.ainvoke(prompt_msgs)  # RouteResponse
    # `resp` is a pydantic object; make it dict-like
    return {"route": resp.route, "follow_up": resp.follow_up or ""}

async def router_node(state: State, writer: StreamWriter) -> dict:
    # Use last up-to-5 messages as history for context continuity
    history_msgs = state["messages"][-5:]
    last_msg = state["messages"][-1]
    query = last_msg.content.strip().lower()

    # Run the hybrid router (deterministic → LLM) and get follow-up support
    result = await _hybrid_route_with_followup(query, history_msgs)
    route = result["route"]
    follow_up = result.get("follow_up", "")
    print(f"Routing query: '{query}' → {route} (follow-up: '{follow_up}')")
    # Keep your uncertain handler: stream a follow-up back to the user
    if route == "uncertain":
        writer(SimpleNamespace(
            id=str(uuid.uuid4()),
            object="chat.completion.chunk",
            model="gpt-4o",
            created=int(time.time()),
            choices=[SimpleNamespace(
                index=0,
                delta=SimpleNamespace(
                    role="assistant",
                    content=follow_up,
                    citations=[],
                    tool_calls=None
                )
            )]
        ))
        return {"route": "uncertain", "follow_up": follow_up}



    # Normal case
    return {"route": route, "follow_up": ""}

 
__all__ = [ "State", "router_node" ]