# RFC-ACDP-0003
# Agent Context Description Protocol (ACDP) — Publish & Supersession

**Document:** RFC-ACDP-0003
**Version:** 0.1.0-rc1
**Status:** Community Standards Track (Release Candidate 1)

This RFC specifies how producers publish contexts to ACDP registries and how registries handle supersession. It depends on RFC-ACDP-0001 (Core) and RFC-ACDP-0002 (Context Body).

---

## 1. Status of This Memo

This document is a Release Candidate (acdp/0.1.0-rc1). Backward-incompatible changes remain possible until Final; only editorial fixes are expected during the RC window.

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

1. **Schema validation.** Validate the request body against `acdp-publish-request.schema.json`. On failure, return `schema_violation` (HTTP 400). The publish-request schema is closed (`additionalProperties: false`); registries MUST reject requests containing fields not defined in `acdp-publish-request.schema.json`. In particular, registries MUST reject requests that include any registry-assigned field — `ctx_id`, `lineage_id` (when `version = 1`), `origin_registry`, or `created_at` — because these are minted by the registry and cannot be producer-supplied. Libraries using typed deserialization SHOULD enable a `deny_unknown_fields` equivalent at the parse layer (Rust `#[serde(deny_unknown_fields)]`, Python pydantic `extra="forbid"`, zod `.strict()`, Go json with `DisallowUnknownFields`) so that schema violations surface before any of the cryptographic steps below. Conformance fixtures `pub-012`, `pub-013`, and `pub-014` exercise this requirement.
2. **Payload-size validation.** Verify total request size ≤ `limits.max_payload_bytes` (RFC-ACDP-0007). On overflow, return `payload_too_large` (HTTP 413).
3. **Embedded validation.** For each `data_refs[].embedded`:
    - Verify decoded size ≤ 65536 bytes (per RFC-ACDP-0002 §6.3 decoding rules: `base64` → RFC 4648 decoded byte count; `utf8` → UTF-8 byte count; `json` → JCS-canonicalized byte count). On overflow, return `embedded_too_large` (HTTP 413).
    - If `embedded.content_hash` is present, recompute the SHA-256 of the decoded bytes (same encoding-aware decoding) and verify it matches. On mismatch, return `data_ref_hash_mismatch` (HTTP 400) — NOT `hash_mismatch`. This is distinct from the body-level `content_hash` check in step 4: step 3's hash-check binds an individual embedded payload to its declared digest (a DataRef-level integrity failure), while step 4 binds the whole producer-controlled body (a body-level failure). The two carry separate error codes precisely so a consumer can tell them apart — see RFC-ACDP-0007 §5 ("Distinguishing hash failures"). Per-embedded `content_hash` is OPTIONAL on publish (the producer commits to whatever `embedded.content` they sign in step 4 either way), but present-and-mismatching is a hard error per RFC-ACDP-0002 §6.6 Check 8.
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

> **Implementation guidance: avoid partial validators (NON-NORMATIVE).**
>
> The §2.1 pipeline is normative as an atomic flow: steps 1–7 MUST all complete before any persistence (steps 8–12). Libraries that expose intermediate validation steps as named public APIs invite misuse — once an API like `validate_schema_only` or `verify_hash_only` exists at the surface, a registry author under deadline can wire it into the publish path "for now" and ship a non-conformant build.
>
> Recommendations for library authors:
>
> - Treat the §2.1 pipeline as the only **public** publish entrypoint. Steps 1–7 SHOULD execute as one transaction inside the library, with no externally callable hooks between them.
> - Specifically, `validate_schema_only` (steps 1–3), `validate_hash_only` (step 4), `validate_structure` (steps 1–6 without signature verification), and similar surfaces are NOT conformant for registry persistence. Libraries MAY offer them as **internal** utilities for debugging or test-suite construction, but MUST NOT name them suggestively or mark them `pub`/exported.
> - Any debug-only API that intentionally bypasses signature verification (`publish_unverified`, `publish_unchecked`, `publish_without_signature_verification`, etc.) MUST be:
>   1. Named to make the safety property obvious at the call site (e.g. `unsafe_publish_without_signature_verification`, not `publish_fast`).
>   2. Gated behind a **non-default** configuration flag (a feature flag, a build feature like Cargo `unsafe-test-paths`, or a runtime config rejected when `ACDP_PROD=true`).
>   3. Hidden from the default API surface (`#[doc(hidden)]` in Rust, `_`-prefix in Python, `@deprecated` + omit from `index.ts` exports in TypeScript, lowercase identifier in Go).
>   4. Refused at server construction time when the server is configured for any non-test environment (the library SHOULD panic / return an error from the constructor, not just log a warning).
>
> The conformant path always includes all steps 1–8 atomically before any mutation. `pub-011-persist-only-after-signature-verify.json` is the fixture that exercises the persist-before-verify failure mode and complements this guidance.

> **⚠️ Non-conformant: persisting before signature verification.**
> A registry that validates the `content_hash` (step 4) but skips DID resolution and signature verification (steps 6–7) is **NOT conformant**, even if it never serves content that fails consumer verification. Persisting unverified content:
>
> - Consumes registry resources for potentially malicious inputs.
> - Creates stored bodies that carry invalid signatures, visible to any consumer who verifies.
> - Allows impersonation: an attacker crafts a correct `content_hash` for a fabricated body, bypasses the registry's verification, and the registry stores the body under the victim's `agent_id` despite the signature being unverifiable.
>
> Libraries and registry frameworks MUST NOT expose a "verified-except-signature" publish path as their default or primary API. The full §2.1 pipeline (steps 1–7 cryptographic validation, then 8–12 persistence) MUST be atomically coupled. A debug-only path that skips signature verification MAY exist for local development, but it MUST be (a) clearly named (e.g. `unsafe_publish_without_signature_verification`), (b) gated by a non-default configuration flag, and (c) refused by default at server construction time when the server is configured for any non-test environment. Conformance fixture `pub-011` exercises this requirement.

### 2.2 Producer-side flow

Producers building a publish request MUST:

1. Construct the publish request without `ctx_id`, `lineage_id`, `origin_registry`, `created_at`, `content_hash`, `signature`.
2. Compute `content_hash` over the JCS-canonicalized **ProducerContent** (RFC-ACDP-0001 §2) — the publish-request body with the full §5.7 exclusion set removed: `content_hash`, `signature`, `ctx_id`, `lineage_id`, `origin_registry`, `created_at`. At this stage, the body has neither `content_hash` nor `signature` set; both are added in steps 3–4 below. The resulting `content_hash` value is the literal string `sha256:` followed by 64 lowercase hex characters.
3. Sign the bytes of the **full `content_hash` string** — the ASCII bytes of `sha256:` followed by the 64 lowercase hex characters — with the producer's signing key, per RFC-ACDP-0001 §5.8. Producers MUST NOT sign the raw 32-byte hash digest, and MUST NOT sign the hex-only substring without the `sha256:` prefix.
4. Set `content_hash` and `signature` and submit the resulting object as the request body.

Producers publishing a first version (`supersedes = null`) **MUST NOT** include `lineage_id` in the publish request. Registries MUST reject first-version requests containing `lineage_id` with `schema_violation` (HTTP 400). The registry derives `lineage_id` from the assigned `ctx_id` (RFC-ACDP-0001 §5.6); producers cannot supply a correct value because they do not know the registry-assigned `ctx_id` at signing time.

Producers publishing a subsequent version (`supersedes != null`) MAY include `lineage_id` for self-verification. If supplied, the registry MUST verify it matches the deterministically-derived value and reject with `superseded_target` (`details.reason = "lineage_mismatch"`) on mismatch.

> **Note on the optional `lineage_id` in supersession publish requests.** The optional `lineage_id` here is a **producer assertion for self-verification**, NOT a registry assignment. Its purpose is to let the producer catch lineage-continuity errors at publish time: if the producer's understanding of the lineage does not match the value the registry computes from walking the `supersedes` chain, the registry returns `superseded_target` (`details.reason = "lineage_mismatch"`) and the producer can investigate before retrying. Producers that omit `lineage_id` on supersession are **not** in error — the registry derives and verifies `lineage_id` unconditionally from the `supersedes` chain regardless. This is a defensive correctness check, not a required part of the publish surface. (A future ACDP version may rename this field to `expected_lineage_id` to make the producer-assertion semantics unmissable; v0.1.0 keeps the original name to remain compatible with existing producer libraries.)

---

## 3. Supersession

To publish a corrected or updated version of a context, the producer publishes a new context with `supersedes` set to the previous version's `ctx_id`. The registry follows the same flow as §2.1 with the additional supersession validation in step 10.

### 3.1 Supersession constraints

For a publish request with `supersedes = <prev_ctx_id>`, the registry MUST:

1. Resolve `<prev_ctx_id>` and verify the context exists and is retrievable. If not, return `superseded_target` with `details.reason = "not_found"` (HTTP 400).
2. If `<prev_ctx_id>` lives in a different origin registry, the registry MUST reject the publish request with `superseded_target` (`details.reason = "cross_registry_supersession_unsupported"`, HTTP 400). **Cross-registry supersession is out of scope for v0.1.0**: the verification semantics (remote identity authentication, lineage continuity over the network, race protection across registries, recovery on partial failure) require additional protocol machinery not yet specified. A producer migrating a logical lineage between registries MUST start a new lineage on the target registry (with `supersedes: null`) and reference the prior lineage via `derived_from`. The reservation for a future cross-registry supersession protocol is in [RFC-ACDP-0009 §2.8](RFC-ACDP-0009-extensions.md).
3. Verify `agent_id` of the new context matches `agent_id` of the superseded context. If not, return `not_authorized` (HTTP 403). (Delegation is out of scope for v0.1.0.)
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
| Recomputed body hash ≠ `content_hash` | `hash_mismatch` | 400 |
| Embedded `data_ref.content_hash` ≠ decoded bytes | `data_ref_hash_mismatch` | 400 |
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

#### 6.2.1 Recommended ordering: idempotency lookup before signature verification

Registries SHOULD process idempotency-key lookup **before** signature verification (steps 6–7 of §2.1) to avoid paying DID resolution and signature-verification cost on benign retries. The recommended ordering is:

1. Parse `agent_id` and `Idempotency-Key` from the request. Validate the header value is 1–256 ASCII printable characters (otherwise treat as absent).
2. If a record exists for `(agent_id, Idempotency-Key)`:
   - Same `content_hash` as the stored record: return the stored response with **HTTP 200** (no re-validation needed; the original publish already passed the full §2.1 pipeline).
   - Different `content_hash`: return `duplicate_publish` (**HTTP 409**) without further validation.
3. Otherwise: run the full §2.1 validation pipeline (steps 1–7).
4. After successful persistence (step 12): atomically record `(agent_id, Idempotency-Key, content_hash, response)` in the same transaction as the body. A registry that records the body but crashes before the idempotency record is durable will, on retry, mint a fresh `ctx_id` for content the producer believes was already published — causing exactly the duplicate publication idempotency exists to prevent.

The atomicity requirement in step 4 is normative: it is the difference between idempotency that survives crashes and idempotency that exists only on the happy path. Implementations using a separate idempotency table SHOULD use a single transaction that writes both rows, or a write-once primary-key constraint that fails the second attempt (see fixture `idem-006` for the concurrent-publish race).

The ordering choice in steps 1–2 is a SHOULD, not a MUST: a registry MAY perform schema validation, payload-size validation, or any other cheap check before idempotency lookup. It MUST NOT perform DID resolution or signature verification before idempotency lookup, because doing so defeats the cost-amortization purpose of the header. Registries that treat the `Idempotency-Key` header as a post-hoc dedup mechanism (after signature verification has already run) are conformant only if their measured cost on retries matches an implementation that performed the lookup first — i.e., the test is observable behavior, not internal sequencing.

The conformance fixtures `idem-001` through `idem-006` exercise this surface.

#### 6.2.2 Distributed idempotency (NORMATIVE)

`idem-006` describes the single-server happy outcome for two concurrent same-key same-hash publishes: one 201 and one 200, or both 201 with the same `ctx_id`. This outcome is straightforward when both requests are handled by a single process with a serializable view of the idempotency table. In a multi-node deployment with eventual-consistency storage, two front-end nodes processing the same idempotency key concurrently MAY both complete §2.1 validation and reach step 12 (persistence) before either has stored the idempotency record — minting two distinct `ctx_id`s for what the producer believes is one logical publication, defeating the safe-retry guarantee.

Registries operating across multiple nodes MUST implement idempotency using an atomic store. "Atomic" here means: the `(agent_id, idempotency_key, content_hash, response)` record and the body persistence MUST commit together (or, equivalently, the idempotency record MUST be written with a unique constraint such that a second concurrent attempt fails before persisting the body). Acceptable mechanisms include:

- a single serializable-isolation transaction covering both writes;
- a compare-and-swap on a unique `(agent_id, idempotency_key)` index that pre-reserves the slot before §2.1 step 12 runs;
- a single-master shard that serializes idempotency-keyed publishes per `(agent_id, idempotency_key)`;
- an external lock service (Redis Redlock, etcd lease, Postgres advisory lock) held for the lifetime of the publish.

A registry that cannot guarantee atomic idempotency storage MUST either:

(a) **Shard idempotency-keyed requests** by `(agent_id, idempotency_key)` to a single node so that the in-node lookup is authoritative, OR

(b) **Not advertise `supports_idempotency_key: true`** in capabilities (RFC-ACDP-0007 §3.2). Producers will treat the header as absent and rely on their own content-deterministic deduplication (§6.3).

A registry advertising `supports_idempotency_key: true` while processing idempotency checks non-atomically is **OUT OF CONFORMANCE**. The advertised capability is a contract: producers depend on it for retry safety, and a registry that silently issues duplicate `ctx_id`s under concurrent retry undermines every higher-layer invariant that producers build on idempotency (deduplication by content_hash, lineage continuity, evidence-chain stability).

Producers relying on idempotency for retry safety SHOULD verify the advertised capability before depending on it AND SHOULD also retain a local content-hash deduplication index (§6.3) as a defense in depth — `Idempotency-Key` is necessary for retry safety but not sufficient if the producer cannot verify the registry's atomicity claim. Conformance fixture `idem-006` covers the race scenario; black-box conformance testing of distributed-store atomicity is implementation-specific (see the rate-limit note pattern in `registries/profiles.md`).

### 6.3 Content-deterministic deduplication

Independent of `Idempotency-Key`, the body's `content_hash` is content-deterministic. Producers MAY use it as a local deduplication key (e.g. record `content_hash` after a successful publish; on retry, look up by hash before re-submitting). This is a producer-side optimization and does not require registry cooperation.

---

## 7. Security Considerations

See [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md). Specific to publishing:

- Producers MUST authenticate with DID-based credentials.
- Registries MUST verify all signatures at publish time. Verification failures MUST result in rejection.
- When a producer rotates keys, prior signatures remain mathematically valid (same content + same key still verifies). Verifying that the *signing key was authorized at the time of publication* requires historical key authorization data, which most DID methods do not natively provide. Verifiers SHOULD verify against the producer's current DID document; verifiers requiring stronger historical guarantees MUST consult external mechanisms — see RFC-ACDP-0008 §9.3.
- Per-agent rate-limiting is REQUIRED (RFC-ACDP-0008 §4).
- Producers SHOULD treat every publish as a public commitment; v0.1.0 has no retraction.

---

## 8. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0006 Cross-Registry References](RFC-ACDP-0006-cross-registry.md)
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)

---

## Appendix A. Role implementation checklists (NON-NORMATIVE)

The §2.1 registry pipeline is normative; the producer-side flow in §2.2 is normative; the consumer-side checks are spread across RFC-ACDP-0001 §5.7 and §5.11 and RFC-ACDP-0004. This appendix collects the three role-specific checklists in one place to make implementation drift visible. The ordering is the recommended ordering — it matches the normative steps where they exist and groups validation that can be done before paying cryptographic cost. Implementations are free to reorder for performance as long as the observable result is identical to running these steps in the listed order.

### A.1 Producer — building a publish request

Before submitting `POST /contexts`:

1. **Build ProducerContent** with all required fields (`version`, `supersedes`, `agent_id`, `contributors`, `title`, `type`, `data_refs`, `derived_from`, `visibility`) and any optional fields the producer intends to include. **Do NOT** include any of the §5.7 exclusion-set fields (`content_hash`, `signature`, `ctx_id`, `lineage_id`, `origin_registry`, `created_at`).
2. **Validate field constraints locally** (so the registry's `schema_violation` is rare): title length ≤ 500; metadata depth ≤ 8 and JCS-canonicalized size ≤ 65536; each `data_refs[]` has exactly one of `location` or `embedded`; tags match `^[A-Za-z0-9][A-Za-z0-9_.-]*$`; `audience` is non-empty when `visibility = "restricted"`; `lineage_id` is absent when `supersedes = null`.
3. **Truncate every timestamp** in the request to canonical millisecond form (RFC-ACDP-0001 §5.3). This applies to `expires_at`, `data_period.{start,end}`, and any timestamps inside `data_refs`.
4. **Validate `agent_id` is `did:web:<…>`** (v0.1.0 mandate, RFC-ACDP-0001 §5.4 DID method scope table).
5. **JCS-canonicalize** ProducerContent.
6. **SHA-256** the canonical bytes; concatenate with the literal prefix `sha256:` to form the `content_hash` string.
7. **Sign** the ASCII bytes of the full `content_hash` string (including the `sha256:` prefix) with the producer's signing key, per RFC-ACDP-0001 §5.8.
8. **Set** `content_hash` and `signature` on the request body.
9. For supersession publishes (`version > 1`): set `version = previous.version + 1` and `supersedes = previous.ctx_id`. MAY set `lineage_id` for self-verification (registries MUST verify match if supplied).
10. **Submit** as `application/acdp+json` to `POST /contexts`.

### A.2 Registry — full §2.1 pipeline

Reproduced here in step-only form for cross-checking (full normative text in §2.1):

1. Schema validation (`schema_violation`).
2. Payload size (`payload_too_large`).
3. Embedded validation: decoded size ≤ 65536 (`embedded_too_large`); recompute optional `embedded.content_hash` (`data_ref_hash_mismatch`).
4. ProducerContent hash recomputation against `content_hash` (`hash_mismatch`).
5. Algorithm check against `supported_signature_algorithms` (`unsupported_algorithm`).
6. Key-id ↔ agent_id binding (`key_not_authorized`); DID document resolution (`key_resolution_failed` permanent / `key_resolution_unreachable` transient); `assertionMethod` authorization (`key_not_authorized`).
7. Signature verification (`invalid_signature`).
8. Identifier assignment (`ctx_id`, `origin_registry`, `created_at` — millisecond canonical).
9. Lineage derivation and walk (`superseded_target` with reasons `lineage_mismatch` or `lineage_walk_failed`).
10. Supersession constraints (§3.1: not_found, cross_registry_supersession_unsupported, lineage_mismatch, version_mismatch, already_superseded, plus `not_authorized` for cross-agent supersession).
11. Visibility validation (`schema_violation` for restricted-without-audience; private semantics — RFC-ACDP-0008 §4.5).
12. Persistence + `status` initialization (RFC-ACDP-0004 §4).
13. Response (§4 — exactly five fields, see fixture pub-007).

Steps 1–7 MUST complete before any persistence. Steps 8–12 are atomic with respect to concurrent publications targeting the same `supersedes` value.

### A.3 Consumer — verifying a retrieved body

Before trusting a body retrieved from any endpoint:

1. **Parse the wire bytes** into a structure that preserves all keys (e.g. `serde_json::Value`, `dict[str, Any]`, `JSON.parse`). Do NOT deserialize into a typed model whose decoder strips unknown fields — that breaks forward compatibility (RFC-ACDP-0001 §5.7 hash verification over raw JSON, fixture `can-008`).
2. **Validate the body's schema structure** against `acdp-context-body.schema.json` (open: tolerate unknown fields per §3.3.1 schema openness map).
3. **Recompute `content_hash`** by removing the §5.7 exclusion set BY NAME (`ctx_id`, `lineage_id`, `origin_registry`, `created_at`, `content_hash`, `signature`), JCS-canonicalizing the remainder, SHA-256ing, and comparing to `body.content_hash`. On mismatch, treat the body as untrusted. (Fixture `can-009`.)
4. **Resolve the producer's DID document** per RFC-ACDP-0001 §5.11 (v0.1.0: did:web only). Cache per the §5.11 caching guidance.
5. **Verify the signature** over the ASCII bytes of `body.content_hash` (with the `sha256:` prefix) using the resolved key.
6. **Validate body fields** against ACDP-0002 invariants (DataRef oneOf, metadata depth/size, tag patterns, `data_period.start ≤ data_period.end`, etc.).
7. **Tolerate unknown fields** in both the body and `registry_state`; treat unknown `status` values as `active` (RFC-ACDP-0004 §4.1, fixture `status-001`); treat unknown top-level capabilities fields as opaque (RFC-ACDP-0007 §3.3, fixture `caps-006`).

Consumers crossing registries (following `derived_from`) additionally apply RFC-ACDP-0006 §4.1 (resolution) and §7 (SSRF protections) before fetching the upstream body.
