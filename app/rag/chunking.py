import hashlib

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.notion_loader import Section

MAX_CHARS = 3200
OVERLAP = 400

_splitter = RecursiveCharacterTextSplitter(chunk_size=MAX_CHARS, chunk_overlap=OVERLAP)


def build_chunks(page_title: str, sections: list[Section]) -> list[dict]:
    chunks: list[dict] = []
    index = 0

    for section in sections:
        breadcrumb = " > ".join([page_title, *section.heading_path])

        # Code and table sections stay atomic even if long; prose sections get
        # split only when they exceed the target chunk size.
        if section.kind in ("code", "table") or len(section.content) <= MAX_CHARS:
            pieces = [section.content]
        else:
            pieces = _splitter.split_text(section.content)

        for piece in pieces:
            chunks.append(
                {
                    "chunk_index": index,
                    "heading_path": " > ".join(section.heading_path),
                    "content": f"{breadcrumb}\n\n{piece}",
                }
            )
            index += 1

    return chunks


def content_hash(sections: list[Section]) -> str:
    joined = "\n".join(section.content for section in sections)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
