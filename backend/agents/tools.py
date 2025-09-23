from langchain_core.tools import tool, InjectedToolArg
from typing import Annotated, Literal, List, Dict, Any
from langchain_core.documents import Document
from backend.client import get_vectorstore
from backend.state import ReasoningInputState, Todo
import cohere
import os
import logging


def _retrieve_from_vectorstore(
    query: str,
    k: int = 10,
    search_type: Literal["hybrid", "similarity", "mmr"] = "hybrid",
) -> List[Dict[str, Any]]:
    """Retrieve Documents and convert to display views (JSON-serializable)."""
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(search_type=search_type, k=k)
    docs: List[Document] = retriever.get_relevant_documents(query)
    return [
        _doc_to_view(
            d,
            idx=i
        )
        for i, d in enumerate(docs)
    ]

def _doc_to_view(doc: Document, idx: int) -> Dict[str, Any]:
    """Make a display-friendly view of a Document."""
    return {
        "id": idx,
        "page": doc.metadata.get("page", None),
        "page_content": doc.page_content
    }

def _rerank_with_cohere(
    query: str,
    views: List[Dict[str, Any]],
    top_n: int = 5,
    cutoff_ratio: float = 0.40,
    model: str = "rerank-english-v3.0",
) -> List[Dict[str, Any]]:
    """Add rerank scores to views and keep those above cutoff.

    If COHERE_API_KEY is not set, fall back to a simple top-N slice with no rerank.
    """
    if not views:
        return []

    api_key = os.environ.get("COHERE_API_KEY")
    if not api_key:
        logging.getLogger("tools").warning("COHERE_API_KEY not set; returning top-N without rerank")
        return views[: min(top_n, len(views))]

    co = cohere.Client(api_key=api_key)

    corpus = [v["page_content"] for v in views]
    resp = co.rerank(
        model=model,
        query=query,
        documents=corpus,
        top_n=min(top_n, len(corpus)),
        return_documents=False,
    )
    results = resp.results or []
    if not results:
        return []

    top1 = float(results[0].relevance_score)
    cutoff = top1 * float(cutoff_ratio)
    score_map = {r.index: float(r.relevance_score) for r in results}

    for idx, v in enumerate(views):
        if idx in score_map:
            v["rerank_score"] = score_map[idx]

    kept = [v for v in views if v.get("rerank_score", 0.0) >= cutoff]
    kept.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
    return kept

def format_pages_output(
    kept: List[Dict[str, Any]],
    header: str = "Search results",
) -> str:
    """Format kept passages with PAGE and CONTENT only."""
    if not kept:
        return "No valid search results found."
    
    out = f"{header}:\n\n"
    for i, item in enumerate(kept, 1):
        page = item.get("page", "unknown")
        title = f"--- PAGE {page} ---"
        out += f"\n\n{title}\n"
        content = item.get("page_content", "")
        out += f"\n{content}\n"
        out += "-" * 80 + "\n"

    return out

@tool(parse_docstring=True)
def retrieve_and_rerank(
    query: str,
    k: Annotated[int, InjectedToolArg] = 10,
    search_type: Annotated[Literal["hybrid", "similarity", "mmr"], InjectedToolArg] = "hybrid",
    top_n: Annotated[int, InjectedToolArg] = 5,
    cutoff_ratio: Annotated[float, InjectedToolArg] = 0.40,
    model: Annotated[str, InjectedToolArg] = "rerank-english-v3.0",
) -> str:
    """Retrieve from the vector store, then rerank with Cohere, and format output.

    Use when you need source passages and want the top ones filtered by a reranker.

    Args:
        query: Natural-language query (use the clarified/rewritten one if available).
        k: Retrieval fanout (default 10).
        search_type: Retriever mode ('hybrid' | 'similarity' | 'mmr').
        top_n: Depth the reranker should score (default 5).
        cutoff_ratio: Keep docs with score >= top1 * cutoff_ratio (default 0.40).
        model: Cohere rerank model ('rerank-3.5', 'rerank-3', 'rerank-lite').

    Returns:
        A formatted string showing retrieval results and then reranked results.
    """

    views = _retrieve_from_vectorstore(query=query, k=k, search_type=search_type)

    kept = _rerank_with_cohere(
        query=query,
        views=views,
        top_n=top_n,
        cutoff_ratio=cutoff_ratio,
        model=model,
    )
    output_pages = format_pages_output(kept)

    return output_pages + "\n\n"

@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.
    
    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.
    
    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?
    
    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?
    
    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        str: Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded: {reflection}"

@tool
def write_todos(todos: List[Todo]) -> str:
    """Overwrite the current TODO list with the given items."""
    return f"Wrote {len(todos)} todo(s)."

@tool
def read_todos() -> str:
    """Read the current TODO list."""
    return "Reading todos."
