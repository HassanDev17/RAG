import time

from app.core.config import get_settings
from app.rag.chunking import build_chunks, content_hash as compute_hash
from app.rag.embeddings import get_embeddings
from app.rag.notion_loader import NotionLoader
from app.rag.store import (
    delete_chunks,
    ensure_schema,
    get_connection,
    get_document_hash,
    insert_chunks,
    upsert_document,
)


def _embed_with_retry(embeddings, texts: list[str], max_retries: int = 8, base_delay: float = 15.0) -> list[list[float]]:
    for attempt in range(max_retries):
        try:
            return embeddings.embed_documents(texts)
        except Exception as exc:
            is_rate_limit = "RESOURCE_EXHAUSTED" in str(exc) or "429" in str(exc)
            if not is_rate_limit or attempt == max_retries - 1:
                raise
            delay = base_delay * (attempt + 1)
            print(f"    rate limited, waiting {delay:.0f}s...")
            time.sleep(delay)
    raise RuntimeError("unreachable")


def run_ingestion() -> None:
    settings = get_settings()
    loader = NotionLoader(settings.notion_api_key)
    embeddings = get_embeddings()

    conn = get_connection()
    ensure_schema(conn)

    pages = loader.list_shared_pages()
    print(f"Found {len(pages)} page(s) shared with the integration.")

    indexed = skipped = failed = 0

    for page in pages:
        try:
            sections = loader.load_page_sections(page.page_id)
            if not sections:
                print(f"  skip (empty): {page.title}")
                skipped += 1
                continue

            new_hash = compute_hash(sections)
            existing_hash = get_document_hash(conn, page.page_id)

            if existing_hash == new_hash:
                print(f"  unchanged: {page.title}")
                skipped += 1
                continue

            chunks = build_chunks(page.title, sections)
            vectors = _embed_with_retry(embeddings, [chunk["content"] for chunk in chunks])
            for chunk, vector in zip(chunks, vectors):
                chunk["embedding"] = vector

            delete_chunks(conn, page.page_id)
            upsert_document(conn, page.page_id, page.title, page.url, new_hash)
            insert_chunks(conn, page.page_id, chunks)
            conn.commit()

            print(f"  indexed: {page.title} ({len(chunks)} chunks)")
            indexed += 1
        except Exception as exc:  # keep the run alive across page failures
            conn.rollback()
            print(f"  FAILED: {page.title} — {exc}")
            failed += 1

    conn.close()
    print(f"\nDone. indexed={indexed} unchanged={skipped} failed={failed}")


if __name__ == "__main__":
    run_ingestion()
