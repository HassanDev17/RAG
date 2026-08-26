from functools import lru_cache

from sentence_transformers import CrossEncoder

_MODEL_NAME = "BAAI/bge-reranker-base"


@lru_cache
def get_reranker() -> CrossEncoder:
    return CrossEncoder(_MODEL_NAME)


def rerank(query: str, candidates: list[dict], top_n: int = 5) -> list[dict]:
    if not candidates:
        return []

    pairs = [(query, candidate["content"]) for candidate in candidates]
    scores = get_reranker().predict(pairs)

    ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)
    return [candidate for candidate, _ in ranked[:top_n]]
