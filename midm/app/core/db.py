"""Database connection helpers (stdlib-only).

This module intentionally avoids importing third-party packages so it can be
unit-tested without requiring optional runtime dependencies.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def build_asyncpg_connection_string(database_url: str) -> str:
    """Convert a Postgres connection string into a SQLAlchemy asyncpg URL.

    Neon often provides a connection string like:
    `postgresql://user:pass@host/db?sslmode=require&channel_binding=require`

    For SQLAlchemy asyncpg, we prefer:
    `postgresql+asyncpg://user:pass@host/db?ssl=require`

    Args:
        database_url: Postgres connection string.

    Returns:
        A connection string using the `postgresql+asyncpg` scheme, with query
        params adjusted for asyncpg.
    """
    parsed = urlparse(database_url)

    scheme = parsed.scheme
    if scheme in {"postgres", "postgresql"}:
        new_scheme = "postgresql+asyncpg"
    elif scheme == "postgresql+asyncpg":
        new_scheme = scheme
    else:
        # Leave unknown schemes untouched; caller can decide what to do.
        new_scheme = scheme

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))

    # asyncpg uses `ssl=require` rather than `sslmode=require`.
    sslmode = query.pop("sslmode", None)
    if sslmode and "ssl" not in query:
        query["ssl"] = sslmode

    # Neon may include `channel_binding=require`; asyncpg doesn't accept it.
    query.pop("channel_binding", None)

    new_query = urlencode(query, doseq=True)
    rebuilt = parsed._replace(scheme=new_scheme, query=new_query)
    return urlunparse(rebuilt)


