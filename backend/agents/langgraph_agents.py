from typing import Literal, Any, Dict, List, Union
from backend.state import ReasoningInputState
from backend.client import get_llm
from backend.agents.tools import think_tool, retrieve_and_rerank
from backend.agents.mech_drawing_tool import page_locator, drawing_image_links
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage, BaseMessage, HumanMessage
from backend.agents.agent_prompt import reasoning_agent_prompt
from langgraph.types import StreamWriter 
from types import SimpleNamespace
import uuid, time
from pprint import pformat
import json
import os
import logging
from backend.settings import app_settings

llm = get_llm()
# ===== AGENT NODES =====

log = logging.getLogger("reasoning")

tools = [think_tool, retrieve_and_rerank, page_locator, drawing_image_links]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = llm.bind_tools(tools)

# Iteration budget (can override via env REACT_MAX_TOOL_ITERS)
MAX_TOOL_CALL_ITERS = int(os.environ.get("REACT_MAX_TOOL_ITERS", "5"))


def llm_call(state: ReasoningInputState):
    """Analyze current state and decide on next actions.
    
    The model analyzes the current conversation state and decides whether to:
    1. Call search tools to gather more information
    2. Provide a final answer based on gathered information
    
    Returns updated state with the model's response.
    """
    # If budget reached, instruct the model to finalize without more tool calls.
    budget_guard = []
    try:
        iters = int(state.get("tool_call_iterations", 0))
    except Exception:
        iters = 0
    if iters >= MAX_TOOL_CALL_ITERS:
        budget_guard.append(SystemMessage(content=(
            "Tool budget reached. Do not call any tools now."
            " Provide the best possible final answer with available information."
        )))

    msg = model_with_tools.invoke(
         [SystemMessage(content=reasoning_agent_prompt)] + budget_guard + state["reasoning_messages"])
    return {"reasoning_messages": [msg]}


def tool_node(state: ReasoningInputState):
    """Execute all tool calls from the previous LLM response.
    
    Executes all tool calls from the previous LLM responses.
    Returns updated state with tool execution results.
    """
    tool_calls = state["reasoning_messages"][-1].tool_calls

    observations: List[str] = []
    citations: List[Dict[str, Any]] = []
    for tool_call in tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        tool = tools_by_name[name]
        log.debug("[TOOL] calling %s with args:\n%s", name, pformat(args))
        try:
            obs = tool.invoke(args)
        except Exception as e:
            log.exception("Tool %s failed", name)
            obs = f"ERROR: {type(e).__name__}: {e}"
        observations.append(obs)
        

        if name == "drawing_image_links":
            try:
                payload = json.loads(obs)
                for pages in payload.get("results", []):
                    page = pages.get("page")
                    url = pages.get("image_url")
                    if url and page is not None:
                        citations.append({"title": f"Page {page}", "url": url})
            except Exception:
                pass
    
    # Create tool message outputs
    tool_outputs = [
        ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"]
        ) for observation, tool_call in zip(observations, tool_calls)
    ]

    # 2) If any tool was drawing_image_links, also append a HumanMessage with image parts
    extra_messages: list[BaseMessage] = []
    if any(tc["name"] == "drawing_image_links" for tc in tool_calls):
        for obs, tc in zip(observations, tool_calls):
            if tc["name"] == "drawing_image_links":
                extra_messages.append(_human_images_from_tool_observation(obs))
    # Merge with any citations already in state for this turn
    prev = state.get("citations") or []
    new_citations = prev + citations

        # Increment tool-call iteration budget
    current_iters = int(state.get("tool_call_iterations", 0) or 0)
    next_iters = current_iters + 1
    return {
        "reasoning_messages": tool_outputs + extra_messages,
        "citations": new_citations,
        "tool_call_iterations": next_iters,
    }

# ===== ROUTING LOGIC =====

def should_continue(state: ReasoningInputState) -> Literal["tool_node", "output_node", "llm_call"]:
    """Determine whether to continue research or provide final answer.
    
    Determines whether the agent should continue the research loop or provide
    a final answer based on whether the LLM made tool calls.
    
    Returns:
        "tool_node": Continue to tool execution
        "output_node": Stop and provide final answer
    """
    last = state["reasoning_messages"][-1]
    iters = int(state.get("tool_call_iterations", 0) or 0)

    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        if iters >= MAX_TOOL_CALL_ITERS:
            log.debug("[ROUTER] decision: output_node (budget reached)")
            return "output_node"
        log.debug("[ROUTER] decision: tool_node")
        return "tool_node"
    if isinstance(last, ToolMessage):
        log.debug("[ROUTER] decision: llm_call")
        return "llm_call"
    log.debug("[ROUTER] decision: output_node")
    return "output_node"


def output_node(state: ReasoningInputState, writer: StreamWriter):
    """
    Grab the last (assistant) message, stream it in custom chunks.
    """
    messages = state["reasoning_messages"]
    last_message = messages[-1]
    log.debug("[FINAL ANSWER]\n%s", last_message.content)
    writer(SimpleNamespace(
        id=str(uuid.uuid4()),
        object="chat.completion.chunk",
        model=app_settings.azure_openai_credentials.model,
        created=int(time.time()),
        choices=[SimpleNamespace(
            index=0,
            delta=SimpleNamespace(
                role="assistant",
                content=last_message.content,
                citations=[],
                tool_calls=None
            )
        )]
    ))

    if state.get("citations"):
        citations = state["citations"]
        # ---------- final envelope with citations --------------------------------
        writer(SimpleNamespace(
            id      = str(uuid.uuid4()),
            object  = "chat.completion.chunk",
            model   = app_settings.azure_openai_credentials.model,
            created = int(time.time()),
            choices = [
                SimpleNamespace(
                    index = 0,
                    delta = SimpleNamespace(
                        role       = "assistant",
                        content    = " ",
                        citations  = citations,
                        tool_calls = None
                    )
                )
            ],
            citations = citations
        ))  

ContentPart = Union[str, Dict[str, Any]]
def _human_images_from_tool_observation(observation: str) -> HumanMessage:
    data = json.loads(observation)
    parts: List[ContentPart] = []
    for r in data.get("results", []):
        url = r.get("image_url")
        page = r.get("page")
        if url:
            parts.append({"type": "text", "text": f"Page {page} image:"})
            parts.append({"type": "image_url", "image_url": {"url": url}})
    # If no images, still return a text hint (harmless)
    if not parts:
        parts = [{"type": "text", "text": "No images returned by drawing_image_links."}]
    return HumanMessage(content=parts)
