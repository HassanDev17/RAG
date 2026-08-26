# RAG Architecture Decisions

Status: decided. Ingestion and retrieval implemented 2026-08-26; reranker included.
History-aware query rewriting and multi-query expansion remain unimplemented (see Open items).

## Context

The project is becoming an internal assistant for new joiners: company principles, policies,
coding/developer guidelines, and past incidents (for diagnosing issues). This requires adding a
retrieval step — implemented with LangChain — that augments the user's query with relevant
context before it reaches the generator (currently `app/services/llm.py`).

Source systems for policies and incidents are not centralized yet (TBD — Confluence, Jira,
Notion, or plain files are all still open). The ingestion layer is designed so that decision can
be made later without restructuring anything below it (see "Ingestion" below).

## 1. Data sources / knowledge bases

Treated as **four distinct collections**, not one corpus — they differ in structure, freshness,
and the cost of a wrong answer.

| Collection | Typical source | Update cadence | Risk if stale/wrong |
|---|---|---|---|
| Company principles/values | A handful of stable docs | Rare | Low — mostly cultural |
| Policies (HR, security, compliance) | Confluence/Notion/PDFs | Occasional, versioned | High — wrong policy answer is a real problem |
| Coding & dev guidelines | Markdown in repos (READMEs, CONTRIBUTING.md, style guides) | Frequent, tied to PRs | Medium — stale advice wastes dev time |
| Past incidents / postmortems | Jira/Linear/Confluence postmortems | Frequent, append-only | High for the diagnosis use case — this is the corpus that most needs retrieval precision |

Every chunk carries metadata: `source_type`, `title`, `url`, `last_updated`, `owner_team`, and
ideally `doc_version` — policies need an "is this still current" signal, since confidently
serving a superseded policy is worse than not answering.

**Ingestion**: sources are TBD, so the loader layer is a generic abstraction
(`app/rag/loaders/`) with one implementation per source type. Start with a local-files loader
(markdown/PDF in a docs directory) as a placeholder; a Confluence or Jira connector slots in
later as one new loader implementation, mirroring the provider-swap pattern already used for
the LLM (`app/services/llm.py`'s `_PROVIDERS` dict).

## 2. Retrieval technique

**Hybrid retrieval (dense + keyword/BM25), not vector-only.** Incident diagnosis queries lean on
exact tokens (error codes, service names, stack traces) that embeddings often miss or blur;
policy/principle queries lean on paraphrase ("how much PTO do I get" → "leave policy") that only
dense search reliably catches. LangChain's `EnsembleRetriever` combining a pgvector retriever and
a full-text/BM25 retriever is the pattern.

**Chunking**: structure-aware, not fixed-width. Split on headings/sections (most of this corpus
is already structured markdown/policy docs), ~500–800 tokens with light overlap, and prepend the
heading breadcrumb to each chunk so it reads sensibly out of context.

**Query augmentation** (the step before the generator) — two mechanisms, not one:

- **History-aware query rewriting** — a new joiner's chat will have follow-ups ("what about for
  contractors?"), so the retrieval query must be reformulated against prior turns before hitting
  the retriever, not just the latest message.
- **Multi-query expansion** for ambiguous queries — have the LLM generate 2–3 phrasings and
  retrieve for each, union the results. Particularly worth it for incident diagnosis, since users
  describing a bug rarely phrase it the way the postmortem did.

## 3. Vector database: Postgres + pgvector

Chosen over Chroma and Pinecone.

- This is internal company data — incidents and policies are exactly the content that shouldn't
  sit in a third-party vector SaaS by default. Pinecone means an extra vendor and a data
  residency question for content that's often sensitive.
- Metadata filtering (source_type, team, freshness, possibly access level) needs to work
  alongside retrieval. pgvector does vector search, full-text search (the BM25 half of hybrid
  retrieval), and relational metadata filtering in **one system** — one set of backups, one
  access-control model — instead of syncing a vector store and a separate metadata store.
- Scale is realistically thousands to low tens-of-thousands of chunks, nowhere near where
  Pinecone's scale advantage matters.
- Chroma remains fine for local prototyping before Postgres is stood up, but isn't the
  production choice — weaker metadata filtering and access control than pgvector.

## 4. Reranker: yes

Hybrid retrieval at top-k≈20–30 is cheap and high-recall but noisy in ranking, especially across
a heterogeneous corpus where a policy chunk and an incident chunk can score similarly for a vague
query. A cross-encoder reranker narrows that to the top 4–6 chunks actually passed to the
generator. Given the use case is diagnosing real issues for someone new to the codebase, ranking
precision matters more than the ~100–300ms added latency.

Leaning toward a self-hosted `bge-reranker` over Cohere Rerank's API, for the same data-residency
reason as the vector DB choice — avoids sending internal incident/policy text to another external
API. Revisit if self-hosted quality or latency proves insufficient.

## Implementation notes (retrieval flow, built 2026-08-26)

Hybrid search is implemented as a single Postgres function, `hybrid_search()`
(`app/rag/schema.sql`), rather than LangChain's `EnsembleRetriever` — one SQL round trip,
RRF fusion done server-side over a vector CTE (`embedding <=> query_embedding`) and a keyword
CTE (`content_tsv @@ websearch_to_tsquery(...)`, generated `tsvector` column + GIN index).
`app/rag/retrieval.py` embeds the query and calls the function; `app/rag/reranker.py` reranks
the top ~25 candidates down to 5 with a self-hosted `BAAI/bge-reranker-base` cross-encoder;
`app/rag/prompt.py` builds the grounded prompt (cite-by-number, explicit "say you don't know"
instruction, and a distinct instruction path when zero chunks match). Orchestrated in
`app/services/chat.py`'s `handle_chat()`.

Verified end-to-end: in-corpus questions (e.g. leave carry-over) return correctly cited,
grounded answers; out-of-corpus questions (e.g. "capital of Mars") correctly return "I don't
know" instead of hallucinating.

## Open items

- Source connectors for policies and incidents — pick once the source systems are decided
  (Confluence/Notion/Jira/plain files); design above already isolates this to the loader layer.
- Access control / sensitivity tiers on documents — not yet designed; matters once policies with
  restricted audiences (e.g., HR-only) enter the corpus.
- Reranker hosting: self-hosted `bge-reranker-base` shipped as decided; not yet benchmarked
  against Cohere Rerank for quality/latency at scale.
- History-aware query rewriting and multi-query expansion — deferred; needs `ChatMessage` and
  the Streamlit frontend to carry conversation history, which neither does yet (single-turn only).
