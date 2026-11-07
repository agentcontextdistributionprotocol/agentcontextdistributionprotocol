# ACDP RFC Index

This directory contains the normative RFCs that define the Agent Context Distribution Protocol (ACDP). ACDP is a coordination-agnostic substrate for **publishing, discovering, and verifying** units of agent-produced content; v0.1.0 is the first published version.

| RFC | Title | Status |
|---|---|---|
| [RFC-ACDP-0001](RFC-ACDP-0001-core.md) | Core — identifiers, JCS, hashing, signatures | Final (0.1.0; 0.2.0/0.3.0 amendments Final; 0.5.0 amendments Final) |
| [RFC-ACDP-0002](RFC-ACDP-0002-context-body.md) | Context Body | Final (0.1.0; 0.3.0 amendment Final; 0.5.0 amendments Final) |
| [RFC-ACDP-0003](RFC-ACDP-0003-publish.md) | Publish & Supersession | Final (0.1.0; 0.2.0/0.3.0 amendments Final; 0.5.0 amendments Final) |
| [RFC-ACDP-0004](RFC-ACDP-0004-retrieval.md) | Retrieval & Lineage | Final (0.1.0; 0.2.0/0.3.0 amendments Final; 0.5.0 amendments Final) |
| [RFC-ACDP-0005](RFC-ACDP-0005-discovery.md) | Discovery (keyword search) | Final (0.1.0; 0.3.0 amendment Final; 0.5.0 amendments Final) |
| [RFC-ACDP-0006](RFC-ACDP-0006-cross-registry.md) | Cross-Registry References | Final |
| [RFC-ACDP-0007](RFC-ACDP-0007-capabilities.md) | Capabilities & Errors | Final (0.1.0; 0.2.0/0.3.0/0.4.0 amendments Final; 0.5.0 amendments Final) |
| [RFC-ACDP-0008](RFC-ACDP-0008-security.md) | Security & Threat Model | Final (0.1.0; 0.2.0/0.3.0 amendments Final; 0.5.0 amendments Final) |
| [RFC-ACDP-0009](RFC-ACDP-0009-extensions.md) | Extensions (attestations, walks, push) | Reserved (§2.7 promoted to RFC-ACDP-0010; §2.1 promoted to RFC-ACDP-0013; §2.11 promoted to RFC-ACDP-0012; §2.12 promoted to RFC-ACDP-0015; §2.10 defined by RFC-ACDP-0018, Final) |
| [RFC-ACDP-0010](RFC-ACDP-0010-registry-receipts.md) | Registry Receipts | Final (acdp/0.2.0; 0.5.0 amendments Final) |
| [RFC-ACDP-0011](RFC-ACDP-0011-lineage-head-receipts.md) | Lineage-Head Receipts | Final (acdp/0.3.0) |
| [RFC-ACDP-0012](RFC-ACDP-0012-transparency-log.md) | Registry Transparency Log | Final (acdp/0.3.0; 0.5.0 amendments Final) |
| [RFC-ACDP-0013](RFC-ACDP-0013-lifecycle-events.md) | Lifecycle Events & Retraction | Final (acdp/0.3.0) |
| [RFC-ACDP-0014](RFC-ACDP-0014-key-revocation.md) | Producer Key-Revocation Signal | Final (acdp/0.3.0; 0.5.0 amendments Final) |
| [RFC-ACDP-0015](RFC-ACDP-0015-witness-cosigning.md) | Transparency-Log Witness Cosigning | Final (acdp/0.4.0; 0.5.0 amendments Final) |
| [RFC-ACDP-0016](RFC-ACDP-0016-external-anchors.md) | Typed External Anchors | Final (acdp/0.5.0) |
| [RFC-ACDP-0017](RFC-ACDP-0017-chain-verification.md) | Chain Verification and Evidence Bundles | Final (acdp/0.5.0) |
| [RFC-ACDP-0018](RFC-ACDP-0018-retraction-recall.md) | Retraction Recall: the Changes Feed and Change Hints | Final (acdp/0.5.0) |
| [RFC-ACDP-0019](RFC-ACDP-0019-mcp-tool-result-provenance.md) | MCP Tool-Result Provenance (the MCP signing proxy) | Final (acdp/0.5.0) |
| [RFC-ACDP-0020](RFC-ACDP-0020-registry-trust-lists.md) | Registry Trust Lists | Final (acdp/0.5.0) |
| [RFC-ACDP-0021](RFC-ACDP-0021-keyless-signing.md) | Keyless Signing | Final (acdp/0.5.0) |
| [RFC-ACDP-0022](RFC-ACDP-0022-a2a-artifact-provenance.md) | A2A Artifact Provenance (agent-signed artifacts) | Final (acdp/0.5.0) |

The acdp/0.2.0 and acdp/0.3.0 lines were promoted from Draft to Final on 2026-07-05, and the acdp/0.4.0 line (RFC-ACDP-0015) on 2026-08-28, each after its conformance pack passed against two independent interoperating implementations (see [CHANGELOG.md](../CHANGELOG.md)). The 0.4.0 gate was met by `acdp-rs` (crates.io `acdp 0.8.1`, require-mode conformance at spec `bff3cf3afbdcea619834916e8f0bcac7e82ba658`, [CI run](https://github.com/agentcontextdistributionprotocol/acdp-rs/actions/runs/33232085544/job/99046540516)) and `acdp-verifier-py` (`v0.1.0`, at the same pinned spec SHA, [CI run](https://github.com/agentcontextdistributionprotocol/acdp-verifier-py/actions/runs/33235087345)), each executing `wit-001..004`. In-prose *(0.2.0)* / *(0.3.0)* / *(0.4.0)* markers record the release line that added a passage; all three lines are Final, so those passages are Final too. The acdp/0.5.0 line was promoted to Final on 2026-11-06, so in-prose *(0.5.0)* passages are Final too. Its consumer-side pieces passed against two independent interoperating implementations (acdp-rs `55f40c3` (require-mode conformance at spec `ce39078`, [CI run](https://github.com/agentcontextdistributionprotocol/acdp-rs/actions/runs/42328766458)); acdp-verifier-py `9267a62` (138 passed, 0 failed, at spec `8cc186d`, [CI run](https://github.com/agentcontextdistributionprotocol/acdp-verifier-py/actions/runs/42338572175))). The pieces with a single implementation (the registry side, the RFC-ACDP-0019 proxy and the RFC-ACDP-0022 agent side) were promoted under the owner's single-implementation gate exception for this line ([VERSIONING.md](../VERSIONING.md)): acdp-registry-rs `92c639a` (v0.11.1; conformance against the fixtures at spec `8cc186d`, including `lc-001`..`lc-003` and `rev-003` A–R, [CI run](https://github.com/agentcontextdistributionprotocol/acdp-registry-rs/actions/runs/42349360187)); acdp-rs `55f40c3` (require-mode conformance at spec `ce39078`, [CI run](https://github.com/agentcontextdistributionprotocol/acdp-rs/actions/runs/42328766458)).

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
14. **[RFC-ACDP-0015 Transparency-Log Witness Cosigning](RFC-ACDP-0015-witness-cosigning.md)** *(0.4.0)* — independent witnesses observe a registry's RFC-ACDP-0012 checkpoints, verify consistency, and cosign what they saw; a consumer trusting any one honest witness inherits split-view protection and an external anchor for checkpoint time. Promotes RFC-ACDP-0009 §2.12; opens the 0.4.0 line.
15. **[RFC-ACDP-0016 Typed External Anchors](RFC-ACDP-0016-external-anchors.md)** *(0.5.0, Final)* — an optional, producer-signed `anchors` field lets a body genesis-link to a non-ACDP, content-addressed external artifact (a commitment, a sealed decision, any digest-identified object); core verification never resolves the external system and never dereferences the advisory `uri`. Opens the 0.5.0 line.
16. **[RFC-ACDP-0017 Chain Verification and Evidence Bundles](RFC-ACDP-0017-chain-verification.md)** *(0.5.0, Final)* — offline, as-of verification of a whole `derived_from` graph from an untrusted `acdp-evidence/1` bundle: deterministic walk, as-of and latest passes, drift, a byte-identical verdict with a sealable `as_of_digest`; adds registry-signed lifecycle event receipts and receipts on lineage members.
17. **[RFC-ACDP-0018 Retraction Recall](RFC-ACDP-0018-retraction-recall.md)** *(0.5.0, Final)* — a sequenced, durable `GET /changes` feed with one entry per retraction, supersession or key revocation, each carrying its signed evidence; stateless watch filters; optional HMAC-authenticated webhook hints that only say "pull now".
18. **[RFC-ACDP-0019 MCP Tool-Result Provenance](RFC-ACDP-0019-mcp-tool-result-provenance.md)** *(0.5.0, Final)* — an MCP signing proxy publishes each tool result it relays as a signed `acdp:mcp-tool-result` body (salted hashes by default, the result only when allowlisted) and returns the `acdp://` link in the result's `_meta`.
19. **[RFC-ACDP-0020 Registry Trust Lists](RFC-ACDP-0020-registry-trust-lists.md)** *(0.5.0, Final)* — a signed `acdp:trust-list` body says which registries a consumer relies on, for which producers and types, and when; issuer pins in configuration are the root of trust; serials defeat rollback; works offline inside an evidence bundle, with a separate `acdp-trust-report/1` beside the RFC-ACDP-0017 verdict.
20. **[RFC-ACDP-0021 Keyless Signing](RFC-ACDP-0021-keyless-signing.md)** *(0.5.0, Final)* — workloads sign with short-lived keys: a registry verifies an OIDC token or JWT-SVID, checks that the producer's `did:web` document lists the workload identity, and publishes a logged `acdp:key-attestation`; consumers place each signature in the attestation window by its receipt and report one of the existing three key statuses.
21. **[RFC-ACDP-0022 A2A Artifact Provenance](RFC-ACDP-0022-a2a-artifact-provenance.md)** *(0.5.0, Final)* — an A2A server agent signs each artifact it completes as a body of its own type, binds it to the task by salted hashes in a `metadata["acdp:a2a"]` record, and returns the `acdp://` link in `Artifact.metadata`; holders verify it and check retraction through the feed.

Reserved (no normative text, numbering pinned for future work):

- **[RFC-ACDP-0009 Extensions](RFC-ACDP-0009-extensions.md)** — post-publication relationships, attestations, push subscriptions, server-side traversal (§2.12 checkpoint witnessing promoted to RFC-ACDP-0015).

## RFC lifecycle

`Draft → Review → Final Comment Period → Release Candidate N → Final` (or `Rejected`). `Reserved` is a sidebar state for placeholder RFCs (e.g. RFC-ACDP-0009). See [governance/RFC-PROCESS.md](../governance/RFC-PROCESS.md) and [VERSIONING.md](../VERSIONING.md).
