from unittest import result
from langgraph.graph import StateGraph
from typing import Optional, TypedDict, Annotated, Literal, List
from langgraph.graph.message import add_messages
from backend.client import get_llm
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from backend.state import State


llm = get_llm()

# Shared routing descriptions
routing_descriptions = {
    "mechanical_drawing": (
        "Use this route when the user is explicitly asking to **view a drawing**, such as a CAD, schematic, BOM, or a specific drawing page or part number."
    ),
    "troubleshooting": (
        "Use this route for technical issues, calibration steps, alarms, sensor readings, and setup or fault resolution procedures involving hydraulic or electrical subsystems. "
        "This includes questions related to Rexroth A10VFE1 and A4VFE1 master/slave pumps, VT5041-3X amplifier cards, Moog servo valves, breakout boxes, electrical signal diagnostics, and control system behavior. "
        "Relevant machines include Husky’s G-Line, Index, ISB, Hylectric, HyPET, and Quadloc platforms. "
        "\n\n"
        "The agent is trained to walk users through detailed setup and troubleshooting scenarios such as:\n"
        "- Swash plate angle calibration for both master and slave pumps\n"
        "- Interpreting voltage readings at test points (PIN1–PIN10) on VT5041 cards\n"
        "- Matching input/output flow commands with pressure transducers and angle feedback\n"
        "- Diagnosing and resolving servo valve faults (e.g., Not Mechanically Centered, Opening Negative, Valve Ready Signal Fault)\n"
        "- Checking jumper settings and verifying card configuration\n"
        "- Using a Moog breakout box to validate spool command, feedback, solenoid signals, and enable status\n"
        "- Servicing and replacing pilot filters, contamination screens, and torqueing components to specification\n"
        "- Performing cable integrity, routing, and grounding checks to identify electrical noise or signal loss\n"
        "\n"
        "Use this route when the user's query involves control system behavior, pressure inconsistencies, wiring diagnostics, valve logic, card failures, or machine behavior during startup, idle, or active motion. "
        "Also route here if the user is asking about alarms or symptoms that occur during pump startup, valve operation, or system tuning. "
        "This agent can provide step-by-step instructions, expected voltage ranges, tuning ranges, mechanical validation checks, and troubleshooting trees pulled directly from Husky service bulletins and Moog setup guides."
    ),
    "general": (
        "Use this route for **non-technical or vague queries**, greetings, small talk, or questions not related to machines, faults, or drawings."
    ),
}

class RouteResponse(BaseModel):
    route: Literal["mechanical_drawing", "troubleshooting", "general", "return"] = Field(...)
    follow_up: str = Field(default="")

router_llm = llm.with_structured_output(RouteResponse)

def router_node(state: State) -> dict:
    history = state["messages"][-5:]
    options = "\n".join([f"{k}: {v}" for k, v in routing_descriptions.items()])
    message_list = [
        SystemMessage(content=(
            "You are a routing agent. Your job is to decide which Agent can best handle the user's query:\n\n"
            f"{options}\n\n"
            "If the query is vague or underspecified, set `route` to 'return' and provide a `follow_up` question.\n"
            "Only assign a specific route if confident."
        ))
    ] + history

    result = router_llm.invoke(message_list)
    if result.route != "return":
        return {"route": result.route,}
    else:
        return {
            "messages": [{"role": "assistant", "content": result.follow_up}],
            "route": result.route,
        }

__all__ = ["router_node"]