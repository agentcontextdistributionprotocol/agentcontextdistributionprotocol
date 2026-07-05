# RFC-ACDP-0004
# Agent Context Distribution Protocol (ACDP) — Retrieval & Lineage

**Document:** RFC-ACDP-0004
**Version:** 0.3.0
**Status:** Community Standards Track (Final)

This RFC specifies how consumers retrieve contexts and lineages from ACDP registries, and how registries derive `status`. It depends on RFC-ACDP-0001 (Core) and RFC-ACDP-0002 (Context Body).

---

## 1. Status of This Memo

This document is a Final ACDP specification (acdp/0.1.0, with Final amendments through acdp/0.3.0). It is stable for the released lines; subsequent breaking changes require a new RFC and a version bump per [VERSIONING.md](../VERSIONING.md).

Passages marked *(0.2.0)* or *(0.3.0)* record the release line that added them (acdp/0.2.0 Trust & Hardening; the acdp/0.3.0 program). Both lines are **Final** as of 2026-07-05, promoted after their conformance packs passed against two independent interoperating implementations (see [CHANGELOG.md](../CHANGELOG.md)). No amendment changes any v0.1.0 body field, hash, or signature semantic.

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

***(0.2.0)* `registry_receipt` member.** The full-retrieval envelope formally gains the OPTIONAL top-level `registry_receipt` member — outside `body` and `registry_state`, in the position reserved since v0.1.0 (RFC-ACDP-0009 §2.7):

```json
{
  "body": { ... },
  "registry_state": { "status": "active" },
  "registry_receipt": { ... }
}
```

A registry advertising the `acdp-registry-receipts` profile MUST include it; other registries MUST NOT emit it (RFC-ACDP-0010 §7). The receipt is never part of the body and never an input to `content_hash`. Receipt-aware consumers verify it per RFC-ACDP-0010 §8 and report its verdict separately from the body verdict; v0.1.0 consumers preserve it verbatim without parsing it (RFC-ACDP-0009 §2.7).

The `{ctx_id}` path parameter is the URL-encoded `acdp://...` URI. Implementations MAY also accept a path-style alternate (`/contexts/<authority>/<uuid>`) for ergonomics; if both forms are supported, they MUST resolve to the same context.

### 2.2 Body-only retrieval

```
GET /contexts/{ctx_id}/body
```

Returns only the body — useful for consumers wishing to verify the signed artifact without registry state. The body alone conforms to [`schemas/json/acdp-context-body.schema.json`](../schemas/json/acdp-context-body.schema.json).

Error responses, visibility rules, path-encoding, and cache-header obligations are identical to §2.1 (full retrieval) except that the response body is the bare context body (no `registry_state` envelope). The body-only endpoint is the recommended cache-friendly retrieval form because it is not affected by `status` mutability (RFC-ACDP-0004 §6.3). *(0.2.0)* The body-only endpoint stays **receipt-free** — `registry_receipt` is never attached here, even by receipts-profile registries — so its immutable-cache story is unchanged (RFC-ACDP-0010 §7).

### 2.3 Visibility-aware response

When the requesting agent is not in the context's effective audience:

- For `visibility: public` — return as normal (HTTP 200).
- For `visibility: restricted` and the requester's DID is not in `audience` — return `not_found` (HTTP 404). Registries MUST NOT distinguish "not found" from "not authorized" externally. The internal label `visibility_denied` MAY be used in registry logs but MUST NOT appear on the wire (RFC-ACDP-0008 §4.5).
- For `visibility: private` and the requester is not `body.agent_id` and not explicitly listed in `audience` (if present) — return `not_found` (HTTP 404). Contributors are NOT auto-authorized; `contributors` is for attribution only (RFC-ACDP-0008 §4.5, RFC-ACDP-0003 §2.1 step 11).

The HTTP status code is the same in both "really doesn't exist" and "exists but you can't see it"; the difference is internal logging only.

---

## 3. Registry State

In v0.1.0, the registry state contains a single field:

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | string | Yes | One of `active`, `superseded`, `expired` — *(0.3.0)* plus `retracted` on lifecycle-advertising registries. See §4. |
| `lifecycle_events` *(0.3.0)* | array | No | Append-only lifecycle event history (RFC-ACDP-0013 §4). Emitted only by registries advertising `acdp-registry-lifecycle`; omitted entirely (never `[]`) when empty. |

The canonical schema is [`schemas/json/acdp-registry-state.schema.json`](../schemas/json/acdp-registry-state.schema.json). Future versions of ACDP will add fields. Consumers MUST tolerate unknown fields in registry state to remain forward-compatible.

---

## 4. Status

The `status` field is **derived** by the registry from supersession queries and the clock:

| Value | Derivation |
|---|---|
| `active` | No other context exists with `supersedes` equal to this context's `ctx_id`; if `expires_at` is set, the current time is at or before `expires_at`. |
| `superseded` | At least one other context exists with `supersedes` equal to this context's `ctx_id`. |
| `expired` | `expires_at` is set and the current time is after `expires_at`. |
| `retracted` *(0.3.0)* | The context's retraction state is *retracted* per its `lifecycle_events` (RFC-ACDP-0013 §7.1). Only on registries advertising `acdp-registry-lifecycle`. |

When both `superseded` and `expired` could apply, `status` is `superseded` (supersession dominates expiration). *(0.3.0)* When retraction also applies, `retracted` dominates both — the full precedence is `retracted` > `superseded` > `expired` > `active` (RFC-ACDP-0013 §7.2); the dominated facts remain independently visible (supersession via the lineage array and the successor's `supersedes`; expiry via the body's signed `expires_at`).

The registry computes `status` from supersession queries against its own data and from the current clock. `status` is **registry-attested**: a consumer cannot independently verify `status` without trusting the registry's supersession index. Consumers wanting independent confirmation MAY query the registry for any context with `supersedes` equal to this context's `ctx_id`; absence (returned over the wire) still relies on registry honesty. See RFC-ACDP-0008 §9.1.

Because `status` is derived, it MUST NOT be persisted into the body. The body's `content_hash` is computed without `status`.

### 4.1 Forward compatibility

Future ACDP versions will add new `status` values — *(0.3.0)* the first, `retracted`, reserved here since v0.1.0 via RFC-ACDP-0009 §2.1, is now **activated** by RFC-ACDP-0013 §7 for registries advertising `acdp-registry-lifecycle`. v0.1.0 consumers MUST NOT fail on unknown `status` values. If a registry returns a `status` value not listed in the table above, consumers SHOULD treat it as `active` for functional decision-making and SHOULD log a warning for operator review. v0.1.0 schemas use an open string pattern for `status` (`^[a-z][a-z0-9_]*$`) to enable this forward compatibility (RFC-ACDP-0001 §6).

**Pattern constraint (NORMATIVE).** Unknown `status` values MUST match the pattern `^[a-z][a-z0-9_]*$` and MUST be 1–64 characters long (lowercase ASCII letters and digits and underscore, starting with a letter). This is the same constraint enforced by `acdp-common.schema.json#/$defs/status`. Consumers MUST reject `status` values that do not match this pattern as malformed registry state — the response is structurally non-conformant and indicates either a registry bug or a man-in-the-middle. A valid-but-unrecognized status (matching the pattern) MUST be tolerated and SHOULD be treated as `active` for functional decisions until the consumer upgrades to a version that defines the new status. This is exactly how `retracted` (reserved by RFC-ACDP-0009 §2.1, activated by RFC-ACDP-0013 in 0.3.0) shipped without breaking v0.1.0 consumers, and how future values like `archived` can, while still rejecting outright-malformed values like `"ACTIVE"`, `"in progress"`, or `""`. The documented consequence is accepted honestly: a pre-0.3.0 consumer treats `retracted` as `active` for functional decisions until it upgrades — the registry-side protections of RFC-ACDP-0013 §8 (default search exclusion, `/current` head exclusion) bound the exposure meanwhile. The conformance fixtures `status-001..004` pin representative cases.

**Library implementation requirement.** Library authors MUST implement `status` as an open string type (or an open enum that gracefully accepts unknown values) — NOT as a closed enum. A closed-enum implementation will deserialize-fail when a registry returns a future status value, breaking every consumer that depends on the library. Concretely:

- **Rust (serde):** model as `String` or use `#[serde(other)]` on a catch-all variant; do **not** use `#[serde(deny_unknown_fields)]`-style closed enums for this field.
- **Python (pydantic v2):** type as `str` (with optional Literal-aliased helpers) or set `model_config = {"extra": "allow"}` on the registry-state model; do not type the wire field as a closed `Literal["active","superseded","expired"]`.
- **TypeScript:** type as `"active" | "superseded" | "expired" | (string & {})` or simply `string`; runtime decoders (zod, valibot) MUST accept unknown values.

This is the same forward-compat policy applied to capabilities-document fields (RFC-ACDP-0007 §3.3) and registry-state extensions (RFC-ACDP-0001 §6).

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

Returns the current non-superseded version of a lineage. The current version is the version `v` in the lineage such that no other version in the lineage has `supersedes = v.ctx_id`.

**Current semantics (NORMATIVE).**

- `GET /lineages/{lineage_id}/current` returns the newest version that has **not been superseded** by another version in the same lineage.
- A version with `status: expired` (i.e. `expires_at` has passed but no successor has been published) **IS a valid current head** — being expired does not make a version superseded. The response MUST carry `registry_state.status: expired` so the consumer knows the context is past its intended validity window. Consumers MUST NOT assume `current` implies `active`.
- A version with `status: superseded` is **NEVER** the current head; it has been explicitly replaced. A registry MUST NOT return a superseded version from this endpoint as a fallback.
- If **every** version in the lineage is `status: superseded` — an abnormal registry state reachable only through admin correction or data corruption — the endpoint MUST return `not_found` (HTTP 404). Registries SHOULD prevent this state via the supersession constraints of RFC-ACDP-0003 §3.1 (every supersession adds exactly one new non-superseded head).
- Visibility filtering applies: see §5.4. If the current head exists but the requester is not authorized to retrieve it, the endpoint MUST behave as specified in §5.4 (return the newest authorized non-superseded version, or `not_found`).

In short: **current = newest non-superseded version; `expired` counts as non-superseded, `superseded` never does.** This endpoint is exercised by the `ret-002` conformance fixture (all-superseded, expired-head, and active-head scenarios). *(0.3.0)* On registries advertising the `acdp-registry-head-receipts` profile, this endpoint's response additionally carries the registry-signed `lineage_head_receipt` member attesting the served head as of response time (RFC-ACDP-0011). *(0.3.0)* On registries advertising `acdp-registry-lifecycle`, a **retracted** version is likewise never the current head: the head is the newest version that is neither superseded nor retracted, else `not_found` — see RFC-ACDP-0013 §8.3 and fixture `lc-003` (an expired head remains servable; a retracted one never is).

### 5.3 Lineage scoping

`GET /lineages/{lineage_id}` is scoped to the registry serving the request — it returns only versions persisted on that registry. Because cross-registry supersession is forbidden in v0.1.0 (RFC-ACDP-0003 §3.1 step 2), every v0.1.0 lineage is wholly contained within one registry; per-registry scoping returns the complete lineage. Cross-registry lineage observability is reserved for RFC-ACDP-0009 §2.8.

### 5.4 Lineage endpoint visibility (NORMATIVE)

Each context version in a lineage carries its own `visibility` and `audience` (RFC-ACDP-0002 §7); versions in the same lineage MAY differ (a producer can narrow the audience in a successor — §7.1). Both lineage endpoints MUST therefore apply the **same per-context visibility rules as `GET /contexts/{ctx_id}`** (§2.3) to **every** version they would otherwise return. Knowing a `lineage_id` MUST NOT grant access to bodies that `ctx_id`-level access control would deny.

- **`GET /lineages/{lineage_id}`** MUST return only the versions the requester is authorized to retrieve. Any version that would return `not_found` via `GET /contexts/{ctx_id}` (a `restricted` or `private` context the requester is not in the effective audience for — §2.3) MUST be omitted from the array. The result is the visible subsequence ordered by `version` ascending; omitted versions leave gaps in the `version` sequence, and that is expected — consumers MUST NOT treat a gap as an error. If the lineage exists but the requester is authorized to see zero versions, the response MUST be an empty array `[]` (HTTP 200), not `not_found` — *except* that a registry which does not advertise `anonymous_public_reads` MUST still reject an unauthenticated requester with `not_authorized` (HTTP 403) per RFC-ACDP-0008 §6.3, the same as any other endpoint.

- **`GET /lineages/{lineage_id}/current`** MUST return the newest non-superseded version (per §5.2) **that the requester is authorized to retrieve**. If the true current head is not visible to the requester, the registry MUST NOT fall back to an older version the requester also cannot see; it returns the newest non-superseded version the requester *is* authorized to retrieve, or `not_found` (HTTP 404) if no such version exists. A registry MUST NOT distinguish "lineage does not exist" from "lineage exists but you may see none of it" on this endpoint — both return `not_found`.

Rationale: lineage endpoints are a convenience projection over per-context retrieval. They MUST NOT widen the effective audience of any context. This is the same existence-leak-prevention principle as §2.3 and RFC-ACDP-0008 §4.5. The `vis-008` conformance fixture pins these behaviors.

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

***(0.2.0)* Receipt caching.** The receipt is **immutable once minted** (RFC-ACDP-0010 §4) and is therefore as cacheable as the body itself. On the full-retrieval response, the mutable `registry_state` still bounds the envelope's cache lifetime (the short `max-age` above); within that envelope, consumers MAY cache the receipt alongside the body indefinitely and SHOULD persist it as durable evidence (RFC-ACDP-0010 §15). A registry MUST serve a byte-identical receipt (after JCS canonicalization) for the same `ctx_id` on every response; the only sanctioned re-mint is the post-compromise case of RFC-ACDP-0010 §9.

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
- [RFC-ACDP-0010 Registry Receipts](RFC-ACDP-0010-registry-receipts.md) *(0.2.0)*
- [RFC-ACDP-0011 Lineage-Head Receipts](RFC-ACDP-0011-lineage-head-receipts.md) *(0.3.0)*
- [RFC-ACDP-0013 Lifecycle Events & Retraction](RFC-ACDP-0013-lifecycle-events.md) *(0.3.0)* — `lifecycle_events`, the `retracted` status, and the amended §4/§5.2 semantics.
