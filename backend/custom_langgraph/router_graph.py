from unittest import result
from langgraph.graph import StateGraph
from typing import Optional, TypedDict, Annotated, Literal
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



def router_node(state: State, writer: StreamWriter) -> dict:
    history = state["messages"][-5:]
    query = state["messages"][-1].content.lower()
    query_lemmas = normalize_query_to_lemmas(query)
   
    system_message = SystemMessage(content=(
        "You are a routing agent for an enterprise maintenance assistant. "
        "Your task is to classify the current user query into one of the following categories:\n"
        "- mechanical_drawing: for diagrams, drawings, drawing item position, drawing item position number, item numbers,BOMs\n"
        "- troubleshooting: for issues, alarms, errors, calibration, fixing steps\n"
        "If a query mentions components or parts but does not clearly request a drawing, list, or part number, classify as 'troubleshooting'."
        "- uncertain: if the intent is unclear or ambiguous\n\n"
        "- general: for greetings, chit-chat, or unrelated queries\n\n"
        "Use conversation history (last 5 messages) to help resolve vague follow-ups like 'what about step 2?'. "
        "Continue the previous intent unless there is a clear switch in topic.\n\n"
        "If you're still unsure, classify it as 'uncertain' and provide a helpful follow-up question."
    ))

    prompt = [system_message] + few_shots + history
    result = router_llm.invoke(prompt)
    route = result.route

     # Step 2: Rule-based overrides
    troubleshooting_keywords = [
        "fix", "fault", "faulty", "issue", "problem", "alarm", "error", "not working",
        "doesn't work", "fail", "failure", "calibrate", "calibration", "adjust", "adjustment",
        "check", "verify", "diagnose", "troubleshoot", "step", "procedure", "test", 
        "pressure", "voltage", "current", "symptom", "reset", "override", "sequence", "enable", "pinout"
    ]

    mechanical_drawing_keywords = [
    "drawing", "diagram", "part number", "part #", "bom", "bill of material", 
    "assembly", "location", "layout", 
    "show", "display", "visual", "illustration", "overview", "render", "schematic"
]


       # Apply keyword-based rules (only override if LLM didn't say 'uncertain')
    if route != "uncertain":
        log = f"[ROUTER OVERRIDE] Original route: {route} | Query: '{query}'"

        if any(kw in query_lemmas for kw in troubleshooting_keywords):
            route = "troubleshooting"
            print(log + " → overridden to: troubleshooting")

        elif any(kw in query_lemmas for kw in mechanical_drawing_keywords) and not any(kw in query_lemmas for kw in troubleshooting_keywords):
            route = "mechanical_drawing"
            print(log + " → overridden to: mechanical_drawing")

    # Step 3: Return
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
                content=result.follow_up,
                citations=[],
                tool_calls=None
            )
        )]
        ))
        return {"route": "uncertain", "follow_up": result.follow_up}
        
    else:
        print(f"[ROUTER] Classified query '{query}' as route: {route}")
        return {"route": route , "follow_up": ""}
 
__all__ = [ "State", "router_node" ]