# ACDP Non-Goals and Design Boundaries

This document is non-normative. It explains what ACDP intentionally does not address. Each non-goal has a rationale; together they keep the spec narrow and shippable.

## 1. Coordination, voting, consensus

**Non-goal.** ACDP does not define how agents converge on shared decisions, vote on outcomes, or reach consensus.

**Rationale.** Coordination is a different problem from substrate. Coordination protocols often conflate "I have computed X" (substrate) with "we agree on X" (coordination). ACDP isolates the substrate so coordination protocols can layer on top without rebuilding it.

**What ACDP does instead.** Provides signed contexts that coordination protocols can reference, exchange, and build on.

## 2. Demand-pull and request semantics

**Non-goal.** ACDP does not specify a "request a context like X" mechanism.

**Rationale.** Demand-pull conflates discovery (what already exists) with commissioning (asking for something to be created). The latter is an agent-to-agent interaction; the substrate doesn't dictate how those happen.

**What ACDP does instead.** Provides keyword search for what already exists; commissioning lives in coordination protocols.

## 3. Marketplaces and payment

**Non-goal.** ACDP does not define payment, settlement, or marketplace semantics.

**Rationale.** Payment is jurisdiction-specific and rapidly evolving (stablecoins, micropayments, escrow). Embedding any of this in the substrate would couple it to choices that change faster than the protocol.

**What ACDP does instead.** Nothing. Payment, when needed, is built on top.

## 4. Reputation algorithms

**Non-goal.** ACDP does not define a universal reputation system.

**Rationale.** Reputation is highly domain-specific. A reputation model for financial agents differs fundamentally from one for science or coding agents. Reputation also evolves faster than protocol layers.

**What ACDP does instead.** Provides primitives (DID-bound signatures, signed `derived_from` chains, immutable bodies) so consumers can compute their own trust.

## 5. Retraction and lifecycle events

**Non-goal in v0.0.1.** Once published, a body is permanent.

**Rationale.** A retraction mechanism added casually creates more problems than it solves: who can retract? With what evidence? Are partial retractions allowed? v0.0.1 chooses absolute permanence so the substrate's invariants are obvious.

**What ACDP does instead.** Supersession: a producer publishes a corrected v2 with `supersedes: ctx_id_of_v1`. Original v1 stays in the registry but `status: superseded`. RFC-ACDP-0009 reserves a formal lifecycle-events mechanism for a future version.

## 6. Post-publication relationships from third parties

**Non-goal in v0.0.1.** Only the producer can claim that this context is `derived_from` other contexts.

**Rationale.** Third-party `builds_on` claims require a separate signing model and a trust evaluation model: do all third-party claims count? Most-trusted? Aggregated by some scheme? These choices belong in higher-order protocols.

**What ACDP does instead.** `derived_from` is producer-only and signed. RFC-ACDP-0009 reserves a `relationships` field in registry state for post-publication third-party claims.

## 7. Attestations (`reproduced` / `disputes`)

**Non-goal in v0.0.1.** No third-party can append a signed claim about another context.

**Rationale.** Same as §6 — attestations are post-publication signed claims and benefit from a fully-considered model.

**What ACDP does instead.** RFC-ACDP-0009 reserves an `attestations` field in registry state.

## 8. Push subscriptions

**Non-goal in v0.0.1.** Discovery is poll-based.

**Rationale.** Push delivery requires operational machinery — webhook signing, retry, backpressure, idempotency tokens. These don't belong in the substrate's first release.

**What ACDP does instead.** `derived_from` polling is sufficient for the lineage-discovery pattern. RFC-ACDP-0009 reserves push semantics under `/subscriptions`.

## 9. Server-side traversal (walks)

**Non-goal in v0.0.1.** Consumers walk `derived_from` chains client-side, one fetch per node.

**Rationale.** A `/walk` endpoint is a real optimization but introduces complexity (depth limits, circular-reference handling, partial-result delivery). Better to ship the substrate first.

**What ACDP does instead.** RFC-ACDP-0009 reserves `/contexts/{ctx_id}/walk`.

## 10. Federation peering and cross-registry query forwarding

**Non-goal.** ACDP does not specify how registries replicate from each other or forward queries.

**Rationale.** Federation requires policy negotiation, conflict resolution, and consistency models — ecosystem-wide problems, not protocol-level. SAML and OIDC federation took years to standardize after their base protocols.

**What ACDP does instead.** Cross-registry resolution via `acdp://` URIs (RFC-ACDP-0006) is the building block for any future federation. Consumers can query each registry separately and merge results client-side.

## 11. Encrypted bodies / field-level confidentiality

**Non-goal.** ACDP does not encrypt bodies. Bodies are signed, not encrypted.

**Rationale.** End-to-end encryption requires a key-distribution model (audience keys, group keys, threshold schemes). That is a separate problem domain.

**What ACDP does instead.** `data_refs` splitting — sensitive content stays behind the producer's data store ACL, only metadata about it is published. The visibility field scopes metadata discoverability.

## 12. Schema hosting

**Non-goal.** ACDP does not host the schemas referenced by `schema_uri`.

**Rationale.** Schema hosting is a separate concern (versioning, availability, schema evolution). ACDP only references schemas; the producer hosts them wherever they prefer.

**What ACDP does instead.** Defines `schema_uri` as an opaque URI consumers can fetch independently.

## 13. Hard deletion of any kind

**Non-goal.** Bodies are never deleted.

**Rationale.** Permanence is the v0.0.1 invariant. Hard deletion would make `derived_from` chains break unpredictably.

**What ACDP does instead.** Supersession for corrections; visibility-restriction for access control over time. (Storage-cost concerns for very old bodies are a deployment problem, not a protocol one.)

## 14. Multi-party / threshold signatures

**Non-goal.** A body has exactly one signing identity (`agent_id`).

**Rationale.** Multi-party signing complicates verification and requires a threshold-signing infrastructure that not every producer has.

**What ACDP does instead.** `contributors` field for joint authorship — the single signing identity is one of them. The signing identity takes responsibility for the body's content.

## 15. Quality scoring by registries

**Non-goal.** Registries don't rank or score the contexts they hold.

**Rationale.** Quality is consumer-specific. A registry that scored contexts would impose its model on every consumer.

**What ACDP does instead.** Returns matches and lets consumers compute their own ranking from `derived_from` evidence, agent reputation models, and domain-specific signals.

## 16. Audit-grade time anchoring

**Non-goal.** `created_at` is the registry's clock.

**Rationale.** Strong time anchoring requires external time-stamp authorities, blockchain anchoring, or similar — high-cost mechanisms not every deployment needs.

**What ACDP does instead.** Producers wishing strong time guarantees can publish a separate context referencing an external time-stamp service in `data_refs`, bound to the original by `derived_from`.
