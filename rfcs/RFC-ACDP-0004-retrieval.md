# RFC-ACDP-0004
# Agent Context Description Protocol (ACDP) — Retrieval & Lineage

**Document:** RFC-ACDP-0004
**Version:** 0.0.1
**Status:** Community Standards Track (Draft)

This RFC specifies how consumers retrieve contexts and lineages from ACDP registries, and how registries derive `status`. It depends on RFC-ACDP-0001 (Core) and RFC-ACDP-0002 (Context Body).

---

## 1. Status of This Memo

This document is a Draft. Backward-incompatible changes remain possible until Final.

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

Error responses, visibility rules, path-encoding, and cache-header obligations are identical to §2.1 (full retrieval) except that the response body is the bare context body (no `registry_state` envelope). The body-only endpoint is the recommended cache-friendly retrieval form because it is not affected by `status` mutability (RFC-ACDP-0004 §6.3).

### 2.3 Visibility-aware response

When the requesting agent is not in the context's effective audience:

- For `visibility: public` — return as normal (HTTP 200).
- For `visibility: restricted` and the requester's DID is not in `audience` — return `not_found` (HTTP 404). Registries MUST NOT distinguish "not found" from "not authorized" externally. The internal label `visibility_denied` MAY be used in registry logs but MUST NOT appear on the wire (RFC-ACDP-0008 §4.5).
- For `visibility: private` and the requester is not `body.agent_id` and not explicitly listed in `audience` (if present) — return `not_found` (HTTP 404). Contributors are NOT auto-authorized; `contributors` is for attribution only (RFC-ACDP-0008 §4.5, RFC-ACDP-0003 §2.1 step 11).

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

The registry computes `status` from supersession queries against its own data and from the current clock. `status` is **registry-attested**: a consumer cannot independently verify `status` without trusting the registry's supersession index. Consumers wanting independent confirmation MAY query the registry for any context with `supersedes` equal to this context's `ctx_id`; absence (returned over the wire) still relies on registry honesty. See RFC-ACDP-0008 §9.1.

Because `status` is derived, it MUST NOT be persisted into the body. The body's `content_hash` is computed without `status`.

### 4.1 Forward compatibility

Future ACDP versions will add new `status` values (e.g. `retracted` per RFC-ACDP-0009 §2.1). v0.0.1 consumers receiving an unknown `status` value MUST NOT reject the response — they SHOULD treat the value as `active` for decision-making and log it for operator review. v0.0.1 schemas use an open string pattern for `status` to support this forward-compatibility (RFC-ACDP-0001 §6).

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

`GET /lineages/{lineage_id}` is scoped to the registry serving the request — it returns only versions persisted on that registry. Because cross-registry supersession is forbidden in v0.0.1 (RFC-ACDP-0003 §3.1 step 2), every v0.0.1 lineage is wholly contained within one registry; per-registry scoping returns the complete lineage. Cross-registry lineage observability is reserved for RFC-ACDP-0009 §2.8.

---

## 6. Caching

Bodies are immutable, so they are highly cache-friendly — but cache directives MUST respect visibility. Registries MUST set cache headers based on the body's `visibility`:

### 6.1 Public bodies

For `visibility: public`:

```
Cache-Control: public, max-age=31536000, immutable
ETag: "<content_hash>"
```

These bodies may be cached by shared caches (CDNs, intermediary proxies) indefinitely.

### 6.2 Restricted and private bodies

For `visibility: restricted` and `visibility: private`:

```
Cache-Control: private, no-store
ETag: "<content_hash>"
```

`private` prevents shared caches from storing the response. `no-store` prevents any caching, including by the requesting agent's local cache, on the conservative assumption that visibility membership may change. Registries MAY use `Cache-Control: private, max-age=<short>` (e.g. 60 seconds) instead of `no-store` if their visibility model is stable; this is a registry-policy decision.

Registries MUST NOT serve a `Cache-Control: public` directive on a non-public body under any circumstances. Doing so violates the visibility model and may leak content to unauthorized consumers via shared caches.

### 6.3 Registry state

Registry state (the `registry_state` object containing `status`) is mutable. Registries SHOULD use a short `Cache-Control: max-age` (e.g. 60–300 seconds) on full retrieval responses (`GET /contexts/{ctx_id}`), or use the body-only endpoint (`GET /contexts/{ctx_id}/body`) when long-lived caching is desired.

### 6.4 ETag value

The ETag value is the body's `content_hash` (the full `sha256:<hex>` string), wrapped in quotes per RFC 9110. Example:

```
ETag: "sha256:5f8d88d6758cfd43be875d49edc9eaa494de8ec645bf7de6c592b15bbb1e2e3c"
```

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

---

## 9. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md)
- [RFC-ACDP-0003 Publish](RFC-ACDP-0003-publish.md)
- [RFC-ACDP-0006 Cross-Registry References](RFC-ACDP-0006-cross-registry.md)
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
