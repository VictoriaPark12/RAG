"""Compatibility shim: re-export Search router from `app/api/routes/search.py`.

This module exists because `app/main.py` imports from `api.routers.*`.
We also expose `vector_store` for `/health` checks.
"""

from api.routes import search as _search

router = _search.router
set_dependencies = _search.set_dependencies
retrieve = _search.retrieve
add_document = _search.add_document
add_documents = _search.add_documents


def __getattr__(name: str):  # pragma: no cover
    # keep vector_store live
    if name == "vector_store":
        return _search.vector_store
    raise AttributeError(name)


