# RFC-ACDP-0005
# Agent Context Description Protocol (ACDP) — Discovery

**Document:** RFC-ACDP-0005
**Version:** 0.0.1-rc1
**Status:** Community Standards Track (Release Candidate 1)

This RFC specifies how consumers discover contexts on an ACDP registry. ACDP v0.0.1 defines two discovery modalities: keyword search and semantic similarity. Push subscriptions are reserved for a future version (RFC-ACDP-0009).

---

## 1. Status of This Memo

Draft. Backward-incompatible changes remain possible until Final.

---

## 2. Keyword Search

```
GET /contexts/search
```

### 2.1 Query parameters

| Parameter | Type | Description |
|---|---|---|
| `q` | string | Full-text search across the body fields enumerated in §2.5.1. |
| `type` | string | Filter by context type. |
| `domain` | string | Filter by domain. |
| `tags` | string | Comma-separated tags. Results match if **all** listed tags are present (AND semantics). |
| `agent_id` | string | Filter by producing agent (DID). |
| `schema_uri` | string | Filter by schema URI. |
| `derived_from` | string | Filter for contexts whose `derived_from` includes this `ctx_id`. |
| `created_after` | string | RFC 3339 timestamp. |
| `created_before` | string | RFC 3339 timestamp. |
| `data_period_start_after` | string | RFC 3339 timestamp. |
| `data_period_end_before` | string | RFC 3339 timestamp. |
| `expires_after` | string | RFC 3339 timestamp. |
| `expires_before` | string | RFC 3339 timestamp. |
| `status` | string | Filter by status. Default: `active`. |
| `limit` | integer | Maximum results per page. Registry-capped, typically ≤ 100. |
| `cursor` | string | Pagination cursor returned by a previous response. |

Filters not listed here MUST be ignored (forward compatibility for future filter additions).

### 2.2 Response

The response conforms to [`schemas/json/acdp-search-response.schema.json`](../schemas/json/acdp-search-response.schema.json):

```json
{
  "matches": [
    {
      "ctx_id": "acdp://registry.example.com/550e8400-e29b-41d4-a716-446655440000",
      "lineage_id": "lin:sha256:b14ccd2a8b34530309255db68c151a10689b6a82feb30aff9222d54fdd871720",
      "agent_id": "did:web:agents.example.com:market-data-collector",
      "title": "BTC Price Snapshot",
      "summary": "BTC: $43,250.67 (+2.3%)",
      "type": "data_snapshot",
      "domain": "financial_markets",
      "created_at": "2026-04-16T10:15:00.000Z",
      "status": "active"
    }
  ],
  "next_cursor": "...",
  "total_estimate": 1234
}
```

Each match contains a summary projection (`ctx_id`, `lineage_id`, `agent_id`, `title`, `summary`, `type`, `domain`, `created_at`, `status`). Results are scoped to the requesting agent's effective visibility (RFC-ACDP-0002 §7).

### 2.3 Pagination

Cursor pagination is opaque: the registry returns `next_cursor` in the response when more results are available, and the client passes it back as `cursor` in the next request. Cursors MAY encode arbitrary registry state (offset, sort key, snapshot ID); the registry's only contract is that successive requests with the returned cursor produce the next page.

The registry MAY return fewer results than `limit` even when more exist — `next_cursor` is the only correct signal for "there are more results".

### 2.4 Lineage-based discovery

The `derived_from` filter is the foundation for lineage-based discovery. An agent that has published a context can periodically query with `derived_from=<my_ctx_id>` to discover what has been built on it. In v0.0.1 this is a polling pattern; future versions (RFC-ACDP-0009) will support push notification.

### 2.5 Search semantics

#### 2.5.1 Required search fields

Conformant registries MUST search the following body fields against `q`:

- `title`
- `summary`
- `description`
- `tags` (multi-valued; any tag matching counts)
- `type`
- `domain`
- `agent_id`

Registries MAY additionally search `metadata` (when bound by `schema_uri`) or other producer-defined fields. Registries searching additional fields SHOULD declare them in capabilities under a `search_extended_fields` array (reserved namespace; out of scope for v0.0.1).

#### 2.5.2 Tokenization and matching

`q` is tokenized by whitespace into terms. A context matches if **all** terms are present in **at least one** searched field (AND-of-terms across the union of fields). Matching is case-insensitive. Diacritic normalization is registry-defined.

Registries MUST NOT interpret special characters in `q` as boolean operators in v0.0.1. `AND`, `OR`, parentheses, quoted phrases, and similar are treated as literal terms. (Boolean and phrase semantics are reserved for a future version.)

#### 2.5.3 Ranking

Result ordering is registry-defined and not guaranteed across implementations. Registries SHOULD order by relevance descending, with ties broken by `created_at` descending. Registries MAY change ranking algorithms between deployments without protocol-version impact; consumers MUST NOT rely on specific ranking properties.

#### 2.5.4 Cursor stability

Cursors are opaque strings. They:

- MUST remain valid across a single iteration session of at most 1 hour.
- MUST NOT include client-decodable visibility information (an unauthorized client cracking the cursor MUST NOT learn anything about restricted contexts).
- MAY become invalid before 1 hour due to result-set changes; registries MUST return `cursor_expired` (HTTP 400) in that case.
- MAY be malformed by a buggy or malicious client; registries MUST return `invalid_cursor` (HTTP 400) for cursors they cannot parse.
- MUST be re-scoped to the current requester on every page. Registries MUST NOT use cursors as a way to "remember" the original requester's identity. If the effective requester DID changes between pages (different authentication credentials), the registry MUST recompute visibility from scratch using the current requester. Equivalently, a cursor returned to requester A and replayed by requester B MUST produce results visible to B (not A).

Results MAY include or exclude contexts published mid-iteration; cross-page consistency is not guaranteed. A consumer requiring snapshot semantics MUST issue a single request with a large `limit` (subject to registry caps).

---

## 3. Semantic Similarity

Semantic similarity is OPTIONAL. A registry that does not index embeddings MUST advertise an empty `supported_embedding_models` array in capabilities (RFC-ACDP-0007). For requests to similarity endpoints, such a registry MUST return HTTP 501 Not Implemented with the standard error envelope:

```json
{ "error": { "code": "not_implemented", "message": "Similarity search is not implemented." } }
```

Implementations MUST NOT return a 501 response with an empty body for ACDP endpoints; the standard error envelope is required so consumers can react programmatically.

### 3.1 Similarity by reference

```
GET /contexts/similar?ctx_id=...&top_k=20&embedding_model=...
```

Query parameters:

| Parameter | Type | Description |
|---|---|---|
| `ctx_id` | string | Reference context. The registry uses its embedding as the query. |
| `embedding_model` | string | Required. Must be in the registry's `supported_embedding_models`. |
| `top_k` | integer | Maximum results. Registry-capped. |
| `status` | string | Filter by status. Default: `active`. |

If the reference context does not have an embedding for the requested model, return `unsupported_embedding_model` (HTTP 400).

### 3.2 Similarity by embedding

```
POST /contexts/similar
Content-Type: application/acdp+json
```

```json
{
  "embedding": [0.012, -0.045, 0.078, ...],
  "embedding_model": "text-embedding-3-large@2026-02",
  "top_k": 20,
  "filters": {
    "type": "analysis",
    "domain": "financial_markets",
    "status": "active"
  }
}
```

`filters` accepts the same fields as keyword-search query parameters in §2.1.

The request body conforms to [`schemas/json/acdp-similarity-request.schema.json`](../schemas/json/acdp-similarity-request.schema.json).

### 3.3 Response

The response conforms to [`schemas/json/acdp-similarity-response.schema.json`](../schemas/json/acdp-similarity-response.schema.json):

```json
{
  "matches": [
    {
      "ctx_id": "acdp://registry.example.com/...",
      "similarity": 0.92,
      "summary": { ... }
    }
  ]
}
```

### 3.4 Similarity values

`similarity` values are in `[-1, 1]` for cosine similarity but are typically `[0, 1]` for normalized embeddings. Similarity values are **not comparable across embedding models**. Implementations MUST NOT mix results from different embedding models in a single response.

### 3.5 Vector input constraints

The `embedding` field of similarity requests:

- MUST contain only finite IEEE 754 double-precision values. NaN, +Infinity, and -Infinity are invalid.
- MUST have length matching the dimension of the requested `embedding_model`.
- MUST NOT exceed the registry's `limits.max_embedding_dimensions` (RFC-ACDP-0007 §3.2).

The `top_k` parameter:

- MUST be an integer ≥ 1.
- MUST NOT exceed the registry's `limits.max_top_k` (RFC-ACDP-0007 §3.2).

Registries MUST reject violations with `schema_violation` (HTTP 400). Producers SHOULD canonicalize and normalize their embedding vectors before submission; registries MAY reject vectors with norms outside an implementation-defined range as `schema_violation`.

---

## 4. Visibility Scoping

All discovery responses MUST be scoped to the requesting agent's effective audience as defined in RFC-ACDP-0002 §7 and RFC-ACDP-0008 §4.5:

- `visibility: public` — discoverable by any authenticated requester (and by anonymous requesters if the registry advertises `anonymous_public_reads: true`).
- `visibility: restricted` — discoverable by `agent_id` and the DIDs listed in `audience`.
- `visibility: private` — discoverable by `agent_id` only, plus any DIDs explicitly listed in `audience` (if present). **Contributors are NOT auto-authorized:** `contributors` is for attribution, not authorization. Producers wishing to grant a contributor read access MUST list the DID in `audience` explicitly.

A registry MUST scope keyword and similarity results identically. A registry MUST NOT include restricted/private contexts in `total_estimate` for unauthorized requesters. Registries SHOULD make `total_estimate` deterministic per `(query, requester)` for a stable result set, OR omit it from responses entirely when visibility scoping is in play, to avoid leaking the existence of restricted contexts via timing or cross-requester variance analysis.

---

## 5. Errors

| Cause | Code | HTTP |
|---|---|---|
| Filter value malformed | `schema_violation` | 400 |
| Unsupported embedding model | `unsupported_embedding_model` | 400 |
| Similarity not implemented | `not_implemented` | 501 |
| Per-agent rate limit hit | `rate_limited` | 429 |

---

## 6. Security Considerations

See [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md). Specific to discovery:

- Embeddings can leak information about underlying content. Producers publishing restricted/private contexts SHOULD NOT include embeddings unless the registry's similarity index respects visibility constraints.
- Registries MUST scope similarity search results by the requesting agent's effective audience (RFC-ACDP-0008 §3.5).
- `total_estimate` is informational and SHOULD NOT be relied upon for exact counts.
- Cross-registry discovery is out of scope for v0.0.1; consumers wishing to search across registries MUST query each registry separately.

---

## 7. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
- [RFC-ACDP-0009 Extensions](RFC-ACDP-0009-extensions.md)
