import time

from app.rag.prompt import build_prompt
from app.rag.reranker import rerank
from app.rag.retrieval import search
from app.schemas.chat import ChatMessage, ChatResponse, TokenUsage
from app.services.llm import generate_reply

RETRIEVE_K = 25
RERANK_TOP_N = 5


def handle_chat(message: ChatMessage) -> ChatResponse:
    start = time.perf_counter()

    candidates = search(message.content, k=RETRIEVE_K)
    top_chunks = rerank(message.content, candidates, top_n=RERANK_TOP_N)
    prompt = build_prompt(message.content, top_chunks)
    result = generate_reply(prompt)

    latency_ms = (time.perf_counter() - start) * 1000

    return ChatResponse(
        role="assistant",
        content=result.content,
        token_usage=TokenUsage(
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
        ),
        latency_ms=round(latency_ms, 1),
    )
