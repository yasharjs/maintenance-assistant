from backend.settings import (app_settings)
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch


_llm = None
_embedding_model = None
_vectorstore = None

def get_llm():
    """Return the shared AzureChatOpenAI instance (lazy singleton)."""
    global _llm
    if _llm is None:
        _llm = AzureChatOpenAI(
            api_version=app_settings.azure_openai_credentials.preview_api_version, 
            azure_deployment=app_settings.azure_openai_credentials.model,
            azure_endpoint=app_settings.azure_openai_credentials.endpoint,
            openai_api_key=app_settings.azure_openai_credentials.key,  # type: ignore
            temperature=app_settings.azure_openai_credentials.temperature,
            streaming=app_settings.azure_openai_credentials.stream,  # enable streaming
        )
    return _llm


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