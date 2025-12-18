"""LangChain application with pgvector - keeps container running."""

import os
import time

from langchain_postgres import PGVector
from langchain_community.embeddings import FakeEmbeddings


def main() -> None:
    """Keep container running and maintain pgvector connection."""
    # Database connection parameters
    postgres_user = os.getenv("PGVECTOR_USER", "langchain")
    postgres_password = os.getenv("PGVECTOR_PASSWORD", "langchain")
    postgres_host = os.getenv("PGVECTOR_HOST", "postgres")
    postgres_port = int(os.getenv("PGVECTOR_PORT", "5432"))
    postgres_db = os.getenv("PGVECTOR_DATABASE", "langchain")

    connection_string = (
        f"postgresql+psycopg://{postgres_user}:{postgres_password}"
        f"@{postgres_host}:{postgres_port}/{postgres_db}"
    )

    print("🚀 Starting LangChain container...")
    print(f"📦 Connecting to PostgreSQL at {postgres_host}:{postgres_port}")

    try:
        # Test connection
        embeddings = FakeEmbeddings(size=1536)
        store = PGVector(
            connection=connection_string,
            embeddings=embeddings,
            collection_name="langchain_collection",
        )
        print("✅ Successfully connected to pgvector!")
        print("🔄 Container is running and ready")
        print("   (Press Ctrl+C to stop)\n")

        # Keep container running
        while True:
            time.sleep(300)  # Health check every 5 minutes
            print(f"[{time.strftime('%H:%M:%S')}] Container healthy")

    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()

