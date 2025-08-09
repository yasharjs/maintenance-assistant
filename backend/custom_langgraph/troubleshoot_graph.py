from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langgraph.types import StreamWriter 
from types import SimpleNamespace
import uuid, time , os, logging, asyncio
from backend.client import get_llm , get_vectorstore
llm = get_llm()
logger = logging.getLogger(__name__)

# --- State schema extended for troubleshooting workflow ---
class State(TypedDict):
    messages: Annotated[list, add_messages]
    route: str
    rewritten: str
    follow_up: Optional[str]
    hits: Optional[list]  # From retriever
    context: Optional[str]  # From splitter/formatter
    final_answer: str
    feedback: Optional[str]
    approved: Optional[bool]
    retry_count : int
    feedback_memory: Optional[list[str]]   # ✅ new field
    score: Optional[float]  
    stream_chunk: Optional[str]  # For streaming responses

# --- Structured output model for evaluator ---
class EvaluationResult(BaseModel):
    approved: bool = Field(..., description="Whether the answer meets custom criteria")
    feedback: str = Field("", description="Feedback when not approved")
    score: float = Field(..., ge=0, le=1, description="Quality score from 0 to 1")

QUERY_REWRITER_SYSTEM_MSG_PREFIX = (
    "**ROLE**: You are a domain-aware, high-precision query rewriter.\n\n"
    "**GOAL**: Rewrite the user’s CURRENT_QUESTION into a standalone, keyword-optimized query (≤25 words).\n"
    "Preserve technical intent. Optimize for dense retrieval.\n\n"
    "**USE CONTEXT**:\n"
    "- Use technical terms from CURRENT_QUESTION exactly as written.\n"
    "- Fill in missing context using RECENT_HISTORY — no guessing.\n\n"
    "**STRICT RULES**:\n"
    "• Output a single line. No explanations.\n"
    "• No quotes, punctuation, symbols, markdown, or rephrasing of keywords.\n"
    "• Do not exceed 25 words.\n"
    "• Resolve co-references (e.g., 'it', 'this') using RECENT_HISTORY.\n"
    "• Only add terms if they are clear technical synonyms or style cues from RECENT_HISTORY.\n\n"
    "RECENT_HISTORY:\n"
)
# --- Node: Rewrite the user query for troubleshooting route ---
async def troubleshooting_rewriter(state: State) -> dict:
    RECENT_HISTORY = state["messages"][-5:]
    CURRENT_QUESTION = state["messages"][-1].content
    
    # Else, continue with rewrite
    system_msg = SystemMessage(
        content=QUERY_REWRITER_SYSTEM_MSG_PREFIX + str(RECENT_HISTORY) + 
        "\n\n[CRITICAL INSTRUCTION]: If the user’s CURRENT_QUESTION is already clear, standalone, and well-formed (≥5 words, with a fault, alarm, or procedure), then return it exactly as-is — do NOT rewrite it."
    )
    result = llm.invoke([system_msg, {"role": "user", "content": "CURRENT_QUESTION: " + CURRENT_QUESTION}])
    print(f"Rewritten query: {result.content.strip()}")
    return {"rewritten": result.content.strip()}

async def retrieve_node(state: State) -> State:
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(
        search_type="hybrid",
        k=6
    )
    hits = await retriever.aget_relevant_documents(state["rewritten"])
    return {**state, "hits": hits}

async def context_window_node(state: State) -> State:
    docs = state.get("hits") or []
    
    # Step 1: Filter only text docs
    out = {"texts": [d for d in docs]}

    # Step 2: Build context text block from extracted documents
    context_text = "\n".join(
        f"{t.page_content} [doc{i+1}]"
        for i, t in enumerate(out["texts"])
    )

    # Step 3: Get chat history if needed (you can truncate or format later)
    history_text = ""  # Optional: convert `state["messages"]` to a readable history string if desired

    # Step 4: Compose system instructions
    TASK_DESCRIPTION = """
    The Maintenance Assistant agent supports technicians in troubleshooting Husky HyPET, Hylectric, and Quadloc machines. It provides step-by-step help with alarms, faults, and procedures, and adapts to all skill levels.
    """

    FORMATTING_RULES = """
    • Do NOT paraphrase technical values (voltages, jumpers). Repeat exactly.
    • Format numerical data using GitHub-Flavored Markdown tables (pipes `|`, dashes `-`).
    • Use numbered lists for procedures. Avoid bullets or code blocks.
    """

    SAFETY_AND_TOOLS = """
    • Mention tools (e.g., breakout box, multimeter) and include safety warnings.
    • Include critical checks: jumper settings, spool centering, signal verification, swashplate calibration.
    """

    INTERACTIVITY_RULES = """
    • Always end responses with one helpful, clarifying question.
    • If the question is vague, ask for clarification — don't assume.
    • Use a professional tone that encourages technician confidence.
    """

    MISSING_INFO_BEHAVIOR = """
    • Clearly state if relevant data is NOT found in the documents.
    • Do NOT guess or invent missing steps or values.

    """

    # Combine for final system prompt
    system_rules = (
        TASK_DESCRIPTION +
        FORMATTING_RULES +
        SAFETY_AND_TOOLS +
        INTERACTIVITY_RULES +
        MISSING_INFO_BEHAVIOR
    )
    system_rules += (
    "\n\nIf the user's question is a general definition or explanation request (e.g., 'what is a servo valve?'), "
    "respond with a brief definition, then immediately ask the user to specify a fault, alarm, or problem they are experiencing. "
    "Do NOT attempt to generate troubleshooting steps unless a specific issue is described."
)
    
    
    # Step 5: Compose prompt blocks
    prompt_header = (
        f"Conversation so far:\n{history_text}\n"
        f"---\nContext:\n{context_text}"
    )

    blocks = [{"type": "text", "text": prompt_header}]
    blocks.append({"type": "text", "text": f"\nQuestion: {state['rewritten']}"})


    # Step 6: Build prompt using LangChain format
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_rules),
        HumanMessage(content=blocks),  # type: ignore
    ])

    return {
        **state,
        "context": str(prompt)  #  convert prompt object to string
    }
    
# --- Node: Generate final answer via RAG with forced troubleshooting route ---
async def troubleshooting_final(state: State):
    chunks = []
    context = state.get("context") or ""
    # Inject feedback directly into prompt if retrying
    if state.get("retry_count", 0) > 0:
        feedback_notes = "\n".join(state.get("feedback_memory") or [])
        context += f"\n\n[Evaluator feedback from previous attempts]:\n{feedback_notes}\nPlease revise your response to address this."

    # Add anti-reference instruction unless explicitly requested
    user_query = state["messages"][-1].content.lower()
    if not any(kw in user_query for kw in ["section", "table", "figure", "diagram", "page", "reference", "doc", "document"]):
        context += "\n\nIMPORTANT: Do NOT reference document sections, tables, figures, or page numbers unless the user specifically asked. Only summarize the relevant information."

    async for chunk in llm.astream(context):
        if chunk.content:
            chunks.append(chunk.content)
            
    final_response = "".join(chunks)
    
    print(f"Final response generated: {final_response.strip()}")
    print(f"[Retry #{state.get('retry_count', 0)+1}]")
    print(f"Current Score: {state.get('score')}")
    print("Feedback Memory:")
    for fb in (state.get("feedback_memory") or []):
        print(f" - {fb}")
    return {
        **state,
        "final_answer": final_response,
        "retry_count": state.get("retry_count", 0) + 1
    }
   
# --- Node: Evaluate answer and provide feedback/approval ---
def troubleshooting_evaluator(state: State) -> dict:
    final_answer = state["final_answer"]

    # Optional hard rule: always end in a question
    if not final_answer.endswith("?"):
        feedback = "Response must end with a helpful follow-up question."
        feedback_memory = (state.get("feedback_memory") or []) + [feedback]
        return {
            "approved": False,
            "feedback": feedback,
            "feedback_memory": feedback_memory,
            "retry_count": state.get("retry_count", 0),
            "score": 0.0
        }
    rewritten = state.get("rewritten", "").lower()

    if any(kw in rewritten for kw in ["what is", "define", "explain", "overview", "how does", 'definition', "describe", "meaning", "purpose", "function", "role"]):
        return {
            "approved": True,
            "feedback": "Approved: general explanation with follow-up question.",
            "feedback_memory": state.get("feedback_memory", []),
            "retry_count": state.get("retry_count", 0),
            "score": 1.0
        }


    # Run structured evaluation prompt
    prompt = SystemMessage(content=(
        "You are a senior technical evaluator for a Maintenance AI Assistant.\n"
        "Evaluate the assistant’s final answer according to the following criteria and return a score (0 to 1), approval flag, and brief feedback.\n\n"
        "**Scoring Guidelines:**\n"
        "- 1.0: Perfect. All rules followed.\n"
        "- 0.8+: Acceptable minor issues (formatting, brevity).\n"
        "- 0.6–0.79: Major issues in clarity, formatting, or coverage.\n"
        "- < 0.6: Unsafe, confusing, or incomplete.\n\n"
        "**Criteria:**\n"
        "1. Diagnostic steps accurate and logical\n"
        "2. Technical values not paraphrased\n"
        "3. Markdown tables used\n"
        "4. Numbered lists for steps\n"
        "5. Tools and safety warnings included\n"
        "6. Transparency on missing info\n"
        "7. Ends with helpful question\n\n"
        "**Respond in this exact format:**\n"
        "```json\n"
        "{\n"
        "  \"approved\": true,\n"
        "  \"feedback\": \"...\",\n"
        "  \"score\": 0.85\n"
        "}\n"
        "```"
        f"\n\nFinal Answer:\n{final_answer}"
    ))

    result = llm.with_structured_output(EvaluationResult).invoke([prompt])

    approved = result.approved or result.score >= 0.8
    feedback_memory = (state.get("feedback_memory") or []) + [result.feedback]
    print(f"Evaluation result: {result}")
    return {
        "approved": approved,
        "feedback": result.feedback,
        "feedback_memory": feedback_memory,
        "retry_count": state.get("retry_count", 0),
        "score": result.score
    }

async def troubleshooting_streamer(state: State, writer: StreamWriter):
    """
    Streams state['final_answer'] in slow, human-like chunks.

    Configurable via environment variables:
      STREAM_INITIAL_DELAY   (float seconds, default 2.0)
      STREAM_CHUNK_SIZE      (int chars,   default 50)
      STREAM_CHUNK_INTERVAL  (float secs,  default 0.05)
    """
    answer = state["final_answer"]
    try:
        # 1. Read configuration (with defaults)
        initial_delay   = float(os.getenv("STREAM_INITIAL_DELAY",   "2.0"))
        chunk_size      = int(  os.getenv("STREAM_CHUNK_SIZE",      "50"))
        chunk_interval  = float(os.getenv("STREAM_CHUNK_INTERVAL",  "0.05"))

        logger.info(f"Streaming will start after {initial_delay}s delay")
        # 2. Initial buffer
        await asyncio.sleep(initial_delay)  # non-blocking pause :contentReference[oaicite:2]{index=2}

        # 3. Split into chunks
        chunks = [answer[i : i + chunk_size]
                  for i in range(0, len(answer), chunk_size)]
        logger.debug(f"Answer split into {len(chunks)} chunks of ~{chunk_size} chars")

        # 4. Stream each chunk with a pause
        for idx, text in enumerate(chunks):
            # Prepare the stream‐mode event
            event = SimpleNamespace(
                id      = str(uuid.uuid4()),
                object  = "chat.completion.chunk",
                model   = "gpt-4o",
                created = int(time.time()),
                choices = [SimpleNamespace(
                    index = 0,
                    delta = SimpleNamespace(
                        role       = "assistant",
                        content    = text,
                        citations  = [],
                        tool_calls = None
                    )
                )]
            )
            writer(event)                       # send chunk
            await asyncio.sleep(chunk_interval) # slow down :contentReference[oaicite:3]{index=3}

        logger.info("Finished streaming answer")
    except Exception:
        # Catch **all** exceptions to avoid killing the graph
        logger.exception("Error in troubleshooting_streamer; aborting stream")  # :contentReference[oaicite:4]{index=4}
    




# Export node functions for main app graph
__all__ = [
    "troubleshooting_rewriter", 
    "troubleshooting_final", 
    "troubleshooting_evaluator",
    "retrieve_node",
    "context_window_node",
    "State",
    "EvaluationResult",
    "troubleshooting_streamer"
]
