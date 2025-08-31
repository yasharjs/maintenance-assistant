from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from backend.assets.toc_data import toc
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from backend.client import get_llm

llm_nostream = get_llm(streaming=False)

class AmbiguousMatch(BaseModel):
    description: str = Field(..., description="Short part/drawing description from the TOC row.")
    pages: List[int] = Field(default_factory=list, description="All pages for that candidate.")

class LLMPageLocatorResult(BaseModel):
    decision: Literal["found", "ambiguous", "not_found"]
    # When decision == "found"
    pages: List[int] = Field(default_factory=list, description="All pages for the selected drawing.")
    # When decision == "ambiguous"
    matches: List[AmbiguousMatch] = Field(default_factory=list, description="Top candidate matches with page lists.")
    # When decision == "not_found"
    message: Optional[str] = Field(default=None, description="Brief reason like 'no matching entry'.")

# ---------- The tool (LLM computes pages from markdown TOC) ----------
structured_llm = llm_nostream.with_structured_output(LLMPageLocatorResult)
@tool(parse_docstring=True)
def page_locator(query: str) -> str:
    """Locate drawing pages from a markdown TOC for a user query (LLM returns pages).

    Args:
        query: The agent's query string (self-contained if possible).

    Returns:
        A JSON string with exactly one of the following:
          - {"decision":"found","pages":[...]}
          - {"decision":"ambiguous","matches":[{"description":"...", "pages":[...]}, ...]}
          - {"decision":"not_found","message":"..."}
    """
    system = SystemMessage(content=(
        "You have a mechanical drawing Table of Contents (BOM) in markdown and a user query.\n\n"
        "TOC columns:\n"
        "1) Page Number (start page of the BOM entry)\n"
        "2) Part Number\n"
        "3) Description\n"
        "4) Drawing Number (NOT a page number)\n\n"
        "SECTION HEADERS (no part/drawing) are NOT valid entries.\n\n"
        "Your job:\n"
        "• If the query targets a specific part/drawing, pick the best matching VALID entry and return ALL PAGES:\n"
        "  - Pages start at the entry's Pg# and continue up to (but NOT including) the next VALID entry's Pg#.\n"
        "  - If there is no next valid entry visible, return just the start page.\n"
        "• If multiple entries plausibly match, return decision='ambiguous' with up to 3 candidates (description + page list).\n"
        "• If nothing matches, return decision='not_found' with a short message.\n\n"
        "Do NOT echo the TOC. Output ONLY JSON. No markdown, no prose.\n"
        "Ensure 'pages' are integers only, sorted ascending, unique.\n"
        "Ambiguous: include at most 3 candidates.\n"
    ))
    user = HumanMessage(content=f"USER QUERY:\n{query}\n\nTOC (markdown):\n{toc}")

    result = structured_llm.invoke([system, user])

    # Return JSON string for ToolMessage.content
    return result.model_dump_json()