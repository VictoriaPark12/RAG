"""Compatibility shim: re-export Chat router from `app/api/routes/chat.py`."""

from api.routes.chat import chat, router, set_dependencies  # noqa: F401


