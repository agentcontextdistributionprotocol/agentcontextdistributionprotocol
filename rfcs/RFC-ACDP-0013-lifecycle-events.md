# RFC-ACDP-0013
# Agent Context Distribution Protocol (ACDP) — Lifecycle Events & Retraction

**Document:** RFC-ACDP-0013
**Version:** 0.3.0-draft
**Status:** Community Standards Track (Draft)

This RFC specifies **lifecycle events**: a signed, append-only event mechanism in registry state through which a producer (or, in the policy/legal case, a registry) formally **retracts** a published context — and, if warranted, later reverses the retraction. It promotes the RFC-ACDP-0009 §2.1 reservation to a full normative specification, activating the reserved `lifecycle_events` registry-state field, the reserved `retracted` status value (RFC-ACDP-0004 §4.1), and the reserved `immutable_field` error code (RFC-ACDP-0007 §5). It depends on RFC-ACDP-0001 (Core), RFC-ACDP-0003 (Publish & Supersession), RFC-ACDP-0004 (Retrieval & Lineage), RFC-ACDP-0005 (Discovery), and RFC-ACDP-0007 (Capabilities & Errors); it integrates with RFC-ACDP-0010/0011 (receipts) where those profiles are deployed.

Retraction is **mark-not-delete**: the body of a retracted context remains permanently retrievable, byte-identical to what its producer signed. This is the design intent recorded since v0.1.0 ([docs/non-goals.md §5, §13](../docs/non-goals.md), [docs/data-protection.md §4](../docs/data-protection.md)); this RFC makes it wire-normative. Retraction is a reputational/epistemic operation — a signed, attributable statement that a context should no longer be relied upon — never an erasure mechanism.

---

## 1. Status of This Memo

This document is a **Draft** ACDP specification targeting acdp/0.3.0. It follows the governance lifecycle in [governance/RFC-PROCESS.md](../governance/RFC-PROCESS.md) (Draft → Review → Final); per [VERSIONING.md](../VERSIONING.md) it is promoted to Final once the conformance fixtures it defines (`lc-001..003`) pass against at least two independent interoperating implementations.

This RFC promotes the RFC-ACDP-0009 §2.1 reservation. The reserved names — the `lifecycle_events` registry-state field, the `retracted` status, and the `immutable_field` error code — are adopted exactly as reserved. Nothing in this document invalidates any v0.1.0/0.2.0 body, signature, `content_hash`, or receipt; retraction never touches a body.

---

## 2. Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described in BCP 14 ([RFC 2119], [RFC 8174]) when, and only when, they appear in all capitals.

| Term | Definition |
|---|---|
| **Lifecycle event** | A JSON object appended to `registry_state.lifecycle_events` recording a formal state action on a context: who did what, when, and (optionally) why — attributable via an actor DID and, where signed, non-repudiable. |
| **Retraction** | A lifecycle event of type `retracted`: the producer (or registry) formally withdraws the context from reliance. The body remains retrievable; `status` becomes `retracted`. |
| **Republication** | A lifecycle event of type `republished`: a prior retraction is reversed. `status` re-derives per RFC-ACDP-0004 §4 as though the retraction had not occurred; the retraction and its reversal both remain in the event history. |
| **Retraction state** | Whether the context is currently retracted: determined by the **last** `retracted`/`republished` event in array order (§7). |
| **Event preimage / event hash** | The event object with the `signature` member removed, JCS-canonicalized (RFC 8785); `"sha256:" + lowercase_hex(SHA-256(preimage))` — the RFC-ACDP-0010 §5 construction applied to events. |
| **Producer-initiated event** | An event whose `actor` is the context's `body.agent_id`, submitted via the §6 endpoints and authenticated by the event signature. |
| **Registry-initiated event** | An event whose `actor` is the registry's DID (`capabilities.registry_did`), recorded by the registry itself under deployment policy or legal compulsion. |

---

## 3. Motivation

v0.1.0 chose absolute permanence: no delete, no redact, no retract (RFC-ACDP-0003 §3.3, non-goals §5). Supersession covers *correction* — publish a fixed v2 — but not *withdrawal*: a producer who discovers that a context is wrong, fraudulent, or produced under a compromised key has no protocol-level way to say "stop relying on this" without publishing a replacement, and no way at all to withdraw the head of a lineage that should not have a head. The v0.1.0 workarounds (supersession, a soft-signal derived context) leave the withdrawn conclusion carrying `status: active` forever.

RFC-ACDP-0009 §2.1 deferred retraction precisely because a casual design would lock in the wrong answers to: *who* can retract, with *what evidence*, and what happens to the record. This RFC answers them conservatively:

- **Who:** the producer (same `agent_id` authorization rule as supersession, RFC-ACDP-0003 §3.1 step 3), or the registry under deployment policy/legal compulsion — attributed distinctly.
- **What evidence:** a signed event. Producer events carry a producer signature over a JCS preimage; registry events are attributed to the registry DID and signed where the registry operates a signing key (§5). Lifecycle history is attributable and, where signed, non-repudiable — consistent with the receipts arc (RFC-ACDP-0010 §13).
- **The record:** mark-not-delete. The body stays retrievable with `status: retracted`; the event history stays visible; search stops surfacing the context by default (§8). Nothing downstream breaks: every `derived_from` chain, `content_hash`, and lineage verification still resolves ([docs/data-protection.md](../docs/data-protection.md) §1, §4).

---

## 4. Lifecycle Event Object

A lifecycle event is a JSON object with exactly the following members. The canonical schema is [`schemas/json/acdp-lifecycle-event.schema.json`](../schemas/json/acdp-lifecycle-event.schema.json) (closed: `additionalProperties: false` — every member is signed where a signature is present, so an unknown member would change the preimage; envelope extensions require a future version).

| Field | Type | Required | Description |
|---|---|---|---|
| `event_id` | string | Yes | UUID (RFC 9562 canonical form) minted by the actor. MUST be unique within the context's `lifecycle_events` array; registries MUST reject a duplicate with `schema_violation`. |
| `ctx_id` | string | Yes | The `ctx_id` of the affected context (RFC-ACDP-0001 §5.5). MUST equal the `ctx_id` of the context whose registry state carries the event — binding the event (and its signature) to exactly one context, so a signed event cannot be replayed against another context. |
| `event_type` | string | Yes | The event kind. MUST match `^[a-z][a-z0-9_]*$` and be 1–64 characters (the RFC-ACDP-0004 §4.1 pattern). The v1 vocabulary is `retracted` and `republished` (§7); the vocabulary is an open registry, [`registries/lifecycle-event-types.md`](../registries/lifecycle-event-types.md), with the unknown-event tolerance rule of §7.3. |
| `occurred_at` | string | Yes | When the actor performed the action: canonical millisecond-precision RFC 3339 UTC (RFC-ACDP-0001 §5.3). For producer-initiated events this is the producer's clock at signing time, millisecond-truncated. Registries MUST reject an `occurred_at` in the future beyond a small skew allowance (RECOMMENDED: 120 seconds, as RFC-ACDP-0011 §7 step 6) with `schema_violation`. Event **ordering** is determined by array position (§4.1), never by `occurred_at`. |
| `actor` | string | Yes | The DID of the party performing the action. For producer-initiated events, MUST equal `body.agent_id`. For registry-initiated events, MUST equal the registry's DID (`capabilities.registry_did`). |
| `reason` | string | No | Human-readable explanation (max 1024 characters). Informational; MUST NOT be used for automated decisions (the RFC-ACDP-0007 §4 `error.message` rule, applied to events). |
| `signature` | object | No (see §5) | Signature over the event hash, using the `signature` object shape of RFC-ACDP-0001 §5.8 (`algorithm`, `key_id`, `value`; closed schema). REQUIRED on producer-initiated events; SHOULD be present on registry-initiated events (§5). |

### 4.1 The `lifecycle_events` array (append-only, NORMATIVE)

`registry_state.lifecycle_events` is an OPTIONAL array of lifecycle event objects, in the order the registry accepted them. Registries advertising the `acdp-registry-lifecycle` profile (§10):

- MUST **append only**: an accepted event is added at the end of the array. Events MUST NOT be removed, reordered, or mutated — including their `signature` members. (A registry deleting or rewriting events can only be detected comparatively, by consumers who persisted earlier responses — the same honest-scope posture as RFC-ACDP-0010 §13; see §12.)
- MUST omit the field entirely (not emit `[]`) for a context with no lifecycle events, per the absent-vs-null wire convention (RFC-ACDP-0005 §2.2.1).
- MUST serve the array on full retrieval (`GET /contexts/{ctx_id}`) and on the lineage array (`GET /lineages/{lineage_id}`), inside each version's `registry_state`. The **body-only endpoint is unaffected** — `GET /contexts/{ctx_id}/body` returns the bare signed body with no registry state of any kind, preserving its immutable-cache story (RFC-ACDP-0004 §2.2).

Lifecycle events are registry state, OUTSIDE the body. They are never an input to the producer's `content_hash` (RFC-ACDP-0001 §5.7) and MUST NOT appear inside a stored body.

---

## 5. Event Signing Construction

The event signing construction **reuses RFC-ACDP-0010 §5 verbatim**; implementations MUST NOT introduce a second canonicalization or signing-input framing:

1. **Preimage.** Remove the `signature` member from the event object. JCS-canonicalize (RFC 8785) the remainder. (Every other member — including `event_id` and `ctx_id` — is covered; there is no exclusion set beyond `signature` itself.)
2. **Hash.** `event_hash = "sha256:" + lowercase_hex(SHA-256(preimage_bytes))`.
3. **Signing input.** The **ASCII bytes of the full `event_hash` string**, `sha256:` prefix included (RFC-ACDP-0001 §5.8). Implementations MUST NOT sign the raw 32-byte digest and MUST NOT sign the hex substring without the prefix.
4. **Signature.** `signature.algorithm` follows RFC-ACDP-0001 §5.10 (`ed25519` mandatory-to-implement; `ecdsa-p256` optional, IEEE 1363 r‖s wire form). `signature.value` is the base64-encoded signature bytes.

**Producer-initiated events** (§6) MUST be signed: `signature.key_id` MUST be a DID URL whose DID portion equals `actor` (= `body.agent_id`), and the registry MUST verify the signature at submission time using the RFC-ACDP-0001 §5.11 resolution algorithm (including `assertionMethod` authorization and the SSRF protections of RFC-ACDP-0008 §4.8) — the same pipeline as a publish. The signing key need not be the key that signed the original body: producers rotate keys, and a retraction is frequently *caused* by the original key's compromise (RFC-ACDP-0014). It MUST be a key currently authorized (in `assertionMethod`) for the producer's DID.

**Registry-initiated events** SHOULD be signed under a key in the registry's DID document. A registry advertising `acdp-registry-receipts` MUST sign its lifecycle events and SHOULD use the RFC-ACDP-0010 receipt signing key — the same key, plumbing, and §9 lifecycle, no new key role (the RFC-ACDP-0011 precedent). An unsigned registry event is attributable only as far as the response transport; consumers SHOULD weight it accordingly.

**Consumer verification.** Consumers SHOULD verify event signatures before treating an event as attributable evidence: recompute the preimage and hash, resolve `signature.key_id` (per §5.11 for producers; per RFC-ACDP-0010 §8 step 1 / §9 for registry receipt keys), verify over the ASCII event-hash bytes, and check `actor` binding (`key_id` DID portion = `actor`) plus `ctx_id` binding (event `ctx_id` = the retrieved context's). A producer key found in `verificationMethod` but not `assertionMethod` verifies a *historical* event with the *historically authorized* caveat of RFC-ACDP-0010 §10. An event whose signature fails verification MUST NOT be treated as evidence of the actor's intent; the event's *status effect* (§7) is registry state either way — a consumer that distrusts the registry's unverifiable event should distrust the derived `status` equally (RFC-ACDP-0004 §4: `status` is registry-attested).

---

## 6. Retraction & Republication Endpoints

Two authenticated endpoints, part of the `acdp-registry-lifecycle` profile (§10):

```
POST /contexts/{ctx_id}/retract
POST /contexts/{ctx_id}/republish
```

The request body is a JSON object with exactly one member (closed shape):

```json
{
  "event": {
    "event_id": "018f6d0a-7b2e-7c4d-9e1f-3a5b7c9d1e2f",
    "ctx_id": "acdp://registry.example.com/12345678-1234-4321-8123-123456781234",
    "event_type": "retracted",
    "occurred_at": "2026-07-04T09:15:42.000Z",
    "actor": "did:web:agents.example.com:test-producer",
    "reason": "underlying data source found to be fabricated",
    "signature": {
      "algorithm": "ed25519",
      "key_id": "did:web:agents.example.com:test-producer#key-2",
      "value": "..."
    }
  }
}
```

Registry processing, in order:

1. **Resolve and authorize the context.** Resolve `{ctx_id}` applying the visibility rules of RFC-ACDP-0004 §2.3 for the *requesting* identity; a context the requester could not retrieve returns `not_found` (HTTP 404) — lifecycle endpoints MUST NOT leak existence.
2. **Validate the envelope and event** against the closed shapes above (`schema_violation` on failure — including a duplicate `event_id`, a malformed or future `occurred_at`, an `event.ctx_id` ≠ the path `ctx_id`, or an `event_type` that does not match the endpoint: `retracted` on `/retract`, `republished` on `/republish`). A request that attempts to supply or alter **body content** through a lifecycle endpoint — a `body` member, or any envelope member named after a body field (`title`, `summary`, `metadata`, `data_refs`, …) — MUST be rejected with **`immutable_field`** (HTTP 400): bodies are immutable, and lifecycle endpoints mutate registry state only. This activates the code reserved since v0.1.0 (RFC-ACDP-0007 §5, RFC-ACDP-0009 §2.1); the distinct code exists so producers learn the *category* error, not a generic validation failure. Fixture `lc-002` pins it.
3. **Authenticate the actor.** `event.actor` MUST equal `body.agent_id`, and `event.signature` MUST be present and verify per §5. Actor mismatch returns `not_authorized` (HTTP 403) — the same rule, for the same reason, as supersession by a different `agent_id` (RFC-ACDP-0003 §3.1 step 3; delegation remains out of scope). A signature that fails verification returns `invalid_signature` (HTTP 400); key-resolution failures map exactly as at publish (`key_resolution_failed` / `key_resolution_unreachable` / `key_not_authorized`).
4. **Validate the state transition.** `retracted` is accepted only when the context's retraction state (§7) is *not retracted*; `republished` only when it *is retracted*. An invalid transition (double retract, republish of a never-retracted context) MUST be rejected with **`invalid_lifecycle_transition`** (HTTP 409 Conflict — a state conflict, like the 409 arm of `superseded_target`), registered by this RFC in [`registries/error-codes.md`](../registries/error-codes.md). The strict alternation keeps the event history minimal and meaningful and bounds its growth; per-agent rate limiting (RFC-ACDP-0008 §4.3) applies to lifecycle endpoints as to every write.
5. **Append and respond.** Append the event to `lifecycle_events` atomically with the state change, then return HTTP 200 with the **full-retrieval envelope** of RFC-ACDP-0004 §2.1 (`body` + `registry_state`, plus `registry_receipt` where the receipts profile requires it) — the caller sees the post-transition state in the shape it already knows. No new response schema is introduced.

**Retry idempotency.** A request whose `event.event_id` equals an already-appended event's `event_id` *with byte-identical event content* MUST be treated as an idempotent retry: return HTTP 200 with the current state and append nothing (the same producer-retry posture as RFC-ACDP-0003 §6 — a producer whose POST timed out after the append must not receive a spurious `invalid_lifecycle_transition`). A duplicate `event_id` with *different* content is rejected in step 2 (`schema_violation`).

**Registry-initiated events** (deployment policy, legal compulsion) do not use these endpoints; the registry records them directly, subject to the same append-only, uniqueness, transition, and shape rules, with `actor` = the registry's DID and signing per §5. A registry retraction is the protocol-visible form of "removed by policy" that [docs/data-protection.md §5](../docs/data-protection.md) demands instead of a silent 404: the body stays served, the withdrawal is explicit and attributed. (A hard delete remains an out-of-protocol override, exactly as documented there.)

Registries that do NOT advertise `acdp-registry-lifecycle` MUST return `not_implemented` (HTTP 501) on both endpoints — the same rule as `GET /contexts/search` without the discovery profile (RFC-ACDP-0007 §5) — and MUST NOT emit `lifecycle_events` or the `retracted` status.

---

## 7. Status Derivation with Retraction (NORMATIVE)

### 7.1 Retraction state

A context's **retraction state** is derived from its `lifecycle_events`: consider only events whose `event_type` is `retracted` or `republished`; the context is *retracted* if and only if the **last such event in array order** has `event_type: retracted`. (`occurred_at` never participates in this derivation; array order is the registry's accepted order and the §6 transition rule guarantees strict alternation.)

### 7.2 Precedence

RFC-ACDP-0004 §4 derives `status` from supersession and the clock, with supersession dominating expiration. This RFC extends the table with `retracted` and places it **above both**:

```
retracted  >  superseded  >  expired  >  active
```

| Value | Derivation *(0.3.0, as amended)* |
|---|---|
| `retracted` | The context's retraction state (§7.1) is *retracted* — regardless of supersession or expiry. |
| `superseded` | Not retracted; at least one other context has `supersedes` equal to this `ctx_id`. |
| `expired` | Not retracted, not superseded; `expires_at` is set and has passed. |
| `active` | None of the above. |

Rationale for retraction dominating: `status` answers "may I rely on this?", and a formal withdrawal is the strongest possible "no" — stronger than "there is a newer version" and "past its validity window". The **underlying facts remain independently visible**: supersession is still discoverable via the lineage array and any successor's `supersedes` field, expiry via the body's own signed `expires_at`, and the withdrawal itself via `lifecycle_events`. Precedence collapses only the single derived summary field, not the evidence.

Republication removes the retraction from the derivation (not from the history): `status` re-derives as `superseded`/`expired`/`active` per the unchanged RFC-ACDP-0004 §4 rules.

### 7.3 Unknown-event tolerance (NORMATIVE)

The event vocabulary is open ([`registries/lifecycle-event-types.md`](../registries/lifecycle-event-types.md)); v1 deliberately registers only `retracted` and `republished`. (A generic `status_changed` was considered and rejected for `lifecycle_events`: `status` is *derived* state (RFC-ACDP-0004 §4) and never transitions by fiat; the name remains in use only inside the reserved RFC-ACDP-0009 §2.10 webhook envelope, which is a different, notification-only vocabulary.) Consumers MUST apply the same tolerance discipline as for unknown `status` values (RFC-ACDP-0004 §4.1):

- An event whose `event_type` matches the §4 pattern but is unrecognized MUST be tolerated, MUST be preserved verbatim on re-serialization, and MUST be treated as having **no effect on retraction state** until the consumer upgrades to a version defining it.
- An event that fails the closed §4 schema (unknown member, malformed `event_type`, missing required member) is malformed registry state; consumers MUST treat the response as structurally non-conformant, exactly as a pattern-violating `status`.
- Registries MUST NOT accept producer-submitted events with unregistered `event_type` values through the §6 endpoints in 0.3.0 (`schema_violation`) — openness is for *future versions and consumers*, not a free-form producer channel.

---

## 8. Retrieval, Search, and `/current` Semantics

### 8.1 Retrieval — the body remains retrievable

Retraction is mark-not-delete. For a retracted context:

- `GET /contexts/{ctx_id}` MUST return HTTP 200 with the unchanged body, `registry_state.status: "retracted"`, and the `lifecycle_events` array. Visibility rules (RFC-ACDP-0004 §2.3) apply unchanged.
- `GET /contexts/{ctx_id}/body` is **unaffected**: the bare signed body, byte-identical, same cache headers (RFC-ACDP-0004 §2.2, §6). Retraction never changes a byte of any body.
- `GET /lineages/{lineage_id}` MUST include retracted versions (with their `retracted` status and events), subject to the per-version visibility rule of RFC-ACDP-0004 §5.4 — the lineage array is the record, and the record includes withdrawals.

This is the permanence invariant of [docs/non-goals.md §5/§13](../docs/non-goals.md) and the mark-not-delete posture of [docs/data-protection.md §4](../docs/data-protection.md): every `derived_from` chain that cites a retracted context still resolves and still verifies; what changes is the *reliance signal*, not the record. Retraction is accordingly **not** an erasure mechanism and MUST NOT be marketed as one — data-protection problems are solved at publication time (carry-by-reference), not by retraction.

### 8.2 Search — excluded by default

The RFC-ACDP-0005 §2.1 `status` filter defaults to `active`; because a retracted context's status is `retracted` (§7.2), it falls out of default searches with no new mechanism:

- Registries advertising `acdp-registry-lifecycle` (and `acdp-registry-discovery`) MUST apply the §7.2 precedence when evaluating the search `status` filter: a retracted context MUST NOT match the default (`status=active`) search, and MUST NOT match `status=superseded` or `status=expired` even where those facts also hold.
- `status=retracted` returns retracted contexts, under unchanged visibility scoping (RFC-ACDP-0005 §2.5.5, §3) — retraction never widens an audience.

Retraction therefore stops *new discovery-path reliance* immediately, including by pre-0.3.0 consumers (who never see the excluded results at all).

### 8.3 `/current` — a retracted head is not a head

`GET /lineages/{lineage_id}/current` (RFC-ACDP-0004 §5.2) is amended: the current head is the newest version that is **neither superseded nor retracted**, as visible to the requester (§5.4). Explicitly:

- A retracted version is **NEVER** served from `/current`, for the same reason a superseded version is not: it has been explicitly withdrawn from reliance, and `/current` exists to answer "what should I rely on now?". (Contrast `expired`, which remains a valid head — expiry is a soft freshness signal, not a withdrawal.)
- If every version of a lineage is superseded or retracted, the endpoint MUST return `not_found` (HTTP 404). In the common linear case this means **retracting the head takes the lineage off `/current` entirely** — every older version is superseded (RFC-ACDP-0003 §3.1), so there is nothing left to serve. This is deliberate: falling back to a superseded version would serve a context the producer already replaced, silently. A 404 tells the consumer honestly that the lineage currently has no endorsable head; the full history remains available via `GET /lineages/{lineage_id}`.
- The producer recovers the lineage by **superseding the retracted version** (publish v(N+1) with `supersedes` = the retracted head's `ctx_id` — supersession of a retracted context is permitted, and every RFC-ACDP-0003 §3.1 constraint applies unchanged) or by **republishing** it (§6). Either restores a servable head. The superseded-and-once-retracted predecessor keeps `status: retracted` per §7.2 precedence; its supersession remains visible in the lineage array.

**Interaction with lineage-head receipts (RFC-ACDP-0011).** Head selection excluding retracted versions means `head_status` in a lineage-head receipt can never be `retracted`, exactly as it can never be `superseded` — in practice it remains `active` or `expired`. RFC-ACDP-0011 §4 and the `head_status` constraint in `acdp-lineage-head-receipt.schema.json` are amended accordingly (the schema previously excluded only `superseded`; a registry advertising both profiles MUST NOT mint a receipt naming a retracted head). When `/current` returns `not_found`, no head receipt is minted — there is no head claim to attest. On full retrieval of a non-head version, the RFC-ACDP-0011 §7 step 5b self-consistency rule accepts `retracted` alongside `superseded` as the retrieved context's status when the receipt names a newer head.

### 8.4 Caching

`status` and `lifecycle_events` are mutable registry state; the short-`max-age` guidance of RFC-ACDP-0004 §6.3 already bounds how stale a consumer's view of retraction can be, and the body-only endpoint's immutable caching is untouched (§8.1). Consumers making reliance decisions SHOULD revalidate registry state at decision time rather than trusting a cached `status`.

---

## 9. Compatibility & Upgrade Path

Lifecycle events are additive registry state; they ride guarantees that v0.1.0 consumers already carry:

- **`lifecycle_events`** appears inside `registry_state`, which is open (`additionalProperties: true`) and whose unknown fields v0.1.0/0.2.0 libraries MUST already tolerate and treat as opaque (RFC-ACDP-0004 §3, RFC-ACDP-0001 §9 consumer rule 2, RFC-ACDP-0009 §3). Libraries that re-serialize or persist registry state MUST preserve the array verbatim — the same obligation they already honor for any unknown registry-state member; the field name has been reserved for this purpose since v0.1.0 (RFC-ACDP-0009 §2.1). No migration is needed.
- **`retracted`** rides the open `status` pattern (RFC-ACDP-0004 §4.1), reserved by name since v0.1.0. The documented forward-compat consequence is stated honestly: a pre-0.3.0 consumer treats an unknown `status` as `active` for functional decisions — so a pre-0.3.0 consumer that retrieves a retracted context *by `ctx_id`* will not recognize the withdrawal until upgraded. Two mitigations bound the exposure: default search exclusion (§8.2) is registry-side and protects all discovery-path consumers regardless of version, and `/current` head-exclusion (§8.3) protects all lineage-following consumers. Consumers upgrading to 0.3.0 MUST map `retracted` to a non-reliance signal (RFC-ACDP-0001 §9 consumer rule 3, as amended).
- **No parse surface changes.** No body field, JCS rule, `content_hash` semantic, signature semantic, or receipt semantic is touched. `acdp-registry-state.schema.json` gains the typed `lifecycle_events` member (open schema — additive); the error enum gains `immutable_field` and `invalid_lifecycle_transition` (additive, like `invalid_receipt` in 0.2.0); pre-0.3.0 registries MUST NOT emit either code, the `retracted` status, or `lifecycle_events`.
- **v0.1.0/0.2.0 registries** that do not advertise the profile are unaffected and remain fully conformant.

---

## 10. Capabilities, Profile, and Errors

- **Profile.** `acdp-registry-lifecycle` (registered in [`registries/profiles.md`](../registries/profiles.md); prerequisite `acdp-registry-core`). OPTIONAL — permanence-only registries remain fully conformant without it. Advertised in `capabilities.profiles`. Advertising it is the commitment to the full §6 endpoint surface, §7 status derivation, §8 retrieval/search/`/current` semantics, and §4.1 append-only discipline. Registries advertising it together with `acdp-registry-discovery` MUST implement §8.2; together with `acdp-registry-head-receipts`, §8.3's receipt interaction.
- **Version.** Registries advertising the profile MUST advertise `acdp_version` ≥ `0.3.0` in capabilities.
- **Error codes.** `immutable_field` (HTTP 400) — activated from the v0.1.0 reservation (RFC-ACDP-0007 §5, RFC-ACDP-0009 §2.1): an attempt to modify immutable body content via a lifecycle (or any future mutation) endpoint. `invalid_lifecycle_transition` (HTTP 409) — new in this RFC: the requested lifecycle transition conflicts with the context's current retraction state (§6 step 4). Both are registered in [`registries/error-codes.md`](../registries/error-codes.md) and added to the `acdp-error.schema.json` wire enum; implementations declaring `acdp_version` < `0.3.0` MUST NOT emit either.
- **No new capability field.** Profile membership in `capabilities.profiles` is the discovery signal, as for receipts.

---

## 11. Producer Guidance (NON-NORMATIVE)

- **Retraction vs supersession.** Supersede when a corrected conclusion exists (the lineage keeps a head); retract when the context should not be relied upon *and no replacement exists yet* — or when the withdrawal itself is the message (fraudulent input data, compromised signing key per RFC-ACDP-0014, retracted upstream evidence). Retract-then-supersede is the common recovery sequence for a bad head (§8.3).
- **Say why.** Populate `reason`, and where the explanation deserves permanence, publish a companion context (type `analysis`, `derived_from` the retracted one) — the reason field is mutable-state metadata; a published explanation is signed record.
- **Retraction does not un-disclose.** Anyone who retrieved the body still has it; the body remains retrievable to its audience forever. For over-shared data the remediation remains supersession-with-narrower-audience plus carry-by-reference ([docs/data-protection.md §2–§3](../docs/data-protection.md)).

---

## 12. Scope and Limitations (honest scope)

- **Retraction state is registry-attested.** Like `status` generally (RFC-ACDP-0004 §4), the *presence and completeness* of `lifecycle_events` relies on registry honesty: a malicious registry can suppress a retraction event (serving stale `active`) or hide a republication. A signed event proves the actor performed the action; **no mechanism in this RFC proves the absence of events**. Consumers SHOULD persist retrieved lifecycle histories (append-only violations between two observations are then provable — the RFC-ACDP-0010 §13/§15 evidence posture); the protocol-native completeness answer is the transparency log reserved as RFC-ACDP-0009 §2.11.
- **A registry cannot be forced to honor a retraction.** The producer's signed event is portable evidence of intent; a registry that refuses to append it is non-conformant but undetectable from a single vantage. Multi-registry deployments SHOULD retract on every registry carrying the lineage.
- **Not erasure.** §8.1. A retracted body is exactly as permanent, and exactly as retrievable to its audience, as an active one.
- **No partial retraction.** Retraction is per-context and whole-context. Withdrawing one claim from a context means retracting it and publishing a corrected successor.
- **No third-party retraction.** Only the producer and the serving registry can retract (§6). Third-party dispute remains the `disputes` attestation reserved by RFC-ACDP-0009 §2.3.

---

## 13. Conformance Fixtures

| ID | What it pins | Runner |
|---|---|---|
| `lc-001-retraction-flow` | End-to-end retraction: authenticated `/retract` → `status: retracted`, event appended (signed, actor-bound, `ctx_id`-bound); body still retrievable (200, byte-identical) and body-only endpoint unchanged; excluded from default search, returned under `status=retracted`; double-retract → `invalid_lifecycle_transition` (409); `/republish` reverses (status re-derives, both events retained, append-only). | Behavioral |
| `lc-002-immutable-field` | Lifecycle request attempting to supply/alter body content (a `body` member / body-field-named member) → `immutable_field` (HTTP 400), not generic `schema_violation`; actor ≠ `agent_id` → `not_authorized`; unsigned producer event → rejected. | Behavioral |
| `lc-003-retracted-head` | §8.3 `/current` semantics: retracted v2 head over superseded v1 → `not_found` (404); recovery via v3 (`supersedes` the retracted v2) restores the head; head receipts (where advertised) never name a retracted head and are absent on the 404. | Behavioral |

---

## 14. Security Considerations

- **Retraction is a write with supersession-grade power** — it silences a context. The §6 authentication rules (producer signature verified through the full §5.11 pipeline; `agent_id` binding; rate limiting) are therefore load-bearing; a registry accepting unsigned or unverified producer events forfeits the attributability this RFC exists to provide.
- **Compromised-key retraction spam.** An attacker holding a producer's current key can retract that producer's contexts. This is the same blast radius as the attacker publishing or superseding under the stolen key, and the recovery is the same: rotate, revoke (RFC-ACDP-0014), and republish (§6) — the signed attack events remain in history as evidence, attributable to the compromised key and datable against the RFC-ACDP-0014 `compromised_since` boundary.
- **Existence leaks.** Lifecycle endpoints MUST apply retrieval visibility before any other check (§6 step 1); error-code ordering MUST NOT let an unauthorized caller distinguish "exists but not yours" from "does not exist" (RFC-ACDP-0008 §4.5).
- **Registry event keys.** Where the receipt key signs registry events (§5), the RFC-ACDP-0010 §15 key-handling requirements apply; the key's blast radius now includes forged lifecycle history, alongside forged receipts.
- **`reason` hygiene.** `reason` strings are producer/registry input surfaced to humans and logs; the RFC-ACDP-0007 §6 injection rules (no unsanitized echo, no automated decisions) apply.

---

## 15. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md) — §5.3 (time), §5.8 (signature construction), §5.11 (key resolution), §9.1 (profiles).
- [RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md)
- [RFC-ACDP-0003 Publish & Supersession](RFC-ACDP-0003-publish.md) — §3.1 (the authorization rule retraction reuses), §3.3 (the v0.1.0 no-retraction posture this RFC succeeds).
- [RFC-ACDP-0004 Retrieval & Lineage](RFC-ACDP-0004-retrieval.md) — §3 (registry state), §4/§4.1 (status derivation and the `retracted` reservation), §5.2 (`/current`).
- [RFC-ACDP-0005 Discovery](RFC-ACDP-0005-discovery.md) — §2.1 (`status` filter).
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md) — §5 (the `immutable_field` reservation).
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md) — §4.5 (visibility), §5 (the acknowledged no-retraction gap).
- [RFC-ACDP-0009 Extensions](RFC-ACDP-0009-extensions.md) — §2.1 (the reservation this RFC promotes).
- [RFC-ACDP-0010 Registry Receipts](RFC-ACDP-0010-registry-receipts.md) — §5 (signing construction, reused), §9 (registry key lifecycle), §13 (honest-scope posture).
- [RFC-ACDP-0011 Lineage-Head Receipts](RFC-ACDP-0011-lineage-head-receipts.md) — §4/§7 (head receipts, as amended by §8.3).
- [RFC-ACDP-0014 Producer Key-Revocation Signal](RFC-ACDP-0014-key-revocation.md) — the sibling 0.3.0 RFC; key compromise is a canonical retraction reason.
- [docs/non-goals.md](../docs/non-goals.md) §5, §13; [docs/data-protection.md](../docs/data-protection.md) — the permanence boundaries this RFC preserves.
- [RFC 8785] Rundgren, A., Jordan, B., and S. Erdtman, "JSON Canonicalization Scheme (JCS)", RFC 8785, June 2020.
- [RFC 9562] Davis, K., Peabody, B., and P. Leach, "Universally Unique IDentifiers (UUIDs)", RFC 9562, May 2024.
