"""Ollama LLM initialization for RAG."""

import os
from typing import Any

try:
    from langchain_ollama import ChatOllama
except ModuleNotFoundError:  # pragma: no cover
    ChatOllama = None  # type: ignore[assignment]


def init_ollama_llm() -> Any:
    """Initialize Ollama LLM.

    Returns:
        ChatOllama instance for generation.

    Raises:
        ModuleNotFoundError: If langchain-ollama is not installed.
        RuntimeError: If Ollama is not running.
    """
    if ChatOllama is None:  # pragma: no cover
        msg = (
            "langchain-ollama is not installed. "
            "Install with: pip install langchain-ollama"
        )
        raise ModuleNotFoundError(msg)

    # 환경 변수에서 설정 읽기
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

    print(f"LLM Provider: Ollama")
    print(f"Ollama base URL: {ollama_base_url}")
    print(f"Ollama model: {ollama_model}")

    try:
        llm = ChatOllama(
            base_url=ollama_base_url,
            model=ollama_model,
            temperature=0.0,  # Deterministic for RAG
            num_predict=256,   # Max tokens to generate
        )

        # Test connection
        print("Testing Ollama connection...")
        test_response = llm.invoke("안녕")
        print(f"[OK] Ollama connection successful! Test response: {test_response.content[:50]}...")

        return llm
    except Exception as e:
        msg = (
            f"Failed to connect to Ollama at {ollama_base_url}. "
            f"Make sure Ollama is installed and running.\n"
            f"Install: https://ollama.com/download\n"
            f"Pull model: ollama pull {ollama_model}\n"
            f"Error: {e}"
        )
        raise RuntimeError(msg) from e

