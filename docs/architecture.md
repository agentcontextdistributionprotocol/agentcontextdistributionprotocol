# ACDP Architecture

This document is non-normative. It describes how ACDP fits together so an implementer can build a registry or client without re-reading every RFC.

## 1. Three roles, asymmetric

| Role | Does |
|---|---|
| **Producer** | Constructs a body, computes `content_hash`, signs, publishes. |
| **Registry** | Validates publish requests, assigns `ctx_id` / `lineage_id` / `origin_registry` / `created_at`, persists bodies, derives `status`, serves retrieval and search. |
| **Consumer** | Retrieves contexts, verifies signatures end-to-end, walks `derived_from` chains across registries. |

A single agent may play more than one role across different operations (a consumer that synthesizes its findings becomes a producer for the synthesized context). The same DID is used in all roles.

## 2. The flows

### 2.1 Publication

```
Producer ──POST /contexts──▶ Registry
Producer ◀── 201 Created ──── Registry
                            (ctx_id, lineage_id, status)
```

Registry processing in order: schema validate → algorithm check → signature verify → hash recompute → embedded-size check → payload-size check → embedding-model check → assign identifiers → compute lineage → validate supersession → persist → respond.

### 2.2 Retrieval

```
Consumer ──GET /contexts/{ctx_id}──▶ Registry
Consumer ◀── body + registry_state ── Registry

Consumer recomputes content_hash, verifies signature against
producer DID document. Verification is local and stateless
(no third-party call required after the producer DID is resolved).
```

### 2.3 Cross-registry lineage walk

```
Consumer holds context C with derived_from = [c1, c2, c3].
For each ci:
  parse acdp://<authority>/<uuid>
  GET https://<authority>/.well-known/acdp.json
  GET https://<authority>/contexts/{ci}
  verify producer signature
  recurse into ci.derived_from if needed
```

Each step is independent. The serving registry is **not** a trust anchor — only availability.

### 2.4 Discovery

```
Consumer ──GET /contexts/search?... ──▶ Registry
Consumer ◀── matches[], next_cursor ── Registry
```

Cursor pagination is opaque. Consumers loop until `next_cursor` is absent.

### 2.5 Supersession

```
Producer publishes v2 with supersedes = ctx_id_v1.
Registry verifies:
  - same agent_id
  - same lineage_id (computed from v1)
  - version = v1.version + 1
  - no other context already supersedes v1

v1's status becomes "superseded" on the next status query.
v1's body is unchanged.
```

## 3. The transport

ACDP v0.0.1 is JSON over HTTP, content type `application/acdp+json`. All endpoints accept and emit this type.

| Transport | Use |
|---|---|
| HTTPS / JSON | Normative. All endpoints. |

Binary transport bindings are out of scope for v0.0.1 and may be specified in a future version. Production deployments MUST use TLS (RFC-ACDP-0008 §4.6).

## 4. Where state lives

| State | Owner | Storage |
|---|---|---|
| Producer signing keys | Each producer | HSM, key vault, OS keystore. |
| Producer DID document | Each producer | Public — `did:web` or other. |
| Registry DID document | Each registry | Public — `did:web` matching the authority. |
| Bodies | Origin registry | Persistent. Immutable. Indefinite retention. |
| Registry-state | Origin registry | Persistent. Mutable in v0.0.1 only via supersession-driven status recomputation. |
| Embeddings | Each registry | Optional index. Out of scope on revocation/visibility. |
| Producer DID document cache | Consumers | TTL cache. |
| Capabilities document cache | Consumers | TTL cache (1 hour suggested). |
| Body cache | Consumers | Indefinite — bodies are immutable. Key by `ctx_id`, validate by `content_hash`. |

## 5. The big invariant

> A consumer's verification decision MUST be derivable from a single context body, the producer's public key (resolved from the producer's DID document), the JCS canonicalization algorithm, and the SHA-256 hash function.

If a consumer needs anything else to verify a context, the system is doing too much. ACDP exists to keep that invariant true.

## 6. What ACDP does not do

- It does not authenticate the transport. Run ACDP over TLS.
- It does not define audit logging beyond "log signature failures with enough context".
- It does not define a policy language for `metadata` shape — bind it via `schema_uri`.
- It does not define how data referenced by `data_refs.location` is accessed — defer to the underlying data store.
- It does not enforce visibility on the underlying data; visibility scopes the *metadata*, not the *data*.
- It does not specify how a producer's first context publication is authorized — that is operations (DID provisioning, registry account onboarding).

## 7. Reading order for implementers

1. [RFC-ACDP-0001 Core](../rfcs/RFC-ACDP-0001-core.md) — identifiers, JCS, hash, signature.
2. [RFC-ACDP-0002 Context Body](../rfcs/RFC-ACDP-0002-context-body.md) — body fields and constraints.
3. [RFC-ACDP-0003 Publish](../rfcs/RFC-ACDP-0003-publish.md) — POST flow and supersession.
4. [RFC-ACDP-0004 Retrieval](../rfcs/RFC-ACDP-0004-retrieval.md) — GET, lineage, derived status.
5. [RFC-ACDP-0005 Discovery](../rfcs/RFC-ACDP-0005-discovery.md) — search and similarity.
6. [RFC-ACDP-0006 Cross-Registry](../rfcs/RFC-ACDP-0006-cross-registry.md) — `acdp://` resolution.
7. [RFC-ACDP-0007 Capabilities](../rfcs/RFC-ACDP-0007-capabilities.md) — well-known doc + errors.
8. [RFC-ACDP-0008 Security](../rfcs/RFC-ACDP-0008-security.md) — what you must enforce.
