from backend.settings import (app_settings)
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch
from functools import lru_cache
from typing import Optional


_llm = None
_embedding_model = None
_vectorstore = None

@lru_cache(maxsize=8)
def _build_llm(
    *, streaming: bool, temperature: float, model: str, endpoint: str, api_version: str
) -> AzureChatOpenAI:
    return AzureChatOpenAI(
        api_version=api_version,
        azure_deployment=model,
        azure_endpoint=endpoint,
        openai_api_key=app_settings.azure_openai_credentials.key,  # type: ignore
        temperature=temperature,
        streaming=streaming,
    )

def get_llm(*, streaming: Optional[bool] = None, temperature: Optional[float] = None) -> AzureChatOpenAI:
    cfg = app_settings.azure_openai_credentials
    use_streaming = cfg.stream if streaming is None else bool(streaming)
    use_temp = cfg.temperature if temperature is None else float(temperature)
    return _build_llm(
        streaming=use_streaming,
        temperature=use_temp,
        model=cfg.model,
        endpoint=cfg.endpoint,
        api_version=cfg.preview_api_version,
    )

def get_embedding_llm():
    """Return the shared AzureOpenAIEmbeddings instance (lazy singleton)."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = AzureOpenAIEmbeddings(
            model                = app_settings.azure_openai_embedding_credentials.model,
            azure_endpoint       = app_settings.azure_openai_embedding_credentials.endpoint,
            api_version   = app_settings.azure_openai_embedding_credentials.api_version,
            api_key              = app_settings.azure_openai_embedding_credentials.key,
        )
    return _embedding_model


def get_vectorstore():
    """Return the shared AzureSearch vectorstore instance (lazy singleton)."""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = AzureSearch(
            azure_search_endpoint=app_settings.azure_search_credentials.endpoint,
            azure_search_key=app_settings.azure_search_credentials.key,
            index_name=app_settings.azure_search_credentials.index,
            embedding_function=get_embedding_llm(),
            vector_search_dimensions=app_settings.azure_search_credentials.search_dimensions,
            text_key="page_content",
            vector_field_name="content_vector",
        )
    return _vectorstore