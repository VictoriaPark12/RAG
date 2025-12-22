"""OpenAI LLM initialization for chat and RAG."""

import os
from typing import Any

try:
    from langchain_openai import ChatOpenAI
except ModuleNotFoundError:  # pragma: no cover
    ChatOpenAI = None  # type: ignore[assignment]


def init_openai_llm() -> Any:
    """Initialize OpenAI LLM.

    Returns:
        ChatOpenAI instance for generation.

    Raises:
        ModuleNotFoundError: If langchain-openai is not installed.
        RuntimeError: If OpenAI API key is not set.
    """
    if ChatOpenAI is None:  # pragma: no cover
        msg = (
            "langchain-openai is not installed. "
            "Install with: pip install langchain-openai"
        )
        raise ModuleNotFoundError(msg)

    # 환경 변수에서 설정 읽기
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Please set it in your .env file."
        )

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

    print(f"LLM Provider: OpenAI")
    print(f"OpenAI Model: {model_name}")
    print(f"Temperature: {temperature}")

    try:
        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=openai_api_key,
        )

        # Test connection
        print("Testing OpenAI connection...")
        test_response = llm.invoke("안녕")
        print(f"[OK] OpenAI connection successful! Test response: {test_response.content[:50]}...")

        return llm
    except Exception as e:
        msg = (
            f"Failed to connect to OpenAI API. "
            f"Make sure OPENAI_API_KEY is valid.\n"
            f"Error: {e}"
        )
        raise RuntimeError(msg) from e

