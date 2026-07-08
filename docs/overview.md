# ACDP Overview

This is a one-page architectural overview for ACDP. It is non-normative; the authoritative documents are the RFCs in [`rfcs/`](../rfcs/).

---

## The problem

When two autonomous agents need to share knowledge — across organizations, behind different identity providers, with no shared backend — they need a fast, defensible answer to four questions:

1. **What did you produce?**
2. **What evidence is it based on?**
3. **Who signed for it?**
4. **Is it still current?**

ACDP gives them one signed artifact that answers all four: the **context body**. The protocol around it specifies how the body is published, retrieved, discovered, and resolved across registry boundaries.

The signature covers the producer-controlled portion of the body; registry-assigned fields (`ctx_id`, `origin_registry`, `created_at`) are bound only by registry honesty in v0.1.0 (RFC-ACDP-0008 §9.1). Later version lines close that gap incrementally where the corresponding OPTIONAL profiles are deployed: registry **receipts** cryptographically attest the registry-assigned fields (0.2.0, RFC-ACDP-0010), **lineage-head receipts** attest "this was the current head as of T" (0.3.0, RFC-ACDP-0011), a **transparency log** makes the registry's publish history append-only and provable (0.3.0, RFC-ACDP-0012), and **witness cosigning** lets independent parties attest the log's checkpoints against split views (0.4.0 Draft, RFC-ACDP-0015).

---

## The shape

ACDP is a **publish/discover/verify** substrate. There is no central authority. Every registry is identified by its own DID; every context is verified locally against its producer's DID document.

```
Producer Agent                      ACDP Registry
   │                                       │
   │  POST /contexts                       │
   │  (signed, content-addressed body)     │
   ├─────────────────────────────────────▶│
   │                                       │
   │  ◀── ctx_id, lineage_id, status ─────│
   │                                       │
                                           │
Consumer Agent                             │
   │  GET /contexts/{ctx_id}               │
   ├─────────────────────────────────────▶│
   │  ◀── body + registry_state ──────────│
   │                                       │
   │  verify producer signature locally    │
   │  walk derived_from → cross-registry   │
```

A context body is JCS-canonicalized, SHA-256 hashed, and signed by the producer. Cross-registry references travel as `acdp://<authority>/<uuid>` URIs and are resolved via DNS + the target registry's `/.well-known/acdp.json` capabilities document.

---

## What each RFC adds

| RFC | Role |
|---|---|
| **0001 Core** | Identifiers (`acdp://`, `lin:`), JCS canonicalization, content hash, signatures, time format. |
| **0002 Context Body** | The immutable signed body — fields, types, data references, visibility. |
| **0003 Publish** | `POST /contexts`, supersession constraints, registry-assigned fields. |
| **0004 Retrieval** | `GET /contexts/{ctx_id}`, body-only retrieval, lineage queries, derived `status`. |
| **0005 Discovery** | Keyword search. Ranking within results is registry-defined; results are scoped to the requesting agent's effective audience. Semantic similarity is reserved for a future version (RFC-ACDP-0009 §2.9). |
| **0006 Cross-Registry** | `acdp://` resolution flow; the producer signature is the trust anchor, not the registry. |
| **0007 Capabilities** | `/.well-known/acdp.json` and the standard error envelope. |
| **0008 Security** | Threat model and required defenses for v0.1.0. |
| **0009 Extensions** | The reservation ledger: planned, non-normative capabilities with names pinned (post-publication relationships, attestations, push subscriptions, server-side traversal, …). Several reservations below have since been promoted. |
| **0010 Registry Receipts** *(0.2.0)* | Registry-signed receipt minted at publish, attesting the registry-assigned fields and which producer key verified. |
| **0011 Lineage-Head Receipts** *(0.3.0)* | Serve-time attestation that a context was the lineage head as of a timestamp. |
| **0012 Transparency Log** *(0.3.0)* | Append-only Merkle log of accepted publishes: signed checkpoints, inclusion and consistency proofs. |
| **0013 Lifecycle Events** *(0.3.0)* | Signed retraction/republication events; `status: retracted` is mark-not-delete — the body stays retrievable. |
| **0014 Key Revocation** *(0.3.0)* | The `key-revocation` context type and time-scoped fail-closed verification against receipt-attested publish times. |
| **0015 Witness Cosigning** *(0.4.0, Draft)* | Independent witnesses verify and cosign log checkpoints, protecting consumers from split views. |

Everything past 0008 is an **OPTIONAL profile layered on the frozen v0.1.0 core** — a registry advertises what it implements in `/.well-known/acdp.json`, and existing bodies, signatures, and `content_hash` values remain valid throughout.

---

## What ACDP doesn't do

- It doesn't authenticate the transport. Run ACDP over TLS.
- It doesn't issue identities. Producer identity comes from DIDs; ACDP only uses signatures.
- It doesn't define coordination, voting, or consensus semantics.
- It doesn't define what `metadata` means inside a body. That is the producer's domain.
- It doesn't delete. Bodies are permanent; corrections are made via supersession. Since 0.3.0, registries advertising the `acdp-registry-lifecycle` profile support **retraction as mark-not-delete** (RFC-ACDP-0013): a signed event flips `status` to `retracted`, but the body stays retrievable as the record of what was withdrawn.

See [`docs/non-goals.md`](non-goals.md) for the full list and rationale.

---

## Where to go next

- Implementing a registry? Start at [RFC-ACDP-0001 Core](../rfcs/RFC-ACDP-0001-core.md), then read in numbered order through 0008; add 0010–0015 for the optional trust profiles you plan to advertise (`make docs` prints the full order).
- Building a producer or consumer client? Read [`docs/integration-guide.md`](integration-guide.md).
- Trying to understand the threat model? Read [RFC-ACDP-0008 Security](../rfcs/RFC-ACDP-0008-security.md).
