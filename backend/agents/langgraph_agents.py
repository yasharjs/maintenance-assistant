from typing import Literal
from backend.state import ReasoningInputState
from backend.client import get_llm
from backend.agents.tools import think_tool, retrieve_and_rerank
from backend.agents.mech_drawing_tool import page_locator
from langchain_core.messages import SystemMessage, BaseMessage, ToolMessage
from backend.agents.agent_prompt import reasoning_agent_prompt
from langgraph.types import StreamWriter 
from types import SimpleNamespace
import uuid, time
from pprint import pformat
import cohere

llm = get_llm()
# ===== AGENT NODES =====

# --- at top of the file ---
from pprint import pformat
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("reasoning")

tools = [think_tool, retrieve_and_rerank, page_locator]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = llm.bind_tools(tools)


def llm_call(state: ReasoningInputState):
    """Analyze current state and decide on next actions.
    
    The model analyzes the current conversation state and decides whether to:
    1. Call search tools to gather more information
    2. Provide a final answer based on gathered information
    
    Returns updated state with the model's response.
    """
    msg = model_with_tools.invoke(
        [SystemMessage(content=reasoning_agent_prompt)] + state["reasoning_messages"]
    )
    print("LLM", [msg])
    return {"reasoning_messages": [msg]}


def tool_node(state: ReasoningInputState):
    """Execute all tool calls from the previous LLM response.
    
    Executes all tool calls from the previous LLM responses.
    Returns updated state with tool execution results.
    """
    tool_calls = state["reasoning_messages"][-1].tool_calls

    # Execute all tool calls
    observations = []
    for tool_call in tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observations.append(tool.invoke(tool_call["args"]))
        log.debug("[TOOL] calling %s with args:\n%s", tool_call["name"], pformat(tool_call["args"]))

    # Create tool message outputs
    tool_outputs = [
        ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"]
        ) for observation, tool_call in zip(observations, tool_calls)
    ]
    print("OBS", tool_outputs)
    return {"reasoning_messages": tool_outputs}


# ===== ROUTING LOGIC =====

def should_continue(state: ReasoningInputState) -> Literal["tool_node", "output_node"]:
    """Determine whether to continue research or provide final answer.
    
    Determines whether the agent should continue the research loop or provide
    a final answer based on whether the LLM made tool calls.
    
    Returns:
        "tool_node": Continue to tool execution
        "output_node": Stop and provide final answer
    """
    messages = state["reasoning_messages"]
    last_message = messages[-1]
    
    # If the LLM makes a tool call, continue to tool execution
    if last_message.tool_calls:
        log.debug("[ROUTER] decision: %s", "tool_node")
        return "tool_node"
    # Otherwise, we have a final answer
    log.debug("[ROUTER] decision: %s", "output_node")
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
        model="gpt-4o",
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

