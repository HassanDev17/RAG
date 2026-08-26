from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector

from app.core.config import get_settings

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> psycopg.Connection:
    settings = get_settings()
    conn = psycopg.connect(settings.supabase_db_url, autocommit=False)
    register_vector(conn)
    return conn


def ensure_schema(conn: psycopg.Connection) -> None:
    conn.execute(_SCHEMA_PATH.read_text())
    conn.commit()


def get_document_hash(conn: psycopg.Connection, page_id: str) -> str | None:
    row = conn.execute(
        "select content_hash from documents where page_id = %s", (page_id,)
    ).fetchone()
    return row[0] if row else None


def upsert_document(conn: psycopg.Connection, page_id: str, title: str, url: str, content_hash: str) -> None:
    conn.execute(
        """
        insert into documents (page_id, title, url, content_hash, last_synced_at)
        values (%s, %s, %s, %s, now())
        on conflict (page_id) do update
        set title = excluded.title,
            url = excluded.url,
            content_hash = excluded.content_hash,
            last_synced_at = now()
        """,
        (page_id, title, url, content_hash),
    )


def delete_chunks(conn: psycopg.Connection, page_id: str) -> None:
    conn.execute("delete from chunks where page_id = %s", (page_id,))


def insert_chunks(conn: psycopg.Connection, page_id: str, chunks: list[dict]) -> None:
    for chunk in chunks:
        conn.execute(
            """
            insert into chunks (page_id, chunk_index, heading_path, content, embedding)
            values (%s, %s, %s, %s, %s)
            """,
            (page_id, chunk["chunk_index"], chunk["heading_path"], chunk["content"], chunk["embedding"]),
        )
