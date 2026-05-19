# RFC-ACDP-0005
# Agent Context Description Protocol (ACDP) — Discovery

**Document:** RFC-ACDP-0005
**Version:** 0.1.0-rc1
**Status:** Community Standards Track (Release Candidate 1)

This RFC specifies how consumers discover contexts on an ACDP registry. ACDP v0.1.0 defines one discovery modality: keyword search. Semantic similarity and push subscriptions are reserved for a future version (RFC-ACDP-0009 §2.4, §2.9).

---

## 1. Status of This Memo

This document is a Release Candidate (acdp/0.1.0-rc1). Backward-incompatible changes remain possible until Final; only editorial fixes are expected during the RC window.

---

## 2. Keyword Search

```
GET /contexts/search
```

This endpoint is part of the `acdp-registry-discovery` profile (RFC-ACDP-0001 §9.1). A registry that does not declare `acdp-registry-discovery` in its `profiles` capability MUST return `not_implemented` (HTTP 501) with the standard error envelope when this endpoint is requested.

### 2.1 Query parameters

| Parameter | Type | Description |
|---|---|---|
| `q` | string | Full-text search across the body fields enumerated in §2.5.1. |
| `type` | string | Filter by context type. |
| `domain` | string | Filter by domain. |
| `tags` | string | Comma-separated tags. Results match if **all** listed tags are present (AND semantics). |
| `agent_id` | string | Filter by producing agent (DID). |
| `schema_uri` | string | Exact string match against `body.schema_uri`. Case-sensitive; no normalization (no trailing-slash, query-string, or fragment folding). Registries MUST treat the value as opaque and return only contexts whose body field is byte-identical to the supplied value. |
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

The response conforms to [`schemas/json/acdp-search-response.schema.json`](../schemas/json/acdp-search-response.schema.json).

The response object MUST use the key `matches` for the result array. The field name `results` is **not conformant**. Registries MUST emit `matches`; consumers MUST NOT accept `results` as a substitute for `matches`. The schema is `additionalProperties: false`, so a registry that emits `results` (or any other alternative spelling) violates the schema and produces a non-conformant response.

**Consumer diagnostic (SHOULD).** When a consumer receives a search response that lacks the `matches` key but contains a `results` key (or any other recognized misspelling such as `records`, `items`, `data`, `hits`, `rows`), the consumer SHOULD surface an observable diagnostic — a logged warning, a structured event, or an OpenTelemetry span attribute — naming the offending key and citing this section. The diagnostic MUST be visible without enabling debug-level logging. The functional outcome (parse error or zero matches) is the same with or without the diagnostic; the SHOULD exists so an operator chasing "search returns nothing" can distinguish "registry returned zero matches" from "registry used the wrong field name". `vis-003-search-response-key.json` includes a fixture scenario for this.

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

Each match contains a summary projection (`ctx_id`, `lineage_id`, `agent_id`, `title`, `summary`, `type`, `domain`, `created_at`, `status`, optional `visibility`). Results are scoped to the requesting agent's effective visibility (RFC-ACDP-0002 §7).

**`visibility` in `match_summary` (OPTIONAL).** Registries MAY include `visibility` in each `match_summary` to let consumers cache-classify a result before a retrieval round-trip — useful for clients that distinguish a 404 from a deletion or restriction. The disclosure rules below are NORMATIVE and exercised by fixtures `vis-006` (positive: public match SHOULD carry `visibility: public`) and `vis-007` (negative: restricted match served to an unauthorized requester MUST omit `visibility`):

- For matches with `visibility: public`, registries SHOULD include `visibility: public` in the `match_summary`. Including this field gives consumers a cache-classification signal without an additional retrieval round-trip.
- For matches with `visibility: restricted` or `visibility: private`, registries MUST include `visibility` ONLY when the requester is already authorized to retrieve the context (i.e., the effective requester DID is in `audience` for `restricted`, or is `agent_id` for either `restricted` or `private`). Including the field for any other requester leaks the visibility class to a non-authorized party even when the match itself is correctly scoped — a violation of the existence-leak prevention rule in RFC-ACDP-0008 §3.5.
- When the field is absent, consumers MUST NOT infer anything about visibility — absence is the registry's choice. v0.1.0 deployments predating this clarification are conformant without the field. Consumers MUST NOT treat `visibility`-absent as a signal of any specific visibility class.

### 2.3 Pagination

Cursor pagination is opaque: the registry returns `next_cursor` in the response when more results are available, and the client passes it back as `cursor` in the next request. Cursors MAY encode arbitrary registry state (offset, sort key, snapshot ID); the registry's only contract is that successive requests with the returned cursor produce the next page.

The registry MAY return fewer results than `limit` even when more exist — `next_cursor` is the only correct signal for "there are more results".

### 2.4 Lineage-based discovery

The `derived_from` filter is the foundation for lineage-based discovery. An agent that has published a context can periodically query with `derived_from=<my_ctx_id>` to discover what has been built on it. In v0.1.0 this is a polling pattern; future versions (RFC-ACDP-0009) will support push notification.

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

Registries MAY additionally search `metadata` (when bound by `schema_uri`) or other producer-defined fields. Registries searching additional fields SHOULD declare them in capabilities under a `search_extended_fields` array (reserved namespace; out of scope for v0.1.0).

#### 2.5.2 Tokenization and matching

`q` is tokenized by whitespace into terms. A context matches if **all** terms are present in **at least one** searched field (AND-of-terms across the union of fields). Matching is case-insensitive. Diacritic normalization is registry-defined.

Registries MUST NOT interpret special characters in `q` as boolean operators in v0.1.0. `AND`, `OR`, parentheses, quoted phrases, and similar are treated as literal terms. (Boolean and phrase semantics are reserved for a future version.)

#### 2.5.3 Ranking

Result ordering is registry-defined and not guaranteed across implementations. Registries SHOULD order by relevance descending, with ties broken by `created_at` descending. Registries MAY change ranking algorithms between deployments without protocol-version impact; consumers MUST NOT rely on specific ranking properties.

**Sort stability within a paginated sequence (MUST).** The sort order MUST be stable within a single paginated sequence. A registry issuing `next_cursor` MUST guarantee that subsequent pages continue from the same logical position in the same sort order that produced the prior page — i.e., the cursor binds not only the position but the comparator. Switching ranking algorithms, secondary sort keys, or relevance scoring mid-sequence is FORBIDDEN; consumers paginating with the returned cursor MUST NOT observe duplicate or skipped results caused by an order change.

Two additional rules govern what the cursor binds:

1. **Primary sort key.** Registries SHOULD use `created_at` descending as the primary sort key for paginated search results. Relevance ranking is permitted (per §2.5.3 above) but registries using relevance MUST snapshot the relevance score per `(query, requester)` at the time the first page's cursor is minted and reuse the snapshotted score for every subsequent page in the sequence; a "live" relevance recomputation across pages violates stability.
2. **Deterministic tiebreaker.** Ties on the primary sort key MUST be broken by a deterministic secondary key. The RECOMMENDED secondary key is `ctx_id` lexicographic ascending. The secondary key MUST be total (no two distinct contexts compare equal), so every context in the result set is reachable via pagination and no context is returned twice.

**Cursor freshness across publishes.** New contexts published between pages MAY or MAY NOT appear in subsequent pages; registries SHOULD document their cursor freshness guarantee (snapshot at first-page mint vs. live-with-stable-order). Snapshot semantics are RECOMMENDED for evidence-assembly and audit-driven consumers; live-with-stable-order is RECOMMENDED for indexing crawlers. Either choice is conformant as long as the in-sequence order is stable per the rule above.

#### 2.5.4 Cursor stability

Cursors are opaque strings. They:

- MUST remain valid across a single iteration session of at most 1 hour.
- MUST NOT include client-decodable visibility information (an unauthorized client cracking the cursor MUST NOT learn anything about restricted contexts).
- MAY become invalid before 1 hour due to result-set changes; registries MUST return `cursor_expired` (HTTP 400) in that case.
- MAY be malformed by a buggy or malicious client; registries MUST return `invalid_cursor` (HTTP 400) for cursors they cannot parse.
- MUST be re-scoped to the current requester on every page. Registries MUST NOT use cursors as a way to "remember" the original requester's identity. If the effective requester DID changes between pages (different authentication credentials), the registry MUST recompute visibility from scratch using the current requester. Equivalently, a cursor returned to requester A and replayed by requester B MUST produce results visible to B (not A).

Results MAY include or exclude contexts published mid-iteration; cross-page consistency is not guaranteed. A consumer requiring snapshot semantics MUST issue a single request with a large `limit` (subject to registry caps).

#### 2.5.5 Visibility in keyword search

The visibility matrix below is normative and consolidates the rules in §3 (visibility scoping) and RFC-ACDP-0002 §7 (visibility semantics) for the keyword-search path specifically. "Appears in search for" means included in `matches[]`, counted in `total_estimate`, and reachable via cursor pages — these are jointly equivalent on the wire.

| Visibility | Appears in keyword search for... | Retrieval (for comparison) |
|---|---|---|
| `public` | Anyone authenticated; anonymous requesters too if the registry advertises `anonymous_public_reads: true` | Same set |
| `restricted` | `agent_id` and DIDs listed in `audience` only | Same set as search |
| `private` | `agent_id` only | `agent_id` and DIDs listed in `audience` (search is strictly narrower) |

**Effect of `anonymous_public_reads` on search (NORMATIVE).** The `anonymous_public_reads` capability flag (RFC-ACDP-0007 §3.2, RFC-ACDP-0008 §6.3) governs keyword search exactly as it governs direct retrieval — it is not a retrieval-only flag:

- When `anonymous_public_reads: false` (the default), a registry MUST reject an anonymous (unauthenticated) search request with `not_authorized` (HTTP 403). An anonymous requester MUST NOT receive `public` contexts in `matches[]` and MUST NOT learn that `public` contexts exist via a non-zero `total_estimate`.
- When `anonymous_public_reads: true`, an anonymous requester MAY search and receives `public` contexts only (never `restricted` or `private`), scoped identically to an authenticated non-audience requester.
- An **authenticated** requester MAY always receive `public` contexts in search results regardless of the value of `anonymous_public_reads` — the flag constrains anonymous access only.

A registry MUST apply the `anonymous_public_reads` rule to `total_estimate` with the same scoping it applies to `matches[]`: when an anonymous request is rejected, no count is disclosed; the rule MUST NOT be enforced on `matches[]` while leaving `total_estimate` to leak the existence of public contexts. The `vis-009` conformance fixture pins this behavior.

**Q1 — `private` + `audience`:** Audience members of a `private` context can RETRIEVE the context if they know its `ctx_id` (RFC-ACDP-0002 §7), but MUST NOT discover it via keyword search. This asymmetry is intentional: `audience` on a `private` context expresses "you may read this if I send you the link", not "you may discover this". Producers wanting cohort discoverability MUST use `visibility: restricted`.

**Q2 — `private` in `derived_from` filter and other lineage queries:** A `private` context MUST NOT appear in any keyword-search result for any requester other than its `agent_id`, *including* responses to `derived_from=<ctx_id>` filter queries and any other lineage-discovery filter that may be added in the future. The `derived_from` filter is search (RFC-ACDP-0005 §2.4); search is strictly narrower than retrieval. Concretely: if a `private` context is derived from a `public` context that an audience member can search, querying `derived_from=<public_ctx_id>` MUST NOT surface the `private` derivative for that audience member. Audience members who learn the `ctx_id` out-of-band MAY retrieve it directly (RFC-ACDP-0002 §7).

This rule MUST also be applied to `total_estimate` (RFC-ACDP-0005 §3): private contexts never count toward another DID's `total_estimate`, and registries MUST avoid leaking their existence via per-requester variance in the estimate.

---

## 3. Visibility Scoping

All discovery responses MUST be scoped per the visibility matrix in RFC-ACDP-0002 §7. Search visibility is **strictly equal to or narrower than** retrieval visibility:

- `visibility: public` — discoverable by any authenticated requester (and by anonymous requesters if the registry advertises `anonymous_public_reads: true`).
- `visibility: restricted` — discoverable by `agent_id` and the DIDs listed in `audience`. Same set as retrieval.
- `visibility: private` — discoverable **only** by `agent_id`. DIDs listed in `audience` (if present) are granted **retrieval** access but NOT search visibility — `private` contexts never appear in another DID's search results, even when that DID is in `audience`. To make a context discoverable to a defined cohort, producers MUST use `restricted` instead. **Contributors are NOT auto-authorized for either retrieval or search:** `contributors` is for attribution, not authorization. Producers wishing to grant a contributor read access MUST list the DID in `audience` explicitly (still retrieval-only for `private`; both retrieval and search for `restricted`).

A registry MUST NOT include restricted contexts in `total_estimate` for non-audience requesters, and MUST NOT include private contexts in `total_estimate` for any requester other than the producer. Registries SHOULD make `total_estimate` deterministic per `(query, requester)` for a stable result set, OR omit it from responses entirely when visibility scoping is in play, to avoid leaking the existence of restricted contexts via timing or cross-requester variance analysis.

**`total_estimate` is whole-result-set, not per-page (NORMATIVE).** When present, `total_estimate` MUST represent the total number of matching contexts visible to the requester across **all** pages of the paginated sequence — NOT the number of results remaining from the current cursor position. Its value MUST NOT decrease as the consumer advances through pages. (Because the count is an estimate over a possibly-changing index, it MAY drift slightly between pages within a single sequence; what is forbidden is the systematic "remaining count" interpretation, which would make page 1 report a larger number than page 2 by construction.) A registry that cannot produce a stable whole-set estimate SHOULD omit `total_estimate` rather than emit a per-page remaining count.

---

## 4. Errors

| Cause | Code | HTTP |
|---|---|---|
| Filter value malformed | `schema_violation` | 400 |
| Per-agent rate limit hit | `rate_limited` | 429 |

---

## 5. Security Considerations

See [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md). Specific to discovery:

- Registries MUST scope keyword search results by the requesting agent's effective audience (RFC-ACDP-0008 §4.5).
- `total_estimate` is informational and SHOULD NOT be relied upon for exact counts.
- Cross-registry discovery is out of scope for v0.1.0; consumers wishing to search across registries MUST query each registry separately.

---

## 6. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
- [RFC-ACDP-0009 Extensions](RFC-ACDP-0009-extensions.md)
