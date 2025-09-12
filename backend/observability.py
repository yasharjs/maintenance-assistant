import logging
import os
from typing import Optional


def enable_langsmith(langsmith_settings, *, default_project: Optional[str] = None) -> None:
    """Enable LangSmith/LangChain tracing via environment variables.

    Respects values provided in `backend.settings._LangsmithSettings`.
    Safe to call multiple times; idempotent.

    Args:
        langsmith_settings: Instance of `_LangsmithSettings` from app settings.
        default_project: Fallback project name if settings.project is empty.
    """
    try:
        if not langsmith_settings or not getattr(langsmith_settings, "api_key", None):
            logging.info("LangSmith tracing disabled: no API key provided")
            return

        # Use the LangSmith API key to set the LangChain env var expected by the SDKs
        api_key = langsmith_settings.api_key  # type: ignore[attr-defined]
        os.environ.setdefault("LANGCHAIN_API_KEY", api_key)

        # Tracing v2 toggle
        tracing_v2 = bool(getattr(langsmith_settings, "tracing_v2", True))
        os.environ["LANGCHAIN_TRACING_V2"] = "true" if tracing_v2 else "false"

        # Endpoint (optional)
        endpoint = getattr(langsmith_settings, "endpoint", None)
        if endpoint:
            os.environ.setdefault("LANGCHAIN_ENDPOINT", endpoint)

        # Project (optional, with sensible default)
        project = getattr(langsmith_settings, "project", None) or default_project or "react-agent-v1"
        os.environ.setdefault("LANGCHAIN_PROJECT", project)

        # Keep logs minimal; do not print secrets
        logging.info(
            "LangSmith tracing enabled (project=%s, endpoint=%s, v2=%s)",
            os.environ.get("LANGCHAIN_PROJECT"),
            os.environ.get("LANGCHAIN_ENDPOINT", "default"),
            os.environ.get("LANGCHAIN_TRACING_V2"),
        )
    except Exception:
        # Never fail app startup due to observability wiring
        logging.exception("Failed to enable LangSmith tracing")