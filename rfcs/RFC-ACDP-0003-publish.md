# RFC-ACDP-0003
# Agent Context Description Protocol (ACDP) — Publish & Supersession

**Document:** RFC-ACDP-0003
**Version:** 0.0.1-draft
**Status:** Community Standards Track (Draft)

This RFC specifies how producers publish contexts to ACDP registries and how registries handle supersession. It depends on RFC-ACDP-0001 (Core) and RFC-ACDP-0002 (Context Body).

---

## 1. Status of This Memo

Draft. Backward-incompatible changes remain possible until Final.

---

## 2. Publishing a Context

```
POST /contexts
Content-Type: application/acdp+json
```

The request body conforms to [`schemas/json/acdp-publish-request.schema.json`](../schemas/json/acdp-publish-request.schema.json). It contains the producer-supplied portion of the context body — all fields except those assigned by the registry (`ctx_id`, `origin_registry`, `created_at`). The producer MUST include `content_hash` and `signature`. The producer MAY include `lineage_id` for self-verification.

### 2.1 Registry processing

The registry MUST execute the following steps in order:

1. **Schema validation.** Validate the request body against `acdp-publish-request.schema.json`. On failure, return `schema_violation` (HTTP 400).
2. **Payload-size validation.** Verify total request size ≤ `limits.max_payload_bytes` (RFC-ACDP-0007). On overflow, return `payload_too_large` (HTTP 413).
3. **Embedded-size validation.** For each `data_refs[].embedded`, verify decoded size ≤ 65536 bytes. On overflow, return `embedded_too_large` (HTTP 413).
4. **Hash recomputation.** Compute SHA-256 over the JCS-canonicalized request body, with the exclusion set from RFC-ACDP-0001 §5.7. If the computed hash does not equal `content_hash`, return `hash_mismatch` (HTTP 400). **This step happens before signature verification:** verifying a signature against an untrusted submitted hash proves nothing — the registry must independently recompute the hash before treating it as the signing input.
5. **Algorithm check.** If `signature.algorithm` is not in the registry's `supported_signature_algorithms` (RFC-ACDP-0007), return `unsupported_algorithm` (HTTP 400).
6. **Key resolution and key-id binding.** Resolve the signing key via `signature.key_id` (a DID URL). Verify that the DID portion of `signature.key_id` (everything before `#`) equals `body.agent_id`. On unresolvable key, return `key_resolution_failed` (HTTP 400). On `key_id`-DID-vs-`agent_id` mismatch, return `key_not_authorized` (HTTP 403). (See RFC-ACDP-0008 for normative DID-method support.)
7. **Signature verification.** Verify `signature.value` against the bytes of the `content_hash` string using the resolved key. On failure, return `invalid_signature` (HTTP 400).
8. **Embedding-model check.** If `embedding` is present, verify `embedding_model` is in the registry's `supported_embedding_models` (RFC-ACDP-0007). On failure, return `unsupported_embedding_model` (HTTP 400).
9. **Identifier assignment.** Assign:
   - `ctx_id = acdp://<own_authority>/<freshly_generated_uuidv4>`
   - `origin_registry = <own_authority>`
   - `created_at = <current_time_in_canonical_rfc3339>`
10. **Lineage computation.** Per RFC-ACDP-0001 §5.6:
    - For first versions (`supersedes = null`), `lineage_id = "lin:" + lowercase_hex(SHA-256(ctx_id))`.
    - For subsequent versions, walk back through `supersedes` to find the version-1 `ctx_id` and apply the same formula.
    - If the producer supplied `lineage_id`, verify it matches the computed value; on mismatch, return `superseded_target` (HTTP 400).
11. **Supersession validation.** If `supersedes` is non-null, validate per §3 below.
12. **Visibility validation.** If `visibility = "restricted"`, verify `audience` is a non-empty array of DIDs. If `visibility = "private"`, the registry MUST treat **only `agent_id`** plus any DIDs explicitly listed in `audience` (if present) as authorized; **`contributors` are NOT auto-authorized** — `contributors` is for attribution, not authorization (see RFC-ACDP-0008 §6.4).
13. **Persistence.** Persist the body. Initialize the derived `status` per RFC-ACDP-0004 §4.
14. **Response.** Return a publish response (§4).

The registry MUST execute steps 1–8 before any persistence. Steps 9–13 are atomic with respect to other concurrent publications: two publications targeting the same `supersedes` value are racing — the registry MUST either accept exactly one, or accept the first and return `superseded_target` for the second.

### 2.2 Producer-side flow

Producers building a publish request MUST:

1. Construct the publish request without `ctx_id`, `lineage_id`, `origin_registry`, `created_at`, `content_hash`, `signature`.
2. Compute `content_hash` over the JCS-canonicalized publish-request body, with the full exclusion set from RFC-ACDP-0001 §5.7: `content_hash`, `signature`, `ctx_id`, `lineage_id`, `origin_registry`, `created_at`. At this stage, the body has neither `content_hash` nor `signature` set; both are added in steps 3–4 below. The resulting `content_hash` value is the literal string `sha256:` followed by 64 lowercase hex characters.
3. Sign the bytes of the **full `content_hash` string** — the ASCII bytes of `sha256:` followed by the 64 lowercase hex characters — with the producer's signing key, per RFC-ACDP-0001 §5.8. Producers MUST NOT sign the raw 32-byte hash digest, and MUST NOT sign the hex-only substring without the `sha256:` prefix.
4. Set `content_hash` and `signature` and submit the resulting object as the request body.

Producers publishing a first version (`supersedes = null`) **MUST NOT** include `lineage_id` in the publish request. Registries MUST reject first-version requests containing `lineage_id` with `schema_violation` (HTTP 400). The registry derives `lineage_id` from the assigned `ctx_id` (RFC-ACDP-0001 §5.6); producers cannot supply a correct value because they do not know the registry-assigned `ctx_id` at signing time.

Producers publishing a subsequent version (`supersedes != null`) MAY include `lineage_id` for self-verification. If supplied, the registry MUST verify it matches the deterministically-derived value and reject with `superseded_target` (`details.reason = "lineage_mismatch"`) on mismatch.

---

## 3. Supersession

To publish a corrected or updated version of a context, the producer publishes a new context with `supersedes` set to the previous version's `ctx_id`. The registry follows the same flow as §2.1 with the additional supersession validation in step 10.

### 3.1 Supersession constraints

For a publish request with `supersedes = <prev_ctx_id>`, the registry MUST:

1. Resolve `<prev_ctx_id>` and verify the context exists and is retrievable. If not, return `superseded_target` with `details.reason = "not_found"` (HTTP 400).
2. If `<prev_ctx_id>` lives in a different origin registry, the registry MAY reject (`superseded_target` with `details.reason = "cross_registry_supersession_unsupported"`) **OR** it MAY resolve the remote context per RFC-ACDP-0006 and validate against it. Behavior is registry-defined; cross-registry supersession is OPTIONAL in v0.0.1.
3. Verify `agent_id` of the new context matches `agent_id` of the superseded context. If not, return `not_authorized` (HTTP 403). (Delegation is out of scope for v0.0.1.)
4. Verify the computed `lineage_id` of the new context matches the superseded context's `lineage_id`. If not, return `superseded_target` with `details.reason = "lineage_mismatch"` (HTTP 400).
5. Verify `version = previous.version + 1`. If not, return `superseded_target` with `details.reason = "version_mismatch"` (HTTP 400).
6. Verify the new context is the first to supersede `<prev_ctx_id>`. If another context already supersedes it, return `superseded_target` with `details.reason = "already_superseded"` (HTTP 400). This makes lineages strictly linear.

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
Location: /contexts/acdp://<authority>/<uuid>
```

```json
{
  "ctx_id": "acdp://registry.example.com/550e8400-e29b-41d4-a716-446655440000",
  "lineage_id": "lin:b14ccd2a8b34530309255db68c151a10689b6a82feb30aff9222d54fdd871720",
  "version": 1,
  "created_at": "2026-04-16T10:30:15.123Z",
  "status": "active"
}
```

The response MUST conform to [`schemas/json/acdp-publish-response.schema.json`](../schemas/json/acdp-publish-response.schema.json). The HTTP status code MUST be 201 Created on success.

---

## 5. Errors

All errors use the envelope defined in RFC-ACDP-0007 §4 with codes from the registry in RFC-ACDP-0007 §5. Publish-specific behavior is summarized below.

| Cause | Code | HTTP |
|---|---|---|
| Body fails schema validation | `schema_violation` | 400 |
| Signature failed verification | `invalid_signature` | 400 |
| Recomputed hash ≠ `content_hash` | `hash_mismatch` | 400 |
| Algorithm not supported | `unsupported_algorithm` | 400 |
| Embedding model not indexed | `unsupported_embedding_model` | 400 |
| Embedded data > 64 KB | `embedded_too_large` | 413 |
| Payload > registry limit | `payload_too_large` | 413 |
| Supersedes target invalid (any reason) | `superseded_target` | 400 |
| `agent_id` mismatch on supersession | `not_authorized` | 403 |
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

- MUST track `(agent_id, idempotency_key)` pairs for at least 24 hours.
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
- When an agent rotates keys, prior signatures remain valid as long as the old key was valid at the operation's timestamp. Registries MUST preserve historical key validity windows from the agent's DID document.
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
