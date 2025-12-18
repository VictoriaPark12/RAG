# pyright: reportMissingImports=false
"""Search and document management endpoints."""

from __future__ import annotations

import importlib
import os
import sys
from typing import TYPE_CHECKING, Any

from api.models import (  # type: ignore
    DocumentListRequest,
    DocumentRequest,
    QueryRequest,
    SearchResponse,
)

if TYPE_CHECKING:  # pragma: no cover
    # 타입체커(Pylance/Pyright)가 다른 인터프리터를 보고 '없다'고 표시하는 걸 피하기 위해
    # 런타임 import는 아래에서 동적으로 수행한다.
    from fastapi import APIRouter, HTTPException
else:
    try:
        fastapi_mod = importlib.import_module("fastapi")
        APIRouter = getattr(fastapi_mod, "APIRouter")  # type: ignore[assignment]
        HTTPException = getattr(fastapi_mod, "HTTPException")  # type: ignore[assignment]
    except ModuleNotFoundError as e:  # pragma: no cover
        msg = (
            "필수 의존성이 설치되지 않아 Search API를 로드할 수 없습니다.\n\n"
            "권장:\n"
            "  pip install -r app/requirements_rag.txt\n\n"
            f"원본 에러: {e}"
        )
        raise RuntimeError(msg) from e

if TYPE_CHECKING:  # pragma: no cover
    from langchain_core.documents import Document
else:
    try:
        Document = importlib.import_module("langchain_core.documents").Document  # type: ignore[assignment]
    except ModuleNotFoundError:  # pragma: no cover
        # Monorepo dev convenience:
        # If `langchain-core` isn't installed in the current environment, fall back to local sources.

        _REPO_ROOT = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        _LOCAL_CORE = os.path.join(_REPO_ROOT, "libs", "core")
        if os.path.isdir(_LOCAL_CORE) and _LOCAL_CORE not in sys.path:
            sys.path.insert(0, _LOCAL_CORE)

        try:
            Document = importlib.import_module("langchain_core.documents").Document  # type: ignore[assignment]
        except ModuleNotFoundError as e2:
            msg = (
                "필수 의존성이 설치되지 않아 Search API를 로드할 수 없습니다. (langchain-core 누락)\n\n"
                "권장(가장 간단):\n"
                "  pip install -r app/requirements_rag.txt\n\n"
                "또는(로컬 소스 사용):\n"
                f"  {_LOCAL_CORE}\n\n"
                f"원본 에러: {e2}"
            )
            raise RuntimeError(msg) from e2

router = APIRouter(tags=["Search & Documents"])

# Global reference (will be set by main app)
vector_store: Any = None


def set_dependencies(vs):
    """Set vector store dependency."""
    global vector_store
    vector_store = vs


@router.post("/retrieve", response_model=SearchResponse)
async def retrieve(request: QueryRequest):
    """Retrieve similar documents (검색만 수행).

    Args:
        request: Query request with question and k.

    Returns:
        Search response with retrieved documents.
    """
    if not vector_store:
        raise HTTPException(status_code=500, detail="Vector store not initialized")

    try:
        # Use async similarity_search from PGVector
        results = await vector_store.asimilarity_search(request.question, k=request.k)

        return SearchResponse(
            question=request.question,
            k=request.k,
            results=[
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                }
                for doc in results
            ],
            count=len(results),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents")
async def add_document(request: DocumentRequest):
    """Add a single document to the vector store.

    Args:
        request: Document request with content and metadata.

    Returns:
        Success message.
    """
    if not vector_store:
        raise HTTPException(status_code=500, detail="Vector store not initialized")

    try:
        # Use async add_texts from PGVector
        doc = Document(
            page_content=request.content,
            metadata=request.metadata or {},
        )
        await vector_store.aadd_documents([doc])

        return {
            "message": "Document added successfully",
            "content": request.content,
            "metadata": request.metadata,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/batch")
async def add_documents(request: DocumentListRequest):
    """Add multiple documents to the vector store.

    Args:
        request: Document list request.

    Returns:
        Success message with count.
    """
    if not vector_store:
        raise HTTPException(status_code=500, detail="Vector store not initialized")

    try:
        # Use async add_documents from PGVector
        docs = [
            Document(
                page_content=doc["content"],
                metadata=doc.get("metadata", {}),
            )
            for doc in request.documents
        ]
        await vector_store.aadd_documents(docs)

        return {
            "message": f"{len(docs)} documents added successfully",
            "count": len(docs),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
