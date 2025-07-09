from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from types import SimpleNamespace
import time, json
import uuid
from azure.storage.blob import BlobServiceClient, generate_container_sas, ContainerSasPermissions
from azure.core.exceptions import ResourceExistsError
from datetime import datetime, timedelta, timezone
from langchain_openai import AzureChatOpenAI
from langchain.chains   import LLMChain
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import re   
from langchain.schema import Document 
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain    

toc="""
| Pg# | Item / Revision | Description                           | Dwg / Revision |
|-----|-----------------|---------------------------------------|----------------|
|     |                 | Electrical Assemblies                 |                |
| 5   | 5488099/3       | RS485 ENCLOSURE                       | 5488099/3      |
| 7   | 2399471/3       | Electrical E-Stop Hardware Grp        | 5726144/0      |
|     |                 | Hydraulic Section                     |                |
| 9   | 2487799/1       | Split Flange Set                      | 2487767/0      |
| 9   | 2487798/1       | Split Flange Set                      | 2487767/0      |
| 9   | 2481966/2       | Split Flange Set                      | 2487767/0      |
| 11  | 6380864/0       | Clamp Manifold Assembly               | 4493108/0      |
| 13  | 6379905/0       | Injection Manifold Assembly           | 4917370/2      |
| 16  | 5994314/1       | Stroke Manifold Assembly              | 4852822/1      |
| 18  | 2487817/3       | Split Flange Set                      | 2487767/0      |
| 20  | 3764548/1       | Hose Restraint Assembly               | 3765171/2      |
| 22  | 2927241/1       | Split Flange Set                      | 2487767/0      |
| 24  | 2900164/2       | Pressure Gauge Assembly               | 5143491/2      |
| 26  | 2683677/3       | Directional Control Valve             | 3164733/0      |
| 28  | 2577036/1       | Split Flange Set                      | 2487767/0      |
| 30  | 5411714/0       | Booster Manifold Assembly             | 4847193/0      |
|     |                 | Hydraulic Serviceable Items           |                |
| 32  | 2601072/1       | Auto Accumulator Dump Valve           | 3213299/0      |
| 34  | 2642077/1       | Active Valve Cover                    | 3176670/1      |
| 36  | 3928979/0       | Cartridge Valve Cover                 | 3396410/0      |
| 38  | 2601070/0       | Manual Accumulator Dump Valve         | 3394959/0      |
| 40  | 2542629/0       | Cartridge Valve                       | 3176600/0      |
| 40  | 2524317/0       | Cartridge Valve                       | 3176600/0      |
| 42  | 2510956/2       | Directional Control Valve             | 3164733/0      |
| 44  | 2506821/0       | Cartridge Valve Cover                 | 3396410/0      |
| 46  | 2506793/0       | Cartridge Check Valve                 | 3201797/0      |
| 48  | 2477748/3       | Directional Control Valve             | 3164733/0      |
| 48  | 2477725/0       | Directional Control Valve             | 3164733/0      |
| 50  | 2155092/0       | Valve, Double Solenoid                | 3465073/1      |
| 52  | 746873/1        | Proportional Directional Valve        | 3427660/0      |
| 54  | 746805/1        | Active Cartridge Valve                | 3176670/1      |
| 56  | 3928985/0       | Cartridge Valve Cover                 | 3396410/0      |
| 58  | 735571/0        | Active Cartridge Valve                | 3176670/1      |
| 58  | 735572/0        | Active Cartridge Cover                | 3176670/1      |
|     |                 | Pneumatic Section                     |                |
| 60  | 5987802/4       | Clamp Air Services Group              | 5987803/3      |
| 64  | 5885819/1       | Air Filter Regulator Assembly         | 5994998/1      |
| 66  | 5611895/2       | Moving Platen Oil Retrieval           | 5439899/1      |
| 69  | 5403319/8       | Vacuum Transfer Services Group        | 5407799/4      |
|     |                 | Pneumatic Serviceable Items           |                |
| 74  | 5172445         | Air Valve, 3 Way Poppet 1.5"          |                |
| 74  | 5172439         | Air Valve, 3 Way Poppet 1"            |                |
| 74  | 746607/0        | Pneumatic Valve- Numatics             | 3465073/1      |
| 76  | 5172453/1       | Air Valve, 3 Way Poppet 1.5"          |                |
| 76  | 717457/1        | Air Valve                             | 3463436/0      |
|     |                 | Water Circuits                        |                |
| 78  | 5341339/4       | Final Base Water Group                | 5345879/2      |
| 79  | 5342556/2       | Base Water Group                      | 5345879/2      |
| 83  | 5390381/6       | Mold Cooling Group                    | 5551848/2      |
| 84  | 5390431/2       | Mold Cooling Hose Kit                 | 5551848/2      |
| 87  | 5466558/1       | No Mold Cooling Manual Valves         | 5734422/0      |
| 90  | 5591582/0       | Baumuller Motor Cooling Assy          | 5640818/0      |
| 92  | 5744951/1       | Robot Cabinet Cooling Group           | 4979677/0      |
|     |                 | Water Circuit Serviceable Item        |                |
| 94  | 2026444/0       | Valve                                 | 3406239/0      |
|     |                 | Safety Gates & Nameplates             |                |
| 96  | 3022670/2       | Nameplates, Clamp                     | 3022150/4      |
| 98  | 6461769/0       | Nameplate Group NA                    | 4610404/2      |
| 102 | 4147028/2       | HyPET Robot Cab NP-UL English         | 4610453/0      |
| 104 | 5314381/3       | Nameplates, Injection-NA Engli        | 5093006/6      |
| 106 | 5332408/2       | Sliding Doors Assy OS                 | 5296146/6      |
| 116 | 5332414/4       | Shutter Guard Assy OS                 | 5268456/5      |
| 123 | 5358135/6       | Clamp End Gate Assembly               | 5391084/3      |
| 130 | 5358141/4       | Robot End Gate Assembly               | 5383220/2      |
| 138 | 5358182/1       | Door Rail Assy OS                     | 5268978/4      |
|     |                 | Gate Assemblies                       |                |
| 145 | 5367200/5       | Vacuum End Gate Assembly              | 5391239/2      |
| 152 | 5398462/2       | Skirting Assembly                     | 5401392/1      |
| 154 | 5499617/4       | Standard Gates Assy                   | 5272402/6      |
| 156 | 5601541/3       | Stat. Platen Guards Assy              | 5610493/2      |
| 161 | 5680617/3       | Robot Gate Assembly                   | 5392642/0      |
| 163 | 5680618/5       | Conveyor End Gate Assembly            | 5386718/6      |
| 173 | 6054848/0       | Discharge Guard Air Return Ass        | 6054973/0      |
| 176 | 6201839/0       | Robot Hood Panel VE                   | 6165215/4      |
| 182 | 6205500/0       | Robot Hood Door VE                    | 6168538/3      |
| 187 | 6206679/0       | Robot Hood Door CE                    | 6156320/3      |
| 194 | 6208219/0       | Robot Hood Panel CE                   | 6131752/3      |
| 199 | 6210275/5       | Clamp Hood Assembly                   | 6199134/7      |
| 209 | 6245953/2       | Shutter Guard CE Assy                 | 6245983/3      |
| 218 | 6262190/6       | Dehumidification Enclosure Ass        | 6214454/1      |
| 221 | 6269702/2       | IMA Hood Door Assy                    | 6182736/5      |
| 226 | 4018482/9       | HyPET-HPP Gate Safety Kit             | 4686812/2      |
|     |                 | Clamp Section                         |                |
| 228 | 2328775/2       | Drop Bar Assembly                     | 4570677/0      |
| 230 | 2679128/2       | Ejector Booster HYPET300-500          | 2679128/2      |
| 232 | 2747262/4       | Safety Drop Bar Group                 | 4944048/1      |
| 235 | 2906589/2       | Final Clamp Group HL300               | 2733185/2      |
| 238 | 3880109/0       | Banana Magnet Assembly                | 3880109/0      |
| 240 | 3907064/1       | Locating Ring Filler Assembly         | 5255938/0      |
| 242 | 4095523/3       | Clamp Cyl. Seal Kit                   | 3890289/4      |
| 246 | 5188688/0       | Walkway Clamp Assembly                | 4155759/0      |
| 248 | 5319205/6       | Moving Platen Group                   | 5637992/2      |
| 251 | 5357878/3       | Final Clamp Hydraulics                | 5478298/1      |
| 256 | 5465661/1       | ASSY - Clamp IO Box (P9)              | 5465661/1      |
| 257 | 5470022/2       | HMI Group                             | 5465736/1      |
| 262 | 5512342/12      | Mold ID Hardware Group                | 5512674/0      |
| 264 | 5543466/0       | Platen Hydr.Hardware BOM              | 5418562/0      |
| 266 | 5591696/0       | Parts Drop Off Collector              | 5577619/0      |
| 270 | 5639850/0       | Column Assy HyPET4.0 300              | 4104020/1      |
"""
llm = AzureChatOpenAI(
    openai_api_version="2024-05-01-preview",  # or your deployed version # type: ignore
    azure_deployment="gpt-4o",
    azure_endpoint="https://conta-m9prji51-eastus2.services.ai.azure.com",
    openai_api_key="9RSNCLiFqvGuUVCxVF1CsmDTLNBkHpX1P1jfMsxGMxqR2ES2wCy8JQQJ99BDACHYHv6XJ3w3AAAAACOGSc3o", # type: ignore
    temperature=0.0,
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
     "- Mechanical drawings, part numbers, technical blueprints, dimensions, CAD references"
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
AZURE_SEARCH_ENDPOINT = "https://aisearchdocumentrag.search.windows.net"
AZURE_SEARCH_KEY      = "ICtH96hEtsivtOz4ug0nP1hUfuw5sMfoCbHAP9ARnRAzSeDt7Z0m" 
index_name: str = "pdfs"

client = SearchClient(
    endpoint=AZURE_SEARCH_ENDPOINT,
    index_name=index_name,
    credential=AzureKeyCredential(AZURE_SEARCH_KEY)
)

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
    vector_field_name     = VECTOR_FIELD,
)

retriever = vectorstore.as_retriever(
    search_type="hybrid",
    k=10,              # was 6
  
)

def _parse_page_numbers(raw: str) -> list[int]:
    """Return sorted unique page ints extracted from any LLM text."""
    return sorted({int(n) for n in re.findall(r"\d+", raw)})

def _docs_to_citations(docs):
    """Return a list[dict] each with id/title/url/chunk so the Vue panel shows them."""
    citations = []
    for i, d in enumerate(docs):
        blob = d.metadata.get("blob_name")
        if not blob:
            continue
        page = d.metadata.get("page")
        if page is not None:
            title = f"Page {page}"
        else:
            title = d.metadata.get("source", f"Chunk {i+1}")
        citations.append({
            "title": title,
            "url":  url_from_blob(blob),
        })
    return citations

# ── 3. Build multimodal prompt ───────────────────4────────────────────────────
def build_prompt(kwargs):
    ctx = kwargs["context"]
    question = kwargs["question"]
    is_drawing_query = kwargs.get("is_drawing_query", False)
    # Joins the page content of each document with a reference tag [doc#]
    context_text = "\n".join(
        f"{t.page_content} [doc{i+1}]"
        for i, t in enumerate(ctx["texts"])
    )
    prompt_header = (
        f"Conversation so far:\n{history_text}\n"
        f"---\nContext:\n{context_text}"
    )
    blocks = [{"type": "text", "text": prompt_header}]
    blocks.append({"type": "text", "text": f"\nQuestion: {question}"})
    
    if not is_drawing_query:
        system_rules = (
        "You are an industrial maintenance assistant. "
        "• Put any tabular data inside a fenced Markdown table. "
        "If any required value is missing from Context, answer: 'I do not have that information.'"
        """ When listing rows & columns, output a **GitHub-Flavored Markdown table** using pipes (|) and dashes, no code fences.
        When creating tables, copy each cell exactly as shown in Context (no re-ordering, no summarising).

            Example:
            | Column A | Column B |
            |---------|---------|
            | 10 V    | OK      |
            
        keep answer to less than 1000 tokens
            
            """       
        )
        # Passing images to LLM for non mechanical drawing documents
        # for url in ctx["images"]:
        #     blocks.append({"type": "image_url", "image_url": {"url": url}})
    else:
        system_rules =  (
        "You are a technical assistant that answers questions based on mechanical drawings and Bill of Materials (BOM) data.\n"
        "If any required value is missing from Context, answer: 'I do not have that information.'"
        "Use the provided context (including component descriptions, drawing references, and part numbers) to give clear and accurate responses.\n"
        "- Tell the user: \"You can view the corresponding drawings by clicking the mechanical drawing link below.\"\n"
        "- End with: \"Feel free to ask any follow-up questions if you need more details or clarification.\"\n"
        "- Summarize where the user can find relevant drawings or BOM entries (based on the context).\n"
        )
        for url in ctx["images"]:
            blocks.append({"type": "image_url", "image_url": {"url": url}})

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

def to_lc_doc(raw: dict) -> Document:
    """
    Convert a raw Azure AI Search record to LangChain Document.
    - Flattens nested stringified 'metadata'
    - Drops unused or vector fields
    """
    meta = {}

    # Start by parsing stringified JSON metadata if present
    if "metadata" in raw and isinstance(raw["metadata"], str):
        try:
            meta.update(json.loads(raw["metadata"]))
        except json.JSONDecodeError:
            pass

    # Include top-level useful fields
    for k in ("id", "blob_name"):
        if k in raw:
            meta[k] = raw[k]

    # Set default source if not already present
    meta.setdefault("source", meta.get("blob_name", f"Chunk {meta.get('page', '-')}" ))

    return Document(
        page_content=raw.get("content", "").strip(),
        metadata=meta,
    )


async def run_test_rag(chat_history: list, user_query: str):
    global history_text                         # let build_prompt see the update
    history_text = ""
    for m in chat_history:                      # m is a BaseMessage
        role = "User" if m.type == "human" else "Assistant"
        history_text += f"{role}: {m.content}\n"

    # 1. Detect if it's a mechanical drawing query (lightweight keyword check)
    drawing_keywords = ["drawing", "part number", "BOM", "blueprint", "revision", "dwg", "item", "description"]
    is_drawing_query = any(kw in user_query.lower() for kw in drawing_keywords)
    print(f"DRAWING QUERY BOOLEAN: {is_drawing_query}")

    # 2. Choose query rewrite prompt based on type
    query_rewrite_prompt = ChatPromptTemplate.from_messages([
        ("system",
        "You are a query rewriting assistant that specializes in improving retrieval for Retrieval-Augmented Generation (RAG) systems.\n"
        "Your task is to take the original user query and rewrite it in a clearer, more keyword-rich way so that it matches relevant context stored in a vector database.\n"
        "Rewrite the query using concise, formal language, and add any technical terms or concepts that improve semantic alignment. Do not change the user’s intent. Do not add unrelated information."
        "Here is the prior conversation:\n\n{history}\n\n"),
        ("user", "{query}")
    ])

    # 3. Rewrite the query
    query_rewrite_chain = LLMChain(llm=llm, prompt=query_rewrite_prompt)
    rewritten_query = await query_rewrite_chain.apredict(query=user_query, history=history_text)

    print(f"Rewritten query: {rewritten_query}")
    hits = []
    # 4. If drawing-related, predict page from ToC
    if is_drawing_query:
        page_lookup_prompt = ChatPromptTemplate.from_messages([
            ("system",
           "You are given a table of contents and a user query about mechanical drawings.\n"
            "The table of contents is a list of BOM entries, each with four columns:\n"
            "1. Page Number (leftmost column — this is the BOM start page)\n"
            "2. Part Number\n"
            "3. Description\n"
            "4. Drawing Number (not a page number)\n"
            "\n"
            "Your task is to:\n"
            "1. Find the **first** BOM entry whose description matches the user query.\n"
            "2. Return all **contiguous page numbers** starting from that entry's BOM page (first column),\n"
            "   up to but **not including** the BOM page of the next entry in the table.\n"
            "\n"
            "If you can NOT find a matching entry, return an empty string.\n"
            "Only return a **comma-separated list of page numbers NO WORDS, PAGE NUMBERS ONLY**.\n"
            "Do NOT include any drawing numbers or part numbers.\n"
            "Do NOT include multiple matching entries — only the **first match**.\n"
            "Do NOT guess or invent page numbers.\n"
            "Use only the page numbers found in the first column of the table.\n"),
            ("human", "TOC:\n\n{toc}\n\nQuery:\n{query}")
        ])
        page_lookup_chain = LLMChain(llm=llm, prompt=page_lookup_prompt)
        page_result = await page_lookup_chain.apredict(toc=toc, query= rewritten_query)
        print(f"📄 Page prediction result: {page_result}")
        page_numbers = _parse_page_numbers(page_result) 
        toc_ids = [f"Husky_2_Mechanical_Drawing_Package-p{p}" for p in page_numbers]
        for doc_id in toc_ids:
            raw = client.get_document(key=doc_id)   # ➜ dict
            hits.append(to_lc_doc(raw)) 
        citations = _docs_to_citations(hits)
    else:
        hits = await retriever.aget_relevant_documents(rewritten_query)
        citations = ""

    # ──  Assemble and run chain ────────────────────────────────────────────────
    chain = (
        {
            "context": RunnableLambda(lambda _q: split_docs(hits)),
            "question": RunnablePassthrough(),
            "is_drawing_query": RunnableLambda(lambda _q: is_drawing_query),
        }
        | RunnableLambda(build_prompt)
        | llm  # gpt-4o in streaming mode
    )

    # ──  Stream response and collect answer text ───────────────────────────────

    async for chunk in chain.astream(rewritten_query):
        token = chunk.content
        if token:
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

 