import logging
import os
import time
import uuid
from types import SimpleNamespace

import cohere
from langchain.schema import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from backend.client import get_llm, get_embedding_llm, get_vectorstore
from backend.state import State
from pydantic import BaseModel, Field


llm = get_llm()
logger = logging.getLogger(__name__)
# embedding_llm = get_embedding_llm()

class RouteResponse(BaseModel):
    rewritten: str = Field(..., description="The rewritten user question that is clear and self-contained.")


llm_rewritter = llm.with_structured_output(RouteResponse)

async def trblsht_rewriter(state: State) -> dict:
    # Get the last 7 messages
    last_messages = state["messages"][-7:]


    system = SystemMessage(
        content=(
            "You are a **Query Rewriter**. "
            "Given the recent conversation, produce a **stand-alone version of the latest USER question** that:\n\n"
            "- Preserves the user's original intent, terminology, and meaning.\n"
            "- Keeps any alarm/fault codes, or other technical tokens **exactly as written**.\n"
            "- Add only the **minimal missing context** needed so the question is fully understandable without the chat history.\n"
            "- Does **not** paraphrase purely for style, guess at details, or answer the question.\n"
            "- Output **only** the rewritten question text-no explanations, no extra fields."
        )
    )

    # Send to LLM as structured output
    result = llm_rewritter.invoke([system, *last_messages])
    logger.debug("Rewritten question: %s", result.rewritten.strip())
    return {"rewritten": result.rewritten.strip()}


async def retriever_node(state: State) -> State:
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(
        search_type="hybrid",
        k=10
    )
    hits = await retriever.aget_relevant_documents(state["rewritten"])
    return {**state, "hits": hits}

async def rerank(state: State) -> dict:
    """Rerank retrieved docs by relevance using Cohere, when configured."""

    hits = list(state.get("hits") or [])
    if not hits:
        logger.debug("No retrieved documents to rerank; returning original state.")
        return {**state, "hits": hits}

    api_key = os.environ.get("COHERE_API_KEY")
    if not api_key:
        logger.warning("COHERE_API_KEY not set; skipping Cohere rerank.")
        return {**state, "hits": hits}

    co = cohere.Client(api_key=api_key)

    query = state.get("rewritten", "")
    corpus = [d.page_content for d in hits]

    try:
        resp = co.rerank(
            model="rerank-english-v3.0",
            query=query,
            documents=corpus,
            top_n=min(5, len(corpus)),
            return_documents=True,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Cohere rerank failed; returning original order: %s", exc)
        return {**state, "hits": hits}

    results = resp.results or []
    if not results:
        logger.debug("Cohere rerank returned no results; returning original order.")
        return {**state, "hits": hits}

    top1 = float(results[0].relevance_score) if results else 0.0
    cutoff = top1 * 0.40 if top1 else 0.0
    keep_indices = [r.index for r in results if float(r.relevance_score) >= cutoff]
    reordered_hits = [hits[i] for i in keep_indices if i < len(hits)]

    return {**state, "hits": reordered_hits or hits}


async def context_window_node(state: State, writer: StreamWriter) -> dict:
    docs = state.get("hits", [])
    last_messages = state.get("messages", [])[-3:]
    rewritten_question = state.get("rewritten", "").strip()

    # Step 1: Build the context string
    context_text = "\n\n".join(
        f"{doc.page_content.strip()} [doc{i+1}]" for i, doc in enumerate(docs) # type: ignore
    )

    message_history = "\n".join(
        f"{msg.__class__.__name__.replace('Message', '')}: {msg.content.strip()}" for msg in last_messages
    )

    rewritten_question = state["rewritten"].strip()
    follow_up = state["follow_up"].strip() if "follow_up" in state else ""
    # Step 3: System rules
    TASK_DESCRIPTION = """
        The Maintenance Assistant agent supports technicians in troubleshooting Husky HyPET, Hylectric, and Quadloc machines. It provides step-by-step help with alarms, faults, and procedures, and adapts to all skill levels.
        """

    FORMATTING_RULES = """
        - Do NOT paraphrase technical values (voltages, jumpers). Repeat exactly.
        - Format numerical data using GitHub-Flavored Markdown tables (pipes `|`, dashes `-`).
        - Use numbered lists for procedures. Avoid bullets or code blocks.
        IMPORTANT: Do NOT reference document sections, tables, figures, or page numbers unless the user specifically asked. Only summarize the relevant information.        
        """

    SAFETY_AND_TOOLS = """
        - Mention tools (e.g., breakout box, multimeter) and include safety warnings.
        - Include critical checks: jumper settings, spool centering, signal verification, swashplate calibration.
        """

    INTERACTIVITY_RULES = f"""
        - Always end responses with one helpful, clarifying question.
        - If the question is vague, ask for clarification - don't assume.
        - Use the follow up provided by the routing agent if the query is vague.
        - Use a professional tone that encourages technician confidence.
        """

    MISSING_INFO_BEHAVIOR = """
        - Do NOT guess or invent missing steps or values.
        """

    SYSTEM_PROMPT = (
        TASK_DESCRIPTION
        + FORMATTING_RULES
        + SAFETY_AND_TOOLS
        + INTERACTIVITY_RULES
        + MISSING_INFO_BEHAVIOR
        + "\n\nIf the user's question is a general definition or explanation request (e.g., 'what is a servo valve?'), "
          "respond, then ask the user to specify a fault, alarm, or problem they are experiencing. "
          "Do NOT attempt to generate troubleshooting steps unless a specific issue is described."
    )

    # Step 3: Combine into final context (LLM input)
    final_context = f"""### Document Context:
                        {context_text}

                        ### Recent Messages:
                        {message_history}

                        ### Rewritten Question:
                        {rewritten_question}

                        ### ROUTER Follow-Up:
                        {follow_up}
                    """

    async for chunk in llm.astream([
        SystemMessage(content=SYSTEM_PROMPT.strip()),
        HumanMessage(content=final_context.strip())
        ]):
        if token := chunk.content:
            writer(SimpleNamespace(                 
                id      = str(uuid.uuid4()),
                object  = "chat.completion.chunk",
                model   = "gpt-4o",
                created = int(time.time()),
                choices = [
                    SimpleNamespace(
                        index = 0,
                        delta = SimpleNamespace(
                            role       = "assistant",
                            content    = token,
                            tool_calls = None
                        )
                    )
                ]
            ))
    
    return {"context": str(context_text)}

__all__ = ["trblsht_rewriter", "retriever_node", "context_window_node"]


