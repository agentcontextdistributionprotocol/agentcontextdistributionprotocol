# RFC-ACDP-0004
# Agent Context Description Protocol (ACDP) — Retrieval & Lineage

**Document:** RFC-ACDP-0004
**Version:** 0.0.1-draft
**Status:** Community Standards Track (Draft)

This RFC specifies how consumers retrieve contexts and lineages from ACDP registries, and how registries derive `status`. It depends on RFC-ACDP-0001 (Core) and RFC-ACDP-0002 (Context Body).

---

## 1. Status of This Memo

Draft. Backward-incompatible changes remain possible until Final.

---

## 2. Retrieval

### 2.1 Full retrieval

```
GET /contexts/{ctx_id}
```

Returns a JSON object with `body` and `registry_state` keys, conforming to [`schemas/json/acdp-context.schema.json`](../schemas/json/acdp-context.schema.json).

```http
HTTP/1.1 200 OK
Content-Type: application/acdp+json
```

```json
{
  "body": { ... },
  "registry_state": {
    "status": "active"
  }
}
```

The `{ctx_id}` path parameter is the URL-encoded `acdp://...` URI. Implementations MAY also accept a path-style alternate (`/contexts/<authority>/<uuid>`) for ergonomics; if both forms are supported, they MUST resolve to the same context.

### 2.2 Body-only retrieval

```
GET /contexts/{ctx_id}/body
```

Returns only the body — useful for consumers wishing to verify the signed artifact without registry state. The body alone conforms to [`schemas/json/acdp-context-body.schema.json`](../schemas/json/acdp-context-body.schema.json).

### 2.3 Visibility-aware response

When the requesting agent is not in the context's effective audience:

- For `visibility: public` — return as normal (HTTP 200).
- For `visibility: restricted` and the requester's DID is not in `audience` — return `not_found` (HTTP 404). Registries MUST NOT distinguish "not found" from "not authorized" externally; this is the `visibility_denied` semantic in RFC-ACDP-0007.
- For `visibility: private` and the requester is not the producer or a contributor — return `not_found` (HTTP 404).

The HTTP status code is the same in both "really doesn't exist" and "exists but you can't see it"; the difference is internal logging only.

---

## 3. Registry State

In v0.0.1, the registry state contains a single field:

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | string | Yes | One of `active`, `superseded`, `expired`. See §4. |

The canonical schema is [`schemas/json/acdp-registry-state.schema.json`](../schemas/json/acdp-registry-state.schema.json). Future versions of ACDP will add fields. Consumers MUST tolerate unknown fields in registry state to remain forward-compatible.

---

## 4. Status

The `status` field is **derived** by the registry from supersession queries and the clock:

| Value | Derivation |
|---|---|
| `active` | No other context exists with `supersedes` equal to this context's `ctx_id`; if `expires_at` is set, the current time is at or before `expires_at`. |
| `superseded` | At least one other context exists with `supersedes` equal to this context's `ctx_id`. |
| `expired` | `expires_at` is set and the current time is after `expires_at`. |

When both `superseded` and `expired` could apply, `status` is `superseded` (supersession dominates expiration).

The registry computes `status` from supersession queries against its own data and from the current clock. Consumers can verify `status` independently by issuing the same queries and observing the same clock.

Because `status` is derived, it MUST NOT be persisted into the body. The body's `content_hash` is computed without `status`.

---

## 5. Lineage Queries

### 5.1 Full lineage

```
GET /lineages/{lineage_id}
```

Returns the full version history of a lineage as a JSON array of full retrieval responses (each with `body` + `registry_state`), ordered by `version` ascending.

```http
HTTP/1.1 200 OK
Content-Type: application/acdp+json
```

```json
[
  { "body": { "version": 1, "ctx_id": "...", ... }, "registry_state": { "status": "superseded" } },
  { "body": { "version": 2, "ctx_id": "...", ... }, "registry_state": { "status": "active" } }
]
```

### 5.2 Current version

```
GET /lineages/{lineage_id}/current
```

Returns the current non-superseded version of a lineage. If no such version exists (every version superseded — unusual), returns `not_found` (HTTP 404).

The current version is the unique version `v` in the lineage such that no other version in the lineage has `supersedes = v.ctx_id`.

### 5.3 Lineage scoping

`GET /lineages/{lineage_id}` is scoped to the registry serving the request — it returns only versions persisted on that registry. A lineage that crosses registries (a producer published v1 on one registry and v2 on another) is uncommon and not specifically supported; consumers walking such lineages MUST follow `supersedes` references manually.

---

## 6. Caching

Bodies are immutable. Registries SHOULD set strong cache headers on body responses:

```
Cache-Control: public, max-age=31536000, immutable
ETag: "<content_hash>"
```

Registry state changes (status transitions); registries SHOULD use a shorter `Cache-Control` on full retrieval responses, or a separate caching policy that key on `status`. The body-only endpoint (§2.2) is the recommended cache-friendly retrieval form.

---

## 7. Errors

| Cause | Code | HTTP |
|---|---|---|
| `ctx_id` does not exist | `not_found` | 404 |
| Visibility-restricted, requester not in audience | `not_found` | 404 |
| Path malformed (e.g. invalid `ctx_id` syntax) | `schema_violation` | 400 |
| Per-agent rate limit hit | `rate_limited` | 429 |

---

## 8. Security Considerations

See [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md). Specific to retrieval:

- Consumers MUST verify the body's signature on every retrieval. Trusting the registry alone is **not** sufficient — the registry could serve a tampered body.
- Visibility enforcement is the registry's responsibility; consumers cannot independently determine they were served the full result set, only that what they received is authentic.
- Embeddings can leak information about restricted contexts. Registries MUST scope similarity search by visibility (RFC-ACDP-0005 §4).

---

## 9. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md)
- [RFC-ACDP-0003 Publish](RFC-ACDP-0003-publish.md)
- [RFC-ACDP-0006 Cross-Registry References](RFC-ACDP-0006-cross-registry.md)
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
