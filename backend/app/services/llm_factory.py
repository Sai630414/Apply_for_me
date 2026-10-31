import asyncio
import logging
from typing import Any

from app.core.config import settings

_logger = logging.getLogger("applyforme.llm_factory")


def _create_ollama_llm() -> Any:
    """Create a LangChain ChatOllama instance based on config.

    Returns:
        ChatOllama: Configured LangChain LLM wrapper.
    """
    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:
        _logger.error("langchain-ollama package not installed: %s", exc)
        raise

    base_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
    model = getattr(settings, "OLLAMA_MODEL", "qwen2.5:3b")
    temperature = getattr(settings, "LLM_TEMPERATURE", 0.4)
    timeout = getattr(settings, "LLM_TIMEOUT_SECONDS", 120.0)

    _logger.info(
        "Creating Ollama ChatLLM: model=%s base_url=%s temperature=%s timeout=%s",
        model, base_url, temperature, timeout
    )
    return ChatOllama(
        model=model,
        base_url=base_url,
        temperature=temperature,
        client_kwargs={"timeout": timeout},
        async_client_kwargs={"timeout": timeout}
    )


def _resolve_groq_model(api_key: str, configured_model: str) -> str:
    """Validate or fallback to an accessible chat model on this Groq account."""
    if not api_key:
        return configured_model
    fallback_candidates = [
        configured_model,
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
        "llama-3.3-70b-versatile",
    ]
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        available = {m.id for m in client.models.list().data}
        if configured_model in available:
            return configured_model
        for cand in fallback_candidates:
            if cand in available:
                _logger.warning(
                    "[Groq] Configured model '%s' not accessible on this account. Automatically using available model '%s'.",
                    configured_model, cand
                )
                return cand
    except Exception as exc:
        _logger.debug("[Groq] Model resolution check note: %s", exc)

    return configured_model


def _create_groq_llm() -> Any:
    """Create a LangChain ChatGroq instance based on config.

    Returns:
        ChatGroq: Configured LangChain ChatGroq wrapper.
    """
    try:
        from langchain_groq import ChatGroq
    except ImportError as exc:
        _logger.error("langchain-groq package not installed: %s", exc)
        raise

    api_key = getattr(settings, "GROQ_API_KEY", "")
    if not api_key or not api_key.strip():
        _logger.error("GROQ_API_KEY is not set or empty. Cannot initialize ChatGroq.")
        raise ValueError("GROQ_API_KEY must be provided when LLM_PROVIDER=groq")

    raw_model = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
    model = _resolve_groq_model(api_key, raw_model)
    temperature = getattr(settings, "LLM_TEMPERATURE", 0.4)
    timeout = getattr(settings, "LLM_TIMEOUT_SECONDS", 120.0)

    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    _logger.info(
        "Creating Groq ChatLLM: model=%s temperature=%s timeout=%s (api_key=%s)",
        model, temperature, timeout, masked_key
    )

    return ChatGroq(
        groq_api_key=api_key,
        model_name=model,
        temperature=temperature,
        request_timeout=timeout,
        max_retries=2
    )


# Simple singleton holder – lazily instantiated on first request per event loop.
_llm_instance: Any = None
_llm_loop: Any = None
_llm_provider: Any = None


def reset_llm() -> None:
    """Clear cached LLM instance, allowing re-initialization with new settings."""
    global _llm_instance, _llm_loop, _llm_provider
    _llm_instance = None
    _llm_loop = None
    _llm_provider = None


def get_llm() -> Any:
    """Return a shared LLM instance bound to the current live event loop and provider.

    The function lazily creates the appropriate LLM based on the ``LLM_PROVIDER``
    setting. Recreates if the underlying event loop changed, closed, or provider changed.
    """
    global _llm_instance, _llm_loop, _llm_provider
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    provider = getattr(settings, "LLM_PROVIDER", "groq").lower().strip()

    if (
        _llm_instance is not None
        and _llm_provider == provider
        and (_llm_loop is None or _llm_loop == current_loop)
        and (_llm_loop is None or not _llm_loop.is_closed())
    ):
        return _llm_instance

    if provider == "groq":
        _llm_instance = _create_groq_llm()
        _llm_loop = current_loop
        _llm_provider = provider
    elif provider == "ollama":
        _llm_instance = _create_ollama_llm()
        _llm_loop = current_loop
        _llm_provider = provider
    else:
        _logger.error("Unsupported LLM provider: %s", provider)
        raise ValueError(f"Unsupported LLM provider: {provider}")

    return _llm_instance
