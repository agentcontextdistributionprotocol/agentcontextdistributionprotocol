# RFC-ACDP-0001
# Agent Context Description Protocol (ACDP) — Core

**Document:** RFC-ACDP-0001
**Version:** 0.0.1
**Status:** Community Standards Track (Draft)
**Canonical wire format:** JSON over HTTP
**Required JSON canonicalization:** [RFC 8785 — JSON Canonicalization Scheme (JCS)](https://datatracker.ietf.org/doc/html/rfc8785)
**Intended status:** Stable Core

> This is an RFC-style open standard. It is not an IETF RFC.

---

## Abstract

The Agent Context Description Protocol (ACDP) lets autonomous AI agents **publish, discover, and verify** units of contextual information ("contexts") across distributed systems and organizational boundaries.

ACDP introduces one strict invariant:

> **Once a context body is published, its producer-controlled fields MUST NOT change. The producer-controlled portion of every body MUST be cryptographically signed by its producer, and every lineage MUST be end-to-end verifiable.**

The "producer-controlled portion" refers to the fields the producer authors and signs (everything except `ctx_id`, `lineage_id`, `origin_registry`, and `created_at`, which are registry-assigned at publish time). See §5.7 for the exact exclusion set, and §5.9 for what the producer signature does and does not bind.

ACDP Core does not define discovery semantics, registry policy, retraction rules, attestation schemas, or domain logic. ACDP Core defines structure: the **identifier formats** (`acdp://`, `lin:`), the **canonicalization algorithm** (JCS), the **content-hash and signature semantics**, the **time format**, and the **registry hooks** the rest of the spec depends on.

---

## 1. Status of This Memo

This document is a Draft. Backward-incompatible changes remain possible until Final.

This is the **first published version** of ACDP. The numbering scheme treats `acdp/0.0.1` as the inaugural release.

---

## 2. Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in this document are to be interpreted as described in BCP 14 ([RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119), [RFC 8174](https://datatracker.ietf.org/doc/html/rfc8174)) when, and only when, they appear in all capitals.

| Term | Definition |
|---|---|
| **Agent** | A software entity that produces or consumes contexts. Agents have stable identifiers (DIDs, per [DID-CORE]). |
| **Context** | A unit of agent-produced content described by an ACDP body and tracked by an ACDP registry. |
| **Body** | The immutable stored object representing a context. Contains producer-controlled fields plus the registry-assigned identity fields (`ctx_id`, `lineage_id`, `origin_registry`, `created_at`) and the integrity fields (`content_hash`, `signature`). All body fields are set at publish time and immutable thereafter. |
| **ProducerContent** | The signature/hash preimage. The Body with `content_hash`, `signature`, and the four registry-assigned identity fields removed (the §5.7 exclusion set). The producer signs ProducerContent; the Body wraps ProducerContent plus the registry-assigned identifiers and the signature. |
| **RegistryState** | The mutable, registry-derived state returned alongside the Body on retrieval. In v0.0.1 contains only the derived `status` field. Future ACDP versions add lifecycle events, relationships, and attestations to RegistryState without changing the Body. |
| **Registry** | A service that accepts, stores, and serves contexts according to this specification. |
| **Lineage** | A chain of contexts representing successive versions of the same logical work, identified by a stable `lineage_id`. |
| **Producer** | An agent that publishes contexts. |
| **Consumer** | An agent that retrieves and uses contexts. |

The Body contains both producer-controlled and registry-assigned fields; only ProducerContent is covered by the producer signature. See §5.7 for the exact exclusion set and §5.9 for what the producer signature does and does not bind.

---

## 3. Scope and Design Goals

ACDP exists to make agent-produced knowledge **discoverable, verifiable, and reusable** across organizational boundaries. It provides:

1. content-addressed, cryptographically-signed bodies;
2. a deterministic lineage model for versioning;
3. a small set of HTTP-based publish/retrieve operations (RFC-ACDP-0003, RFC-ACDP-0004);
4. keyword discovery (RFC-ACDP-0005);
5. cross-registry references via the `acdp://` URI scheme (RFC-ACDP-0006);
6. registry capability declaration and a defined error surface (RFC-ACDP-0007);
7. a threat model (RFC-ACDP-0008).

ACDP does **not** define:

- coordination, voting, consensus, or convergent decision-making;
- demand-pull, requests, or fulfillment mechanics;
- payment, settlement, or marketplaces;
- workflow or pipeline declarations;
- reputation algorithms;
- quality scoring by registries;
- audit-grade time anchoring;
- encrypted bodies (use `data_refs` splitting and external ACLs);
- schema hosting (ACDP only references schemas);
- hard deletion of any kind;
- multi-party or threshold signatures (use `contributors`).

See [docs/non-goals.md](../docs/non-goals.md) for the full non-goals list and rationale.

---

## 4. Architecture

```
┌────────────────────────────┐                ┌────────────────────────────┐
│  Producer Agent            │                │  Consumer Agent            │
│  (DID, signing key)        │                │  (DID, key resolver)       │
└──────────────┬─────────────┘                └──────────────┬─────────────┘
               │ POST /contexts (signed body)                │
               ▼                                             │
       ┌──────────────────────────┐                          │
       │  ACDP Registry           │                          │
       │  did:web:reg.example     │  ◀──── GET /contexts/{ctx_id}┘
       │  /.well-known/acdp.json  │  (body + registry_state)
       └──────────────────────────┘
                 │
                 │ verify producer signature locally,
                 │ walk derived_from → cross-registry resolves
                 ▼
       Other ACDP registries
```

Each role's responsibilities:

- **Producer.** Builds a body, computes `content_hash` over the JCS-canonicalized body (excluding the fields listed in §5.7 — `content_hash`, `signature`, and the registry-assigned identity fields), signs the hash with its DID-bound key, and submits a publish request.
- **Registry.** Recomputes `content_hash` over the JCS-canonicalized ProducerContent, then verifies the producer's signature over the recomputed hash. Only after both checks pass does the registry assign `ctx_id` / `lineage_id` / `origin_registry` / `created_at`, validate supersession constraints, persist the body, and derive `status`. See RFC-ACDP-0003 §2.1 for the full ordered step list.
- **Consumer.** Fetches a context, verifies the producer's signature against the producer's DID document, walks `derived_from` references via cross-registry resolution.

Verification is **stateless and local** for the consumer: to check a context, a consumer needs only the producer's public key (resolved from the producer's DID document), the canonicalization algorithm (JCS), and the spec-defined exclusion set for `content_hash`.

---

## 5. Wire Format

### 5.1 JSON encoding

All ACDP messages on the wire are JSON ([RFC 8259]) objects encoded as UTF-8 ([RFC 3629]). Implementations MUST emit valid UTF-8 and MUST accept any valid UTF-8.

The HTTP `Content-Type` for ACDP bodies is `application/acdp+json`. Implementations MAY also accept `application/json` for compatibility but SHOULD emit `application/acdp+json`. See [`registries/media-types.md`](../registries/media-types.md).

### 5.2 Canonicalization

Cryptographic hashes over ACDP data structures use JSON Canonicalization Scheme (JCS) [RFC 8785]. Implementations MUST canonicalize using JCS before hashing for any normative cryptographic operation.

Cross-language interoperability of canonicalization is the most common source of ACDP implementation bugs. The conformance fixtures under `schemas/conformance/can-*.json` define the authoritative test vectors; implementations failing those vectors MUST NOT claim conformance.

**Implementer note — Python `json.dumps`.** Python's stdlib `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)` is JCS-conformant for most input shapes but is **not conformant on negative zero**: it preserves `-0.0` as `-0.0` rather than emitting `0` per RFC 8785 §3.2.2.3. Implementations using stdlib will fail `can-001-jcs-vector.json`'s number-formatting vector. Use the `jcs` package on PyPI (https://pypi.org/project/jcs/), or pre-process input to normalize negative zero before serialization. Similar canonicalization gotchas exist in other languages (e.g., serializers that escape non-ASCII as `\uXXXX` by default); verify against the conformance fixtures before claiming conformance.

### 5.3 Time Format

All timestamps in ACDP are RFC 3339 [RFC 3339] date-time strings in UTC with the explicit `Z` suffix.

The **canonical emission form** uses millisecond precision:

```
2026-04-16T10:30:15.123Z
```

**Timestamp precision (MUST).** Producers MUST truncate every timestamp value in a publish request to millisecond precision **before** computing `content_hash`. Because timestamps are part of the JCS-canonicalized body, a timestamp with microsecond or nanosecond precision produces a different canonical string than its millisecond-truncated equivalent — and therefore a different `content_hash` that no other conformant implementation can reproduce from the same logical timestamp. Library authors MUST apply millisecond truncation automatically in every API surface that accepts a timestamp on the producer path (`expires_at`, `data_period.start`, `data_period.end`, and any `data_refs` timestamps). Standard-library types in many languages (`time.Time` in Go, `datetime` in Python, `chrono::DateTime` in Rust, `Date` / `Temporal.Instant` in JS) default to higher precision and silently emit nanosecond strings unless explicitly truncated; this is the most common source of cross-implementation hash divergence.

Implementations:
- MUST emit timestamps in canonical form when generating new timestamps.
- MUST accept any valid RFC 3339 date-time on input. This includes timestamps with no fractional seconds, microsecond, or nanosecond precision.
- SHOULD normalize accepted timestamps to canonical form on storage.

**Producer note.** Because timestamps are part of the JCS-canonicalized body, two contexts with timestamps differing only in fractional precision will produce different `content_hash` values. The canonical millisecond form is mandatory for the producer path; the conformance fixture `can-006-timestamp-precision.json` pins a nanosecond-precision input and locks in the hash that the *exact serialized string* produces, making the "hash binds the bytes, not the logical instant" rule explicit.

**Clock and skew.** Registries SHOULD use NTP-synchronized UTC clocks. The registry's clock is authoritative for `created_at` (registry-assigned) and for the `status: expired` derivation (RFC-ACDP-0004 §4). Consumers computing `expired` locally MAY apply a skew tolerance of up to ±60 seconds against `expires_at`; consumers comparing a registry's `created_at` against their own local clock SHOULD allow the same tolerance. Producers MUST set `expires_at` and `data_period.{start,end}` based on their own UTC clock; small skew between producer and registry is expected and harmless because these fields are signed (not derived).

### 5.4 Identifier Formats

| Identifier | Form | Spec |
|---|---|---|
| **`ctx_id`** (context identifier) | `acdp://<authority>/<uuid>` where `<authority>` is a DNS hostname identifying the origin registry and `<uuid>` is a UUID v4 [RFC 9562]. | §5.5 |
| **`lineage_id`** | `lin:<algorithm>:<digest>`. v0.0.1 form: `lin:sha256:<64-lowercase-hex>`. | §5.6 |
| **`agent_id`** | A Decentralized Identifier [DID-CORE]. v0.0.1 producers MUST use `did:web` so that any conformant registry can resolve their keys via §5.11. | RFC-ACDP-0002 |

The `ctx_id` is assigned by the registry at publish time; producers MUST NOT supply a `ctx_id` in publish requests. The corresponding URI scheme `acdp` is registered in §11.

### 5.5 Context-ID assignment

A registry assigns `ctx_id` at publish time as `acdp://<own_authority>/<freshly_generated_uuidv4>`. The authority component MUST equal the DNS hostname declared in the registry's capabilities document (RFC-ACDP-0007). Two registries MUST NOT share an authority.

### 5.6 Lineage Identifier Derivation

A context's `lineage_id` MUST be derived deterministically from the `ctx_id` of the lineage's first version (the version with `supersedes: null`):

```
lineage_id = "lin:sha256:" + lowercase_hex(SHA-256(first_version_ctx_id))
```

The hash input is the UTF-8 encoding of the `ctx_id` string. The `sha256` algorithm prefix is fixed in v0.0.1; future ACDP versions MAY introduce additional algorithms (`lin:sha3-256:...`, `lin:blake3:...`) for new lineages without invalidating existing v0.0.1 `lin:sha256:` identifiers. Consumers MUST NOT compare lineage_ids across different algorithm prefixes.

For first versions, the registry computes `lineage_id` from the `ctx_id` it just assigned. For subsequent versions, the registry MUST walk back through `supersedes` references to find the version 1 context and apply the same formula.

A producer publishing a first version (`supersedes: null`) MUST NOT include `lineage_id` in the publish request — the producer cannot know the registry-assigned `ctx_id` at signing time, so any supplied value would be a guess. Registries MUST reject first-version requests containing `lineage_id` with `schema_violation` (RFC-ACDP-0003 §2.2).

A producer publishing a subsequent version (`supersedes != null`) MAY include `lineage_id` for self-verification. If supplied, the registry MUST verify it matches the deterministically-derived value and MUST reject mismatches with `superseded_target` (`details.reason = "lineage_mismatch"`, RFC-ACDP-0003 §3.1 step 4).

#### 5.6.1 Lineage walk failure

If, while walking back through `supersedes` references to compute `lineage_id` for a subsequent-version publish, the registry cannot retrieve an intermediate context, the registry MUST reject the publish request with `superseded_target` (`details.reason = "lineage_walk_failed"`, HTTP 400). In v0.0.1 this most commonly means the immediate-predecessor chain is intact (RFC-ACDP-0003 §3.1 step 1 already gates the head with `details.reason = "not_found"` if absent) but a deeper intermediate is missing — for example because of out-of-band administrative deletion (which ACDP itself forbids). Cross-registry intermediate cases cannot arise in v0.0.1 because cross-registry supersession is rejected at §3.1 step 2 with `cross_registry_supersession_unsupported` before any walk runs; the trigger is reserved here for forward compatibility with v0.1+ cross-registry supersession (RFC-ACDP-0009 §2.8). The error envelope SHOULD include the failing intermediate `ctx_id` in `details` for debuggability:

```json
{
  "error": {
    "code": "superseded_target",
    "message": "Could not retrieve intermediate context while walking the supersession chain.",
    "details": {
      "reason": "lineage_walk_failed",
      "unreachable_ctx_id": "acdp://reg.example/2dffa0..."
    }
  }
}
```

This reason is reserved for the lineage-walk path; it does NOT cover the immediate-target case (RFC-ACDP-0003 §3.1 step 1 returns `details.reason = "not_found"` for that) and it does NOT cover the cross-registry case (§3.1 step 2 returns `cross_registry_supersession_unsupported`).

### 5.7 Content Hash

The `content_hash` field of a body is the SHA-256 [FIPS 180-4] digest of the JCS-canonicalized **ProducerContent** (§2), encoded as the literal string `sha256:` followed by 64 lowercase hexadecimal characters. ProducerContent is the publish request body with the following fields removed:

- `content_hash` itself (a field cannot contain its own hash);
- `signature` (the signature is over the hash, so cannot be in the hashed input);
- `ctx_id`, `lineage_id`, `origin_registry`, `created_at` (registry-assigned, not known to the producer at signing time).

All other fields present in the publish request are included in the hash input. The producer computes `content_hash` over this reduced object, then sets the `content_hash` and `signature` fields on the request before submission.

The exclusion list permits the producer to compute `content_hash` and sign before the registry assigns identifiers. The producer commits to the content; the registry separately binds the identifiers.

Implementations MUST produce identical `content_hash` values for the same body content across all conforming implementations. Test vectors are provided in the conformance fixtures.

### 5.8 Signature

The `signature` field of a body is a JSON object:

| Field | Type | Required | Description |
|---|---|---|---|
| `algorithm` | string | Yes | Signature algorithm identifier. See §5.10. |
| `key_id` | string | Yes | DID URL identifying the signing key. |
| `value` | string | Yes | Base64-encoded signature bytes. |

The signature value is computed over the bytes of the full `content_hash` string — that is, the ASCII bytes of `sha256:` followed by the 64 lowercase hex characters. Implementations MUST NOT sign the raw hash bytes alone.

Registries MUST verify the signature at publish time. A context whose signature does not verify MUST be rejected with the `invalid_signature` error code (RFC-ACDP-0007).

### 5.9 Replay, Tamper, and Impersonation Protection

ACDP's protections decompose by what the producer signature does and does not bind:

**What the producer signature binds (cryptographic protection):**

- **Body tampering** is detected by recomputing `content_hash` over the canonicalized ProducerContent (§2). Any change in any non-excluded field changes the hash; the signature will not verify.
- **Producer impersonation** of content is prevented: a third party cannot forge a signature without the producer's private key.
- **Lineage integrity**: each ancestor in `derived_from` is independently signed by its own producer.

**What the producer signature does NOT bind (registry-honesty protection):**

- `ctx_id`, `lineage_id`, `origin_registry`, and `created_at` are registry-assigned. The producer signature does not cover them. A consumer cannot cryptographically verify which registry first accepted the content, what `ctx_id` it was assigned, what lineage it belongs to, or when publication occurred. These facts rely on **registry honesty** in v0.0.1.

A malicious or compromised registry could republish a producer's signed content under a different `ctx_id` or `origin_registry` (the signature would still verify), or backdate `created_at`. See RFC-ACDP-0008 §9.1 for the full discussion and §9.2 for mitigations.

A future ACDP version will introduce **registry receipts** (RFC-ACDP-0009 §2.7) that bind registry-assigned identifiers to the registry's DID, closing this gap cryptographically.

**Replay** at the wire level is mitigated by HTTPS transport security. ACDP itself does not specify per-request nonces — the body's content hash makes "the same body twice" content-level idempotent. Registries SHOULD implement `Idempotency-Key` (RFC-ACDP-0003 §6) for true publication-level idempotency.

Distinguish two senses of idempotency:

- **Content-level idempotency:** identical bodies produce identical `content_hash` values. This is automatic and intrinsic to ACDP.
- **Publication-level idempotency:** identical publish requests produce identical `ctx_id`s and do not create duplicate registry records. This requires the optional `Idempotency-Key` mechanism (RFC-ACDP-0003 §6).

Without `Idempotency-Key`, replaying a publish request creates a new `ctx_id` for the same content. Producers SHOULD deduplicate locally on `content_hash`.

### 5.10 Signature Algorithms

Implementations MUST support `ed25519` [RFC 8032]. Implementations MAY support additional algorithms (e.g. `ecdsa-p256`). A registry's supported algorithms MUST be declared in its capabilities document (RFC-ACDP-0007). Registries MUST reject `unsupported_algorithm` for any algorithm not in their declared list. The full algorithm vocabulary is maintained in [`registries/signature-algorithms.md`](../registries/signature-algorithms.md).

### 5.11 Key Resolution

To verify a producer signature, an implementation MUST resolve `signature.key_id` (a DID URL) to a public key. v0.0.1 mandates support for `did:web` only; producers MUST use `did:web` keys, and registries MUST resolve `did:web` keys.

The resolution algorithm:

1. **Parse the DID URL.** Split `signature.key_id` into the DID portion (everything before `#`) and the fragment (everything after `#`, REQUIRED). A `key_id` without a fragment MUST be rejected with `key_resolution_failed`.

2. **Verify producer binding.** The DID portion MUST equal `body.agent_id`. Mismatch MUST be rejected with `key_not_authorized`.

3. **Resolve the DID document.** For `did:web:<authority>[:<path>...]`:
   - Construct the URL: `https://<authority>/.well-known/did.json` for a bare `did:web:<authority>`, or `https://<authority>/<path-with-colons-replaced-by-slashes>/did.json` for a path-bearing form.
   - HTTPS is REQUIRED; HTTP requests MUST NOT be made. The certificate MUST be valid.
   - The response MUST be a JSON object with `Content-Type: application/did+json` (or `application/json`).
   - Failures are classified as transient or permanent and reported with distinct error codes:
     - **Transient** (network or upstream-availability): DNS resolution failure, TLS handshake failure, HTTP non-2xx response, or timeout fetching the DID document. MUST be reported as `key_resolution_unreachable` (HTTP 502). These are typically retryable.
     - **Permanent** (the upstream document is malformed or does not authorize the requested key): JSON parse error of the fetched document, missing fragment in `signature.key_id`, or no `verificationMethod` matches the requested fragment. MUST be reported as `key_resolution_failed` (HTTP 400). These are not retryable without producer-side action (republish with a corrected `key_id`, fix the DID document, etc.).

4. **Locate the verification method.** The DID document's `verificationMethod` array contains key entries. Find the entry whose `id` ends with `#<fragment>` (matching the parsed fragment from step 1). If no entry matches, return `key_resolution_failed`.

5. **Verify authorization.** The verification method's `id` MUST be referenced by the DID document's `assertionMethod` array (either by full `id` URL or by relative `#<fragment>`). If not, return `key_not_authorized`.

6. **Extract the public key bytes.** The verification method MUST have one of:
   - `publicKeyMultibase` — base58-btc encoded, with the multibase `z` prefix and the multicodec algorithm prefix (e.g., `0xed01` for ed25519).
   - `publicKeyJwk` — a JWK object with `kty`, `crv`, `x` (and `y` for `crv: P-256`).

   Implementations MUST support `publicKeyJwk` and SHOULD support `publicKeyMultibase`. The verification method's `type` field SHOULD match the algorithm in `signature.algorithm` (`Ed25519VerificationKey2020` for ed25519, `JsonWebKey2020` for either); a mismatch MUST be rejected with `invalid_signature`.

7. **Verify the signature.** Use the extracted public key to verify `signature.value` (base64-decoded bytes) against the ASCII bytes of `body.content_hash` (per §5.8).

**Caching.** Implementations SHOULD cache resolved DID documents for at least 5 minutes and at most 24 hours. The cache key is the DID (not the full DID URL). Implementations MUST refresh on any verification failure that could plausibly be due to key rotation.

**Future DID methods.** v0.1+ may add `did:key`, `did:jwk`, and other methods. The resolution algorithm above is `did:web`-specific; other methods will be specified separately.

---

## 6. Compatibility Model

ACDP uses a layered compatibility model:

- **Registry protocol version** is advertised in the registry capabilities document as `acdp_version` (e.g. `0.0.1`). It tells consumers which protocol surface the registry implements.
- **Body protocol version** is advertised optionally inside each body as `body.acdp_version`. The body field is producer-signed and bound to the body's `content_hash`. An absent `body.acdp_version` MUST be treated as `0.0.1`. v0.1+ producers SHOULD set the field explicitly so verifiers can apply the correct exclusion set (§5.7) and algorithm vocabulary.
- **Body extensibility** is forward-compatible only via additive fields. Breaking body changes require a new protocol version, signaled by `body.acdp_version`.
- **Registry-state extensibility** is open: future versions add fields (lifecycle events, relationships, attestations); consumers MUST tolerate unknown fields in registry state. Schema enums for known fields (e.g. `status`) use open string patterns so unknown values do not fail validation.

Major protocol version mismatches are not compatible. Minor versions are expected to be backward compatible. Consumers receiving an unknown `acdp_version` (in capabilities or in a body) SHOULD treat it as a higher version and degrade gracefully, using only operations defined in the version they understand.

---

## 7. Transport

ACDP operations are HTTP-based with JSON request and response bodies, content type `application/acdp+json`. Operations are defined in:

- RFC-ACDP-0003 — `POST /contexts`, supersession.
- RFC-ACDP-0004 — `GET /contexts/{ctx_id}`, `GET /contexts/{ctx_id}/body`, `GET /lineages/{lineage_id}`, `GET /lineages/{lineage_id}/current`.
- RFC-ACDP-0005 — `GET /contexts/search`.
- RFC-ACDP-0007 — `GET /.well-known/acdp.json`.

ACDP v0.0.1 is JSON-only. Binary transport bindings are out of scope for this version and MAY be specified in a future release.

All ACDP traffic MUST run over TLS in production deployments.

---

## 8. Registry Hooks

ACDP maintains the following registries under [`registries/`](../registries/):

- **context-types** — registered values for `Body.type`.
- **error-codes** — protocol-level error codes returned in error envelopes.
- **media-types** — content types used in transport bindings.
- **locator-schemes** — well-known dotted-namespace schemes for structured `data_refs.location`.
- **signature-algorithms** — open vocabulary for `signature.algorithm` and `capabilities.supported_signature_algorithms`.
- **auth-methods** — open vocabulary for `capabilities.read_authentication_methods`.
- **profiles** — open vocabulary for `capabilities.profiles`.

New entries are added via the [RFC process](../governance/RFC-PROCESS.md). Experimental identifiers SHOULD use reverse-domain notation.

---

## 9. Conformance

A conformant ACDP registry MUST:

1. Parse and validate publish requests against `acdp-publish-request.schema.json`.
2. Recompute `content_hash` per §5.7 and reject on mismatch.
3. Verify the producer's signature per §5.8 and reject on failure.
4. Assign `ctx_id`, `origin_registry`, `created_at` per §5.5.
5. Compute `lineage_id` per §5.6.
6. Validate supersession constraints per RFC-ACDP-0003.
7. Serve `GET /.well-known/acdp.json` per RFC-ACDP-0007.
8. Pass the conformance fixtures in [`schemas/conformance/`](../schemas/conformance/).
9. Reproduce the JCS test vectors exactly (`can-001-jcs-vector.json`).

A conformant ACDP consumer MUST:

1. Verify signatures end-to-end for every context it relies on.
2. Treat unknown fields in body and registry state as opaque.
3. Treat `status: superseded` and `status: expired` as signals that a context's conclusions may not be current.
4. Resolve cross-registry `acdp://` references per RFC-ACDP-0006 if it follows them.

### 9.1 Implementation Profiles

ACDP defines profiles to allow partial implementations to declare conformance honestly. Implementations declare their profile(s) in the capabilities document `profiles` field (RFC-ACDP-0007 §3.1). Each profile is a strict superset of its prerequisite.

#### `acdp-registry-core`

The minimum profile for any registry. Implementations MUST:

- Implement `POST /contexts` per RFC-ACDP-0003 (full validation pipeline §2.1, supersession §3, idempotency §6 if `supports_idempotency_key` is advertised).
- Implement `GET /contexts/{ctx_id}` and `GET /contexts/{ctx_id}/body` per RFC-ACDP-0004 §2.
- Implement `GET /lineages/{lineage_id}` and `GET /lineages/{lineage_id}/current` per RFC-ACDP-0004 §5.
- Implement `GET /.well-known/acdp.json` per RFC-ACDP-0007 §3.
- Apply visibility rules per RFC-ACDP-0008 §4.5.
- Pass all conformance fixtures in `schemas/conformance/` (publish, retrieval, visibility, canonicalization).

#### `acdp-registry-discovery`

Adds keyword search. Implementations MUST:

- Be `acdp-registry-core` conformant.
- Implement `GET /contexts/search` per RFC-ACDP-0005 §2 (search semantics §2.5 — required fields, AND-of-terms, ranking, cursor stability).
- Pass discovery and visibility-discovery conformance fixtures (notably `vis-002`).

#### `acdp-registry-federated`

Adds cross-registry resolution. Implementations MUST:

- Be `acdp-registry-core` conformant.
- Resolve `acdp://` references in `derived_from` chains per RFC-ACDP-0006 §4.1 (and apply the trust model in §4.2 and caching guidance in §4.3).
- Verify the upstream registry's DID at resolution time per RFC-ACDP-0006 §4.1 step 3: fetch `https://<authority>/.well-known/acdp.json`, extract `registry_did`, resolve the DID document, and confirm the DID's web binding matches `<authority>`. On mismatch, treat the cross-registry resolution as failed and return `cross_registry_resolution_failed` (defined in RFC-ACDP-0007 §5; emitted per RFC-ACDP-0006 §7).
- Implement SSRF protections per RFC-ACDP-0006 §7 (IP-range filtering, HTTPS-only, response/timeout caps, redirect cap, DNS-rebinding pin).

#### `acdp-consumer`

A consumer of contexts (not a registry). Implementations MUST:

- Verify producer signatures end-to-end on every retrieved context they rely on.
- Resolve cross-registry `acdp://` references per RFC-ACDP-0006 if they follow them (and apply the SSRF protections of §7 if they perform server-side resolution).
- Apply visibility rules per RFC-ACDP-0008 §4.5 when retrieving (do not assume a registry's results are scoped on their behalf — verify locally where possible).
- Tolerate unknown fields in body and registry state.

There is no producer-only profile: producers MUST be able to verify their own publications, which requires the same cryptographic core as a consumer.

---

## 10. Security Considerations

See [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md) for the full threat model. Implementations MUST use a cryptographically secure RNG for UUIDs, store private keys in secure storage, and validate all inputs against the JSON Schemas before processing.

---

## 11. IANA Considerations

### 11.1 URI Scheme Registration

This document requests provisional registration of the `acdp` URI scheme:

- **Scheme name:** `acdp`
- **Status:** Provisional
- **Applications/protocols that use this scheme:** Agent Context Description Protocol (ACDP)
- **Contact:** Zer07 Labs `<specifications@zer07labs.com>`
- **Change controller:** Zer07 Labs
- **References:** This document
- **Syntax:** `acdp://<authority>/<uuid>`, where `<authority>` is a DNS hostname per [RFC 1035] and `<uuid>` is a UUID v4 per [RFC 9562]
- **Security considerations:** See RFC-ACDP-0008
- **Encoding considerations:** See §5

### 11.2 Media Type Registration

- **Type:** `application`
- **Subtype:** `acdp+json`
- **Required parameters:** None
- **Optional parameters:** None. Protocol version is carried in JSON: `acdp_version` in the capabilities document (RFC-ACDP-0007 §3) and optional `body.acdp_version` in context bodies (§6). The media type does NOT carry a `version` parameter; doing so would create two competing version sources.
- **Encoding considerations:** UTF-8 per [RFC 8259]
- **Security considerations:** See RFC-ACDP-0008
- **Published specification:** This document
- **Applications that use this media type:** ACDP registries and clients

### 11.3 Well-Known URI Registration

- **URI suffix:** `acdp.json`
- **Change controller:** Zer07 Labs
- **Specification document(s):** This document; RFC-ACDP-0007 §3
- **Related information:** None

---

## 12. References

### 12.1 Normative References

- [DID-CORE] World Wide Web Consortium, "Decentralized Identifiers (DIDs) v1.0", W3C Recommendation, July 2022.
- [FIPS 180-4] National Institute of Standards and Technology, "Secure Hash Standard (SHS)", FIPS PUB 180-4, August 2015.
- [RFC 1035] Mockapetris, P., "Domain names — implementation and specification", STD 13, RFC 1035, November 1987.
- [RFC 2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.
- [RFC 3339] Klyne, G. and C. Newman, "Date and Time on the Internet: Timestamps", RFC 3339, July 2002.
- [RFC 3629] Yergeau, F., "UTF-8, a transformation format of ISO 10646", STD 63, RFC 3629, November 2003.
- [RFC 9562] Davis, K., Peabody, B., and P. Leach, "Universally Unique IDentifiers (UUIDs)", RFC 9562, May 2024. Obsoletes RFC 4122.
- [RFC 8032] Josefsson, S. and I. Liusvaara, "Edwards-Curve Digital Signature Algorithm (EdDSA)", RFC 8032, January 2017.
- [RFC 8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.
- [RFC 8259] Bray, T., "The JavaScript Object Notation (JSON) Data Interchange Format", STD 90, RFC 8259, December 2017.
- [RFC 8785] Rundgren, A., Jordan, B., and S. Erdtman, "JSON Canonicalization Scheme (JCS)", RFC 8785, June 2020.

### 12.2 Cross-references

- [RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md)
- [RFC-ACDP-0003 Publish](RFC-ACDP-0003-publish.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0005 Discovery](RFC-ACDP-0005-discovery.md)
- [RFC-ACDP-0006 Cross-Registry References](RFC-ACDP-0006-cross-registry.md)
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
