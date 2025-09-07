from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from backend.assets.toc_data import toc
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from backend.client import get_llm
from backend.settings import (app_settings)
from azure.storage.blob import generate_container_sas, ContainerSasPermissions
from datetime import datetime, timedelta, timezone
import json

llm_nostream = get_llm(streaming=False)

class EntryHit(BaseModel):
    """One TOC hit with metadata + computed pages."""
    item_revision: Optional[str] = Field(
        default=None, description="Column 2: Item / Revision (e.g., '5994314/1')."
    )
    description: str = Field(
        ..., description="Column 3: Description from the TOC row."
    )
    dwg_revision: Optional[str] = Field(
        default=None, description="Column 4: Dwg / Revision (e.g., '4852822/1')."
    )
    pages: List[int] = Field(
        default_factory=list, description="List of BOM page numbers to show the drawing"
    )

class LLMPageLocatorResult(BaseModel):
    decision: Literal["found", "ambiguous", "not_found"]

    # When decision == "found"
    entry: Optional[EntryHit] = Field(
        default=None, description="The single best-matching entry."
    )

    # When decision == "ambiguous"
    matches: List[EntryHit] = Field(
        default_factory=list, description="Top candidate matches."
    )

    # When decision == "not_found"
    message: Optional[str] = Field(
        default=None, description="Brief reason like 'no matching entry'."
    )
# ---------- The tool (LLM computes pages from markdown TOC) ----------
structured_llm = llm_nostream.with_structured_output(LLMPageLocatorResult)
@tool(parse_docstring=True)
def page_locator(drawing: str) -> str:
    """Locate drawing pages from a markdown TOC for a user query (LLM returns pages).

    Args:
        drawing: Only one drawing/assembly name or part/drawing number.

    Returns:
        A JSON string with exactly one of the following:
          - {"decision":"found","pages":[...]}
          - {"decision":"ambiguous","matches":[{"description":"...", "pages":[...]}, ...]}
          - {"decision":"not_found","message":"..."}
    """
    system = SystemMessage(content=("""
        "You have a mechanical drawing Table of Contents (BOM) in markdown and a user query.\n\n"
        "TOC columns:\n"
        "1) Page Number (this is the BOM start page)\n"
        "2) Part Number\n"
        "3) Description\n"
        "4) Drawing Number (NOT a page number)\n\n"
        "Your job:\n"
        "• If the query targets a specific part/drawing, pick the best matching VALID entry and return a list of **contiguous page numbers** starting from the matched entry's page number (first column), up to (but not including) the next **valid BOM entry** (ignore section headers).\n"
        "  - Pages start at the entry's Pg# and continue up to (but NOT including) the next VALID entry's Pg#.\n"
        "• If multiple entries plausibly match, return decision='ambiguous' with EVERY SINGLE candidate that partially matches (description + pages list).\n"
        "• If nothing matches, return decision='not_found' with a short message.\n\n"
        "Do NOT echo the TOC. Output ONLY JSON. No markdown, no prose.\n"
        "Ensure 'pages' are integers only, sorted ascending, unique.\n"
        "Ambiguous: include ALL candidates.\n\n\n" \
        "Here are some exampels:" \
        Here are some examples:

        EXAMPLE A
        User query: "Booster Manifold Assembly"
        Decision: "found"
        entry: {
        "item_revision": "5411714/0",
        "description": "Booster Manifold Assembly",
        "dwg_revision": "4847193/0",
        "pages": [30, 31]
        }

        EXAMPLE B
        User query: "Auto Accumulator Dump Valve"
        Decision: "found"
        entry: {
        "item_revision": "2601072/1",
        "description": "Auto Accumulator Dump Valve",
        "dwg_revision": "3213299/0",
        "pages": [32, 33]
        }

        EXAMPLE C
        User query: "Split Flange Set 2487817/3"
        Decision: "found"
        entry: {
        "item_revision": "2487817/3",
        "description": "Split Flange Set",
        "dwg_revision": "2487767/0",
        "pages": [18, 19]
        }
        """))
    user = HumanMessage(content=f"USER QUERY:\n{drawing}\n\nTOC (markdown):\n{toc}")

    result = structured_llm.invoke([system, user])

    # Return JSON string for ToolMessage.content
    return result.model_dump_json()

client = SearchClient(
    endpoint=app_settings.azure_search_credentials.endpoint,
    index_name=app_settings.azure_search_credentials.index,
    credential=AzureKeyCredential(app_settings.azure_search_credentials.key)
)  

def get_fresh_sas_token():
    return generate_container_sas(
        account_name=app_settings.azure_storage_credentials.account,
        container_name=app_settings.azure_storage_credentials.container,
        account_key=app_settings.azure_storage_credentials.key,
        permission=ContainerSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(minutes=60),
    )

def url_from_blob(blob_name: str) -> str:
    sas_token = get_fresh_sas_token()
    return (
        f"https://{app_settings.azure_storage_credentials.account}.blob.core.windows.net/"
        f"{app_settings.azure_storage_credentials.container}/{blob_name}?{sas_token}"
    )

@tool(parse_docstring=True)
def drawing_image_links(
    pages: List[int],
    document_name: str
) -> str:
    """Return image URLs for mechanical drawing pages.

    Use this only when the model must visually inspect a drawing or bill of material
    (e.g., read dimensions, part numbers, quantities). Call this after page_locator
    returns page numbers.

    Args:
        pages (List[int]): Page numbers to fetch as images.
        document_name (str, optional): Name of the supported mechanical drawing
            package. Defaults to "Husky_2_Mechanical_Drawing_Package".

    Returns:
        str: JSON string with keys:
            - "document": the document name.
            - "results": a list of objects, each with:
                - "page": the page number (int).
                - "image_url": an HTTPS URL to the page image.
            If the document is not supported, "results" is an empty list.
    """

    norm_pages = sorted(dict.fromkeys(int(p) for p in pages))
    results: List[Dict[str, Any]] = []
    for p in norm_pages:
        doc_id = f"Husky_2_Mechanical_Drawing_Package-p{p}"
        raw = client.get_document(key=doc_id)
        metadata = json.loads(raw["metadata"])
        blob = metadata.get("blob_name")
        url = url_from_blob(blob)
        results.append({"page": p, "image_url": url})

    
    return json.dumps({
        "document": document_name,
        "results": results
    })
