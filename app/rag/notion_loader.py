from dataclasses import dataclass

from notion_client import Client

# Block types that carry a simple rich_text field we render as-is (or with a
# small prefix). Anything not listed here that also isn't handled specially
# below (heading/code/table/image/child_page) is skipped.
_TEXT_BLOCK_TYPES = {
    "paragraph",
    "bulleted_list_item",
    "numbered_list_item",
    "to_do",
    "quote",
    "callout",
}

# Block types whose children are worth flattening into the parent section
# (nested list items, expanded toggles) rather than treated as new sections.
_INLINE_CHILD_TYPES = {"toggle", "bulleted_list_item", "numbered_list_item", "quote", "callout"}


@dataclass
class Section:
    heading_path: list[str]
    kind: str  # "text" | "code" | "table"
    content: str


@dataclass
class NotionPage:
    page_id: str
    title: str
    url: str = ""


def _rich_text(rich_text: list[dict]) -> str:
    return "".join(part.get("plain_text", "") for part in rich_text)


def _block_text(block: dict) -> str:
    btype = block["type"]
    if btype not in _TEXT_BLOCK_TYPES:
        return ""

    data = block.get(btype, {})
    text = _rich_text(data.get("rich_text", []))
    if not text:
        return ""

    if btype == "bulleted_list_item":
        return f"- {text}"
    if btype == "numbered_list_item":
        return f"1. {text}"
    if btype == "to_do":
        mark = "x" if data.get("checked") else " "
        return f"[{mark}] {text}"
    if btype in ("quote", "callout"):
        return f"> {text}"
    return text


def _extract_title(page: dict) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return _rich_text(prop.get("title", [])) or "(untitled)"
    return "(untitled)"


class NotionLoader:
    def __init__(self, api_key: str) -> None:
        self.client = Client(auth=api_key)

    def list_shared_pages(self) -> list[NotionPage]:
        pages: list[NotionPage] = []
        cursor = None

        while True:
            response = self.client.search(
                filter={"property": "object", "value": "page"},
                start_cursor=cursor,
                page_size=100,
            )
            for result in response["results"]:
                pages.append(
                    NotionPage(
                        page_id=result["id"],
                        title=_extract_title(result),
                        url=result.get("url", ""),
                    )
                )
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        return pages

    def load_page_sections(self, page_id: str) -> list[Section]:
        blocks = self._list_children(page_id)
        sections: list[Section] = []
        heading_path: list[str] = []
        buffer: list[str] = []

        def flush() -> None:
            text = "\n".join(line for line in buffer if line.strip())
            if text.strip():
                sections.append(Section(heading_path=list(heading_path), kind="text", content=text))
            buffer.clear()

        for block in blocks:
            btype = block["type"]

            if btype in ("heading_1", "heading_2", "heading_3"):
                flush()
                level = int(btype[-1])
                text = _rich_text(block[btype].get("rich_text", []))
                heading_path[:] = heading_path[: level - 1] + ([text] if text else [])
                continue

            if btype == "code":
                flush()
                text = _rich_text(block["code"].get("rich_text", []))
                language = block["code"].get("language", "")
                sections.append(
                    Section(list(heading_path), "code", f"```{language}\n{text}\n```")
                )
                continue

            if btype == "table":
                flush()
                table_text = self._render_table(block["id"])
                if table_text:
                    sections.append(Section(list(heading_path), "table", table_text))
                continue

            if btype == "image":
                # Skipped for now — see docs/rag-architecture-decisions.md for the
                # caption-first / vision-fallback plan when images enter the corpus.
                continue

            if btype in ("child_page", "child_database"):
                # These are separate top-level documents (already covered by
                # list_shared_pages), not content nested inside this page.
                continue

            text = _block_text(block)
            if text:
                buffer.append(text)

            if block.get("has_children") and btype in _INLINE_CHILD_TYPES:
                buffer.extend(f"  {line}" for line in self._flatten_children_text(block["id"]))

        flush()
        return sections

    def _list_children(self, block_id: str) -> list[dict]:
        results: list[dict] = []
        cursor = None

        while True:
            response = self.client.blocks.children.list(
                block_id=block_id, start_cursor=cursor, page_size=100
            )
            results.extend(response["results"])
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        return results

    def _flatten_children_text(self, block_id: str) -> list[str]:
        lines: list[str] = []
        for child in self._list_children(block_id):
            text = _block_text(child)
            if text:
                lines.append(text)
            if child.get("has_children"):
                lines.extend(self._flatten_children_text(child["id"]))
        return lines

    def _render_table(self, table_block_id: str) -> str:
        rows = self._list_children(table_block_id)
        lines: list[str] = []
        for index, row in enumerate(rows):
            cells = row.get("table_row", {}).get("cells", [])
            cell_texts = [_rich_text(cell) for cell in cells]
            lines.append("| " + " | ".join(cell_texts) + " |")
            if index == 0:
                lines.append("| " + " | ".join("---" for _ in cells) + " |")
        return "\n".join(lines)
