from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessageChunk,SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from types import SimpleNamespace
import time
import uuid
from azure.storage.blob import BlobServiceClient, generate_container_sas, ContainerSasPermissions
from azure.core.exceptions import ResourceExistsError
from datetime import datetime, timedelta, timezone
import json
from langchain_openai import AzureChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains   import LLMChain

llm = AzureChatOpenAI(
    openai_api_version="2024-05-01-preview",  # or your deployed version # type: ignore
    azure_deployment="gpt-4o",
    azure_endpoint="https://conta-m9prji51-eastus2.services.ai.azure.com",
    openai_api_key="9RSNCLiFqvGuUVCxVF1CsmDTLNBkHpX1P1jfMsxGMxqR2ES2wCy8JQQJ99BDACHYHv6XJ3w3AAAAACOGSc3o", # type: ignore
    temperature=0,
    streaming=True,  # enable streaming
)
router_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a classifier. Decide if the user query needs to search the uploaded maintenance documents.\n"
     "Answer ONLY `yes` or `no`.\n"
     "Do not explain. Do not include any other words.\n"
     "\n"
     "Say `yes` if the query asks about:\n"
     "- pump setup, calibration, swash plate, pressure command, jumper settings, VT5041 amplifier, Rexroth pump setup\n"
     "- servo valve operation, Moog valves, spool position, pilot unlock valve, hydraulic troubleshooting, faults, alarms\n"
     "- voltages, PIN measurements, breakout box, system/extruder pumps, Husky G-Line, HyPET, Hylectric, Quadloc machines\n"
     "- Mechanical drawings and part numbers"
     "\n"
     "Say `no` if the query is:\n"
     "- greetings, general conversation, personal questions, jokes\n"
     "- not about equipment setup, troubleshooting, hydraulic systems, or machine faults\n"
     "\n"
     "You must output ONLY one word: `yes` or `no`."
    ),
    ("user", "{query}")
])
router_chain = LLMChain(llm=llm, prompt=router_prompt)

AZURE_STORAGE_ACCOUNT = "stdocumentra243626647348"
AZURE_STORAGE_KEY = "J1qMHEQBce8UJEn5Le4uYrSZQJxeoe2Np/lg0G15pITaguQtQxw4Yt9xargTrc+hla2AgCQjjZM8+AStqA8hxw=="
CONTAINER = "pages" 

service = BlobServiceClient(
    f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net",
    credential=AZURE_STORAGE_KEY,
)
container = service.get_container_client(CONTAINER)
try:
    container.create_container()          # private by default
except ResourceExistsError:
    pass  

CONTAINER_SAS = generate_container_sas(
    account_name   = AZURE_STORAGE_ACCOUNT,
    container_name = CONTAINER,
    account_key    = AZURE_STORAGE_KEY,
    permission     = ContainerSasPermissions(read=True),   # no 'list'
    expiry         = datetime.now(timezone.utc) + timedelta(days=1),
)
#images folder path
IMAGES_DIR   = "images_pump" 
CONTAINER_SAS = f"{CONTAINER_SAS}"

def url_from_blob(blob_name: str) -> str:
    return (
        f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/"
        f"{CONTAINER}/{blob_name}?{CONTAINER_SAS}"
    )

AZURE_SEARCH_ENDPOINT = "https://aisearchdocumentrag.search.windows.net"
AZURE_SEARCH_KEY      = "ICtH96hEtsivtOz4ug0nP1hUfuw5sMfoCbHAP9ARnRAzSeDt7Z0m"  # or paste the key here
INDEX_NAME            = "pages"                      # all lower-case
EMBED_DIM             = 1536  
VECTOR_FIELD    = "content_vector"

# ── 1) Configure an Azure‐backed OpenAIEmbeddings instance ─────────────────
AZURE_OPENAI_API_BASE    = "https://conta-m9prji51-eastus2.openai.azure.com"
AZURE_OPENAI_API_KEY     = "9RSNCLiFqvGuUVCxVF1CsmDTLNBkHpX1P1jfMsxGMxqR2ES2wCy8JQQJ99BDACHYHv6XJ3w3AAAAACOGSc3o"
AZURE_OPENAI_API_VERSION = "2023-05-15"             # use the exact API version your Foundry resource supports
AZURE_EMBEDDING_DEPLOY   = "text-embedding-ada-002" # the name of your deployed embedding model in Azure Foundry

azure_embeddings = AzureOpenAIEmbeddings(
    model                = AZURE_EMBEDDING_DEPLOY,   # e.g. "text-embedding-ada-002"
    azure_endpoint       = AZURE_OPENAI_API_BASE,
    openai_api_version   = AZURE_OPENAI_API_VERSION, # type: ignore
    api_key              = AZURE_OPENAI_API_KEY,
)

index_name: str = "pdfs"
vectorstore = AzureSearch(
    azure_search_endpoint=AZURE_SEARCH_ENDPOINT,
    azure_search_key     = AZURE_SEARCH_KEY,
    index_name = index_name,
    embedding_function = azure_embeddings,
    vector_search_dimensions = 1536, 
    text_key              = "page_content",
    vector_field_name     = VECTOR_FIELD
)

retriever = vectorstore.as_retriever(
    search_type="hybrid",
     k=6,
   )
# keep only the N most recent user/assistant pairs
memory = ConversationBufferMemory(return_messages=True)

chat_history = memory.load_memory_variables({}).get("history", [])
history_text = ""
for m in chat_history:                     # m is a BaseMessage
    role = "User" if m.type == "human" else "Assistant"
    history_text += f"{role}: {m.content}\n"
    
def trim_and_dedupe(docs, max_chars: int = 1200):
    """Remove duplicate text blocks and cap each chunk length."""
    seen, out = set(), []
    for d in docs:
        text = d.page_content[:max_chars].strip()
        if text not in seen:
            seen.add(text)
            d.page_content = text              # keep the trimmed version
            out.append(d)
    return out


def _docs_to_citations(docs):
    """Return a list[dict] each with id/title/url/chunk so the Vue panel shows them."""
    citations = []
    for i, d in enumerate(docs):
        citations.append({
        
            "title": d.metadata.get("source", d.metadata.get("file_name", f"Chunk {i+1}")),
            "url": url_from_blob(d.metadata["blob_name"]),     # you already have this helper
            
        })
    return citations

# ── 3. Build multimodal prompt ───────────────────────────────────────────────
def build_prompt(kwargs):
    ctx = kwargs["context"]
    question = kwargs["question"]

    context_text = "\n".join(
f"{t.page_content} [doc{i+1}]"
for i, t in enumerate(ctx["texts"])
)
    prompt_header = (
        f"Conversation so far:\n{history_text}\n"
        f"---\nContext:\n{context_text}"
    )
    blocks = [{"type": "text", "text": prompt_header}]
    # for url in ctx["images"]:
    #     blocks.append({"type": "image_url", "image_url": {"url": url}})
    blocks.append({"type": "text", "text": f"\nQuestion: {question}"})
    system_rules = (
        "You are an industrial maintenance assistant. "
        "• Put any tabular data inside a fenced Markdown table. "
        """ When listing rows & columns, output a **GitHub-Flavored Markdown table** using pipes (|) and dashes, no code fences.
            Example:
            | Column A | Column B |
            |---------|---------|
            | 10 V    | OK      |"""
            "keep all your answers to 250 tokens or less."
    )

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_rules),
        HumanMessage(content=blocks),
    ])


# ── 2. Helper to split out text vs images ────────────────────────────────────
def split_docs(docs):
    out = {"texts": [], "images": []}
    for d in docs:
        out["texts"].append(d)
        if "blob_name" in d.metadata:
            out["images"].append(url_from_blob(d.metadata["blob_name"]))
   
    return out
    
async def run_test_rag(user_query: str):

    
 #Rewrite the query
    query_rewrite_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a query optimizer for a maintenance assistant supporting Husky HyPET, Hylectric, and Quadloc machines."
      "  Your task is to rewrite the user's query so it will help improve retrieval of maintenance documents related to:"
       " - troubleshooting faults, alarms, error codes"
       " - servo valves, Rexroth Master/Slave pumps, Moog breakout box measurements"
        "- machine setup, calibration, signal checks, hydraulic systems"
        "- mechanical drawings and part numbers"),
        ("user", "{query}")
])
    query_rewrite_chain = LLMChain(llm=llm, prompt=query_rewrite_prompt)
    rewritten_query = await query_rewrite_chain.apredict(query=user_query)
    print(f"Rewritten query: {rewritten_query}")
   
    # ── 1. Retrieve supporting documents ─────────────────────────────────────────
    hits = trim_and_dedupe(
    await retriever.aget_relevant_documents(rewritten_query)
)
    
    citations = _docs_to_citations(hits)  # → list[dict] tailor‑made for the UI
    
    # ── 4. Assemble and run chain ────────────────────────────────────────────────
    chain = (
        {
            "context": RunnableLambda(lambda _q: split_docs(hits)),
            "question": RunnablePassthrough(),
        }
        | RunnableLambda(build_prompt)
        | llm  # gpt-4o in streaming mode
    )

    # ── 5. Stream response and collect answer text ───────────────────────────────
    answer_parts = []

    async for chunk in chain.astream(rewritten_query):
        token = chunk.content
        if token:
            answer_parts.append(token)
            yield SimpleNamespace(
                id=str(uuid.uuid4()),
                object="chat.completion.chunk",
                model="gpt-4o",
                created=int(time.time()),
                choices=[
                    SimpleNamespace(
                        index=0,
                        delta=SimpleNamespace(
                            role="assistant",
                            content=token,
                            tool_calls=None
                        )
                    )
                ]
            )

    # ── 6. Final assistant chunk with full text + citations ─────────────────────
    final_answer = "".join(answer_parts)
    memory.save_context(
     {"input": user_query},
    {"output": final_answer}
)

    yield SimpleNamespace(
        id=str(uuid.uuid4()),
        object="chat.completion.chunk",
        model="gpt-4o",
        created=int(time.time()),
        choices=[
            SimpleNamespace(
                index=0,
                delta=SimpleNamespace(
                    role="assistant",
                    content=" ",
                    citations=citations,
                    tool_calls=None
                )
            )
        ],
        citations=citations
    )

 