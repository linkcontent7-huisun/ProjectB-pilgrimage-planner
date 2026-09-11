"""The single construction point for the chat model."""

from langchain_openai import ChatOpenAI

from app.config import settings


def get_llm(temperature: float = 0.3) -> ChatOpenAI:
    """Build the configured OpenAI-compatible chat model."""
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL or None,
        temperature=temperature,
        max_retries=3,
        timeout=60,
    )
