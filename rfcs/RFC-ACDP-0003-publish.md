# RFC-ACDP-0003
# Agent Context Description Protocol (ACDP) — Publish & Supersession

**Document:** RFC-ACDP-0003
**Version:** 0.0.1
**Status:** Community Standards Track (Draft)

This RFC specifies how producers publish contexts to ACDP registries and how registries handle supersession. It depends on RFC-ACDP-0001 (Core) and RFC-ACDP-0002 (Context Body).

---

## 1. Status of This Memo

This document is a Draft. Backward-incompatible changes remain possible until Final.

---

## 2. Publishing a Context

```
POST /contexts
Content-Type: application/acdp+json
```

The request body conforms to [`schemas/json/acdp-publish-request.schema.json`](../schemas/json/acdp-publish-request.schema.json). It contains the producer-supplied portion of the context body — all fields except those assigned by the registry (`ctx_id`, `origin_registry`, `created_at`). The producer MUST include `content_hash` and `signature`. The producer MAY include `lineage_id` for self-verification.

> **Implementer note: schema-valid ≠ publish-valid.** Passing `acdp-publish-request.schema.json` validation is necessary but NOT sufficient for a publish to succeed. The schema enforces structural validity only. Cryptographic correctness (`hash_mismatch`, `invalid_signature`), key resolution (`key_resolution_failed`, `key_not_authorized`), supersession races (`superseded_target` with `version_mismatch` / `already_superseded`), unsupported algorithms or DID methods, and rate limits are all checked at runtime by the registry per §2.1. A schema-valid request MAY still be rejected with any of these codes.

### 2.1 Registry processing

The registry MUST execute the following steps in order:

1. **Schema validation.** Validate the request body against `acdp-publish-request.schema.json`. On failure, return `schema_violation` (HTTP 400).
2. **Payload-size validation.** Verify total request size ≤ `limits.max_payload_bytes` (RFC-ACDP-0007). On overflow, return `payload_too_large` (HTTP 413).
3. **Embedded validation.** For each `data_refs[].embedded`:
    - Verify decoded size ≤ 65536 bytes (per RFC-ACDP-0002 §6.3 decoding rules: `base64` → RFC 4648 decoded byte count; `utf8` → UTF-8 byte count; `json` → JCS-canonicalized byte count). On overflow, return `embedded_too_large` (HTTP 413).
    - If `embedded.content_hash` is present, recompute the SHA-256 of the decoded bytes (same encoding-aware decoding) and verify it matches. On mismatch, return `hash_mismatch` (HTTP 400). This is distinct from the body-level `content_hash` check in step 4: step 3's hash-check binds an individual embedded payload to its declared digest; step 4 binds the whole producer-controlled body. Per-embedded `content_hash` is OPTIONAL on publish (the producer commits to whatever `embedded.content` they sign in step 4 either way), but present-and-mismatching is a hard error per RFC-ACDP-0002 §6.6 Check 8.
4. **Hash recomputation.** Compute SHA-256 over the JCS-canonicalized request body, with the exclusion set from RFC-ACDP-0001 §5.7. If the computed hash does not equal `content_hash`, return `hash_mismatch` (HTTP 400). **This step happens before signature verification:** verifying a signature against an untrusted submitted hash proves nothing — the registry must independently recompute the hash before treating it as the signing input.
5. **Algorithm check.** If `signature.algorithm` is not in the registry's `supported_signature_algorithms` (RFC-ACDP-0007), return `unsupported_algorithm` (HTTP 400).
6. **Key-id binding and key resolution.** First, verify that the DID portion of `signature.key_id` (everything before `#`) equals `body.agent_id`; on mismatch, return `key_not_authorized` (HTTP 403). This sub-check is a string comparison and registries MAY perform it earlier (before step 4) as an optimization to reject obvious mismatches without paying the SHA-256 cost. Then resolve the signing key per RFC-ACDP-0001 §5.11. On a permanent resolution failure (DID document fetched but JSON parse error, missing the requested key fragment in `verificationMethod`, or `key_id` lacks a fragment), return `key_resolution_failed` (HTTP 400). On a transient failure (DNS, TLS, HTTP non-2xx, timeout fetching the DID document), return `key_resolution_unreachable` (HTTP 502). On successful resolution, verify the resolved verification method is in the DID document's `assertionMethod` array; if not, return `key_not_authorized` (HTTP 403).
7. **Signature verification.** Verify `signature.value` against the bytes of the `content_hash` string using the resolved key. On failure, return `invalid_signature` (HTTP 400).
8. **Identifier assignment.** Assign:
   - `ctx_id = acdp://<own_authority>/<freshly_generated_uuidv4>`
   - `origin_registry = <own_authority>`
   - `created_at = <current_time_in_canonical_rfc3339>`
9. **Lineage computation.** Per RFC-ACDP-0001 §5.6:
    - For first versions (`supersedes = null`), `lineage_id = "lin:sha256:" + lowercase_hex(SHA-256(ctx_id))`.
    - For subsequent versions, walk back through `supersedes` to find the version-1 `ctx_id` and apply the same formula.
    - If the producer supplied `lineage_id`, verify it matches the computed value; on mismatch, return `superseded_target` (HTTP 400).
10. **Supersession validation.** If `supersedes` is non-null, validate per §3 below.
11. **Visibility validation.** If `visibility = "restricted"`, verify `audience` is a non-empty array of DIDs. If `visibility = "private"`, the registry MUST treat **only `agent_id`** plus any DIDs explicitly listed in `audience` (if present) as authorized; **`contributors` are NOT auto-authorized** — `contributors` is for attribution, not authorization (see RFC-ACDP-0008 §4.5).
12. **Persistence.** Persist the body. Initialize the derived `status` per RFC-ACDP-0004 §4.
13. **Response.** Return a publish response (§4).

The registry MUST execute steps 1–7 before any persistence. Steps 8–12 are atomic with respect to other concurrent publications: when two publications target the same `supersedes` value, the registry MUST accept exactly one (the first to fully validate and reach step 12 (persistence)), and MUST reject every subsequent attempt with `superseded_target` (`details.reason = "already_superseded"`, HTTP 409 Conflict).

### 2.2 Producer-side flow

Producers building a publish request MUST:

1. Construct the publish request without `ctx_id`, `lineage_id`, `origin_registry`, `created_at`, `content_hash`, `signature`.
2. Compute `content_hash` over the JCS-canonicalized **ProducerContent** (RFC-ACDP-0001 §2) — the publish-request body with the full §5.7 exclusion set removed: `content_hash`, `signature`, `ctx_id`, `lineage_id`, `origin_registry`, `created_at`. At this stage, the body has neither `content_hash` nor `signature` set; both are added in steps 3–4 below. The resulting `content_hash` value is the literal string `sha256:` followed by 64 lowercase hex characters.
3. Sign the bytes of the **full `content_hash` string** — the ASCII bytes of `sha256:` followed by the 64 lowercase hex characters — with the producer's signing key, per RFC-ACDP-0001 §5.8. Producers MUST NOT sign the raw 32-byte hash digest, and MUST NOT sign the hex-only substring without the `sha256:` prefix.
4. Set `content_hash` and `signature` and submit the resulting object as the request body.

Producers publishing a first version (`supersedes = null`) **MUST NOT** include `lineage_id` in the publish request. Registries MUST reject first-version requests containing `lineage_id` with `schema_violation` (HTTP 400). The registry derives `lineage_id` from the assigned `ctx_id` (RFC-ACDP-0001 §5.6); producers cannot supply a correct value because they do not know the registry-assigned `ctx_id` at signing time.

Producers publishing a subsequent version (`supersedes != null`) MAY include `lineage_id` for self-verification. If supplied, the registry MUST verify it matches the deterministically-derived value and reject with `superseded_target` (`details.reason = "lineage_mismatch"`) on mismatch.

> **Note on the optional `lineage_id` in supersession publish requests.** The optional `lineage_id` here is a **producer assertion for self-verification**, NOT a registry assignment. Its purpose is to let the producer catch lineage-continuity errors at publish time: if the producer's understanding of the lineage does not match the value the registry computes from walking the `supersedes` chain, the registry returns `superseded_target` (`details.reason = "lineage_mismatch"`) and the producer can investigate before retrying. Producers that omit `lineage_id` on supersession are **not** in error — the registry derives and verifies `lineage_id` unconditionally from the `supersedes` chain regardless. This is a defensive correctness check, not a required part of the publish surface. (A future ACDP version may rename this field to `expected_lineage_id` to make the producer-assertion semantics unmissable; v0.0.1 keeps the original name to remain compatible with existing producer libraries.)

---

## 3. Supersession

To publish a corrected or updated version of a context, the producer publishes a new context with `supersedes` set to the previous version's `ctx_id`. The registry follows the same flow as §2.1 with the additional supersession validation in step 10.

### 3.1 Supersession constraints

For a publish request with `supersedes = <prev_ctx_id>`, the registry MUST:

1. Resolve `<prev_ctx_id>` and verify the context exists and is retrievable. If not, return `superseded_target` with `details.reason = "not_found"` (HTTP 400).
2. If `<prev_ctx_id>` lives in a different origin registry, the registry MUST reject the publish request with `superseded_target` (`details.reason = "cross_registry_supersession_unsupported"`, HTTP 400). **Cross-registry supersession is out of scope for v0.0.1**: the verification semantics (remote identity authentication, lineage continuity over the network, race protection across registries, recovery on partial failure) require additional protocol machinery not yet specified. A producer migrating a logical lineage between registries MUST start a new lineage on the target registry (with `supersedes: null`) and reference the prior lineage via `derived_from`. The reservation for a future cross-registry supersession protocol is in [RFC-ACDP-0009 §2.8](RFC-ACDP-0009-extensions.md).
3. Verify `agent_id` of the new context matches `agent_id` of the superseded context. If not, return `not_authorized` (HTTP 403). (Delegation is out of scope for v0.0.1.)
4. Verify the computed `lineage_id` of the new context matches the superseded context's `lineage_id`. If not, return `superseded_target` with `details.reason = "lineage_mismatch"` (HTTP 400).
5. Verify `version = previous.version + 1`. If not, return `superseded_target` with `details.reason = "version_mismatch"` (HTTP 409 Conflict — race condition between two producers attempting to supersede the same version).
6. Verify the new context is the first to supersede `<prev_ctx_id>`. If another context already supersedes it, return `superseded_target` with `details.reason = "already_superseded"` (HTTP 409 Conflict — race condition). This makes lineages strictly linear.

### 3.2 Effect on prior version

The previous version's body is unchanged. The previous version's derived `status` becomes `superseded` (RFC-ACDP-0004 §4) — automatically, on the next status query. Registries MAY cache `status` but MUST recompute on supersession events.

### 3.3 No retraction

This version of ACDP does not provide a retraction mechanism. Once a context is published, its body is permanent. A producer that discovers an error has two options:

1. **Publish a corrected superseding version.** The original v1 will have `status: superseded`. Consumers walking forward via `lineage_id` will find the correction.
2. **Publish a context describing the issue,** with the buggy context in `derived_from` and a `description` explaining the problem. This is a soft signal.

In neither case does the original context disappear. A formal retraction mechanism is reserved in RFC-ACDP-0009.

---

## 4. Publish Response

On success, the registry returns:

```http
HTTP/1.1 201 Created
Content-Type: application/acdp+json
Location: /contexts/acdp%3A%2F%2Fregistry.example.com%2F550e8400-e29b-41d4-a716-446655440000
```

```json
{
  "ctx_id": "acdp://registry.example.com/550e8400-e29b-41d4-a716-446655440000",
  "lineage_id": "lin:sha256:b14ccd2a8b34530309255db68c151a10689b6a82feb30aff9222d54fdd871720",
  "version": 1,
  "created_at": "2026-04-16T10:30:15.123Z",
  "status": "active"
}
```

The `Location` header value is the canonical retrieval URL for the new context. The `ctx_id` in the URL path MUST be percent-encoded: `:` → `%3A`, `/` → `%2F`. This is the form clients pass to `GET /contexts/{ctx_id}` (RFC-ACDP-0004 §2). Implementations MUST emit the percent-encoded form in `Location` and MUST accept either form on `GET` retrieval (some clients percent-decode before re-sending). A `Location` header containing literal `://` and unencoded `/` inside a path segment will not parse correctly in many HTTP clients and proxies.

The response body MUST conform to [`schemas/json/acdp-publish-response.schema.json`](../schemas/json/acdp-publish-response.schema.json). The HTTP status code MUST be 201 Created on success.

The publish response object has exactly the following fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `ctx_id` | string | Yes | Registry-assigned context identifier in the form `acdp://<authority>/<uuid>` (RFC-ACDP-0001 §5.5). |
| `lineage_id` | string | Yes | Computed lineage identifier (RFC-ACDP-0001 §5.6). |
| `version` | integer | Yes | Version number of the newly published context (1 for first version, `previous.version + 1` otherwise). |
| `created_at` | string | Yes | Registry-assigned creation timestamp (RFC 3339, canonical millisecond form per RFC-ACDP-0001 §5.3). |
| `status` | string | Yes | Initial lifecycle status. MUST be `"active"` (a newly-published context cannot already be `superseded` or `expired`). |

Registries MUST NOT include `content_hash`, `signature`, or any other body field in the publish response. `content_hash` is part of ProducerContent (RFC-ACDP-0001 §2, §5.7); the producer already submitted it and signed it, so echoing it back conveys no integrity guarantee. Consumers that need the full body for verification MUST retrieve it via `GET /contexts/{ctx_id}` (RFC-ACDP-0004 §2) — the body returned there is byte-identical to what the producer signed. The publish response is intentionally minimal: it conveys only the registry-assigned identifiers needed for subsequent retrieval and the initial derived `status`. The response schema is `additionalProperties: false`; consumer deserializers MUST NOT rely on additional fields appearing.

---

## 5. Errors

All errors use the envelope defined in RFC-ACDP-0007 §4 with codes from the registry in RFC-ACDP-0007 §5. Publish-specific behavior is summarized below.

| Cause | Code | HTTP |
|---|---|---|
| Body fails schema validation | `schema_violation` | 400 |
| Signature failed verification | `invalid_signature` | 400 |
| Recomputed hash ≠ `content_hash` | `hash_mismatch` | 400 |
| Algorithm not supported | `unsupported_algorithm` | 400 |
| Key resolution failed (permanent) | `key_resolution_failed` | 400 |
| Key resolution unreachable (transient) | `key_resolution_unreachable` | 502 |
| Signing key DID does not match `agent_id` | `key_not_authorized` | 403 |
| Embedded data > 64 KB | `embedded_too_large` | 413 |
| Payload > registry limit | `payload_too_large` | 413 |
| `supersedes` target not found | `superseded_target` (`reason: not_found`) | 400 |
| `lineage_id` mismatch on supersession | `superseded_target` (`reason: lineage_mismatch`) | 400 |
| Cross-registry supersession | `superseded_target` (`reason: cross_registry_supersession_unsupported`) | 400 |
| `version` not previous + 1 (race) | `superseded_target` (`reason: version_mismatch`) | **409** |
| Target already superseded (race) | `superseded_target` (`reason: already_superseded`) | **409** |
| `agent_id` mismatch on supersession | `not_authorized` | 403 |
| Idempotency key reused with different content | `duplicate_publish` | 409 |
| Per-agent rate limit hit | `rate_limited` | 429 |

---

## 6. Idempotency

Identical publish requests create distinct `ctx_id`s by default. Producers retrying after network errors can inadvertently create duplicate publications. Registries SHOULD support the `Idempotency-Key` HTTP header for safe retries.

### 6.1 Producer behavior

Producers MAY include an `Idempotency-Key` header on `POST /contexts`:

- Value: opaque string, 1–256 ASCII printable characters.
- Producers SHOULD use UUID v4 or similar high-entropy values.
- Producers retrying a failed request SHOULD reuse the same key.

### 6.2 Registry behavior

Registries supporting idempotency:

- MUST track `(agent_id, idempotency_key)` pairs for at least 24 hours and at most 168 hours (7 days). Registries MUST advertise their actual TTL in the capabilities document as `limits.idempotency_key_ttl_seconds` so producers can scope retry windows correctly.
- On a repeated request with the same `(agent_id, idempotency_key)` AND the same `content_hash`: return the original publish response with **HTTP 200 OK** (instead of 201) and the original assigned identifiers (`ctx_id`, `lineage_id`, `version`, `created_at`, `status`).
- On a repeated request with the same `(agent_id, idempotency_key)` BUT a different `content_hash`: return `duplicate_publish` (HTTP 409). The producer is reusing an idempotency key for new content, which is a programming error.

Registries supporting idempotency MUST declare `"supports_idempotency_key": true` in capabilities (RFC-ACDP-0007 §3.2). Registries not supporting it MUST ignore the `Idempotency-Key` header (treat as absent).

### 6.3 Content-deterministic deduplication

Independent of `Idempotency-Key`, the body's `content_hash` is content-deterministic. Producers MAY use it as a local deduplication key (e.g. record `content_hash` after a successful publish; on retry, look up by hash before re-submitting). This is a producer-side optimization and does not require registry cooperation.

---

## 7. Security Considerations

See [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md). Specific to publishing:

- Producers MUST authenticate with DID-based credentials.
- Registries MUST verify all signatures at publish time. Verification failures MUST result in rejection.
- When a producer rotates keys, prior signatures remain mathematically valid (same content + same key still verifies). Verifying that the *signing key was authorized at the time of publication* requires historical key authorization data, which most DID methods do not natively provide. Verifiers SHOULD verify against the producer's current DID document; verifiers requiring stronger historical guarantees MUST consult external mechanisms — see RFC-ACDP-0008 §9.3.
- Per-agent rate-limiting is REQUIRED (RFC-ACDP-0008 §4).
- Producers SHOULD treat every publish as a public commitment; v0.0.1 has no retraction.

---

## 8. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0006 Cross-Registry References](RFC-ACDP-0006-cross-registry.md)
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
