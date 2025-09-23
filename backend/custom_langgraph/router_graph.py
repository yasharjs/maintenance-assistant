import logging
from typing import Literal
from backend.client import get_llm
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.messages import HumanMessage, AIMessage
import time
import uuid
from types import SimpleNamespace
from langgraph.types import StreamWriter 
from backend.custom_langgraph.troubleshoot_graph import State
llm = get_llm()
logger = logging.getLogger(__name__)

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
    
    HumanMessage(content="what are the main components of a filter o-ring "),
    AIMessage(content="troubleshooting"),

    HumanMessage(content="im looking for table 2-1 in servo valve troubleshooting document"),
    AIMessage(content="troubleshooting"),

    HumanMessage(content="what are the servo valve command values table 2-1?"),
    AIMessage(content="troubleshooting"),


    HumanMessage(content="can you give me a list of valve drawings available?"),
    AIMessage(content="mechanical_drawing"),

    HumanMessage(content="green enabled light at the front of card is off, what do I do?"),
    AIMessage(content="troubleshooting"),

    HumanMessage(content="what are the components of a typical servo "),
    AIMessage(content="troubleshooting"),

    HumanMessage(content="what is the purpose of Pop Rivet - Dome Head?"),
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
    HumanMessage(content="my pump isn't calibrating properly"),
    AIMessage(content="troubleshooting"),
    HumanMessage(content="can you show me the wiring diagram for the pump area?"),
    AIMessage(content="mechanical_drawing"),

    # Vague user question relying on previous context
    HumanMessage(content="explain briefly how to calibrate"),
    AIMessage(content="troubleshooting"),
    HumanMessage(content="and what if it fails?"),
    AIMessage(content="troubleshooting"),

    HumanMessage(content="centering?"),
    AIMessage(content="uncertain"),

    HumanMessage(content="values?"),
    AIMessage(content="uncertain"),


    
]


# Shared routing descriptions
routing_descriptions = {
    "mechanical_drawing": (
        "Use this route ONLY when the user explicitly wants to VIEW or OPEN a visual engineering artifact such as a "       
        "drawing or diagram. Positive signals include terms like: drawing, schematic, diagram,"  
        "CAD, exploded view, BOM (as a drawing artifact), item numbers on a sheet, "
        "BOM Description, revision/sheet references (e.g., 'Sheet 3', 'Rev B'), or requests to open a specific page of a "
        "drawing set.\n\n"
        "Do NOT use this route for references to tables/figures/sections inside troubleshooting or procedure manuals "
        "(e.g., 'table 2-1', 'figure 3-4', 'section 5.2') unless the user explicitly asks for a schematic/diagram/drawing "
        "itself. Those should go to troubleshooting.\n\n"
        "Only classify as 'mechanical_drawing' if the main intent is to access or view the drawing/BOM itself. "
        "Do NOT route here when:\n"
        "• The user cites a table/figure/section from a troubleshooting/operations/maintenance manual (default: troubleshooting).\n"
        "• The user asks about fault codes, calibration steps, signal readings, procedures, command values, pin values or diagnostics (troubleshooting).\n\n"
        ),
    "troubleshooting": (
        "Select this route for **all technical diagnostic, setup, repair, calibration, or fault-resolution queries** related to hydraulic or electrical subsystems.\n\n"
        "Covers, but is not limited to:\n"
        "- Servo Valve Failure Data Sheet"
        "- servo valve command values"
        "- Machine faults, alarms, and error messages\n"
        "- Hydraulic or electrical calibration and tuning\n"
        "- Sensor readings, voltage checks, and signal measurements\n"
        "- Pin/pinout details, breakout box usage, electrical connector pins\n"
        "- Control system behavior and logic\n"
        "- Pressure inconsistencies or flow mismatches\n"
        "- Component operation, testing, and replacement procedures\n\n"
        "- Checking jumper settings and verifying card configuration\n"
        "- Using a Moog breakout box to validate spool command, feedback, solenoid signals, and enable status\n"
        "- Servicing and replacing pilot filters, contamination screens, and torqueing components to specification\n"
        "- Swash plate angle calibration for both master and slave pumps\n"
        "- Interpreting voltage readings at test points (PIN1-PIN10) on VT5041 cards\n"
        "- Matching input/output flow commands with pressure transducers and angle feedback\n"
        "- Diagnosing and resolving servo valve faults (e.g., Not Mechanically Centered, Opening Negative, Valve Ready Signal Fault)\n"
        "Relevant equipment:\n"
        "- Rexroth A10VFE1 & A4VFE1 pumps (master/slave)\n"
        "- VT5041-3X amplifier cards\n"
        "- Moog servo valves and breakout boxes\n"
        "- Husky G-Line, Index, ISB, Hylectric, HyPET, and Quadloc machines\n\n"
        "Example troubleshooting scenarios:\n"
        "- Swash plate angle calibration (master/slave)\n"
        "- Voltage readings at VT5041 test points (PIN1-PIN10)\n"
        "- Diagnosing servo valve faults (Not Mechanically Centered, Opening Negative, Valve Ready Signal Fault)\n"
        "- Verifying jumper settings and card configurations\n"
        "- Cable integrity, grounding, and noise checks\n\n"
        "If the user references a table/figure inside a troubleshooting/manual document (e.g., 'table 2-1' or 'figure 2-1), route to troubleshooting unless they ask for a schematic/BOM/drawing."
        "**Routing rule:** If the query mentions a part/component without clearly asking for a drawing/BOM view, default to 'troubleshooting'."
    ),
    "general": (
        "Use this route for **non-technical or vague queries**, greetings, small talk, or questions not related to machines, faults, or drawings."
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

async def _hybrid_route_with_followup(query: str, history_msgs):
 

    # LLM structured fallback
    llm_resp = await classify_structured(query, history_msgs)
    route = llm_resp["route"]
    follow_up = llm_resp["follow_up"]
    logger.debug("LLM routing result: %s (follow-up: %s)", route, follow_up)
    if route == "uncertain":
         return {"route": "uncertain", "follow_up": follow_up}

    # Normal case
    return {"route": route, "follow_up": ""}

async def classify_structured(query: str, history_msgs):
    """
    Calls the LLM and returns a RouteResponse-like dict:
      {"route": "...", "follow_up": "..."}
    """
    options = "\n".join([f"{k}: {v}" for k, v in routing_descriptions.items()])

    # We'll reuse your existing few_shots and pass a compact history
    prompt_msgs = [
        SystemMessage(content=(
            "You are a routing agent for an enterprise maintenance assistant. "
            "Your task is to classify the current user query into one of the following categories:\n"
            f"{options}\n\n"
            "- uncertain: if the intent is unclear or ambiguous\n\n"
            "provide a helpful follow-up question if the query is uncertain, to clarify the user's intent.\n\n"
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
    query = last_msg.content.strip()

    # Run the hybrid router (deterministic → LLM) and get follow-up support
    result = await _hybrid_route_with_followup(query, history_msgs)
    route = result["route"]
    # Keep your uncertain handler: stream a follow-up back to the user
    if route == "uncertain":
        follow_up = result.get("follow_up", "")
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

