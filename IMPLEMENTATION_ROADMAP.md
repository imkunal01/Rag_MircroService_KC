# Production Recommendation System Roadmap

## 1. Current State (Already Implemented)

### API and Core Flow
- FastAPI app and routing are set up.
- `POST /api/recommend` returns:
  - parsed filters
  - ranked products
  - generated answer
  - explainability fields (`top_products`, `why_recommended`, `comparison`)
- Products are sourced from external API via `PRODUCTS_API_URL`.

### Retrieval and Ranking
- Query parser supports category and price extraction.
- Hybrid ranking combines:
  - semantic score
  - lexical overlap
  - intent match
  - rating prior
- Semantic vectors are currently built in memory at request time.

### LLM Generation
- Gemini integration is implemented through REST API.
- Prompt includes guardrails to reduce hallucinations.
- Fallback deterministic answer exists if Gemini is unavailable.

### Operational Basics
- Environment loading via `.env` is enabled.
- Basic logging is present.
- Product source connection failures are logged.

---

## 2. Critical Gaps to Become Production-Ready

### Vector Database (Must Have)
- No persistent vector DB is connected yet.
- No index lifecycle (create, upsert, delete, reindex).
- No background index synchronization.

### Reliability
- Retrieval path can still degrade to full failure without detailed diagnostics.
- No circuit breaker/retry policy for external product API and Gemini.
- No cache warming strategy for high traffic.

### Observability
- No metrics (latency, error rate, embedding time, vector query time, token usage).
- No tracing or correlation IDs.
- No dashboards/alerts.

### Security and Governance
- No authentication/authorization on recommendation endpoints.
- No rate limiting or abuse controls.
- No secrets validation at startup.
- No PII redaction/log policy.

### Testing and Quality
- No dedicated integration test suite for:
  - external product API failures
  - vector DB failures
  - Gemini timeout/errors
- No load/performance test baselines.
- No regression benchmark set for recommendation quality.

### Deployment and DevOps
- No production Docker setup and runtime profile.
- No CI/CD checks for lint, tests, security scan.
- No migration/versioning strategy for vector index schema.

---

## 3. Pinecone Implementation Plan

## Phase A: Foundation
1. Add dependencies:
- `pinecone-client`

2. Add environment variables:
- `PINECONE_API_KEY`
- `PINECONE_INDEX_NAME`
- `PINECONE_NAMESPACE`
- `PINECONE_CLOUD`
- `PINECONE_REGION`
- `PINECONE_TOP_K_DEFAULT`

3. Create Pinecone store module:
- `app/rag/pinecone_store.py`
- Responsibilities:
  - connect/init index
  - upsert vectors with metadata
  - query vectors with optional metadata filters
  - delete/update by product id

## Phase B: Indexing Pipeline
1. Build product-to-document transformer:
- canonical text generation for embeddings

2. Implement sync job:
- pull products from `PRODUCTS_API_URL`
- generate embeddings
- upsert to Pinecone
- persist sync status (`last_sync_at`, item count, failed ids)

3. Add admin endpoint (secured):
- `POST /api/admin/reindex`
- `GET /api/admin/index-status`

## Phase C: Query Path Migration
1. In recommendation flow:
- parse filters
- convert query to embedding
- query Pinecone top-k with metadata constraints (category/price)
- apply hybrid reranker on returned candidates

2. Remove per-request in-memory vector rebuild.

3. Keep graceful fallback policy:
- if Pinecone unavailable, return explicit service error (or controlled degraded mode if chosen).

## Phase D: Hardening
1. Add retries/timeouts:
- product API, Pinecone, Gemini

2. Add caching:
- short TTL cache for frequent queries

3. Add structured logging and metrics:
- request id
- durations per stage
- model and token usage

4. Add rate limiting + auth.

---

## 4. Production Readiness Checklist

## Functional
- [ ] `POST /api/recommend` uses Pinecone retrieval in production path.
- [ ] Reindex endpoint works and is secured.
- [ ] Metadata filters (category, min/max price) are applied at retrieval layer.

## Reliability
- [ ] Timeouts configured for all external calls.
- [ ] Retry policy with backoff implemented.
- [ ] Clear failure modes and HTTP status mapping defined.

## Performance
- [ ] p95 and p99 latency measured under load.
- [ ] Embedding and vector query timings logged.
- [ ] Throughput targets documented and met.

## Security
- [ ] API auth enabled.
- [ ] Rate limiting enabled.
- [ ] Secrets only from env/secret manager.

## Quality
- [ ] Unit tests for parser/reranker/generator prompt constraints.
- [ ] Integration tests with mocked Pinecone and product API.
- [ ] End-to-end tests for success and failure paths.

## Ops
- [ ] Health endpoints for dependencies.
- [ ] Dashboard + alerts for error rate and latency.
- [ ] Runbook for incidents (Pinecone down, product API down, Gemini down).

---

## 5. Suggested Next 7-Day Execution Plan

### Day 1
- Add Pinecone config + client module
- Create index connection checks

### Day 2
- Build reindex pipeline and status tracking
- Add admin endpoints for reindex/status

### Day 3
- Wire Pinecone query into recommendation service
- Keep existing hybrid reranker on top-k candidates

### Day 4
- Add reliability patterns (timeouts/retries/circuit breakers)
- Improve error classification and response codes

### Day 5
- Add metrics, request IDs, and structured logs
- Add dependency health checks

### Day 6
- Write integration and load tests
- Validate quality with benchmark queries

### Day 7
- Security hardening and deployment checklist
- Final documentation and handoff
