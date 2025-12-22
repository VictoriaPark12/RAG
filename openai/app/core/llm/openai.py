"""OpenAI LLM initialization for chat and RAG."""

import os
from pathlib import Path
from typing import Any

# .env 파일 자동 로드
try:
    from dotenv import find_dotenv, load_dotenv

    # 현재 파일 기준으로 .env 파일 찾기
    current_dir = Path(__file__).parent.parent.parent.parent.parent
    env_path = current_dir / ".env"

    # .env 파일이 있으면 로드
    if env_path.exists():
        load_dotenv(env_path, override=False)

    # 현재 작업 디렉토리에서도 .env 찾기
    cwd_env = find_dotenv(usecwd=True)
    if cwd_env:
        load_dotenv(cwd_env, override=False)
except ImportError:
    # python-dotenv가 없어도 계속 진행 (환경 변수는 이미 설정되어 있을 수 있음)
    pass

# ChatOpenAI 타입 선언
_ChatOpenAI: Any = None

try:
    from langchain_openai import ChatOpenAI as _ChatOpenAIClass

    _ChatOpenAI = _ChatOpenAIClass
except ModuleNotFoundError:  # pragma: no cover
    pass

ChatOpenAI = _ChatOpenAI


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

    # 디버깅: 환경 변수 확인 (키는 마스킹)
    if openai_api_key:
        key_preview = (
            f"{openai_api_key[:8]}...{openai_api_key[-4:]}"
            if len(openai_api_key) > 12
            else "***"
        )
        print(
            f"[DEBUG] OPENAI_API_KEY found (length: {len(openai_api_key)}, preview: {key_preview})"
        )
    else:
        print("[DEBUG] OPENAI_API_KEY not found in environment variables")
        openai_vars = [k for k in os.environ.keys() if "OPENAI" in k.upper()]
        print(f"[DEBUG] Available env vars with 'OPENAI': {openai_vars}")
        print(f"[DEBUG] Current working directory: {os.getcwd()}")
        print(".env file paths checked:")
        env_exists = env_path.exists() if "env_path" in locals() else False
        print(f"  - {env_path} (exists: {env_exists})")
        if "cwd_env" in locals() and cwd_env:
            cwd_exists = Path(cwd_env).exists()
            print(f"  - {cwd_env} (exists: {cwd_exists})")

    if not openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Please set it in your .env file or as an environment variable."
        )

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

    print("LLM Provider: OpenAI")
    print(f"OpenAI Model: {model_name}")
    print(f"Temperature: {temperature}")

    try:
        # ChatOpenAI는 api_key를 문자열로 받을 수 있음
        # 타입 체크: ChatOpenAI는 실제로 문자열 api_key를 받을 수 있음
        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=openai_api_key,  # type: ignore[arg-type]
        )

        # Test connection
        print("Testing OpenAI connection...")
        test_response = llm.invoke("안녕")
        print(
            f"[OK] OpenAI connection successful! Test response: {test_response.content[:50]}..."
        )

        return llm
    except Exception as e:
        msg = (
            f"Failed to connect to OpenAI API. "
            f"Make sure OPENAI_API_KEY is valid.\n"
            f"Error: {e}"
        )
        raise RuntimeError(msg) from e
