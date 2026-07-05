# RFC-ACDP-0009
# Agent Context Distribution Protocol (ACDP) — Extensions

**Document:** RFC-ACDP-0009
**Version:** 0.2.0-reserved
**Status:** **Reserved** — number pinned, no normative text yet (§2.7 promoted to [RFC-ACDP-0010](RFC-ACDP-0010-registry-receipts.md) in acdp/0.2.0)

This RFC is a placeholder. It reserves the numbering and the field namespaces under which post-v0.1.0 capabilities will be specified. **It contains no normative requirements.**

---

## 1. Status of This Memo

Reserved. The capabilities below are *planned* for future versions of ACDP, after the 0.1.0 release. Their concrete designs will be specified in their own version documents. Implementations MUST NOT depend on any behavior described here.

This document exists so that:

- Implementers know which feature areas are coming, and avoid building incompatible alternatives.
- Numbering 0009 is not consumed by an unrelated proposal.
- Future PRs adding the underlying mechanics know where they go.

---

## 2. Reserved Capabilities

### 2.1 Retraction & lifecycle events

A signed-event mechanism appended to **registry state** that allows producers to formally withdraw or annotate a context. Will use a `lifecycle_events` field in registry state (open-ended array of signed objects).

**Why deferred:** v0.1.0 is intentionally permanent-publication. Adding retraction without a fully-considered lifecycle vocabulary risked locking in a too-narrow design. Producers wanting effective retraction in v0.1.0 use supersession.

### 2.2 Post-publication relationships

Signed `builds_on` claims by *any* agent (not just the producer), allowing the lineage graph to grow after publication. Will use a `relationships` field in registry state.

**Why deferred:** v0.1.0 makes `derived_from` part of the signed body — only the producer can declare lineage at publish time. Post-publication relationships require a separate signing model and trust evaluation; out of scope for the substrate.

### 2.3 Attestations

Signed claims about a context: `reproduced` (a third party reran the analysis and got the same result), `disputes` (a third party disagrees with a conclusion), and other attestation kinds. Will use an `attestations` field in registry state.

**Why deferred:** Attestations are domain-specific and benefit from established post-publication patterns. v0.1.0 keeps the substrate clean.

### 2.4 Push subscriptions

Webhook and Server-Sent-Events delivery of search matches as they arrive. Will use new endpoints under `/subscriptions`. Will preserve `derived_from` polling semantics so unsubscribed consumers still work.

**Why deferred:** v0.1.0 polling is sufficient for the lineage-discovery pattern. Push subscriptions require operational machinery (delivery guarantees, retry, backpressure) that doesn't belong in the substrate's first release.

### 2.5 Server-side traversal (walks)

Single-call traversal of `derived_from` chains to avoid round-trip amplification. Will use a `/contexts/{ctx_id}/walk` endpoint with depth and breadth controls.

**Why deferred:** v0.1.0 consumers walk `derived_from` chains client-side, one fetch per node. This works but is N round-trips for an N-deep chain. A `/walk` endpoint compresses this.

### 2.6 Federation peering & cross-registry search

Mechanisms for one registry to query another, or for registries to peer for replication. Out of scope for the protocol — these are likely operational concerns built on top of `acdp://` resolution.

### 2.7 Registry receipts — **PROMOTED to RFC-ACDP-0010 (acdp/0.2.0)**

> **Status of this section:** the reservation below was promoted to a full normative specification, [RFC-ACDP-0010 Registry Receipts](RFC-ACDP-0010-registry-receipts.md), as part of the acdp/0.2.0 Trust & Hardening program. The reserved JSON shape was adopted unchanged. The text below is retained verbatim for 0.1.0-pinned libraries: **everything in this section — in particular the "Minimum structural guidance for v0.1.0 libraries" (preserve verbatim, do not parse or verify, hash exclusion) — remains the governing guidance for any library that declares `acdp_version` `0.1.0`.** Receipt-aware behavior (minting, verification, the `acdp-registry-receipts` profile, `invalid_receipt`) is specified exclusively by RFC-ACDP-0010 and applies to 0.2.0 implementations.

A future ACDP version will introduce **registry receipts**: registry-signed attestations binding registry-assigned identifiers to producer content_hash, providing cryptographic proof of publication beyond producer signature alone.

#### Motivation

ACDP v0.1.0 producer signatures bind producer-controlled content but do not bind `ctx_id`, `lineage_id`, `origin_registry`, or `created_at`. See RFC-ACDP-0008 §9.1 for the full discussion.

#### Reserved structure

Future versions will add a `registry_receipt` object to retrieval responses:

```json
{
  "body": { ... },
  "registry_state": { ... },
  "registry_receipt": {
    "registry_did": "did:web:registry.example.com",
    "ctx_id": "acdp://registry.example.com/<uuid>",
    "lineage_id": "lin:...",
    "origin_registry": "registry.example.com",
    "created_at": "2026-04-16T10:30:15.123Z",
    "content_hash": "sha256:...",
    "key_fingerprint": "sha256:<resolved-producer-key-digest>",
    "signature": {
      "algorithm": "ed25519",
      "key_id": "did:web:registry.example.com#key-1",
      "value": "..."
    }
  }
}
```

#### Why not in v0.1.0

Receipts add a second signing identity (the registry's), require key management for that identity, and introduce a new top-level retrieval shape. v0.1.0 keeps the trust model simple — producer signatures only — and acknowledges the resulting limitation honestly. Receipts are intended for a future ACDP version.

#### Reserved field names

`registry_receipt` (top-level in retrieval response) and `key_fingerprint` (within signature objects) are RESERVED in v0.1.0 and MUST NOT be used by extensions.

#### Minimum structural guidance for v0.1.0 libraries

The field `registry_receipt` (top-level in `FullContext`, OUTSIDE `body` and `registry_state`) is reserved. v0.1.0 libraries MUST NOT use it themselves but SHOULD handle its presence safely on the wire when forward-compatible registries begin emitting it:

- **Preserve verbatim.** If `registry_receipt` is present in a retrieval response (`FullContext`), v0.1.0 libraries MUST preserve the field verbatim as an opaque JSON value (object, but no schema enforcement) when forwarding the response, persisting it, or re-serializing for any reason. Libraries MUST NOT silently drop the field or strip its inner properties.
- **Do not parse, validate, or verify.** v0.1.0 libraries MUST NOT attempt to parse the receipt's substructure, MUST NOT validate its `signature`, and MUST NOT use it as evidence of authenticity. The receipt's signing model (registry-signed binding of registry-assigned identifiers to the producer-signed body) is specified in a future version; verifying it under v0.1.0 produces no meaningful trust signal.
- **Detect upgrade signal.** Registry receipts are not part of ACDP 0.1.0. A `registry_receipt` present on a response from a registry advertising `acdp_version: 0.1.0` is therefore anomalous — the registry is emitting a field from a future version while declaring 0.1.0 conformance; v0.1.0 libraries SHOULD log a warning naming the registry and the receipt's `registry_did`. A `registry_receipt` accompanied by a higher (future) `acdp_version` indicates the consumer is talking to a receipts-capable registry; consumers SHOULD log an informational signal and MAY upgrade to a receipt-aware library to take advantage of the receipt.
- **Hash exclusion.** The `registry_receipt` is OUTSIDE the body and is therefore not part of the producer's `content_hash` calculation under any version. v0.1.0 libraries MUST NOT include `registry_receipt` in their `content_hash` recomputation pipeline (which already operates on `body` alone, with the §5.7 exclusion set applied within `body`).

This guidance is the minimum required to keep v0.1.0 libraries forward-compatible with future registry-receipt deployments. The full receipt format (signing algorithm, canonicalization rules, verification procedure) is out of scope for v0.1.0 and will be specified in a future RFC.

### 2.8 Cross-registry supersession

ACDP v0.1.0 forbids supersession across registries (RFC-ACDP-0003 §3.1 step 2): if a producer attempts to publish a v2 on registry B with `supersedes` pointing at v1 on registry A, registry B MUST reject with `superseded_target` (`details.reason = "cross_registry_supersession_unsupported"`).

The verification semantics required to make this safe are not normatively defined in v0.1.0. A future version will specify:

- A protocol for the publishing registry to verify the remote `agent_id` identity and the producer's DID-document state at supersession time (consistent across the two registries).
- A protocol for verifying the remote context's signature, `content_hash`, and `lineage_id` continuity across the network.
- Race-protection semantics: the original registry must serialize supersession events for the target context, even when the publishing registry is different. This requires either a coordination handshake or a transparency-log mechanism.
- Recovery behavior when the original registry becomes unreachable mid-supersession.
- Fee / authorization model: which registry is authoritative for the lineage, who pays for storage, etc.

Until that version, all supersessions MUST occur within a single registry. Producers needing to migrate a logical lineage between registries MUST start a new lineage on the target registry (with `supersedes: null`) and reference the prior lineage via `derived_from`. This produces a soft, signed link without making cross-registry continuity claims that v0.1.0 cannot verify.

### 2.9 Semantic Similarity and Embeddings

ACDP v0.1.0 does not include semantic similarity search. The feature was scoped out to keep the first release minimal and keyword-only.

A future ACDP version will define:

- `embedding` and `embedding_model` body fields (producer-signed vector representations).
- A `POST /contexts/similar` endpoint for vector similarity search by reference or by raw embedding.
- Capability fields: `supported_embedding_models`, `previously_supported_embedding_models`, `limits.max_embedding_dimensions`, `limits.max_top_k`.
- An `unsupported_embedding_model` error code (HTTP 400).
- Similarity privacy requirements (visibility-scoped vector indexing; producer guidance on omitting embeddings from sensitive contexts).
- Embedding-model retirement / deprecation semantics.

Reserved profile name: `acdp-registry-similarity` (added to a future RFC-ACDP-0001 §9.1; current registries advertising similarity gating remain non-conformant in v0.1.0).

### 2.10 Registry webhook event profile

An OPTIONAL companion profile for **registry-to-control-plane events**: signed notifications a registry emits to an operator's control plane when a context is published, superseded, or otherwise changes lifecycle state. This is distinct from §2.4 (push subscriptions), which delivers **search matches** to ordinary discovery *consumers*; the webhook event profile is a server-to-operator integration channel and carries no body, only registry-attested metadata about the event.

This profile is reserved, not normative — its concrete shape (transport, retry/backpressure, exact field encodings, signature construction) will be specified in a future version, and implementations MUST NOT depend on the sketch below for interoperability.

#### Reserved profile name

`acdp-registry-events` (to be added to a future RFC-ACDP-0001 §9.1). Registries emitting these events in v0.1.0 do so as a private operational feature; the profile is not advertisable for conformance in v0.1.0.

#### Reserved event shape

A future version will define a registry-event object carrying at least:

| Field | Meaning |
|---|---|
| `event_id` | Unique identifier for this event instance (the idempotency key — see below). |
| `event_version` | Schema version of the event envelope (independent of `acdp_version`). |
| `event_type` | Lifecycle event kind, e.g. `context_published`, `context_superseded`, `status_changed`. |
| `registry_authority` | DNS authority of the emitting registry (matches the `<authority>` in minted `ctx_id`s). |
| `ctx_id` | The affected context. |
| `lineage_id` | The affected context's lineage (RFC-ACDP-0001 §5.6). |
| `agent_id` | Producer DID of the affected context. |
| `visibility` | `public` / `restricted` / `private` of the affected context. |
| `derived_from` | The affected context's `derived_from` references, if any. |
| `created_at` | Registry-clock timestamp of the event (RFC 3339, millisecond precision per RFC-ACDP-0001 §5.3). |

#### Tenanting, signing, and delivery semantics

- **Tenant binding is by deployment policy.** Consistent with RFC-ACDP-0008 §6.4, the event envelope defines no protocol-level tenant field; tenant attribution on emitted events is established by the registry's deployment policy (the registry knows the tenant of the context it is emitting about) and MUST NOT be derived from any unauthenticated request input.
- **HMAC signature header.** Events SHOULD be authenticated to the receiving control plane with a keyed HMAC over the canonical event bytes (JCS per RFC-ACDP-0001 §5.2, then HMAC-SHA-256) carried in a signature header, with a shared secret provisioned out of band between the registry and its control plane. This is a registry-to-operator integrity check — it is **not** the producer signature (RFC-ACDP-0001 §5.8) and conveys no producer authenticity; receivers MUST still retrieve and verify the context per RFC-ACDP-0004 before treating its body as trustworthy.
- **Idempotency.** Delivery is at-least-once; receivers MUST deduplicate by `event_id` and process idempotently. `event_id` is stable across redeliveries of the same logical event, so a receiver that has already applied an `event_id` MUST treat a repeat as a no-op.

**Why deferred:** the same reasoning as §2.4 — push delivery requires operational machinery (delivery guarantees, retry, backpressure, idempotency, signing-key management) that does not belong in the substrate's first release. v0.1.0 control planes poll the discovery/search endpoints (RFC-ACDP-0005) instead.

### 2.11 Transparency log — **PROMOTED to RFC-ACDP-0012 (acdp/0.3.0)**

> **Status of this section:** the reservation below was promoted to a full normative specification, [RFC-ACDP-0012 Registry Transparency Log](RFC-ACDP-0012-transparency-log.md), as part of the acdp/0.3.0 program. The reserved names — `log_inclusion`, `log_checkpoint`, `log_id`, `leaf_index`, `inclusion_path`, the profile `acdp-registry-transparency-log`, and the endpoint paths `/log/checkpoint`, `/log/proof`, `/log/entries` — were all adopted with their reserved meanings, with three refinements of the sketch recorded in RFC-ACDP-0012 §12: (1) `log_inclusion` is a **top-level** retrieval-envelope member, a sibling of `registry_receipt` rather than a member of it (the receipt is closed, fully signed, and byte-immutable per RFC-ACDP-0010 §4, so a mutable proof cannot live inside it); (2) the sketch's informal `checkpoint_signature` member is realized as the standard `signature` envelope of RFC-ACDP-0001 §5.8; (3) the capabilities field `supports_transparency_log` is retired unused in favor of profile advertisement — the name remains reserved and MUST NOT be emitted. The leaf binds each minted receipt by its RFC-ACDP-0010 §2 receipt hash (plus the identity fields), rather than embedding the receipt verbatim. The text below is retained verbatim as the historical reservation; transparency-log behavior is specified exclusively by RFC-ACDP-0012 and applies to 0.3.0 implementations. Gossip/witness machinery remains reserved — see §2.12.

An **append-only, registry-signed publication log** in the Certificate-Transparency / Merkle-tree-checkpoint style: every minted receipt (RFC-ACDP-0010) is appended as a leaf; the registry periodically signs a checkpoint (tree head) over the log; consumers and independent auditors verify inclusion proofs for individual receipts and consistency proofs between checkpoints. This is the layer above registry receipts: receipts make registry claims *attributable and non-repudiable* (RFC-ACDP-0010 §13); the log makes mint-time backdating and per-consumer equivocation *detectable by any auditor*, because a backdated receipt must be inserted into an already-checkpointed history and conflicting receipts cannot both carry valid inclusion proofs against the same checkpoint chain.

#### Reserved field and endpoint names

The following names are RESERVED and MUST NOT be used by extensions: `log_inclusion` (a member of `registry_receipt` carrying an inclusion proof), `log_checkpoint` (a signed tree-head object: `tree_size`, `root_hash`, `checkpoint_signature`), `log_id`, `leaf_index`, `inclusion_path`, the capabilities field `supports_transparency_log`, the profile name `acdp-registry-transparency-log`, and the endpoint paths `/log/checkpoint`, `/log/proof`, and `/log/entries`.

**Why deferred:** receipts had to ship first — the log's leaves *are* receipts, and the receipt construction (preimage, fingerprint, key lifecycle) needed to stabilize before an append-only history could be built over it. The log also brings real operational machinery (checkpoint cadence, proof serving, auditor ecosystem, gossip for split-view detection) that should not gate the 0.2.0 trust improvements. Named future work per RFC-ACDP-0010 §13; no normative content in the 0.2.0 program.

---

### 2.12 Checkpoint witnessing & cosigning

A future ACDP version may introduce **external witnesses** for the RFC-ACDP-0012 transparency log: independent parties that observe a registry's checkpoints over time, verify consistency between them (RFC-ACDP-0012 §9.2), and **cosign** checkpoints they have verified — so that a consumer can require "this checkpoint was also seen, consistency-checked, and signed by N witnesses I trust" instead of trusting the registry's clock and history alone. This closes the two gaps RFC-ACDP-0012 §13 leaves open by design: checkpoint `timestamp` values are registry-asserted (a witness cosignature anchors *when the checkpoint was witnessed* against parties the registry does not control), and split-view detection requires comparing checkpoints across vantages (witnesses *are* the standing vantages, and a gossip protocol among them makes comparison systematic rather than incidental).

#### Reserved field and endpoint names

The following names are RESERVED and MUST NOT be used by extensions: `witness_signatures` (an array member of `log_checkpoint`-bearing responses carrying witness cosignatures over the checkpoint hash), `witnessed_checkpoint`, `witness_id`, `witnessed_at`, the profile name `acdp-log-witness`, and the endpoint path `/log/witness`.

**Why deferred:** witnessing is an *ecosystem*, not an endpoint — it needs a witness identity and discovery story, a cosignature format, witness-policy expression on the consumer side ("which witnesses, how many"), and a gossip protocol with its own anti-partition and privacy analysis. None of that should gate the 0.3.0 log itself, which is already independently useful (any party that retains checkpoints is an ad-hoc witness). Named future work per RFC-ACDP-0012 §13; no normative content in the 0.3.0 program.

---

## 3. Forward Compatibility

Future capabilities will follow these rules to maintain backward compatibility:

- **Body fields** are additive only. v0.1.0 bodies remain valid.
- **Registry state** is open (`additionalProperties: true`); new fields appear here without breaking consumers.
- **Capabilities document** advertises new flags (`additionalProperties: true`); consumers detect support before using a feature.
- **New endpoints** under new paths (`/subscriptions/...`, `/contexts/{ctx_id}/walk`); existing endpoints' contracts do not change.

Consumers reading a capabilities document with an unknown `acdp_version` SHOULD treat it as a higher version and degrade gracefully — using only the operations defined in v0.1.0 plus any flags they recognize.

---

## 4. Status

This document will be replaced by concrete RFCs when each capability is specified. Until then, the numbering 0009 (and any sub-numbering reserved by future planning) is held by this placeholder.

---

## 5. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
- [RFC-ACDP-0010 Registry Receipts](RFC-ACDP-0010-registry-receipts.md) — promotion of §2.7
- [VERSIONING.md](../VERSIONING.md)
- [CHANGELOG.md](../CHANGELOG.md)
