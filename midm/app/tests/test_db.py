import os
import sys

# Ensure `app/` package modules are importable even though repo root has `app.py`.
_APP_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _APP_DIR)

from core.db import build_asyncpg_connection_string  # noqa: E402


def test_build_asyncpg_connection_string_neon_sslmode_and_channel_binding() -> None:
    url = (
        "postgresql://user:pass@host.example/neondb"
        "?sslmode=require&channel_binding=require"
    )
    out = build_asyncpg_connection_string(url)
    assert out.startswith("postgresql+asyncpg://user:pass@host.example/neondb?")
    assert "ssl=require" in out
    assert "sslmode=" not in out
    assert "channel_binding=" not in out


def test_build_asyncpg_connection_string_preserves_other_query_params() -> None:
    url = "postgresql://u:p@h/db?sslmode=require&foo=bar"
    out = build_asyncpg_connection_string(url)
    assert out.startswith("postgresql+asyncpg://u:p@h/db?")
    assert "ssl=require" in out
    assert "foo=bar" in out


