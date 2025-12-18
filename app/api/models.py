"""Pydantic models for API requests and responses."""

from typing import List, Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    """Query request model."""

    question: str
    k: int = 3
    conversation_history: Optional[List[dict]] = (
        None  # [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    )


class DocumentRequest(BaseModel):
    """Document add request model."""

    content: str
    metadata: Optional[dict] = None


class DocumentListRequest(BaseModel):
    """Multiple documents add request model."""

    documents: List[dict]  # [{"content": "...", "metadata": {...}}]


class RAGResponse(BaseModel):
    """RAG response model."""

    question: str
    answer: str
    retrieved_documents: List[dict]
    retrieved_count: int


class SearchResponse(BaseModel):
    """Search response model."""

    question: str
    k: int
    results: List[dict]
    count: int


class ChatRequest(BaseModel):
    """Chat request model (non-RAG)."""

    message: str
    conversation_history: Optional[List[dict]] = (
        None  # [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    )


class ChatResponse(BaseModel):
    """Chat response model (non-RAG)."""

    message: str
    answer: str
