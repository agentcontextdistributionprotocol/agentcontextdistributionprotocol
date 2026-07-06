# ACDP RFC Index

This directory contains the normative RFCs that define the Agent Context Distribution Protocol (ACDP). ACDP is a coordination-agnostic substrate for **publishing, discovering, and verifying** units of agent-produced content; v0.1.0 is the first published version.

| RFC | Title | Status |
|---|---|---|
| [RFC-ACDP-0001](RFC-ACDP-0001-core.md) | Core — identifiers, JCS, hashing, signatures | Final (0.1.0; 0.2.0/0.3.0 amendments Final) |
| [RFC-ACDP-0002](RFC-ACDP-0002-context-body.md) | Context Body | Final (0.1.0; 0.3.0 amendment Final) |
| [RFC-ACDP-0003](RFC-ACDP-0003-publish.md) | Publish & Supersession | Final (0.1.0; 0.2.0/0.3.0 amendments Final) |
| [RFC-ACDP-0004](RFC-ACDP-0004-retrieval.md) | Retrieval & Lineage | Final (0.1.0; 0.2.0/0.3.0 amendments Final) |
| [RFC-ACDP-0005](RFC-ACDP-0005-discovery.md) | Discovery (keyword search) | Final (0.1.0; 0.3.0 amendment Final) |
| [RFC-ACDP-0006](RFC-ACDP-0006-cross-registry.md) | Cross-Registry References | Final |
| [RFC-ACDP-0007](RFC-ACDP-0007-capabilities.md) | Capabilities & Errors | Final (0.1.0; 0.2.0/0.3.0 amendments Final) |
| [RFC-ACDP-0008](RFC-ACDP-0008-security.md) | Security & Threat Model | Final (0.1.0; 0.2.0/0.3.0 amendments Final) |
| [RFC-ACDP-0009](RFC-ACDP-0009-extensions.md) | Extensions (attestations, walks, push) | Reserved (§2.7 promoted to RFC-ACDP-0010; §2.1 promoted to RFC-ACDP-0013; §2.11 promoted to RFC-ACDP-0012; §2.12 promoted to RFC-ACDP-0015) |
| [RFC-ACDP-0010](RFC-ACDP-0010-registry-receipts.md) | Registry Receipts | Final (acdp/0.2.0) |
| [RFC-ACDP-0011](RFC-ACDP-0011-lineage-head-receipts.md) | Lineage-Head Receipts | Final (acdp/0.3.0) |
| [RFC-ACDP-0012](RFC-ACDP-0012-transparency-log.md) | Registry Transparency Log | Final (acdp/0.3.0) |
| [RFC-ACDP-0013](RFC-ACDP-0013-lifecycle-events.md) | Lifecycle Events & Retraction | Final (acdp/0.3.0) |
| [RFC-ACDP-0014](RFC-ACDP-0014-key-revocation.md) | Producer Key-Revocation Signal | Final (acdp/0.3.0) |
| [RFC-ACDP-0015](RFC-ACDP-0015-witness-cosigning.md) | Transparency-Log Witness Cosigning | Draft (acdp/0.4.0) |

The acdp/0.2.0 and acdp/0.3.0 lines were promoted from Draft to Final on 2026-07-05, after their conformance packs passed against two independent interoperating implementations (see [CHANGELOG.md](../CHANGELOG.md)). In-prose *(0.2.0)* / *(0.3.0)* markers record the release line that added a passage. The acdp/0.4.0 line opens with RFC-ACDP-0015 (Draft); it goes Final once its `wit-*` conformance pack passes against two independent implementations.

## Reading order

The numbering matches dependency order. Read top-to-bottom:

1. **[RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)** — identifiers, JCS canonicalization, content hashing, signatures, time format.
2. **[RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md)** — the immutable signed body; context types; data references; visibility.
3. **[RFC-ACDP-0003 Publish](RFC-ACDP-0003-publish.md)** — `POST /contexts`, supersession constraints, registry-assigned fields.
4. **[RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)** — `GET /contexts/{ctx_id}` and lineage queries.
5. **[RFC-ACDP-0005 Discovery](RFC-ACDP-0005-discovery.md)** — keyword search.
6. **[RFC-ACDP-0006 Cross-Registry](RFC-ACDP-0006-cross-registry.md)** — `acdp://` URI scheme and resolution flow.
7. **[RFC-ACDP-0007 Capabilities](RFC-ACDP-0007-capabilities.md)** — `/.well-known/acdp.json` and the error envelope.
8. **[RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)** — threat model and required defenses.
9. **[RFC-ACDP-0010 Registry Receipts](RFC-ACDP-0010-registry-receipts.md)** *(0.2.0)* — registry-signed attestations binding the registry-assigned identifiers, content hash, and producer-key fingerprint to the registry's DID.
10. **[RFC-ACDP-0011 Lineage-Head Receipts](RFC-ACDP-0011-lineage-head-receipts.md)** *(0.3.0)* — registry-signed serve-time attestations of the current lineage head ("as of T, the head of L is X at version N with status S"), extending the RFC-ACDP-0010 receipt layer from publish-time facts to current-ness claims.
11. **[RFC-ACDP-0012 Registry Transparency Log](RFC-ACDP-0012-transparency-log.md)** *(0.3.0)* — a per-registry append-only Merkle tree over publish events with signed checkpoints, inclusion proofs, and consistency proofs, making mint-time backdating, omission, and per-consumer equivocation detectable by any auditor holding checkpoints; the capstone of the receipt trust arc (promotes RFC-ACDP-0009 §2.11).
12. **[RFC-ACDP-0013 Lifecycle Events & Retraction](RFC-ACDP-0013-lifecycle-events.md)** *(0.3.0)* — signed, append-only lifecycle events in registry state; producer/registry retraction and republication; the `retracted` status (dominating `superseded`/`expired`); mark-not-delete throughout. Promotes RFC-ACDP-0009 §2.1.
13. **[RFC-ACDP-0014 Producer Key-Revocation Signal](RFC-ACDP-0014-key-revocation.md)** *(0.3.0)* — the normative `key-revocation` context type and time-scoped verification boundary: receipt-attested publish times before `compromised_since` stay historically authorized; at/after (or unverifiable) fail closed.
14. **[RFC-ACDP-0015 Transparency-Log Witness Cosigning](RFC-ACDP-0015-witness-cosigning.md)** *(0.4.0, Draft)* — independent witnesses observe a registry's RFC-ACDP-0012 checkpoints, verify consistency, and cosign what they saw; a consumer trusting any one honest witness inherits split-view protection and an external anchor for checkpoint time. Promotes RFC-ACDP-0009 §2.12; opens the 0.4.0 line.

Reserved (no normative text, numbering pinned for future work):

- **[RFC-ACDP-0009 Extensions](RFC-ACDP-0009-extensions.md)** — post-publication relationships, attestations, push subscriptions, server-side traversal (§2.12 checkpoint witnessing promoted to RFC-ACDP-0015).

## RFC lifecycle

`Draft → Review → Final Comment Period → Release Candidate N → Final` (or `Rejected`). `Reserved` is a sidebar state for placeholder RFCs (e.g. RFC-ACDP-0009). See [governance/RFC-PROCESS.md](../governance/RFC-PROCESS.md) and [VERSIONING.md](../VERSIONING.md).
