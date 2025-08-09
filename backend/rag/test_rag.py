# from langchain_community.vectorstores.azuresearch import AzureSearch
# from langchain_openai import AzureOpenAIEmbeddings
# from langchain_core.runnables import RunnableLambda, RunnablePassthrough
# from langchain_core.messages import HumanMessage, SystemMessage
# from langchain_core.prompts import ChatPromptTemplate
# from types import SimpleNamespace
# import time, json
# import uuid
# from azure.storage.blob import BlobServiceClient, generate_container_sas, ContainerSasPermissions
# from azure.core.exceptions import ResourceExistsError
# from datetime import datetime, timedelta, timezone
# from langchain_openai import AzureChatOpenAI
# from langchain.chains   import LLMChain
# from azure.search.documents import SearchClient
# from azure.core.credentials import AzureKeyCredential
# import re   
# from langchain.schema import Document 
# from langchain_core.prompts import ChatPromptTemplate
# from langchain.chains import LLMChain    
# from langchain.utils.math import cosine_similarity

# # from langsmith import traceable
# # from langsmith import trace
# import os

# # os.environ["LANGCHAIN_TRACING_V2"] = "true"
# # os.environ["LANGSMITH_API_KEY"] = "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"
# # os.environ["LANGSMITH_PROJECT"] = "testing-rag"
# # os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"






# # ── 1) Configure an Azure‐backed OpenAIEmbeddings instance ─────────────────
# AZURE_OPENAI_API_BASE    = "https://conta-m9prji51-eastus2.openai.azure.com"
# AZURE_OPENAI_API_KEY     = "9RSNCLiFqvGuUVCxVF1CsmDTLNBkHpX1P1jfMsxGMxqR2ES2wCy8JQQJ99BDACHYHv6XJ3w3AAAAACOGSc3o"
# AZURE_OPENAI_API_VERSION = "2023-05-15"             # use the exact API version your Foundry resource supports
# AZURE_EMBEDDING_DEPLOY   = "text-embedding-ada-002" # the name of your deployed embedding model in Azure Foundry

# azure_embeddings = AzureOpenAIEmbeddings(
#     model                = AZURE_EMBEDDING_DEPLOY,   # e.g. "text-embedding-ada-002"
#     azure_endpoint       = AZURE_OPENAI_API_BASE,
#     openai_api_version   = AZURE_OPENAI_API_VERSION, # type: ignore
#     api_key              = AZURE_OPENAI_API_KEY,
# )

# # ── Prepare routing descriptions ────────────────────────────────────────
# routing_descriptions = {
#     "mechanical_drawing": (
#         "Use this route for requests involving diagram illustrations, CAD drawings, Bill of Materials (BOM), part numbers, component revisions, or specific references to page numbers in technical drawing packages. "
#         "Examples include: locating a valve in the drawing set, identifying a drawing number, or asking for part compatibility across revisions."
#     ),
#     "troubleshooting": (
#         "Use this route for technical issues, alarms, calibration steps, electrical or hydraulic faults, and setup procedures. "
#         "Covers questions about Moog servo valves, Rexroth A10V/A4V pumps, VT5041 amplifier cards, wiring diagnostics, pressure readings, jumper settings, breakout box measurements, or tuning instructions."
#     ),
#     "general": (
#         "Use this route for greetings, questions unrelated to machinery or setup, or vague/general inquiries not referring to part drawings or faults. "
#     )
# }

# # ── Prepare Text and Keys ────────────────────────────────────────────────────
# route_texts = list(routing_descriptions.values())
# route_keys = list(routing_descriptions.keys())

# # ── One-time embedding of route descriptions ────────────────────────────────────────────────────
# route_embeddings = azure_embeddings.embed_documents(route_texts)

# # ── Initialize vector store and retriever ────────────────────────────────────────────────────
# index_name: str = "pdfs"
# vectorstore = AzureSearch(
#     azure_search_endpoint=AZURE_SEARCH_ENDPOINT,
#     azure_search_key     = AZURE_SEARCH_KEY,
#     index_name = index_name,
#     embedding_function = azure_embeddings,
#     vector_search_dimensions = 1536, 
#     text_key              = "page_content",
#     vector_field_name     = VECTOR_FIELD,
# )
# retriever = vectorstore.as_retriever(
#     search_type="hybrid",
#     k=6,              # was 10
  
# )

# # ── Prepare the query-rewrite prompt and chain ────────────────────────────────────────────────
# query_rewrite_prompt = ChatPromptTemplate.from_messages([
#     # ---- SYSTEM ---------------------------------------------------
#     ("system",
#      "You are a **query-rewriter**.  You never answer questions.\n"
#      "GOAL → Produce ONE LINE (≤25 words) that is an optimized, standalone search query using clear, keyword-rich language, while preserving the original intent and goal of the user.\n"
#      "HOW →\n"
#      "• Use the CURRENT_QUESTION plus any missing subject words from RECENT_HISTORY.\n"
#      "• Keep all technical terms verbatim (± Vdc, Pin 3, enable signal, etc.).\n"
#      "• Do NOT add analogies, definitions, or explanations.\n"
#      "• Do NOT answer the question.\n"
#      "• Return *only* the rewritten query text, no punctuation before/after, no extra lines.\n"
#      "**Strict Instructions:**\n"
#          "- Do NOT remove any critical keywords present in the original query.\n"
#          "- Do NOT add speculative content or terms not found in the original query unless they are synonymous technical equivalents or found in RECENT_HISTORY.\n"
#          "- Do NOT rephrase into vague or general language — be specific and precise.\n"
#          "- Do NOT include any greetings, explanations, or formatting. Return only the rewritten query text.\n"
#         "- Do NOT use any special characters, emojis, or formatting like bold/italics.\n"
#          "- You MAY include intent modifiers like 'for beginners', 'like a 5 year old', or 'for experts' **if they are clearly part of the user’s query or style request."
#     ),
#     # ---- FEW-SHOT EXAMPLES ----------------------------------------
#     # ❶ follow-up without subject
#     ("human", "RECENT_HISTORY:\nUser: What is the enable signal voltage range?\nAssistant: …\n\nCURRENT_QUESTION:\nWhy is it important?"),
#     ("assistant", "importance of enable signal voltage range Moog servo valve breakout box"),
#     # ❷ “explain like 5” request
#     ("human", "RECENT_HISTORY:\nUser: How does a servo valve control flow?\nAssistant: …\n\nCURRENT_QUESTION:\nExplain it like I'm 5"),
#     ("assistant", "servo valve flow control principle electrohydraulic mechanism explanation like a 5 year old"),

#     ("human", "CURRENT_QUESTION: what's a hydraulic pump do in kid language?"),
#     ("assistant", "hydraulic pump basic function explanation like a 5 year old"),

#     ("human", "CURRENT_QUESTION: explain A10V pump to a junior technician"),
#     ("assistant", "A10V hydraulic pump function explained for junior technician"),

#     ("human", "CURRENT_QUESTION: explain directional valve in simple terms"),
#     ("assistant", "directional valve purpose and operation simple explanation for beginners"),

#     # ---- REAL-TIME SLOT -------------------------------------------
#     ("human",
#      "RECENT_HISTORY:\n{history}\n\nCURRENT_QUESTION:\n{query}")
# ])
# query_rewrite_chain = LLMChain(llm=llm,prompt=query_rewrite_prompt)

# # ── QUERY-REWRITE HELPER ────────────────────────────────────────────────────
# async def rewrite_query(user_query: str, history: str) -> str:
#     """Return an LLM-rewritten version of `user_query`."""
#     return await query_rewrite_chain.apredict(query=user_query, history=history)

# # ── Helper to convert blob name to URL ────────────────────────────────────────────────
# def url_from_blob(blob_name: str) -> str:
#     sas_token = get_fresh_sas_token()
#     return (
#         f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/"
#         f"{CONTAINER}/{blob_name}?{sas_token}"
#     )

# # ── Helper to parse page numbers from LLM text ────────────────────────────────────────────────
# def _parse_page_numbers(raw: str) -> list[int]:
#     """Return sorted unique page ints extracted from any LLM text."""
#     return sorted({int(n) for n in re.findall(r"\d+", raw)})

# # ── Helper to convert documents to citations ────────────────────────────────────────────────
# def _docs_to_citations(docs):
#     """Return a list[dict] each with id/title/url/chunk so the Vue panel shows them."""
#     citations = []
#     for i, d in enumerate(docs):
#         blob = d.metadata.get("blob_name")
#         if not blob:
#             continue
#         page = d.metadata.get("page")
#         if page is not None:
#             title = f"Page {page}"
#         else:
#             title = d.metadata.get("source", f"Chunk {i+1}")
#         citations.append({
#             "title": title,
#             "url":  url_from_blob(blob),
#         })
#     return citations

# # ── Helper to build the prompt for the LLM ────────────────────────────────────────────────
# def build_prompt(kwargs):
#     ctx = kwargs["context"]
#     question = kwargs["question"]
#     is_drawing_query = kwargs.get("is_drawing_query", False)
#     # Joins the page content of each document with a reference tag [doc#]
#     context_text = "\n".join(
#         f"{t.page_content} [doc{i+1}]"
#         for i, t in enumerate(ctx["texts"])
#     )
#     prompt_header = (
#         f"Conversation so far:\n{history_text}\n"
#         f"---\nContext:\n{context_text}"
#     )
#     blocks = [{"type": "text", "text": prompt_header}]
#     blocks.append({"type": "text", "text": f"\nQuestion: {question}"})
    
#     if not is_drawing_query:
#         system_rules = (
#         "You are an industrial maintenance assistant. "
#         "• Put any tabular data inside a fenced Markdown table. "
#         """You are an industrial maintenance assistant for hydraulic and servo-controlled machines, including Husky G-Line, Hylectric, HyPET, and Quadloc models. You help users troubleshoot issues with Rexroth A10V/A4V pumps, VT5041 amplifier cards, Moog servo valves, and associated control systems.

#         Your answers must be clear, factual, helpful, and always based strictly on the context provided. Do not guess or make assumptions. If any required information is missing from the documents, respond with: "I do not have that information in the current context. Please provide more detail."

#         Rules:
#         • Always verify and fact-check your answer against the provided technical documentation before responding.
#         • If unsure or ambiguous, ask the user for clarification instead of assuming intent.
#         • Do NOT summarize or reword numerical or calibration values. Repeat them exactly as shown.
#         • If a user asks about test points, voltages, jumper settings, or pin numbers, respond with the exact values from the documentation.
#         • When referencing tabular data (voltages, jumper settings, resistance values, etc.), use a **GitHub-Flavored Markdown table** with pipes (`|`) and dashes (`-`). Do NOT use code fences or bullet lists.
#         • Do NOT reorder, omit, or paraphrase data from any table.
#         • If giving step-by-step instructions, use a numbered list.
#         • When referring to measurement procedures, safety steps, or tools (e.g. breakout box, multimeter, jumper plug), mention specific document-based terminology and steps.

#         Example table:
#         | Pin | Signal               | Voltage       |
#         |-----|----------------------|---------------|
#         | 1   | Pressure Command     | +8.0V         |
#         | 4   | Swivel Angle         | +9.9V (±0.1V) |

#         Always prioritize precision over brevity. If multiple procedures apply, summarize each clearly and label them (e.g., "Step 4.1 – A10VFE1 Pumps", "Section 2.2.3 – Servo Valve Opening Negative Fault").

#         Never speculate. If the query is vague, say: "Can you clarify the exact machine, card type, or valve you're referring to?"

#         Be professional, clear, and accurate.
            
#             """       
#         )
#         # Passing images to LLM for non mechanical drawing documents
#         # for url in ctx["images"]:
#         #     blocks.append({"type": "image_url", "image_url": {"url": url}})
#     else:
#         system_rules =  (
#         "You are a technical assistant that answers questions based on mechanical drawings and Bill of Materials (BOM) data.\n"
#         "Use the provided context (including drawing references, and part numbers) to give clear and accurate responses.\n"
#         "- Tell the user: \"You can view the corresponding drawings by viewing the mechanical parts below.\"\n"
#         "- End with: \"Feel free to ask any follow-up questions if you need more details or clarification.\"\n"
#         "- Summarize where the user can find relevant drawings or BOM entries (based on the context).\n"
#         )
#         for url in ctx["images"]:
#             blocks.append({"type": "image_url", "image_url": {"url": url}}) # type: ignore

#     return ChatPromptTemplate.from_messages([
#         SystemMessage(content=system_rules),
#         HumanMessage(content=blocks), # type: ignore
#     ])

# # ── Helper to split out text vs images ────────────────────────────────────
# def split_docs(docs):
#     out = {"texts": [], "images": []}
#     for d in docs:
#         out["texts"].append(d)
#         if "blob_name" in d.metadata:
#             out["images"].append(url_from_blob(d.metadata["blob_name"]))
   
#     return out

# def to_lc_doc(raw: dict) -> Document:
#     """
#     Convert a raw Azure AI Search record to LangChain Document.
#     - Flattens nested stringified 'metadata'
#     - Drops unused or vector fields
#     """
#     meta = {}

#     # Start by parsing stringified JSON metadata if present
#     if "metadata" in raw and isinstance(raw["metadata"], str):
#         try:
#             meta.update(json.loads(raw["metadata"]))
#         except json.JSONDecodeError:
#             pass

#     # Include top-level useful fields
#     for k in ("id", "blob_name"):
#         if k in raw:
#             meta[k] = raw[k]

#     # Set default source if not already present
#     meta.setdefault("source", meta.get("blob_name", f"Chunk {meta.get('page', '-')}" ))

#     return Document(
#         page_content=raw.get("content", "").strip(),
#         metadata=meta,
#     )


# # ── MAIN FUNCTION ────────────────────────────────────────────────────
# async def run_test_rag(chat_history: list, user_query: str, forced_route: str | None = None):
#     global history_text                         # let build_prompt see the update
#     history_text = ""
#     for m in chat_history:                      # m is a BaseMessage
#         role = "User" if m.type == "human" else "Assistant"
#         history_text += f"{role}: {m.content}\n"

#     route = forced_route
#     is_drawing_query = route == "mechanical_drawing"
#     print(f"DRAWING QUERY BOOLEAN: {is_drawing_query}")

#     hits = []
#     # 4. If drawing-related, predict page from ToC
#     if is_drawing_query:
#         page_lookup_prompt = ChatPromptTemplate.from_messages([
#             ("system",
#            "You are given a table of contents and a user query about mechanical drawings.\n"
#             "The table of contents is a list of BOM entries, each with four columns:\n"
#             "1. Page Number (leftmost column — this is the BOM start page)\n"
#             "2. Part Number\n"
#             "3. Description\n"
#             "4. Drawing Number (not a page number)\n"
#             "\n"
#             "Your task is to:\n"
#             "1. Find the **first** BOM entry whose description matches the user query.\n"
#             "2. Return all **contiguous page numbers** starting from that entry's BOM page (first column),\n"
#             "   up to but **not including** the BOM page of the next entry in the table.\n"
#             "\n"
#             "If you can NOT find a matching entry, return an empty string.\n"
#             "Only return a **comma-separated list of page numbers NO WORDS, PAGE NUMBERS ONLY**.\n"
#             "Do NOT include any drawing numbers or part numbers.\n"
#             "Do NOT include multiple matching entries — only the **first match**.\n"
#             "Do NOT guess or invent page numbers.\n"
#             "Use only the page numbers found in the first column of the table.\n"),
#             ("human", "TOC:\n\n{toc}\n\nQuery:\n{query}")
#         ])
#         page_lookup_chain = LLMChain(llm=llm, prompt=page_lookup_prompt)
#         page_result = await page_lookup_chain.apredict(toc=toc, query= user_query)
#         print(f"📄 Page prediction result: {page_result}")
#         page_numbers = _parse_page_numbers(page_result) 
#         toc_ids = [f"Husky_2_Mechanical_Drawing_Package-p{p}" for p in page_numbers]
#         for doc_id in toc_ids:
#             raw = client.get_document(key=doc_id)   # ➜ dict
#             hits.append(to_lc_doc(raw)) 
#         citations = _docs_to_citations(hits)
#     else:
#         hits = await retriever.aget_relevant_documents(user_query)
#         citations = ""

#     # ──  Assemble and run chain ────────────────────────────────────────────────
#     chain = (
#         {
#             "context": RunnableLambda(lambda _q: split_docs(hits)),
#             "question": RunnablePassthrough(),
#             "is_drawing_query": RunnableLambda(lambda _q: is_drawing_query),
#         }
#         | RunnableLambda(build_prompt)
#         | llm  # gpt-4o in streaming mode
#     )

#     # ──  Stream response and collect answer text ───────────────────────────────

#     async with trace(name="test-rag-response"):
#         async for chunk in chain.astream(user_query):
#             token = chunk.content
#             if token:
#                 yield SimpleNamespace(
#                     id=str(uuid.uuid4()),
#                     object="chat.completion.chunk",
#                     model="gpt-4o",
#                     created=int(time.time()),
#                     choices=[
#                         SimpleNamespace(
#                             index=0,
#                             delta=SimpleNamespace(
#                                 role="assistant",
#                                 content=token,
#                                 tool_calls=None
#                             )
#                         )
#                     ]
#                 )

#     yield SimpleNamespace(
#         id=str(uuid.uuid4()),
#         object="chat.completion.chunk",
#         model="gpt-4o",
#         created=int(time.time()),
#         choices=[
#             SimpleNamespace(
#                 index=0,
#                 delta=SimpleNamespace(
#                     role="assistant",
#                     content=" ",
#                     citations=citations,
#                     tool_calls=None
#                 )
#             )
#         ],
#         citations=citations
#     )