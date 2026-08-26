import psycopg.rows

from app.rag.embeddings import get_embeddings
from app.rag.store import get_connection


def search(query: str, k: int = 25) -> list[dict]:
    embeddings = get_embeddings()
    query_embedding = embeddings.embed_query(query)

    conn = get_connection()
    try:
        cur = conn.cursor(row_factory=psycopg.rows.dict_row)
        cur.execute(
            "select * from hybrid_search(%s, %s::vector, %s)",
            (query, query_embedding, k),
        )
        return cur.fetchall()
    finally:
        conn.close()
