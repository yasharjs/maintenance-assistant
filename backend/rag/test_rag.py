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
from langchain.utils.math import cosine_similarity

from langsmith import traceable
from langsmith import trace
import os

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGSMITH_API_KEY"] = "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"
os.environ["LANGSMITH_PROJECT"] = "testing-rag"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"

#hello


toc="""
| Pg# | Item / Revision | Description                           | Dwg / Revision |
|-----|-----------------|---------------------------------------|----------------|
|Electrical Assemblies                                                           |
| 5   | 5488099/3       | RS485 ENCLOSURE                       | 5488099/3      |
| 7   | 2399471/3       | Electrical E-Stop Hardware Grp        | 5726144/0      |
|Hydraulic Section                                                               |
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
|Hydraulic Serviceable Items                                                     |
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
|Pneumatic Section                                                               |
| 60  | 5987802/4       | Clamp Air Services Group              | 5987803/3      |
| 64  | 5885819/1       | Air Filter Regulator Assembly         | 5994998/1      |
| 66  | 5611895/2       | Moving Platen Oil Retrieval           | 5439899/1      |
| 69  | 5403319/8       | Vacuum Transfer Services Group        | 5407799/4      |
|Pneumatic Serviceable Items                                                     |
| 74  | 5172445         | Air Valve, 3 Way Poppet 1.5"          |                |
| 74  | 5172439         | Air Valve, 3 Way Poppet 1"            |                |
| 74  | 746607/0        | Pneumatic Valve- Numatics             | 3465073/1      |
| 76  | 5172453/1       | Air Valve, 3 Way Poppet 1.5"          |                |
| 76  | 717457/1        | Air Valve                             | 3463436/0      |
|Water Circuits                                                                  |
| 78  | 5341339/4       | Final Base Water Group                | 5345879/2      |
| 79  | 5342556/2       | Base Water Group                      | 5345879/2      |
| 83  | 5390381/6       | Mold Cooling Group                    | 5551848/2      |
| 84  | 5390431/2       | Mold Cooling Hose Kit                 | 5551848/2      |
| 87  | 5466558/1       | No Mold Cooling Manual Valves         | 5734422/0      |
| 90  | 5591582/0       | Baumuller Motor Cooling Assy          | 5640818/0      |
| 92  | 5744951/1       | Robot Cabinet Cooling Group           | 4979677/0      |
|Water Circuit Serviceable Item                                                  |
| 94  | 2026444/0       | Valve                                 | 3406239/0      |
|Safety Gates & Nameplates                                                       |
| 96  | 3022670/2       | Nameplates, Clamp                     | 3022150/4      |
| 98  | 6461769/0       | Nameplate Group NA                    | 4610404/2      |
| 102 | 4147028/2       | HyPET Robot Cab NP-UL English         | 4610453/0      |
| 104 | 5314381/3       | Nameplates, Injection-NA Engli        | 5093006/6      |
| 106 | 5332408/2       | Sliding Doors Assy OS                 | 5296146/6      |
| 116 | 5332414/4       | Shutter Guard Assy OS                 | 5268456/5      |
| 123 | 5358135/6       | Clamp End Gate Assembly               | 5391084/3      |
| 130 | 5358141/4       | Robot End Gate Assembly               | 5383220/2      |
| 138 | 5358182/1       | Door Rail Assy OS                     | 5268978/4      |
|Gate Assemblies                                                                 |
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
| Clamp Section                                                                  |
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
| 274 | 5691020/1       | Air Direction Rear Clamp Cyl          | 4239812/5      |
| 278 | 5749389/2       | Coolpik Cable Group                   | 5771108/0      |
| 280 | 5818189/0       | Stationary Platen Group               | 4070312/3      |
| 284 | 5826309/2       | Hose Kit-Clamp Cylinder H300          | 5826374/2      |
| 287 | 5875186/0       | Mold TC Interface Group               | 5501380/0      |
| 289 | 5999057/0       | PERMA NOVA AUTO LUBE ASSEMBLY         | 5708264/0      |
| 291 | 6298698/0       | MOLD ID ELEC H/W GRP 300T             | 6299934/1      |
| 294 | 6436470/0       | Clamp Cylinder Group                  | 5826374/2      |
| 299 | 6582425/1       | Clamp Final Oil Retrieval             | 5604821/0      |
| 299 | 6582426/1       | Clamp Cylinder Oil Retrieval          | 5604821/0      |
| 302 | 6663655/0       | Alarm Light Group                     | 6663698/0      |
| 304 | 6687622/0       | Hose Kit-Final Hydraulic HP300        | 5652886/0      |
| Clamp Serviceable Items                                                        |
| 308 | 746606/1        | Drop Bar Cylinder                     | 3364074/1      |
| Clamp Base Section                                                             |
| 310 | 5466789/3       | Clamp Base Sub-Assy                   | 5566015/2      |
| 310 | 5466785/4       | Clamp Base Group                      | 5566015/2      |
| 315 | 5871623/0       | Interface Hoses 300HPP E85            | 5871690/0      |
| 319 | 4436005/2       | Mold Cooling Monitoring Group         | 4889075/0      |
| 322 | 3387437/1       | Drool Guard Assembly                  | 3388470/0      |
| 324 | 2506586/0       | Leveling Mount Assy                   | 2250911/0      |
| 324 | 2238831/0       | Leveling Mount Assy                   | 2250911/0      |
| 324 | 2195983/1       | Leveling Mount Assy                   | 2250911/0      |
| Clamp Base Serviceable Items                                                   | 
| 326 | 4195869/0       | Linear Bearing Assembly               | 3176640/1      |
| Injection Section                                                              |
| 328 | 5370061/2       | Inj Final Cable Track Group           | 5800027/2      |
| 332 | 5144705/1       | Extruder Guard Assembly               | 4961198/1      |
| 334 | 5123142/0       | Barrel Heater Group E85               | 5121907/0      |
| 336 | 5080903/0       | Barrel Head Extension                 | 4962985/0      |
| 338 | 5058398/0       | Drive Housing Assy                    | 4893171/3      |
| 342 | 5058395/6       | Extruder Housing Ass'y                | 4826211/4      |
| 346 | 4235305/2       | Shooting Pot Assembly                 | 3979864/2      |
| 349 | 3926916/0       | Breather Group                        | 4126073/0      |
| 351 | 3549000/5       | Hopper Housing Assembly               | 6632607/0      |
| 353 | 727X735/D       | Hopper Drawer Magnet                  | 701969/C       |
| 355 | 5385744/1       | Barrel Hardware Group                 | 4881831/0      |
| 357 | 6710574/0       | Nozzle Adapt Assy MC38 P85            | 6711913/0      |
| 360 | 6704341/0       | Bell Housing Assembly                 | 6182149/0      |
| 362 | 5605864/0       | Gearbox Guard Assembly                | 4916198/1      |
| 364 | 5749319/0       | Nozzle Tip Assembly                   | 5834840/0      |
| 366 | 5756401/4       | Upper Injection Services Group        | 5800027/2      |
| 371 | 5758088/0       | Carriage Cylinder Group               | 2937257/0      |
| 373 | 5767094/3       | Purge Guard Assembly                  | 5721942/7      |
| 376 | 5798581/1       | Upper Injection Hose Kit              | 5800027/2      |
| 380 | 5824772/5       | Extruder Services Hardware            | 5824862/0      |
| 382 | 5847351/1       | Shooting Pot Heater Group             | 5849837/1      |
| 384 | 6000339/0       | Shut-off Group MC38                   | 5621987/0      |
| 387 | 6006801/0       | Spare Parts Group, Gearbox            | 3472074/1      |
| 389 | 6069151/1       | Feed Throat Assembly                  | 6063569/0      |
| 391 | 6200686/1       | Injection Unit Assembly               | 5729585/1      |
| 396 | 6226263/2       | Motor and Gearbox Group               | 4891178/1      |
| 398 | 6414666/0       | Blanket Insulation Group              | 5058272/1      |
| 400 | 6445498/0       | Barrel Cover Group                    | 4939128/0      |
| 402 | 6687591/0       | Hose Kit Injection Final Hoses        | 4967263/6      |
| Injection Serviceable Items                                                    |
| 406 | 4253033/0       | Spare Parts Group, Carr. Cyl.         |                |
| 406 | 2157438/7       | Hopper Shutoff Cyl & Valve            | 3464990/0      |
| 408 | 5370073/1       | Cable Track with Separators           | 4868330/0      |
| Injection Base Section                                                         |
| 410 | 4281775/3       | Accumulator Inst. Double              | 4344023/0      |
| 412 | 4998788/2       | Motor Mounting Group                  | 5017964/7      |
| 415 | 5196899/7       | Oil Retrieval Unit                    | 5271648/1      |
| 418 | 5218954/1       | Power Train Cover Group               | 4063089/1      |
| 418 | 5218964/0       | Power Train Cover Group               | 4063099/1      |
| 420 | 5223916/3       | Oil Retrieval Assy                    | 5226900/1      |
| 424 | 5789988/6       | Injection Base Group                  | 6240159/1      |
| 431 | 5791457/3       | Injection Base Assembly               | 5226495/0      |
|Injection Base Serviceable Items                                                |
| 433 | 2334327/0       | Circle Seal Relief Valve              | 3463684/0      |
|Hydraulic Power Unit                                                            |
| 435 | 4858493/1       | Heat Exchanger Group                  | 4943684/0      |
| 437 | 5342551/0       | PPack Services Group                  | 5343971/1      |
| 442 | 5435367/0       | Accumulator Bracket Group             | 5343992/1      |
| 447 | 5852987/1       | Power Manifold Assembly               | 5143491/2      |
| 450 | 5977237/1       | Powerpack Final Hardware              | 5854809/1      |
| 456 | 6705926/0       | Pump Assembly Group                   | 5220259/0      |
| 458 | 6687584/0       | Hose Kit - Powerpack Final            | 5343971/1      |
|Hyd Power Serviceable Items                                                     |
| 463 | 2927310/0       | Check Valve                           | 3454731/0      |
| 465 | 3409029/0       | Filter Pump, Vane                     | 3532930/0      |
|Z Axis Section                                                                  |
| 467 | 5624208/1       | Drive Assembly                        | 2691808/3      |
| 469 | 3888224/0       | Idler Assembly                        | 2691815/0      |
| 471 | 5683271/2       | Z-AXIS Group                          | 5396348/3      |
|Frame Section                                                                   |
| 479 | 6028880/0       | No APMC Group w/Manual Valve          | 6030948/0      |
| 483 | 5682257/0       | Vacuum Relief Valve Assy              | 5682208/3      |
| 491 | 6043342/0       | Robot Water Hose Kit                  | 6030948/0      |
| 495 | 6433389/1       | Robot Frame Assembly                  | 6206230/3      |
| 497 | 6206107/1       | Air Regulator Assembly                | 6206230/3      |
|Photoeyes Section                                                               |
| 506 | 4116255/5       | Photoeye Assembly                     | 5396348/3      |
| 513 | 5682226/1       | Photoeye Reflector Assembly           | 5682208/3      |
|Robot Mech/Elec Assembly                                                        |
| 521 | 4099616/2       | Air & Water Manifold Assembly         | 3629343/3      |
| 523 | 6433391/0       | Robot Assembly                        | 5652481/1      |
|Coolpik                                                                         |
| 526 | 5604681/1       | Coolpik Fan Group                     | 5884275/0      |
| 526 | 5886938/1       | Coolpik Fan Hardware                  | 5884275/0      |
| 529 | 5886936/4       | CoolPik Services HyPET300 HPP4        | 5886937/1      |
| 537 | 5651073/3       | Coolpik Mechanical Assembly           | 5688043/0      |
|Spares Section                                                                  |
| 542 | 6420095/0       | LEVELING SPACER GROUP                 | 6420145/0      |
| 544 | 5997747/0       | HyPET4.0 Pro-Act Spares Kit           | 5889364/0      |
| 546 | 5859850/0       | Spares Kit                            | 4520851/3      |
| 548 | 5576744/1       | Walkway Group                         | 5573388/0      |
| 553 | 6516546/2       | Start-up Kit HyPET                    | 6516560/0      |
| 553 | 3581644/1       | O Ring Spares KIT                     |                |
"""
llm = AzureChatOpenAI(
    openai_api_version="2024-08-01-preview",  # or your deployed version # type: ignore
    azure_deployment="gpt-4o",
    azure_endpoint="https://conta-m9prji51-eastus2.services.ai.azure.com",
    openai_api_key="9RSNCLiFqvGuUVCxVF1CsmDTLNBkHpX1P1jfMsxGMxqR2ES2wCy8JQQJ99BDACHYHv6XJ3w3AAAAACOGSc3o", # type: ignore
    temperature=0.0,
    streaming=True,  # enable streaming
    max_tokens=1536,
)

multi_route_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a routing assistant. Choose ONE category for the user’s intent:\n"
     "- `mechanical_drawing`: BOM pages, CAD, part numbers, revisions, blueprints\n"
     "- `troubleshooting`: faults, alarms, pumps, servo valves, sensors, wiring\n"
     "- `general`: greetings or anything not covered above\n"
     "Respond with ONLY: mechanical_drawing, troubleshooting, or general."),
    ("human", "History:\n{history}\n\nUser Question:\n{query}")
])
route_classifier_chain = LLMChain(llm=llm,prompt=multi_route_prompt)
SIMILARITY_THRESHOLD = 0.80   # keep tuning as you wish



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

def get_fresh_sas_token():
    return generate_container_sas(
        account_name=AZURE_STORAGE_ACCOUNT,
        container_name=CONTAINER,
        account_key=AZURE_STORAGE_KEY,
        permission=ContainerSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(minutes=60),
    )
#images folder path
IMAGES_DIR   = "images_pump" 
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

# ── Prepare routing descriptions ────────────────────────────────────────
routing_descriptions = {
    "mechanical_drawing": (
        "Use this route **only** for queries involving static documents such as CAD diagrams, blueprint illustrations, BOM tables, part numbers, revision comparisons, or locating items by page number in mechanical drawing sets.\n\n"
        "Focus is on **visual layout and document structure**, not functional behavior.\n\n"
        "Examples include: identifying a part's page number, comparing drawing versions (e.g., rev D vs F), locating valve placement on a schematic, or listing components in a BOM table.\n\n"
        "**Do NOT use this route for operational issues, pressure problems, or electrical faults — even if a part is mentioned.**"
    ),
    "troubleshooting": (
        "Use this route **only** for queries involving system behavior, diagnostics, calibration, faults, alarms, or performance issues during machine operation.\n\n"
        "Focus is on **dynamic system function**, real-time problems, or electrical/hydraulic tuning.\n\n"
        "Examples include: diagnosing Moog servo valve faults, calibrating A10V pump settings, interpreting pressure readings, wiring or jumper configs, VT5041 amplifier tuning, or fixing alarms.\n\n"
        "**Do NOT use this route if the user is asking to locate parts or compare drawing pages — even if the part is malfunctioning.**"
    ),
    "general": (
        "Use this route for greetings, chit-chat, or queries unrelated to machinery, drawings, or diagnostics. This includes vague questions or off-topic requests."
    )
}

# ── Prepare Text and Keys ────────────────────────────────────────────────────
route_texts = list(routing_descriptions.values())
route_keys = list(routing_descriptions.keys())

# ── One-time embedding of route descriptions ────────────────────────────────────────────────────
route_embeddings = azure_embeddings.embed_documents(route_texts)

# ── Initialize vector store and retriever ────────────────────────────────────────────────────
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
    k=6,              # was 10
  
)

# ── Prepare the query-rewrite prompt and chain ────────────────────────────────────────────────
query_rewrite_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "**ROLE**: You are a domain-aware, high-precision query rewriter.\n\n"
     "**OBJECTIVE**: Rewrite the user’s CURRENT_QUESTION into a **standalone**, **keyword-optimized**, ≤25-word search query.\n"
     "It must preserve original **intent**, use **clear technical language**, and be suited for high-performance retrieval in dense knowledge bases.\n\n"
     "**METHOD**:\n"
     "1. Use all relevant technical terms from CURRENT_QUESTION exactly as written.\n"
     "2. Fill in missing subject context using RECENT_HISTORY, but do not speculate.\n"
     "3. Output **only one line**: the rewritten query. No punctuation, formatting, or commentary.\n\n"
     "**STRICT RULES**:\n"
     "- NEVER answer the question or provide explanations.\n"
     "- NEVER remove critical keywords from the query.\n"
     "- NEVER add terms unless they are:\n"
     "    • Technical synonyms from RECENT_HISTORY\n"
     "    • Part of clearly implied user style (e.g., 'like a 5 year old', 'for experts')\n"
     "- NEVER rephrase into vague or generic wording. Retain specificity.\n"
     "- NEVER use markdown, quotes, symbols, emojis, or sentence-ending punctuation.\n"
     "- NEVER exceed 25 words.\n"
     "- ALWAYS resolve co-references (e.g., 'it', 'this part') using RECENT_HISTORY."
    ),
    # ---- FEW-SHOT EXAMPLES ----------------------------------------
    ("human", "RECENT_HISTORY:\nUser: What is the enable signal voltage range?\nAssistant: …\n\nCURRENT_QUESTION:\nWhy is it important?"),
    ("assistant", "importance of enable signal voltage range Moog servo valve breakout box"),

    ("human", "RECENT_HISTORY:\nUser: How does a servo valve control flow?\nAssistant: …\n\nCURRENT_QUESTION:\nExplain it like I'm 5"),
    ("assistant", "servo valve flow control principle electrohydraulic mechanism explanation like a 5 year old"),

    ("human", "CURRENT_QUESTION: what's a hydraulic pump do in kid language?"),
    ("assistant", "hydraulic pump basic function explanation like a 5 year old"),

    ("human", "CURRENT_QUESTION: explain A10V pump to a junior technician"),
    ("assistant", "A10V hydraulic pump function explained for junior technician"),

    ("human", "CURRENT_QUESTION: explain directional valve in simple terms"),
    ("assistant", "directional valve purpose and operation simple explanation for beginners"),

    ("human", "CURRENT_QUESTION: show me stroke manifold assembly"),
    ("assistant", "stroke manifold assembly drawing or diagram"),
    

    # ---- EXECUTION SLOT -------------------------------------------
    ("human", "RECENT_HISTORY:\n{history}\n\nCURRENT_QUESTION:\n{query}")
])
query_rewrite_chain = LLMChain(llm=llm,prompt=query_rewrite_prompt)

# ── QUERY-REWRITE HELPER ────────────────────────────────────────────────────
async def rewrite_query(user_query: str, history: str) -> str:
    """Return an LLM-rewritten version of `user_query`."""
    return await query_rewrite_chain.apredict(query=user_query, history=history)

# ── Helper to convert blob name to URL ────────────────────────────────────────────────
def url_from_blob(blob_name: str) -> str:
    sas_token = get_fresh_sas_token()
    return (
        f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/"
        f"{CONTAINER}/{blob_name}?{sas_token}"
    )


# ── Helper to parse page numbers from LLM text ────────────────────────────────────────────────
def _parse_page_numbers(raw: str) -> list[int]:
    """Return sorted unique page ints extracted from any LLM text."""
    return sorted({int(n) for n in re.findall(r"\d+", raw)})

# ── Helper to convert documents to citations ────────────────────────────────────────────────
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

# ── Helper to build the prompt for the LLM ────────────────────────────────────────────────
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
        "The Maintenance Assistant agent supports maintenance technicians of all experience levels in troubleshooting and learning how to operate and maintain Husky HyPET, Hylectric, and Quadloc machines. It acts as a 24/7 assistant to help workers diagnose machine issues, follow proper maintenance procedures, and build skills over time. The agent serves two primary functions: real-time troubleshooting and on-demand training. It guides technicians through diagnosing faults, alarms, and error codes using simple step-by-step instructions, helps identify root causes, recommends corrective actions, lists necessary parts or tools, and flags safety concerns. It also offers bite-sized lessons tailored by machine type and user skill level, covering daily checks, startup and shutdown sequences, component replacement, and subsystem functions. General instructions - Guide technicians through diagnosing faults, alarms, and error codes on Husky HyPET, Hylectric, and Quadloc machines by providing structured, step-by-step diagnostic workflows based on official service procedures. - Assist technicians of all experience levels by offering precise and easy-to-follow guidance. - For servo valve issues, walk users through identifying specific fault types, explaining alarm logic, and guiding users to measure voltages using a Moog breakout box. - Help verify signals like command (Pin 4), feedback (Pin 6), and valve enable (Pin 3), and identify whether signals fall within expected ranges. - Walk through safety window logic, spool centering checks, and signal integrity tests to determine root causes. - For Rexroth Master/Slave pumps, support the technician in confirming jumper settings and calibrating swashplate angles using test point measurements on the VT5041 amplifier card. - Help set and verify system pressure, swashplate angles, and voltage values, and recommend adjustments to resistors as needed. - List corrective actions clearly, including part numbers, wiring checks, and recommendations for replacing faulty components. - Identify required tools and emphasize safety warnings. - Make the process interactive, guiding users step by step, listing common root causes, and offering clear corrective action paths for each scenario. Clarification and guidance behavior - Always follow up your responses with a supportive and helpful question. - If the user's question is vague or lacks detail, ask for clarification or extra context to ensure accurate support. - If the user's input is already clear, offer additional guidance, explanation, or training to deepen understanding. - Use a warm, professional tone. Keep questions focused on helping the technician progress or avoid confusion. - Avoid making assumptions. Ask only one clear, helpful question at the end of each reply. - If you must make any assumptions in order to answer the question, clearly state what those assumptions are. - When referencing information from documents, indicate what was found in the documents and what was not. Be transparent about the source and scope of your knowledge."

        "Technical formatting rules: "
        "• Do NOT summarize, paraphrase, or reword numerical values (voltages, calibration, jumpers). Repeat them exactly. "
        "• When referencing data (voltages, jumper settings, resistance, etc.), present it in a **GitHub-Flavored Markdown table** using pipes (`|`) and dashes (`-`). "
        "• Do NOT use code fences, bullet points, or reorder data from tables. "
        "• Use numbered lists for step-by-step procedures. "
        "• Mention specific tools and procedures from the documents (e.g., breakout box, multimeter, jumper plug, swashplate calibration, Moog VT5041 signals). "
        "• For servo valves, guide users through command (Pin 4), feedback (Pin 6), and valve enable (Pin 3) checks, and confirm values using Moog breakout box. "
        "• For Rexroth pumps, help confirm jumper settings and measure swashplate angles using test points on the VT5041 card. "

  

    )
        # Passing images to LLM for non mechanical drawing documents
        # for url in ctx["images"]:
        #     blocks.append({"type": "image_url", "image_url": {"url": url}})
    else:
        system_rules =  (
        "You are a technical assistant that answers questions based on mechanical drawings and Bill of Materials (BOM) data.\n"
        "Use the provided context (including drawing references, and part numbers) to give clear and accurate responses.\n"
        "- Tell the user: \"You can view the corresponding drawings by viewing the mechanical parts below.\"\n"
        "- End with: \"Feel free to ask any follow-up questions if you need more details or clarification.\"\n"
        "- Summarize where the user can find relevant drawings or BOM entries (based on the context).\n"
        )
        for url in ctx["images"]:
            blocks.append({"type": "image_url", "image_url": {"url": url}}) # type: ignore

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_rules),
        HumanMessage(content=blocks), # type: ignore
    ])

# ── Helper to split out text vs images ────────────────────────────────────
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


# ── MAIN FUNCTION ────────────────────────────────────────────────────
@traceable
async def run_test_rag(chat_history: list, user_query: str, forced_route: str | None = None):
    global history_text                         # let build_prompt see the update
    history_text = ""
    for m in chat_history:                      # m is a BaseMessage
        role = "User" if m.type == "human" else "Assistant"
        history_text += f"{role}: {m.content}\n"

    route = forced_route
    is_drawing_query = route == "mechanical_drawing"
    print(f"DRAWING QUERY BOOLEAN: {is_drawing_query}")

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
            "2. Return the **page number** from that entry’s BOM page (first column),\n"
            "If you can NOT find a matching entry, return an empty string.\n"
            "Only return a **comma-separated list of page numbers, NO WORDS, PAGE NUMBERS ONLY**.\n"
            "Do NOT include any drawing numbers or part numbers.\n"
            "Return ONLY the first matching page number up to but **NOT INCLUDING** the next BOM entry. Ignore all later entries, even if they match.\n"
            "Do NOT guess or invent page numbers.\n"
            "Use only the page numbers found in the first column of the table.\n"),
            ("human", "TOC:\n\n{toc}\n\nQuery:\n{query}")
        ])
        page_lookup_chain = LLMChain(llm=llm, prompt=page_lookup_prompt)
        page_result = await page_lookup_chain.apredict(toc=toc, query= user_query)
        print(f"📄 Page prediction result: {page_result}")
        # Step 1: Get all valid BOM page numbers from the TOC
        valid_bom_pages = _parse_page_numbers(toc)

        # Step 2: Get the first matched page from LLM
        page_numbers = _parse_page_numbers(page_result)
        if not page_numbers:
            toc_ids = []
        else:
            first_page = page_numbers[0]

            # Step 3: Find next BOM page after the match
            following_pages = [p for p in valid_bom_pages if p > first_page]
            next_bom_page = min(following_pages) if following_pages else None

            # Step 4: Generate page range
            final_pages = list(range(first_page, next_bom_page)) if next_bom_page else [first_page]

            # Step 5: Convert to doc IDs
            toc_ids = [f"Husky_2_Mechanical_Drawing_Package-p{p}" for p in final_pages]
        for doc_id in toc_ids:
            raw = client.get_document(key=doc_id)   # ➜ dict
            hits.append(to_lc_doc(raw)) 
        citations = _docs_to_citations(hits)
    else:
        hits = await retriever.aget_relevant_documents(user_query)
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

    async with trace(name="test-rag-response"):
        async for chunk in chain.astream(user_query):
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