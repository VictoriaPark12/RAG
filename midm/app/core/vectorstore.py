"""Vector store initialization with pgvector and HuggingFace embeddings (async)."""

import os
from typing import Any

from langchain_huggingface import HuggingFaceEmbeddings

try:
    from langchain_postgres import PGVector  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    PGVector = None  # type: ignore[assignment]

from core.db import build_asyncpg_connection_string  # type: ignore


async def init_vector_store() -> Any:
    """Initialize vector store with pgvector and Korean embeddings (async).

    Returns:
        A PGVector-compatible vector store instance connected to PostgreSQL (async mode).
    """
    # Check if DATABASE_URL is provided (for cloud PostgreSQL like Neon)
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        connection_string = build_asyncpg_connection_string(database_url)
        print("Using cloud PostgreSQL via DATABASE_URL (asyncpg)")
    else:
        # Fallback to individual environment variables (for backward compatibility)
        postgres_user = os.getenv("PGVECTOR_USER", "langchain")
        postgres_password = os.getenv("PGVECTOR_PASSWORD", "langchain")
        postgres_host = os.getenv("PGVECTOR_HOST", "localhost")
        postgres_port = int(os.getenv("PGVECTOR_PORT", "5432"))
        postgres_db = os.getenv("PGVECTOR_DATABASE", "langchain")

        connection_string = (
            f"postgresql+asyncpg://{postgres_user}:{postgres_password}"
            f"@{postgres_host}:{postgres_port}/{postgres_db}"
        )
        print(f"Using local PostgreSQL with asyncpg: {postgres_host}:{postgres_port}")

    # Use HuggingFace Korean embeddings
    print("Using HuggingFace Korean embeddings (jhgan/ko-sroberta-multitask)")
    embeddings = HuggingFaceEmbeddings(
        model_name="jhgan/ko-sroberta-multitask",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    collection_name = os.getenv("COLLECTION_NAME", "rag_collection")

    # Use PGVector (current stable API in langchain-postgres 0.0.16)
    if PGVector is None:  # pragma: no cover
        msg = (
            "langchain-postgres is not installed. "
            "Install with: pip install -U langchain-postgres asyncpg"
        )
        raise ModuleNotFoundError(msg)

    print("Creating PGVector with async mode...")
    store = PGVector(
        embeddings=embeddings,
        connection=connection_string,
        collection_name=collection_name,
        async_mode=True,  # Enable async mode for asyncpg
        create_extension=False,  # Neon cloud already has pgvector extension installed
    )

    return store
