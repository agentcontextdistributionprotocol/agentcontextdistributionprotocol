# RFC-ACDP-0009
# Agent Context Description Protocol (ACDP) — Extensions

**Document:** RFC-ACDP-0009
**Version:** 0.0.1-reserved
**Status:** **Reserved** — number pinned, no normative text yet

This RFC is a placeholder. It reserves the numbering and the field namespaces under which post-v0.0.1 capabilities will be specified. **It contains no normative requirements.**

---

## 1. Status of This Memo

Reserved. The capabilities below are *planned* for future versions of ACDP. Their concrete designs will be specified in their own version documents (likely v0.1, v0.2). Implementations MUST NOT depend on any behavior described here.

This document exists so that:

- Implementers know which feature areas are coming, and avoid building incompatible alternatives.
- Numbering 0009 is not consumed by an unrelated proposal.
- Future PRs adding the underlying mechanics know where they go.

---

## 2. Reserved Capabilities

### 2.1 Retraction & lifecycle events *(likely v0.1)*

A signed-event mechanism appended to **registry state** that allows producers to formally withdraw or annotate a context. Will use a `lifecycle_events` field in registry state (open-ended array of signed objects).

**Why deferred:** v0.0.1 is intentionally permanent-publication. Adding retraction without a fully-considered lifecycle vocabulary risked locking in a too-narrow design. Producers wanting effective retraction in v0.0.1 use supersession.

### 2.2 Post-publication relationships *(likely v0.1)*

Signed `builds_on` claims by *any* agent (not just the producer), allowing the lineage graph to grow after publication. Will use a `relationships` field in registry state.

**Why deferred:** v0.0.1 makes `derived_from` part of the signed body — only the producer can declare lineage at publish time. Post-publication relationships require a separate signing model and trust evaluation; out of scope for the substrate.

### 2.3 Attestations *(likely v0.1)*

Signed claims about a context: `reproduced` (a third party reran the analysis and got the same result), `disputes` (a third party disagrees with a conclusion), and other attestation kinds. Will use an `attestations` field in registry state.

**Why deferred:** Attestations are domain-specific and benefit from established post-publication patterns. v0.0.1 keeps the substrate clean.

### 2.4 Push subscriptions *(likely v0.2)*

Webhook and Server-Sent-Events delivery of search matches as they arrive. Will use new endpoints under `/subscriptions`. Will preserve `derived_from` polling semantics so unsubscribed consumers still work.

**Why deferred:** v0.0.1 polling is sufficient for the lineage-discovery pattern. Push subscriptions require operational machinery (delivery guarantees, retry, backpressure) that doesn't belong in the substrate's first release.

### 2.5 Server-side traversal (walks) *(likely v0.2)*

Single-call traversal of `derived_from` chains to avoid round-trip amplification. Will use a `/contexts/{ctx_id}/walk` endpoint with depth and breadth controls.

**Why deferred:** v0.0.1 consumers walk `derived_from` chains client-side, one fetch per node. This works but is N round-trips for an N-deep chain. A `/walk` endpoint compresses this.

### 2.6 Federation peering & cross-registry search *(no schedule)*

Mechanisms for one registry to query another, or for registries to peer for replication. Out of scope for the protocol — these are likely operational concerns built on top of `acdp://` resolution.

---

## 3. Forward Compatibility

Future capabilities will follow these rules to maintain backward compatibility:

- **Body fields** are additive only. v0.0.1 bodies remain valid.
- **Registry state** is open (`additionalProperties: true`); new fields appear here without breaking consumers.
- **Capabilities document** advertises new flags (`additionalProperties: true`); consumers detect support before using a feature.
- **New endpoints** under new paths (`/subscriptions/...`, `/contexts/{ctx_id}/walk`); existing endpoints' contracts do not change.

Consumers reading a capabilities document with an unknown `acdp_version` SHOULD treat it as a higher version and degrade gracefully — using only the operations defined in v0.0.1 plus any flags they recognize.

---

## 4. Status

This document will be replaced by concrete RFCs when each capability is specified. Until then, the numbering 0009 (and any sub-numbering reserved by future planning) is held by this placeholder.

---

## 5. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
- [VERSIONING.md](../VERSIONING.md)
- [CHANGELOG.md](../CHANGELOG.md)
