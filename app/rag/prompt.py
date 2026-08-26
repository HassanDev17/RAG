SYSTEM_INSTRUCTIONS = (
    "You are an internal assistant helping new joiners understand company principles, "
    "policies, coding guidelines, and past incidents. Answer the question using ONLY the "
    "context below. Cite sources by their [number]. If the context doesn't contain the "
    "answer, say you don't know rather than guessing."
)

NO_CONTEXT_INSTRUCTIONS = (
    "You are an internal assistant for new joiners. No relevant company documents were "
    "found for this question. Tell the user clearly that nothing relevant was found in "
    "the knowledge base, rather than guessing or answering from general knowledge."
)


def build_prompt(question: str, chunks: list[dict]) -> str:
    if not chunks:
        return f"{NO_CONTEXT_INSTRUCTIONS}\n\nQuestion: {question}"

    context = "\n\n".join(
        f"[{index}] Source: {chunk['title']} ({chunk['url']})\n{chunk['content']}"
        for index, chunk in enumerate(chunks, start=1)
    )

    return f"{SYSTEM_INSTRUCTIONS}\n\nContext:\n{context}\n\nQuestion: {question}"
