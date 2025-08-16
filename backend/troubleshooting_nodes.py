from pydantic import Field, BaseModel
from langgraph.types import StreamWriter 
from backend.state import State
from langchain.schema import SystemMessage, HumanMessage
from backend.client import get_llm, get_embedding_llm, get_vectorstore
from types import SimpleNamespace
import uuid, time
import cohere


llm = get_llm()
embedding_llm = get_embedding_llm()

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
            "• Preserves the user’s original intent, terminology, and meaning.\n"
            "• Keeps any alarm/fault codes, or other technical tokens **exactly as written**.\n"
            "• Add only the **minimal missing context** needed so the question is fully understandable without the chat history.\n"
            "• Does **not** paraphrase purely for style, guess at details, or answer the question.\n"
            "• Output **only** the rewritten question text—no explanations, no extra fields."
        )
    )

    # Send to LLM as structured output
    result = llm_rewritter.invoke([system, *last_messages])
    print("Rewritten question:", result.rewritten.strip())
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
    """Rerank retrieved_docs by relevance to question using Cohere Rerank."""
    COHERE_API_KEY = "zOxAfT9v1nO8fk2yFWqcl1TQQcbwnWqDtsVPs6x3"
    co = cohere.Client(api_key=COHERE_API_KEY)

    hits  = state["hits"]
    query = state["rewritten"]
    corpus = [d.page_content for d in hits]

    # Models: 'rerank-3.5' (best), 'rerank-3', or 'rerank-lite' (cheaper)
    resp = co.rerank(
        model="rerank-english-v3.0",
        query=query,
        documents=corpus,
        top_n=5,   # adjust as you like
        return_documents=True
    )
    results = resp.results
    top1 = float(results[0].relevance_score)
    cutoff = top1 * 0.40
    new_hits = []
    keep = [r.index for r in results if float(r.relevance_score) >= cutoff]
    for i in keep:
        h = hits[i]
        new_hits.append(h)
    
    return {**state, "hits": new_hits}


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

    # Step 3: System rules
    TASK_DESCRIPTION = """
        The Maintenance Assistant agent supports technicians in troubleshooting Husky HyPET, Hylectric, and Quadloc machines. It provides step-by-step help with alarms, faults, and procedures, and adapts to all skill levels.
        """

    FORMATTING_RULES = """
        • Do NOT paraphrase technical values (voltages, jumpers). Repeat exactly.
        • Format numerical data using GitHub-Flavored Markdown tables (pipes `|`, dashes `-`).
        • Use numbered lists for procedures. Avoid bullets or code blocks.
        IMPORTANT: Do NOT reference document sections, tables, figures, or page numbers unless the user specifically asked. Only summarize the relevant information.        
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
        • Do NOT guess or invent missing steps or values.
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