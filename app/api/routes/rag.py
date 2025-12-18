"""Backward-compatible wrapper for the RAG router.

The implementation was moved to `app/router/chat_router.py` per request.
"""

from router.chat_router import rag_query, router, set_dependencies  # noqa: F401
