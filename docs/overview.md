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

The signature covers the producer-controlled portion of the body; registry-assigned fields (`ctx_id`, `origin_registry`, `created_at`) are bound only by registry honesty in v0.1.0. See RFC-ACDP-0008 §9.1.

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

Reserved (numbering pinned, no normative text yet):

- **0009 Extensions** — retraction/lifecycle events, post-publication relationships, attestations, push subscriptions, server-side traversal.

---

## What ACDP doesn't do

- It doesn't authenticate the transport. Run ACDP over TLS.
- It doesn't issue identities. Producer identity comes from DIDs; ACDP only uses signatures.
- It doesn't define coordination, voting, or consensus semantics.
- It doesn't define what `metadata` means inside a body. That is the producer's domain.
- It doesn't retract. Once published, bodies are permanent in v0.1.0; corrections are made via supersession.

See [`docs/non-goals.md`](non-goals.md) for the full list and rationale.

---

## Where to go next

- Implementing a registry? Start at [RFC-ACDP-0001 Core](../rfcs/RFC-ACDP-0001-core.md), then read in numbered order through 0008.
- Building a producer or consumer client? Read [`docs/integration-guide.md`](integration-guide.md).
- Trying to understand the threat model? Read [RFC-ACDP-0008 Security](../rfcs/RFC-ACDP-0008-security.md).
