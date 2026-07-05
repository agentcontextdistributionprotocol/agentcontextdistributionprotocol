# RFC-ACDP-0001
# Agent Context Distribution Protocol (ACDP) — Core

**Document:** RFC-ACDP-0001
**Version:** 0.2.0-draft
**Status:** Community Standards Track (Final for acdp/0.1.0; sections marked *(0.2.0)* are Draft)
**Canonical wire format:** JSON over HTTP
**Required JSON canonicalization:** [RFC 8785 — JSON Canonicalization Scheme (JCS)](https://datatracker.ietf.org/doc/html/rfc8785)
**Intended status:** Stable Core

> This is an RFC-style open standard. It is not an IETF RFC.

---

## Abstract

The Agent Context Distribution Protocol (ACDP) lets autonomous AI agents **publish, discover, and verify** units of contextual information ("contexts") across distributed systems and organizational boundaries.

ACDP introduces one strict invariant:

> **Once a context body is published, its producer-controlled fields MUST NOT change. The producer-controlled portion of every body MUST be cryptographically signed by its producer, and every lineage MUST be end-to-end verifiable.**

The "producer-controlled portion" refers to the fields the producer authors and signs (everything except `ctx_id`, `lineage_id`, `origin_registry`, and `created_at`, which are registry-assigned at publish time). See §5.7 for the exact exclusion set, and §5.9 for what the producer signature does and does not bind.

ACDP Core does not define discovery semantics, registry policy, retraction rules, attestation schemas, or domain logic. ACDP Core defines structure: the **identifier formats** (`acdp://`, `lin:`), the **canonicalization algorithm** (JCS), the **content-hash and signature semantics**, the **time format**, and the **registry hooks** the rest of the spec depends on.

---

## 1. Status of This Memo

This document is a Final ACDP specification (acdp/0.1.0). It is stable for the 0.1.0 release; subsequent breaking changes require a new RFC and a version bump per [VERSIONING.md](../VERSIONING.md).

This revision additionally carries the **acdp/0.2.0 Trust & Hardening amendments** (registry receipts — RFC-ACDP-0010; `did:key` producers; explicit `acdp_version`; lineage anchoring; historical key retention). Amended or added passages are marked *(0.2.0)* and have **Draft** status until the 0.2.0 conformance pack passes against two independent implementations; everything else remains Final and wire-frozen. No 0.2.0 amendment changes any v0.1.0 body field, JCS rule, content-hash semantic, or signature semantic — every existing v0.1.0 body, signature, and `content_hash` remains valid.

ACDP `0.1.0` is the **first published Final version** of the protocol; the numbering scheme treats `acdp/0.1.0` as the inaugural release. The `0.0.1` identifier was used only for internal pre-release drafts and was never promoted to a Release Candidate or Final status. `0.1.0` is wire-compatible with those drafts — the body format, JCS canonicalization, content-hash, and signature semantics are unchanged.

---

## 2. Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in this document are to be interpreted as described in BCP 14 ([RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119), [RFC 8174](https://datatracker.ietf.org/doc/html/rfc8174)) when, and only when, they appear in all capitals.

| Term | Definition |
|---|---|
| **Agent** | A software entity that produces or consumes contexts. Agents have stable identifiers (DIDs, per [DID-CORE]). |
| **Context** | A unit of agent-produced content described by an ACDP body and tracked by an ACDP registry. |
| **Body** | The immutable stored object representing a context. Contains producer-controlled fields plus the registry-assigned identity fields (`ctx_id`, `lineage_id`, `origin_registry`, `created_at`) and the integrity fields (`content_hash`, `signature`). All body fields are set at publish time and immutable thereafter. |
| **ProducerContent** | The signature/hash preimage. The Body with `content_hash`, `signature`, and the four registry-assigned identity fields removed (the §5.7 exclusion set). The producer signs ProducerContent; the Body wraps ProducerContent plus the registry-assigned identifiers and the signature. |
| **RegistryState** | The mutable, registry-derived state returned alongside the Body on retrieval. In v0.1.0 contains only the derived `status` field. Future ACDP versions add lifecycle events, relationships, and attestations to RegistryState without changing the Body. |
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

Cross-language interoperability of canonicalization is the most common source of ACDP implementation bugs. The conformance fixtures under `schemas/conformance/can-*.json` define the authoritative test vectors; implementations failing those vectors MUST NOT claim conformance. Numeric serialization is the subtlest part of JCS: `can-011-jcs-numeric-vectors.json` pins the RFC 8785 §3.2.2.3 (ECMAScript Number-to-String) behavior — the exponential-notation boundaries (magnitude ≥ 1e21 and ≤ 1e-7), the plain-decimal band between them, integer exactness through 2^53, and negative-zero normalization — which a naïve serializer will silently get wrong.

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

**Registry timestamp emission (MUST).** Registries MUST assign `created_at` using canonical millisecond precision (e.g. `2026-04-16T10:30:15.123Z`). Implementations using OS clock APIs that return higher-precision timestamps — `time.Now()` in Go (nanoseconds), `Instant::now()` / `chrono::Utc::now()` in Rust, `datetime.datetime.now(tz=UTC)` in Python (microseconds), `Date.now()` returning a millisecond `Number` but `Temporal.Now.instant()` returning nanoseconds in JS, `Instant.now()` in Java (nanoseconds) — MUST truncate to millisecond precision before serializing `created_at` into both the publish response and the stored body. Truncation MUST round toward the past (floor); rounding to nearest can produce a `created_at` greater than the registry's wall-clock instant of acceptance, which violates the Time Format invariant. The registry-side requirement is identical to the producer-side rule above; `can-007-registry-created-at.json` pins it as a separate fixture so registry implementers can verify their emission path independently of any producer payload.

**Clock and skew.** Registries SHOULD use NTP-synchronized UTC clocks. The registry's clock is authoritative for `created_at` (registry-assigned) and for the `status: expired` derivation (RFC-ACDP-0004 §4). Consumers computing `expired` locally MAY apply a skew tolerance of up to ±60 seconds against `expires_at`; consumers comparing a registry's `created_at` against their own local clock SHOULD allow the same tolerance. Producers MUST set `expires_at` and `data_period.{start,end}` based on their own UTC clock; small skew between producer and registry is expected and harmless because these fields are signed (not derived).

### 5.4 Identifier Formats

| Identifier | Form | Spec |
|---|---|---|
| **`ctx_id`** (context identifier) | `acdp://<authority>/<uuid>` where `<authority>` is a DNS hostname identifying the origin registry and `<uuid>` is a UUID v4 [RFC 9562]. | §5.5 |
| **`lineage_id`** | `lin:<algorithm>:<digest>`. v0.1.0 form: `lin:sha256:<64-lowercase-hex>`. | §5.6 |
| **`agent_id`** | A Decentralized Identifier [DID-CORE]. v0.1.0 producers MUST use `did:web` so that any conformant registry can resolve their keys via §5.11. *(0.2.0)* `agent_id` MAY additionally be `did:key` (grammar `did:key:z<base58btc>`) when the registry advertises `"did:key"` in `supported_did_methods` (RFC-ACDP-0007 §3.1); resolution is pure per §5.11.1. | RFC-ACDP-0002 |

The `ctx_id` is assigned by the registry at publish time; producers MUST NOT supply a `ctx_id` in publish requests. The corresponding URI scheme `acdp` is registered in §11.

#### DID method scope by field (NORMATIVE)

The `did:web` requirement of v0.1.0 applies to fields the registry must resolve to a key, not to every DID-typed field on a body. The following table is normative for v0.1.0; the schema's `did` definition (`schemas/json/acdp-common.schema.json#/$defs/did`) is intentionally loose so that `contributors[]` and `audience[]` can carry other methods today, even while `agent_id` and `signature.key_id` are constrained to `did:web` by this section.

| Field | v0.1.0 requirement | Rationale |
|---|---|---|
| `agent_id` | MUST be `did:web`. | The signing agent must be resolvable by every conformant registry via the §5.11 algorithm. Schema-loose is by design; the registry enforces the method. |
| `signature.key_id` (DID portion, before `#`) | MUST be `did:web`, and MUST equal `agent_id`. | The §5.11 resolver fetches the DID document for this DID. Mismatch with `agent_id` is rejected as `key_not_authorized` (RFC-ACDP-0003 §2.1 step 6). |
| `contributors[]` | SHOULD be `did:web`; other DID methods are permitted. | Attribution only — v0.1.0 does not resolve contributor keys. A producer crediting a `did:key`-only collaborator MUST NOT have its publish rejected for that reason. |
| `audience[]` | MAY be any DID method. | Authorization list — registries match the requester's authenticated DID against `audience[]` as opaque strings (RFC-ACDP-0008 §4.5). No key resolution is performed. |
| `body.agent_id` of an ancestor in `derived_from` | Same rule as the ancestor's own `agent_id` (i.e. for v0.1.0 ancestors, `did:web`). | A consumer following the ancestor link verifies the ancestor's signature, which requires resolving its key via §5.11. |

Registries MUST reject a publish whose `agent_id` is not `did:web` with `schema_violation` (preferred — caught at request validation) or with `key_not_authorized` if discovered later in the §5.11 pipeline. Registries MUST NOT reject a publish solely because `contributors[]` includes a non-`did:web` entry. Conformance fixtures `pub-008`, `pub-009`, and `pub-010` pin these behaviors.

#### `did:key` producers *(0.2.0, NORMATIVE)*

ACDP 0.2.0 adds `did:key` as a second supported producer DID method:

- **Grammar.** `did:key:z<base58btc>`, where `z<base58btc>` is the multibase base58-btc encoding of a multicodec-prefixed public key (§5.11.1). Only the `z` (base58-btc) multibase prefix is valid.
- **`signature.key_id` form.** `did:key:z<mb>#z<mb>` — per the W3C `did:key` convention, the fragment equals the key identifier, which equals the DID's method-specific identifier. A `did:key` `key_id` whose fragment does not byte-equal the DID's key part MUST be rejected with `key_resolution_failed`.
- **Gating.** A registry accepts `did:key` publishes only when it advertises `"did:key"` in `supported_did_methods`. A registry that does not advertise it MUST reject a `did:key` publish with `key_resolution_failed` (permanent, HTTP 400 — RFC-ACDP-0007 §3.1). Fixture `dk-003` pins this code choice.
- **`registry_did` stays `did:web`-only.** Registries are DNS-bound servers; the registry-identity binding of RFC-ACDP-0006 §4.1 and RFC-ACDP-0010 §8 step 2 depends on the DID ↔ authority equality that only `did:web` provides. This does not change in 0.2.0.
- The same rule extends to the §5.4 scope table: the `agent_id` and `signature.key_id` rows read "`did:web`, or *(0.2.0)* `did:key` where advertised"; the `contributors[]`, `audience[]`, and ancestor rows are unchanged.

**Tradeoff (NORMATIVE note).** `did:key` has no rotation: a new key is a new identity, and `supersedes` requires the same `agent_id` (RFC-ACDP-0003 §3.1 step 3), so lineage continuity ends with the key. Conversely, `did:key` contexts are immune to the historical-key problem (RFC-ACDP-0008 §9.3) and to domain-lapse hijacking — verification outlives the producer's infrastructure, because the DID *is* the key. Producers choose per identity; Appendix B describes the recommended two-tier pattern.

### 5.5 Context-ID assignment

A registry assigns `ctx_id` at publish time as `acdp://<own_authority>/<freshly_generated_uuidv4>`. The authority component MUST equal the DNS hostname declared in the registry's capabilities document (RFC-ACDP-0007). Two registries MUST NOT share an authority.

### 5.6 Lineage Identifier Derivation

A context's `lineage_id` MUST be derived deterministically from the `ctx_id` of the lineage's first version (the version with `supersedes: null`):

```
lineage_id = "lin:sha256:" + lowercase_hex(SHA-256(first_version_ctx_id))
```

The hash input is the UTF-8 encoding of the `ctx_id` string. The `sha256` algorithm prefix is fixed in v0.1.0; future ACDP versions MAY introduce additional algorithms (`lin:sha3-256:...`, `lin:blake3:...`) for new lineages without invalidating existing v0.1.0 `lin:sha256:` identifiers. Consumers MUST NOT compare lineage_ids across different algorithm prefixes.

For first versions, the registry computes `lineage_id` from the `ctx_id` it just assigned. For subsequent versions, the registry MUST walk back through `supersedes` references to find the version 1 context and apply the same formula.

A producer publishing a first version (`supersedes: null`) MUST NOT include `lineage_id` in the publish request — the producer cannot know the registry-assigned `ctx_id` at signing time, so any supplied value would be a guess. Registries MUST reject first-version requests containing `lineage_id` with `schema_violation` (RFC-ACDP-0003 §2.2).

A producer publishing a subsequent version (`supersedes != null`) MAY include `lineage_id` for self-verification. If supplied, the registry MUST verify it matches the deterministically-derived value and MUST reject mismatches with `superseded_target` (`details.reason = "lineage_mismatch"`, RFC-ACDP-0003 §3.1 step 4).

The `lin-001` conformance fixture is the dedicated golden-vector set for this derivation; `can-001` additionally cross-checks the same vectors alongside the JCS canonicalization vectors, and `sig-001` re-derives the lineage from its registry-assigned `ctx_id`. All three MUST agree byte-for-byte. The bundled conformance runner (`scripts/conformance-runner.py`) executes `lin-*` and `can-*` lineage vectors directly.

#### 5.6.1 Lineage walk failure

If, while walking back through `supersedes` references to compute `lineage_id` for a subsequent-version publish, the registry cannot retrieve an intermediate context, the registry MUST reject the publish request with `superseded_target` (`details.reason = "lineage_walk_failed"`, HTTP 400). In v0.1.0 this most commonly means the immediate-predecessor chain is intact (RFC-ACDP-0003 §3.1 step 1 already gates the head with `details.reason = "not_found"` if absent) but a deeper intermediate is missing — for example because of out-of-band administrative deletion (which ACDP itself forbids). Cross-registry intermediate cases cannot arise in v0.1.0 because cross-registry supersession is rejected at §3.1 step 2 with `cross_registry_supersession_unsupported` before any walk runs; the trigger is reserved here for forward compatibility with a future version's cross-registry supersession (RFC-ACDP-0009 §2.8). The error envelope SHOULD include the failing intermediate `ctx_id` in `details` for debuggability:

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

#### 5.6.2 Lineage anchoring *(0.2.0, NORMATIVE)*

A registry MAY validate a version-(N+1) publish against the **persisted** `lineage_id` and `version` of the immediate predecessor (the `supersedes` target) instead of re-walking the full `supersedes` chain to version 1 on every publish. The registry's own storage is trusted for this purpose: it computed and persisted the predecessor's `lineage_id` under the same §5.6 derivation when the predecessor was published, so `lineage_id(new) = lineage_id(predecessor)` and `version(new) = version(predecessor) + 1` are sufficient publish-time checks. Anchoring is exactly equivalent to the full walk by induction over §5.6 and RFC-ACDP-0003 §3.1, and it removes the `lineage_walk_failed` liveness failure mode in which a deep intermediate is unretrievable while the immediate predecessor exists.

Registries using anchoring SHOULD run the full walk-back as a periodic or on-demand **integrity audit** (detecting storage corruption or out-of-band mutation), not as a publish-path dependency. A registry that does walk the full chain at publish time remains conformant; `lineage_walk_failed` (§5.6.1) then remains its rejection signal for an unretrievable intermediate. The derivation formula and the end-to-end verifiability of `lineage_id` are unchanged — consumers can always audit a lineage by walking it themselves.

### 5.7 Content Hash

The `content_hash` field of a body is the SHA-256 [FIPS 180-4] digest of the JCS-canonicalized **ProducerContent** (§2), encoded as the literal string `sha256:` followed by 64 lowercase hexadecimal characters. ProducerContent is the publish request body with the following fields removed:

- `content_hash` itself (a field cannot contain its own hash);
- `signature` (the signature is over the hash, so cannot be in the hashed input);
- `ctx_id`, `lineage_id`, `origin_registry`, `created_at` (registry-assigned, not known to the producer at signing time).

All other fields present in the publish request are included in the hash input. The producer computes `content_hash` over this reduced object, then sets the `content_hash` and `signature` fields on the request before submission.

The exclusion list permits the producer to compute `content_hash` and sign before the registry assigns identifiers. The producer commits to the content; the registry separately binds the identifiers.

Implementations MUST produce identical `content_hash` values for the same body content across all conforming implementations. Test vectors are provided in the conformance fixtures.

#### Exclusion-set registry (NORMATIVE)

The table below is the authoritative, versioned list of fields excluded from ProducerContent. It is the single source of truth for the §5.7 exclusion set; the prose above and the conformance fixtures (`can-008`, `can-009`) are derived from it.

| Field | Location | Included in ProducerContent? | Introduced in | Rationale |
|---|---|---|---|---|
| `content_hash` | body | No | 0.1.0 | Self-referential — a field cannot contain its own hash. |
| `signature` | body | No | 0.1.0 | The signature covers (and therefore cannot be covered by) the hash. |
| `ctx_id` | body | No | 0.1.0 | Registry-assigned at publish time (§5.5). Not known to the producer at signing time. |
| `lineage_id` | body | No | 0.1.0 | Registry-assigned at publish time (§5.6). |
| `origin_registry` | body | No | 0.1.0 | Registry-assigned at publish time. |
| `created_at` | body | No | 0.1.0 | Registry-assigned at publish time (§5.3). |
| `registry_state` | top-level, outside body | N/A — outside body | 0.1.0 | Mutable, registry-derived state (RFC-ACDP-0004 §4). Never part of the body and therefore never an input to `content_hash`. |
| `registry_receipt` | top-level, outside body | N/A — outside body | reserved | Reserved by RFC-ACDP-0009 §2.7 for future registry-binding receipts. v0.1.0 consumers MUST ignore this field if present. |

**Unknown body fields (NORMATIVE).** Body fields not listed in this table AND not in the published body schema (`schemas/json/acdp-context-body.schema.json`) are **included** in ProducerContent by default. This is the forward-compatibility guarantee from §6 made concrete: future producer-controlled fields added in minor versions are automatically covered by the producer signature without an exclusion-set update. The fixture `can-008-body-with-unknown-producer-field.json` is the positive case (an unknown producer field MUST be retained for hashing).

**Closed-by-name exclusion (NORMATIVE).** Conversely, a field whose name appears in the table above is excluded by name even when its value is unexpected or its presence is irregular. The fixture `can-009-body-with-unknown-excluded-field.json` is the negative case: a body that carries a non-standard value in `origin_registry` (for example, set by a malicious or misbehaving producer to spoof another registry) MUST still be excluded by name from ProducerContent at the consumer's hash-recomputation step — the producer signature never bound `origin_registry`, so its value is registry-honesty territory regardless (§5.9, RFC-ACDP-0008 §9.1).

**Exclusion-set evolution (NORMATIVE).** Implementations MUST NOT expand the exclusion set without a spec version change. Adding a row to the table above — or treating a field as excluded in any implementation when this table does not list it — is a non-conformant deviation: it would silently break signature verification across the ecosystem because consumers and registries would disagree on what bytes the producer signed. Future versions of ACDP that add a registry-assigned field MUST advertise the new exclusion via the `acdp_version` mechanism (§6, `body.acdp_version`) so that downstream verifiers can apply the correct exclusion set for the body's declared version.

#### Hash verification over raw JSON (REQUIRED for forward compatibility)

Consumers and registries MUST recompute `content_hash` from the raw received JSON object — not from a lossy typed deserialization of it — unless the typed deserialization provably preserves every unknown field byte-for-byte.

The hazard. ACDP body extensibility is forward-compatible via additive producer-controlled fields (§6). A v0.1 producer adding a new optional field (e.g. `priority`) signs the JCS canonicalization of an object that includes it. A v0.1.0 consumer that deserializes the body into a typed `Body` struct without an unknown-field catch-all will silently drop `priority`; recomputing `content_hash` from the typed struct then yields a different hash than the producer signed, and the body fails verification with a false `hash_mismatch`. The error appears at exactly the moment minor-version evolution should be invisible to existing consumers.

Required implementation pattern. To verify a received body:

1. Parse the wire bytes into a structure that preserves all keys and their original ordering only if needed by your canonicalizer (most JCS libraries re-sort, so order at parse time does not matter — but field presence does). Examples: `serde_json::Value` in Rust, `json.loads` into `dict[str, Any]` in Python, `JSON.parse` in TypeScript, `interface{}` / `map[string]json.RawMessage` in Go.
2. Remove the four registry-assigned identity fields and the two integrity fields (the §5.7 exclusion set: `ctx_id`, `lineage_id`, `origin_registry`, `created_at`, `content_hash`, `signature`).
3. JCS-canonicalize the resulting object and SHA-256 the canonical bytes; compare against `body.content_hash`.
4. Only after the hash matches, verify the signature over the ASCII bytes of `body.content_hash` (per §5.8).
5. Only after both checks pass, deserialize into a typed model for application use.

Implementations that prefer to deserialize into a typed model first (for ergonomics) MUST guarantee that the typed model preserves unknown producer-controlled fields. Concrete patterns:

- **Rust (serde):** add `#[serde(flatten)] pub extensions: serde_json::Map<String, serde_json::Value>` to capture unknown keys; do NOT use `#[serde(deny_unknown_fields)]` on `Body`. The flattened map MUST be re-emitted in canonicalization.
- **Python (pydantic v2):** set `model_config = ConfigDict(extra="allow")` on the `Body` model, OR keep `dict[str, Any]` for unknown keys.
- **TypeScript:** define `Body` as `{ … known fields …, [key: string]: unknown }` or use a passthrough decoder (zod's `.passthrough()`).
- **Go:** unmarshal into `map[string]json.RawMessage` for the verification path; the typed `Body` struct (used by application code) is built from the verified map.

Discarding unknown fields before hash recomputation is a CONFORMANCE FAILURE. The fixtures `can-008-body-with-unknown-producer-field.json` (positive: a producer-added unknown field is part of the hash and MUST be retained) and `can-009-body-with-unknown-excluded-field.json` (negative: a field whose name is in the exclusion set is excluded by name regardless of whether the v0.1.0 consumer recognizes it) pin the rule.

### 5.8 Signature

The `signature` field of a body is a JSON object:

| Field | Type | Required | Description |
|---|---|---|---|
| `algorithm` | string | Yes | Signature algorithm identifier. See §5.10. |
| `key_id` | string | Yes | DID URL identifying the signing key. |
| `value` | string | Yes | Base64-encoded signature bytes. |

The signature value is computed over the bytes of the full `content_hash` string — that is, the ASCII bytes of `sha256:` followed by the 64 lowercase hex characters. Implementations MUST NOT sign the raw hash bytes alone.

Registries MUST verify the signature at publish time. A context whose signature does not verify MUST be rejected with the `invalid_signature` error code (RFC-ACDP-0007).

**Key generation (NORMATIVE).** Producers MUST generate Ed25519 and ECDSA-P256 key pairs using a cryptographically secure random number generator drawing from the OS entropy pool. On Unix-like systems this is `getrandom(2)` (Linux ≥ 3.17, macOS ≥ 10.12) or a fresh read from `/dev/urandom`; on Windows this is `BCryptGenRandom` (or the legacy `CryptGenRandom`); managed runtimes MUST use the platform's secure-random API (`crypto.getRandomValues` / `crypto.randomBytes` in JS, `secrets.token_bytes` / `os.urandom` in Python, `crypto/rand.Read` in Go, `ring::rand::SystemRandom` or `OsRng` in Rust). Implementations MUST NOT use:

- all-zero seeds (every keypair would be the same and publicly known);
- timestamp-based seeds, PID-based seeds, or any seed derived from low-entropy inputs;
- the seed `0x00..01` (the sig-002 test scalar) or any other test-vector seed published in this specification — these are TEST-ONLY and publicly known;
- the language's default non-cryptographic PRNG (`rand` package in Rust, `random` in Python, `math/rand` in Go) — these are deterministic from a low-entropy seed and signatures generated under them are forgeable;
- a single global seed re-derived per process without re-seeding from the OS — long-running processes that don't re-seed are vulnerable after sufficient state observation.

Recommended pattern: a library-provided `SigningKey::generate()` (or language equivalent) that invokes the OS RNG directly and returns a fresh keypair. `SigningKey::from_bytes` (or equivalent) SHOULD be reserved for loading key material already stored securely; it MUST NOT be the path users reach for when they want a "new" key. Library authors SHOULD make this distinction visible in the API — e.g., `generate()` returns `(SigningKey, VerifyingKey)`, `from_bytes(&[u8])` is named and documented as "load existing key".

**Key storage (NORMATIVE).** Private key bytes MUST NOT be persisted in cleartext on disk, in a config file, in a `.env` file committed to source control, in a container image, in process environment variables that other processes can read (`/proc/<pid>/environ`), in container metadata services, or in cloud-function environment-variable pages. Acceptable storage: an OS keychain (macOS Keychain, Windows DPAPI, Linux Secret Service / libsecret), a hardware security module (HSM), a cloud KMS (AWS KMS, GCP KMS, Azure Key Vault, HashiCorp Vault) with the private key never leaving the boundary, or a trusted execution environment (TPM, SGX, Apple Secure Enclave). The signing operation SHOULD happen inside the boundary — the producer process holds a handle, not the bytes.

For development and CI, the same secure-storage requirement applies; ephemeral test keys generated per-CI-run and discarded at job end are acceptable, but committed test keys MUST be flagged as TEST-ONLY (as `sig-002`'s keypair is) and MUST NOT be used to sign anything that reaches a production registry. A production publish signed by a leaked, committed, or test-only key is a security incident regardless of whether the content is correct.

### 5.9 Replay, Tamper, and Impersonation Protection

ACDP's protections decompose by what the producer signature does and does not bind:

**What the producer signature binds (cryptographic protection):**

- **Body tampering** is detected by recomputing `content_hash` over the canonicalized ProducerContent (§2). Any change in any non-excluded field changes the hash; the signature will not verify.
- **Producer impersonation** of content is prevented: a third party cannot forge a signature without the producer's private key.
- **Lineage integrity**: each ancestor in `derived_from` is independently signed by its own producer.

**What the producer signature does NOT bind (registry-honesty protection):**

- `ctx_id`, `lineage_id`, `origin_registry`, and `created_at` are registry-assigned. The producer signature does not cover them. A consumer cannot cryptographically verify which registry first accepted the content, what `ctx_id` it was assigned, what lineage it belongs to, or when publication occurred. These facts rely on **registry honesty** in v0.1.0.

A malicious or compromised registry could republish a producer's signed content under a different `ctx_id` or `origin_registry` (the signature would still verify), or backdate `created_at`. See RFC-ACDP-0008 §9.1 for the full discussion and §9.2 for mitigations.

*(0.2.0)* ACDP 0.2.0 introduces **registry receipts** ([RFC-ACDP-0010](RFC-ACDP-0010-registry-receipts.md), promoted from the RFC-ACDP-0009 §2.7 reservation): registry-signed attestations binding `ctx_id`, `lineage_id`, `origin_registry`, `created_at`, the body's `content_hash`, and the resolved producer-key fingerprint to the registry's DID. Where a verified receipt accompanies a response, the registry-honesty facts above become attributable and non-repudiable registry commitments (with the mint-time limitations documented in RFC-ACDP-0010 §13). Receipt-less responses retain the v0.1.0 trust model unchanged.

**Replay** at the wire level is mitigated by HTTPS transport security. ACDP itself does not specify per-request nonces — the body's content hash makes "the same body twice" content-level idempotent. Registries SHOULD implement `Idempotency-Key` (RFC-ACDP-0003 §6) for true publication-level idempotency.

Distinguish two senses of idempotency:

- **Content-level idempotency:** identical bodies produce identical `content_hash` values. This is automatic and intrinsic to ACDP.
- **Publication-level idempotency:** identical publish requests produce identical `ctx_id`s and do not create duplicate registry records. This requires the optional `Idempotency-Key` mechanism (RFC-ACDP-0003 §6).

Without `Idempotency-Key`, replaying a publish request creates a new `ctx_id` for the same content. Producers SHOULD deduplicate locally on `content_hash`.

### 5.10 Signature Algorithms

Implementations MUST support `ed25519` [RFC 8032]. Implementations MAY support additional algorithms (e.g. `ecdsa-p256`). A registry's supported algorithms MUST be declared in its capabilities document (RFC-ACDP-0007). Registries MUST reject `unsupported_algorithm` for any algorithm not in their declared list. The full algorithm vocabulary is maintained in [`registries/signature-algorithms.md`](../registries/signature-algorithms.md).

### 5.11 Key Resolution

To verify a producer signature, an implementation MUST resolve `signature.key_id` (a DID URL) to a public key. v0.1.0 mandates support for `did:web` only; producers MUST use `did:web` keys, and registries MUST resolve `did:web` keys.

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

**Testability of key resolution (NON-NORMATIVE).** Fixture-bound conformance tests for signature verification (`pub-001`, `pub-006`, the sig-* goldens) require outbound HTTPS to a DID-document host. Library users in CI environments without outbound network access — or with self-signed test infrastructure — cannot run these fixtures unless the resolver is testable offline, which in practice means many implementations silently skip them. Library authors implementing the §5.11 resolver SHOULD therefore provide one or both of:

1. **A custom-root-of-trust constructor** that accepts an additional root CA certificate (or a custom TLS verifier callback) so the resolver can be pointed at a local HTTPS server with a self-signed cert. Concrete shapes by language: `WebResolver::with_root_cert(cert_der: &[u8])` in Rust, `WebResolver(root_ca=cert_bytes)` in Python, `new WebResolver({ rootCAs: [cert] })` in TypeScript, `WebResolver{RootCAs: pool}` in Go.
2. **A pluggable DID-document store** that bypasses network I/O entirely — the application supplies `DidDocument`s by DID, and the resolver consults the store before any HTTP fetch. This is the strict-offline pattern and is the only option that survives a fully air-gapped CI.

These testing surfaces MUST be guarded so they do not weaken production:

- They SHOULD be behind a test-only build flag (Rust feature `test-resolver`, Python `extras_require={"testing": [...]}`, etc.) OR be available only via a separate `testing` module that is not re-exported from the package root.
- The default production constructor MUST validate certificates against the operating system's trust store; injecting an additional root MUST be an explicit, named operation at construction time (no implicit fallback, no env var).
- Constructors that disable certificate validation entirely MUST NOT exist — a self-signed cert can be added to the trust list, but `verify=False`-equivalents have no place in the public API.

Without these surfaces, conformance testing for `pub-001` and `pub-006` requires a live network and a public DID-document host, which discourages running the fixtures at all and silently lowers ecosystem-wide assurance.

#### 5.11.1 `did:key` resolution *(0.2.0, NORMATIVE)*

`did:key` resolution is **pure**: it is a deterministic computation over the DID string itself. No network request is made, no DID document is fetched, no caching rules apply, and there is no `assertionMethod` check — the DID *is* the key, so the key is authorized by construction. The algorithm:

1. **Parse.** Split `signature.key_id` into the DID portion and the fragment. The fragment is REQUIRED and MUST byte-equal the DID's method-specific identifier (`did:key:z<mb>#z<mb>`); mismatch or absence MUST be rejected with `key_resolution_failed`. The DID portion MUST equal `body.agent_id` (`key_not_authorized` on mismatch — same as step 2 of the `did:web` algorithm).
2. **Decode multibase.** The method-specific identifier MUST begin with `z` (base58-btc). Decode the remainder with the base58-btc alphabet (`123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz`). Any other multibase prefix, or a string that does not decode, MUST be rejected with `key_resolution_failed`.
3. **Check the multicodec prefix.** The decoded bytes MUST begin with the unsigned-varint encoding of the multicodec code: `0xed 0x01` for `ed25519-pub` (code `0xed`) or `0x80 0x24` for `p256-pub` (code `0x1200` — its varint encoding is `0x80 0x24`, NOT the big-endian literal `0x12 0x00`; using the literal would reject every W3C-conformant `zDn…` P-256 did:key). Any other prefix MUST be rejected with `key_resolution_failed`.
4. **Extract the key bytes.** The bytes after the multicodec prefix are the public key: exactly 32 raw bytes for Ed25519, or exactly 33 bytes (SEC1 compressed point) for P-256, which the verifier decompresses before use. A length mismatch MUST be rejected with `key_resolution_failed`.
5. **Check algorithm consistency.** `signature.algorithm` MUST match the multicodec-implied algorithm (`ed25519` for multicodec code `0xed`, `ecdsa-p256` for multicodec code `0x1200`); mismatch MUST be rejected with `invalid_signature` (the same algorithm-binding rule as step 6 of the `did:web` algorithm).
6. **Verify the signature** over the ASCII bytes of `body.content_hash`, exactly as §5.8.

Because resolution is pure, every SSRF consideration of RFC-ACDP-0008 §4.8 is vacuous for `did:key`, verification works offline and outlives the producer's infrastructure, and the §5.11 caching guidance does not apply. The golden vector `sig-003-did-key-golden.json` pins the identity derivation, hash, and signature end-to-end; `dk-001`/`dk-002`/`dk-004` pin the multicodec, multibase, and fragment rejection rules.

**Producer key retention *(0.2.0, NORMATIVE)*.** `did:web` producers SHOULD retain rotated signing keys in their DID document's `verificationMethod` array indefinitely, removing them from `assertionMethod` only. `assertionMethod` membership is checked at **publish time** by the registry (step 5 above — unchanged); retaining the retired key in `verificationMethod` is what lets receipt-aware verifiers later verify historical contexts with the distinguishable *historically authorized (receipt-attested)* status of RFC-ACDP-0010 §10. Removing a key from `verificationMethod` entirely is the producer's compromise-revocation signal: verifiers then fail closed for bodies signed by that key, receipt or no receipt.

**Future DID methods.** A future ACDP version may add `did:jwk` and other methods. The `did:web` resolution algorithm above and the `did:key` algorithm of §5.11.1 are method-specific; other methods will be specified separately.

**v0.1.0 strict verification profile (NORMATIVE).** A verification implementation conformant with the `acdp-consumer` profile (§9.1) MUST, when verifying a v0.1.0 context (`body.acdp_version` absent or `"0.1.0"`):

1. Require `body.agent_id` and the DID portion of `signature.key_id` to be `did:web` DIDs (RFC-ACDP-0001 §5.4); reject other DID methods.
2. Run full body schema validation (`acdp-context-body.schema.json`) **before** any cryptographic step — a structurally invalid body MUST NOT reach hash recomputation or signature verification.
3. Recompute `content_hash` over ProducerContent and verify it before checking the signature (§5.7, §5.8).
4. Verify the producer signature per the resolution algorithm above.
5. Verify every embedded `data_ref.content_hash` against its decoded `embedded.content` (RFC-ACDP-0002 §6.3); on mismatch, report `data_ref_hash_mismatch` (RFC-ACDP-0007 §5).

Library authors MAY expose configuration to relax these requirements (e.g. for test environments, compatibility bridges, or future protocol versions), but any relaxed mode MUST be explicitly labeled as **non-conformant with v0.1.0** and MUST NOT be the default. The RECOMMENDED API shape is a strict default that cannot be loosened without an explicit, named opt-in — e.g. a `VerificationPolicy::strict_v0_1_0()` (Rust) / `VerificationPolicy.strict_v0_1_0()` (Python/TypeScript) constructor as the default, with any other mode reachable only through a separately-named constructor. This strict default is the `StrictV010` verification profile of §9.2. Implementations MUST document that only the strict mode is covered by the `acdp-consumer` conformance profile.

**Recommended verification report stage names (NON-NORMATIVE).** SDKs that expose a diagnostic verification report (a per-stage pass/fail breakdown) SHOULD use the following stage identifiers, so logs and telemetry are comparable across language implementations. The identifier is the snake_case form for code and config; the display name is for human-facing output.

| Stage identifier | What it covers |
|---|---|
| `schema` | Structural body validation (field presence, types, patterns). |
| `producer_content_hash` | SHA-256 recomputation over ProducerContent matches `body.content_hash`. |
| `key_binding` | The DID portion of `signature.key_id` equals `body.agent_id`. |
| `did_resolution` | The DID document was fetched and parsed successfully. |
| `assertion_method` | The verification method is referenced by the DID document's `assertionMethod`. |
| `signature` | The Ed25519 or ECDSA-P256 signature verifies against the resolved public key. |
| `embedded_data_refs` | Per-DataRef embedded-hash verification (an array of per-ref outcomes). |
| `external_data_refs` | Per-DataRef external fetch + hash verification (an array of per-ref outcomes). |
| `registry_receipt` | Registry receipt verification (RFC-ACDP-0010 §8). Absent in v0.1.0 reports; *(0.2.0)* active when a receipt accompanies the response. |

The stage vocabulary is advisory: it does not change the verification algorithm, only the names implementations SHOULD use when surfacing intermediate results. A v0.1.0 report covers `schema` through `external_data_refs`; *(0.2.0)* a receipt-aware report additionally carries `registry_receipt`, reported independently of the body verdict (RFC-ACDP-0010 §8).

---

## 6. Compatibility Model

ACDP uses a layered compatibility model:

- **Registry protocol version** is advertised in the registry capabilities document as `acdp_version` (e.g. `0.1.0`). It tells consumers which protocol surface the registry implements.
- **Body protocol version** is advertised optionally inside each body as `body.acdp_version`. The body field is producer-signed and bound to the body's `content_hash`. An absent `body.acdp_version` MUST be treated as `0.1.0`, the inaugural release. Producers SHOULD set the field explicitly so verifiers can unambiguously apply the correct exclusion set (§5.7) and algorithm vocabulary for the body's declared version, especially as future versions evolve them.
- **Body extensibility** is forward-compatible only via additive fields. Breaking body changes require a new protocol version, signaled by `body.acdp_version`.
- **Registry-state extensibility** is open: future versions add fields (lifecycle events, relationships, attestations); consumers MUST tolerate unknown fields in registry state. Schema enums for known fields (e.g. `status`) use open string patterns so unknown values do not fail validation.

**`acdp_version` and the content hash (NORMATIVE).** Producers SHOULD include `acdp_version: "0.1.0"` explicitly in every published body, even though the protocol treats its absence as equivalent to `0.1.0`. Explicit inclusion aids debugging, log analysis, and future version negotiation, and removes any ambiguity about which exclusion set (§5.7) and algorithm vocabulary a verifier should apply.

***(0.2.0)* Explicit `acdp_version` is mandatory for 0.2.0 producers (NORMATIVE).** A publish request authored under acdp/0.2.0 MUST include `acdp_version` explicitly (e.g. `"acdp_version": "0.2.0"`). Registries continue accepting the omitted form from 0.1.0 producers indefinitely — there is no retroactive hash change, and both forms remain valid on the wire (an omitted field is still *interpreted* as `0.1.0`). The MUST removes the omitted-vs-explicit hash ambiguity for everything minted going forward: a 0.2.0 verifier always knows which version's exclusion set and vocabulary the producer committed to, because the commitment is inside the signed bytes. The fixture `can-012-divergence-corpus.json` pins the omitted, explicit-`"0.1.0"`, and explicit-`"0.2.0"` hashes as three distinct preimages, and 0.2.0 SDK builders MUST default to emitting the field (the §6 omission default below is no longer available to 0.2.0 builders).

Consumers, verifiers, and registries MUST NOT inject a default `acdp_version` value into a body before recomputing `content_hash`. The hash is computed over the body exactly as received (§5.7, "Hash verification over raw JSON"); adding a synthetic `acdp_version` field — or any other field — before hashing produces a different hash from the one the producer signed and raises a false `hash_mismatch`. A body that omits `acdp_version` MUST be hashed without it; a body that includes it MUST be hashed with it. The default-to-`0.1.0` rule above governs the *interpretation* of an absent field, never a *mutation* of the body: absence is read as `0.1.0`, but the absent field is never materialized.

**SDK default behavior guidance.** For SDKs that auto-construct `PublishRequest` objects via a builder, the RECOMMENDED default is to **emit `acdp_version: "0.1.0"` explicitly**. This makes the protocol version visible in every produced request without the producer having to call an explicit setter, and aligns the builder's default with the producer SHOULD above.

A 0.1.0-targeting SDK MAY instead ship with the omission default — emitting no `acdp_version` field — for golden-vector compatibility or other reasons *(0.2.0: this option is closed for 0.2.0 builders, which MUST emit the field — see the NORMATIVE paragraph above)* (an absent field and `"0.1.0"` are wire-equivalent for consumers: the default-to-`0.1.0` interpretation rule makes them semantically identical, though they produce different `content_hash` values because the bytes differ). An SDK that takes the omission default MUST:

1. Document the choice prominently — in the builder's API documentation and in the SDK README.
2. Provide a one-line override that emits the version explicitly (e.g. `.acdp_version(ACDP_VERSION)`).
3. State that absent and explicit `"0.1.0"` are interpreted identically by conformant consumers, while noting they are distinct byte sequences and therefore distinct `content_hash` preimages — a producer MUST pick one and sign over exactly what it emits.

Whichever default an SDK chooses, it MUST NOT mutate a *received* body to add or normalize `acdp_version` before hash recomputation — that is the verifier-side prohibition in the NORMATIVE paragraph above.

Major protocol version mismatches are not compatible. Minor versions are expected to be backward compatible. Consumers receiving an unknown `acdp_version` (in capabilities or in a body) SHOULD treat it as a higher version and degrade gracefully, using only operations defined in the version they understand.

---

## 7. Transport

ACDP operations are HTTP-based with JSON request and response bodies, content type `application/acdp+json`. Operations are defined in:

- RFC-ACDP-0003 — `POST /contexts`, supersession.
- RFC-ACDP-0004 — `GET /contexts/{ctx_id}`, `GET /contexts/{ctx_id}/body`, `GET /lineages/{lineage_id}`, `GET /lineages/{lineage_id}/current`.
- RFC-ACDP-0005 — `GET /contexts/search`.
- RFC-ACDP-0007 — `GET /.well-known/acdp.json`.

ACDP v0.1.0 is JSON-only. Binary transport bindings are out of scope for this version and MAY be specified in a future release.

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
3. Treat `status: superseded` and `status: expired` as signals that a context's conclusions may not be current. *(0.3.0)* Treat `status: retracted` as a formal withdrawal — a stronger non-reliance signal than either (RFC-ACDP-0013 §7).
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
- Apply SSRF protections when dereferencing any producer-controlled URL: producer `did:web` resolution during signature verification (RFC-ACDP-0008 §4.8) and external `data_refs[].location` fetches (RFC-ACDP-0008 §4.9).
- Apply visibility rules per RFC-ACDP-0008 §4.5 when retrieving (do not assume a registry's results are scoped on their behalf — verify locally where possible).
- Tolerate unknown fields in body and registry state.

There is no producer-only profile: producers MUST be able to verify their own publications, which requires the same cryptographic core as a consumer.

#### `acdp-registry-receipts` *(0.2.0)*

Adds registry receipts. Implementations MUST:

- Be `acdp-registry-core` conformant and advertise `acdp_version` ≥ `0.2.0`.
- Mint, persist, and serve receipts per RFC-ACDP-0010 §4–§7 (publish response and full retrieval; never on the body-only endpoint; always — there is no degraded mode).
- Apply the receipt-key lifecycle of RFC-ACDP-0010 §9.
- Pass the receipt conformance fixtures (`rcpt-001..004`, `fp-001`, `rot-001`; plus `fed-009` when `acdp-registry-federated` is also advertised).

Receipt-aware consumers (the `acdp-consumer` profile under 0.2.0) verify receipts per RFC-ACDP-0010 §8 whenever one is present, and report the receipt verdict separately from the body verdict.

#### `acdp-registry-head-receipts` *(0.3.0)*

Adds lineage-head receipts. Implementations MUST:

- Be `acdp-registry-receipts` conformant and advertise `acdp_version` ≥ `0.3.0`.
- Mint and serve lineage-head receipts per RFC-ACDP-0011 §4–§6: a fresh receipt (registry response-time `as_of`, millisecond-truncated) on every `GET /lineages/{lineage_id}/current` response; optionally on full retrieval; never on the body-only endpoint; always — there is no degraded mode.
- Sign head receipts with the RFC-ACDP-0010 receipt signing key and construction (RFC-ACDP-0011 §5), under the RFC-ACDP-0010 §9 key lifecycle — no new key role.
- Pass the head-receipt conformance fixtures (`lhr-001..004`).

Head-receipt-aware consumers verify lineage-head receipts per RFC-ACDP-0011 §7 whenever they rely on one, and report the head-receipt verdict (and `as_of` freshness policy) separately from the body and context-receipt verdicts.

#### `acdp-registry-lifecycle` *(0.3.0)*

Adds lifecycle events and retraction (RFC-ACDP-0013). OPTIONAL — permanence-only registries remain fully conformant without it. Implementations MUST:

- Be `acdp-registry-core` conformant and advertise `acdp_version` ≥ `0.3.0`.
- Implement `POST /contexts/{ctx_id}/retract` and `POST /contexts/{ctx_id}/republish` per RFC-ACDP-0013 §6 (visibility-first resolution, producer-signature authentication with the same `agent_id` rule as supersession, `immutable_field` on body-mutation attempts, `invalid_lifecycle_transition` on state conflicts).
- Maintain `registry_state.lifecycle_events` as a closed-schema, append-only, verbatim-preserved array per RFC-ACDP-0013 §4, and derive `status` with the RFC-ACDP-0013 §7.2 precedence (`retracted` > `superseded` > `expired`).
- Keep retracted bodies retrievable (mark-not-delete), exclude retracted contexts from default search (with `acdp-registry-discovery`), and never serve a retracted version as a lineage head per RFC-ACDP-0013 §8 (with `acdp-registry-head-receipts`: never mint a head receipt naming one).
- Pass the lifecycle conformance fixtures (`lc-001..003`).

Registries that do not advertise the profile MUST return `not_implemented` on the lifecycle endpoints and MUST NOT emit `lifecycle_events`, the `retracted` status, or the 0.3.0 lifecycle error codes.

There is no profile for RFC-ACDP-0014 (producer key revocation) — deliberately: a revocation is an ordinary context (type `key-revocation`) carried entirely by existing surfaces, with the registry-side validation bound to `acdp_version` ≥ `0.3.0` and the consumer semantics bound to `acdp-consumer` (RFC-ACDP-0014 §10).

### 9.2 Verification profile names (RECOMMENDED)

v0.1.0 verification is always strict for any conformance claim — §5.11 ("v0.1.0 strict verification profile") defines the strict pipeline and requires that it be the non-loosenable default. SDKs MAY additionally expose relaxed or diagnostic verification modes for debugging and test harnesses. When they do, they SHOULD use the following identifiers so documentation, logs, and error messages are consistent across language implementations:

| Profile name | What it verifies | Conformant for v0.1.0? |
|---|---|---|
| `StrictV010` | The full §5.11 strict pipeline: schema validation, `content_hash` recomputation, `did:web` resolution, signature verification, and embedded `data_ref.content_hash` verification. Returns on the first failure. | **Yes** — the only mode covered by the `acdp-consumer` conformance profile. |
| `Diagnostic` | Runs every strict-pipeline stage but records each stage's outcome rather than returning on the first failure, producing a per-stage report (the §5.11 "verification report stage names"). | **No** — debugging only. A `Diagnostic` run that reports any stage failure MUST be treated as an overall verification failure. |
| `UnsafeForTests` | May skip DID resolution, signature verification, or schema validation (e.g. to exercise fixtures offline). | **No** — test harness only. |

`StrictV010` is the profile-name spelling of the §5.11 strict policy; the two refer to the same behavior. SDKs MUST NOT expose `Diagnostic` or `UnsafeForTests` as default behavior — the default constructor MUST be `StrictV010`, reachable without opt-in, and any weaker mode MUST require an explicit, separately-named opt-in (§5.11). If an SDK offers a `VerificationPolicy` type, any policy that weakens a strict-mode requirement MUST be documented as **non-conformant with v0.1.0**, and a verification result produced under it MUST NOT be presented as a conformant verification.

---

## 10. Security Considerations

See [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md) for the full threat model. Implementations MUST use a cryptographically secure RNG for UUIDs, store private keys in secure storage, and validate all inputs against the JSON Schemas before processing.

---

## 11. IANA Considerations

### 11.1 URI Scheme Registration

This document requests provisional registration of the `acdp` URI scheme:

- **Scheme name:** `acdp`
- **Status:** Provisional
- **Applications/protocols that use this scheme:** Agent Context Distribution Protocol (ACDP)
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
- [RFC-ACDP-0010 Registry Receipts](RFC-ACDP-0010-registry-receipts.md) *(0.2.0)*

---

## Appendix A. SDK implementers' hash-divergence checklist *(0.2.0, NON-NORMATIVE)*

Cross-implementation `content_hash` divergence is the most common ACDP implementation bug class: two conformant-looking implementations silently compute different hashes for the same logical content, and every downstream signature check fails with a false `hash_mismatch`. This appendix enumerates every known divergence source with the conformance fixture that pins it. Together these fixtures form the **divergence corpus**; an SDK MUST pass all of them before claiming conformance, and SHOULD wire them into CI as a single suite.

| # | Divergence source | What goes wrong | Fixture |
|---|---|---|---|
| 1 | **Timestamp precision** — microsecond/nanosecond timestamps from default clock APIs | The hash binds the serialized bytes, not the logical instant; `…15.123456789Z` ≠ `…15.123Z`. Producers MUST truncate to milliseconds (§5.3) or reject higher precision; both the divergent and post-truncation hashes are pinned. | `can-006` (nanosecond), `can-012` (microsecond) |
| 2 | **Registry `created_at` emission** — registry-side clock precision | Same rule on the registry path; floor-truncate to milliseconds. | `can-007` |
| 3 | **Negative zero** — `-0.0` preserved by the serializer | RFC 8785 §3.2.2.3 normalizes `-0.0` to `0`; Python stdlib `json.dumps` does not (§5.2). | `can-001`, `can-011` |
| 4 | **Numeric boundaries** — `1e21` exponent switch, `1e-7`, 2^53 integer exactness, IEEE 754 extremes | A non-ECMAScript number formatter diverges at the exponential-notation boundaries. | `can-011` |
| 5 | **Empty vs absent** — `"tags": []` vs no `tags` key | Distinct bytes, distinct hashes; an SDK that "helpfully" materializes empty collections changes the hash. | `can-005` |
| 6 | **Null vs absent vs empty object** — `"metadata": {"note": null}` vs `"metadata": {}` vs absent | Three distinct preimages. Serializers that strip null-valued members, or builders that inject empty objects, diverge. | `can-012` |
| 7 | **Non-ASCII UTF-8** — precomposed vs escaped Unicode | JCS emits raw UTF-8 (no `\uXXXX` escaping of non-ASCII); `ensure_ascii`-style defaults diverge. | `can-002` |
| 8 | **Unknown producer fields dropped** — typed deserialization without a catch-all | The §5.7 raw-JSON rule: unknown body fields are part of the preimage and MUST be retained. | `can-008` (body root), `can-010` (DataRef) |
| 9 | **Exclusion set applied by type, not by name** | The §5.7 exclusion set is stripped by field name from the raw object, even for irregular values. | `can-009` |
| 10 | **`acdp_version` omitted vs explicit** | Absent and explicit `"0.1.0"` are semantically identical but byte-distinct preimages; injecting or stripping the field on either side breaks the hash. 0.2.0 producers MUST emit it (§6). | `can-012` |
| 11 | **DataRef open root / closed `embedded`** — unknown fields inside `data_refs[]` | The DataRef root is open (retain unknowns in the hash); the `embedded` sub-object is closed (reject unknowns). | `can-010`, `schema-003` |
| 12 | **Signing-input framing** — signing raw digest bytes or unprefixed hex | The signature input is the ASCII bytes of the full `sha256:<hex>` string (§5.8); receipt signing reuses the identical framing (RFC-ACDP-0010 §5). | `sig-001`, `sig-002`, `sig-003`, `rcpt-001` |
| 13 | **Key-fingerprint encoding** — fingerprinting SPKI/multibase/JWK instead of raw key bytes | `key_fingerprint` is SHA-256 over the 32-byte raw Ed25519 key or 33-byte SEC1-compressed P-256 point, nothing else (RFC-ACDP-0010 §6). | `fp-001` |

Rows 1–11 are hash-preimage divergences; rows 12–13 are signing-layer divergences with the same blast radius. When adding a new `can-*`/`sig-*`/`rcpt-*` vector, compute `canonical_form` and the digests with the reference `jcs` library — never by hand (the runner byte-compares against them).

---

## Appendix B. Two-tier producer identity pattern *(0.2.0, NON-NORMATIVE)*

`did:web` and `did:key` producers make opposite tradeoffs (§5.4): `did:web` supports rotation and human-meaningful, organization-anchored identity but makes every verification — forever — depend on the producer's domain resolving; `did:key` verification is pure and outlives the producer's infrastructure, but the key *is* the identity, so there is no rotation and lineage continuity ends with the key.

The recommended deployment pattern is **two-tier**:

- **Organization anchors on `did:web`.** Long-lived organizational producer identities (`did:web:agents.example.com:research-bot`) use `did:web`: they need rotation, are operationally tied to the org's domain anyway, and benefit from the receipt-attested historical-key path (RFC-ACDP-0010 §10) when keys rotate.
- **Ephemeral and archival producers on `did:key`.** Short-lived workers (one pipeline run, one experiment) and archival publications meant to be verifiable decades out use `did:key`: no DID-document hosting, no domain-lapse hijacking risk, no historical-key problem — anyone holding the body can verify it offline forever.
- **Link the tiers with `derived_from`.** An ephemeral `did:key` worker's outputs reference the org anchor's contexts via `derived_from` (and the org credits the worker in `contributors`, which permits any DID method). The org's `did:web` signature on the anchoring context is the organizational endorsement; the `did:key` signature on the leaf is the imperishable integrity seal.

Anti-patterns: using `did:key` for an identity that will need rotation (rotation = new identity, broken lineage); using `did:web` for archival content whose domain may lapse before the content stops mattering; sharing one `did:key` across workers (the DID is the key — sharing the key is sharing the identity).
