
import json
from backend.state import State
from langchain.schema import SystemMessage, HumanMessage, BaseMessage  # Add this import or adjust based on your actual library
from pydantic import BaseModel, Field
from typing import List, Optional
from backend.assets.toc_data import toc
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from backend.client import get_llm
from backend.settings import (
    app_settings,
)
from langgraph.types import StreamWriter 
from azure.storage.blob import generate_container_sas, ContainerSasPermissions
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import uuid
import time

llm = get_llm()


# ---------- Structured Output ----------
class PagePredictResponse(BaseModel):
    pages: List[int] = Field(
        default_factory=list,
        description="List of BOM page numbers to show the drawing, if applicable."
    )
    answer: Optional[str] = Field(
        default=None,
        description="Direct response to the user's query, used when the user is not asking for a drawing."
    )
    clarification_needed: bool = Field(
        default=False,
        description="True if the user's query was ambiguous or underspecified."
    )

# -- Bind structured output model to LLM --
page_locator_llm = llm.with_structured_output(PagePredictResponse)

def drawing_rewriter_node(state: State) -> dict:
    # Get the last 7 messages
    last_messages = state["messages"][-7:]


    system = SystemMessage(
        content=(
            "You are a query rewriter. Using the following conversation context, "
            "rewrite the most recent *user* query so it is self-contained, precise, "
            "and technically accurate. Preserve page refs, part numbers, units, and fault codes. "
            "Return ONLY the rewritten query text."
        )
    )
    # Send to LLM as structured output
    result = llm.invoke([system, *last_messages])

    return {"rewritten": result.content.strip()}



async def page_locator_node(state: State, writer: StreamWriter) -> dict:
    query = state.get("rewritten")
    # 3) Build messages for the LLM
    system = SystemMessage(content=(
    "You are an assistant with access to a table of contents (BOM) and a user query about mechanical drawings or parts.\n\n"
    "The table of contents is a list of BOM entries with four columns:\n"
    "1. Page Number (this is the BOM start page)\n"
    "2. Part Number\n"
    "3. Description\n"
    "4. Drawing Number (not a page number)\n\n"
    "Some rows may be section headers or group titles (e.g., 'Water Circuits') and do not contain part numbers or drawing numbers. These are **not** valid BOM entries and should be skipped when determining page ranges.\n\n"
    "Based on the user's query, respond in one of the following ways:\n\n"
    "- If the user is asking to **see a drawing of a specific part**, return a list of **contiguous page numbers** starting from the matched entry's page number (first column), up to (but not including) the next **valid BOM entry** (ignore section headers).\n"
    "- If the user's query **partially matches multiple parts**, return a helpful response listing the most likely matching part descriptions and their page numbers to help narrow down what drawing they are looking for. Add this response to the `answer` field and set `clarification_needed` to true.\n"
    "- If the user is asking a **general question** (e.g., 'what types of valve drawings are available?'), respond directly to the user in natural language using the `answer` field and set `clarification_needed` to true.\n"
    "- If the user's query exactly or partially matches **multiple BOM entries**, and it's not clear which one they meant, do NOT return a list of page numbers. Instead, respond with a list of the most likely matching entries (descriptions and page numbers) to help them choose, and set `clarification_needed` to true.\n"
    "- If the user's query matches multiple BOM entries — even if they all contain the same phrase (e.g., 'Robot Hood') — and they refer to different parts or drawing numbers, you MUST treat the request as ambiguous. Do NOT return a range of page numbers. Instead, list the matching entries with their descriptions and page numbers, and set `clarification_needed` to true so the user can choose the correct one.\n\n"
    "Do not guess or make up page numbers. Only use information present in the table of contents.\n"
    "Format your response nicely in markdown format \n"
    "Use *italics* sparingly for emphasis; avoid ALL CAPS.\n"
    "End with a concise follow-up question to guide the user.\n"
    ))
    user = HumanMessage(content=f"TOC:\n{toc}\n\nUSER QUERY:\n{query}")
    result = page_locator_llm.invoke([system, user])

    if result.clarification_needed or result.answer:
        writer(SimpleNamespace(                 
            id      = str(uuid.uuid4()),
            object  = "chat.completion.chunk",
            model   = "gpt-4o",
            created = int(time.time()),
            choices = [SimpleNamespace(
                index = 0,
                delta = SimpleNamespace(
                    role       = "assistant",
                    content    = result.answer,
                    citations  = [],
                    tool_calls = None
                )
            )]
        ))
        return {
            "route": "return",
            "pages": [],
            "messages": state["messages"] + [
                {"role": "assistant", "content": result.answer}
            ],
        }
    
    pages, seen = [], set()
    for p in result.pages:
        if isinstance(p, int) and p not in seen:
            pages.append(p); seen.add(p)
        
    return {
        "pages": pages,
        "route": "mechanical_drawing",
    }

client = SearchClient(
    endpoint=app_settings.azure_search_credentials.endpoint,
    index_name=app_settings.azure_search_credentials.index,
    credential=AzureKeyCredential(app_settings.azure_search_credentials.key)
)    

def url_from_blob(blob_name: str) -> str:
    sas_token = get_fresh_sas_token()
    return (
        f"https://{app_settings.azure_storage_credentials.account}.blob.core.windows.net/"
        f"{app_settings.azure_storage_credentials.container}/{blob_name}?{sas_token}"
    )

def get_fresh_sas_token():
    return generate_container_sas(
        account_name=app_settings.azure_storage_credentials.account,
        container_name=app_settings.azure_storage_credentials.container,
        account_key=app_settings.azure_storage_credentials.key,
        permission=ContainerSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(minutes=60),
    )

async def mech_drwg_ans (state: State, writer: StreamWriter):
    toc_ids = [f"Husky_2_Mechanical_Drawing_Package-p{p}" for p in state.get("pages")]
    urls = []
    citations = []
    for i, doc_id in enumerate(toc_ids):
        raw = client.get_document(key=doc_id)
        metadata = json.loads(raw["metadata"])
        blob = metadata.get("blob_name")
        page = metadata.get("page")
        url = url_from_blob(blob)  # This should return a full https://... URL
        urls.append(url)
        if page is not None:
            title = f"Page {page}"
            citations.append({
                "title": title,
                "url": url
            })

    chat_history = state.get("chat_history", [])

    # Get the last 5 messages
    chat_history = state["messages"][-5:]

    # System prompt
    system_prompt = (
        "You are the answer-generation agent for a mechanical-maintenance assistant. "
        "Use the mechanical drawings referenced below to answer the user’s question **clearly and accurately**.\n\n"

        "🖼  **Drawing access** – The user can open every drawing you mention in the “References” section under your reply. "
        "When relevant, briefly tell them **what** each drawing shows (e.g., “Page 182: Robot-hood door, VE variant”) and remind them they can click it for full detail.\n\n"

        "✍️  **Response style** – One concise paragraph (3–5 sentences) is ideal. "
        "Explain the core information the user asked for, then add any key context that will help them interpret the drawing (dimensions, orientation, major components). "
        "Avoid referring to the image as “the provided image” or similar UI-breaking phrases.\n\n"

        "💡  **Guidance & next steps** – Finish with one or two follow-up suggestions if they would help the user move forward \n\n "

        "Stay factual, don’t invent data, and keep technical terminology precise."
    )

    # Image blocks + optional text message
    image_blocks = [{"type": "image_url", "image_url": {"url": url}} for url in urls]
    human_input = [
        {"type": "text", "text": "Please review the following mechanical drawing(s):"},
        *image_blocks
    ]

    # Full prompt
    messages: List[BaseMessage] = [
        SystemMessage(content=system_prompt),
        *chat_history,
        HumanMessage(content=human_input)
    ]

    async for chunk in llm.astream(messages):
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

    # ---------- final envelope with citations --------------------------------
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
                    content    = " ",
                    citations  = citations,
                    tool_calls = None
                )
            )
        ],
        citations = citations
    ))    
