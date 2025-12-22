"""Compatibility shim: re-export RAG router from `app/api/routes/rag.py`.

We also expose `rag_chain` for `/health` checks.
"""

from router import chat_router as _rag_impl

router = _rag_impl.router
set_dependencies = _rag_impl.set_dependencies
rag_query = _rag_impl.rag_query


def __getattr__(name: str):  # pragma: no cover
    if name == "rag_chain":
        return _rag_impl.rag_chain
    raise AttributeError(name)


