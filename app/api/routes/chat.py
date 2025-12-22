"""General chat endpoint (non-RAG)."""

from __future__ import annotations

import logging
import os

from api.models import ChatRequest, ChatResponse  # type: ignore

try:
    from fastapi import APIRouter, HTTPException, Request
except ModuleNotFoundError as e:  # pragma: no cover
    msg = (
        "필수 의존성이 설치되지 않아 Chat API를 로드할 수 없습니다.\n\n"
        "권장:\n"
        "  pip install -r app/requirements.txt\n\n"
        f"원본 에러: {e}"
    )
    raise RuntimeError(msg) from e

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger("rag-api")

# Global reference (will be set by main app)
llm = None


def set_dependencies(llm_instance) -> None:
    """Set LLM dependency."""
    global llm
    llm = llm_instance


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, raw_request: Request) -> ChatResponse:
    """General chat that does not rely on vector store / RAG.

    Args:
        request: User message + optional conversation history.

    Returns:
        ChatResponse with model answer.
    """
    request_id = getattr(getattr(raw_request, "state", None), "request_id", "-")
    logger.info(
        "[CHAT] id=%s qlora=%s message=%r history_len=%s",
        request_id,
        os.getenv("USE_QLORA", "0"),
        (request.message or "")[:160],
        len(request.conversation_history or []),
    )
    print(
        "[ROUTER] /chat received",
        {"request_id": request_id, "message_preview": (request.message or "")[:200]},
    )
    # If llm is not wired (e.g. USE_QLORA mode skips HF init), fall back to QLoRA.
    if llm is None:
        use_qlora = os.getenv("USE_QLORA", "0").lower() in {"1", "true", "yes"}
        base_model_path = os.getenv("QLORA_BASE_MODEL_PATH")
        adapter_path = os.getenv("QLORA_ADAPTER_PATH") or None
        if use_qlora and base_model_path:
            from service.chat_service import chat_with_qlora  # type: ignore

            try:
                answer_text = chat_with_qlora(
                    base_model_path=base_model_path,
                    adapter_path=adapter_path,
                    message=request.message,
                    conversation_history=request.conversation_history or [],
                    max_new_tokens=int(os.getenv("QLORA_MAX_NEW_TOKENS", "256")),
                    request_id=request_id,
                )
                logger.info(
                    "[CHAT] id=%s backend=qlora answer_preview=%r",
                    request_id,
                    answer_text[:120],
                )
                return ChatResponse(message=request.message, answer=answer_text)
            except FileNotFoundError as e:
                logger.error(f"[CHAT] id={request_id} QLoRA model not found: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"QLoRA 모델을 찾을 수 없습니다: {base_model_path}. 모델 경로를 확인하세요.",
                ) from e
            except Exception as e:
                logger.exception(f"[CHAT] id={request_id} QLoRA error: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"QLoRA 모델 실행 중 오류 발생: {str(e)}",
                ) from e

        raise HTTPException(
            status_code=500,
            detail=f"LLM이 초기화되지 않았습니다. USE_QLORA={use_qlora}, QLORA_BASE_MODEL_PATH={base_model_path}",
        )

    try:
        history = request.conversation_history or []

        # Check if LLM is ChatOpenAI (uses messages format)
        try:
            from langchain_openai import ChatOpenAI  # type: ignore
            is_chat_openai = isinstance(llm, ChatOpenAI)
        except ImportError:
            is_chat_openai = False

        if is_chat_openai:
            # OpenAI ChatOpenAI uses messages format
            messages = []
            # System message
            messages.append({"role": "system", "content": "너는 친절하고 유용한 한국어 어시스턴트야. 가능하면 구체적으로 답하고, 모르면 모른다고 말하되 대안을 제시해."})
            # History (last 10 messages)
            for msg in history[-10:]:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role and content:
                    # Convert to OpenAI format
                    if role == "user":
                        messages.append({"role": "user", "content": content})
                    elif role == "assistant":
                        messages.append({"role": "assistant", "content": content})
            # Current user message
            messages.append({"role": "user", "content": request.message})

            # Invoke with messages
            if hasattr(llm, "ainvoke"):
                answer = await llm.ainvoke(messages)
            else:
                answer = llm.invoke(messages)
            answer_text = str(getattr(answer, "content", answer)).strip()
        else:
            # For other LLMs (HuggingFace, Ollama), use prompt format
            history_text = ""
            for msg in history[-10:]:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role and content:
                    history_text += f"{role}: {content}\n"

            prompt = (
                "너는 친절하고 유용한 한국어 어시스턴트야.\n"
                "가능하면 구체적으로 답하고, 모르면 모른다고 말하되 대안을 제시해.\n\n"
                f"{history_text}"
                f"user: {request.message}\n"
                "assistant:"
            )

            # Support both sync/async invoke depending on implementation.
            if hasattr(llm, "ainvoke"):
                answer = await llm.ainvoke(prompt)
            elif hasattr(llm, "invoke"):
                answer = llm.invoke(prompt)
            else:
                # HuggingFacePipeline is callable in LangChain
                answer = llm(prompt)

            answer_text = str(getattr(answer, "content", answer)).strip()

        return ChatResponse(message=request.message, answer=answer_text)
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"[CHAT] id={request_id} Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"채팅 처리 중 오류 발생: {str(e)}") from e
