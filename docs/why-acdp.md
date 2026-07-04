# Why ACDP

This document explains the problem ACDP solves and why existing tools don't solve it.

---

## The problem

Two autonomous agents need to share knowledge. They are run by different teams, sign with different keys, and have no shared backend between them. Before one can build on the other's output, the consuming agent needs to know:

1. **What did you produce?**
2. **What evidence is it based on?**
3. **Who signed for it?**
4. **Is it still current?**

Existing tools answer some of these questions, but none gives a single signed artifact that answers all four for an agent-to-agent knowledge handoff:

**Databases / data warehouses**
- Local to a deployment; no portable artifact crosses organizational boundaries.
- No producer signature, no portable provenance.
- Discovery is a SQL join, not a protocol.

**REST APIs / event streams**
- Per-vendor formats; integration is point-to-point.
- "Who signed for this" is implicit in the calling system, not in the payload.
- Lineage is operational — log lines, not signed artifacts.

**JWT / signed tokens**
- Designed to carry capability claims for a request; not designed as a permanent signed publication.
- No content-addressing primitive; no `derived_from` semantics.
- Short-lived by design.

**Blockchain / DAG-based data structures**
- Solve permanence and provenance, but at very high coordination cost.
- Don't have content-addressing of arbitrary structured data with discovery semantics.
- Operational complexity is order-of-magnitude higher than HTTP + JSON.

**The result:** every agent ecosystem invents its own data-sharing layer. They don't compose across organizations.

---

## What ACDP does

ACDP defines a single publish/discover/verify interface:

> A producer agent constructs a context body, signs it, and POSTs it to a registry.
> A consumer agent retrieves the body, verifies the producer's signature locally, and walks `derived_from` chains across registries.

The body is content-addressed (`content_hash`), content-deterministic (JCS canonicalization), and signed by an identifiable producer (DID). A consuming agent needs only:

1. The producer's public key (from the producer's DID document).
2. A JCS implementation.
3. A SHA-256 implementation.

No knowledge of the producing system's database, the producer's internal state, or the registry's policy.

---

## What ACDP is not

ACDP is not a coordination protocol. It does not specify sessions, voting, consensus, marketplaces, or reputation. Coordination protocols can be built **on top of** ACDP — using contexts as the substrate — but ACDP itself is coordination-agnostic.

ACDP is not an identity system. Producer identity comes from DIDs (or any equivalent that publishes a verifiable public key). The identity system you already use continues to work.

ACDP is not an authorization layer. It produces signed content; what consumers do with it is their concern. (For agent-to-agent authorization, see complementary protocols in the agent identity & trust space.)

ACDP is not a replacement for purpose-built data systems. A registry is a metadata layer. The actual data lives wherever it lives — `data_refs.location` references it, but ACDP does not move it.

---

## Why this version is minimal

The first published version of ACDP is intentionally a **minimal substrate**. Lifecycle events, retractions, third-party `builds_on` claims, attestations, push subscriptions, and server-side traversal are all reserved (RFC-ACDP-0009) but not specified.

That choice keeps the surface area small and the trust model legible: every body is signed, every lineage is derivable, every retrieval is locally verifiable. Once that substrate is solid, higher-order capabilities can be added without breaking the contract.

The bet: the right primitive is **content-addressed signed bodies with deterministic lineage**. Everything else can be layered on.

---

## See also

The comparisons above cover data-layer tools (databases, APIs, tokens, blockchains). For how ACDP relates to the *protocols* evaluators usually ask about — MCP, A2A, C2PA, AT Protocol, DIDComm — see [acdp-vs-the-field.md](acdp-vs-the-field.md).
