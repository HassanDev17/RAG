from app.rag.prompt import build_prompt
from app.rag.reranker import rerank
from app.rag.retrieval import search
from app.schemas.chat import ChatMessage, ChatResponse
from app.services.llm import generate_reply

RETRIEVE_K = 25
RERANK_TOP_N = 5


def handle_chat(message: ChatMessage) -> ChatResponse:
    candidates = search(message.content, k=RETRIEVE_K)
    top_chunks = rerank(message.content, candidates, top_n=RERANK_TOP_N)
    prompt = build_prompt(message.content, top_chunks)
    reply = generate_reply(prompt)
    return ChatResponse(role="assistant", content=reply)
