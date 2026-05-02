# RFC-ACDP-0006
# Agent Context Description Protocol (ACDP) — Cross-Registry References

**Document:** RFC-ACDP-0006
**Version:** 0.0.1-draft
**Status:** Community Standards Track (Draft)

This RFC specifies how consumers resolve `acdp://` references that point to contexts on a different registry. It depends on RFC-ACDP-0001 (Core) and RFC-ACDP-0007 (Capabilities).

---

## 1. Status of This Memo

Draft. Backward-incompatible changes remain possible until Final.

---

## 2. Motivation

ACDP contexts produced in one registry can be referenced from any other registry — a producer's `derived_from` array, an analyst's manual citation, an alert's evidence chain. Cross-registry references are the mechanism by which knowledge accumulates beyond a single deployment.

The `acdp://<authority>/<uuid>` URI scheme is the basis for cross-registry references. The `<authority>` component is the DNS hostname of the origin registry; resolution starts from there.

---

## 3. Registry Identity

Every ACDP registry MUST have:

- A DID, typically `did:web:<hostname>`. The hostname MUST equal the authority component used in `ctx_id` URIs the registry mints.
- A published key set in its DID document.
- A `/.well-known/acdp.json` capabilities document (RFC-ACDP-0007 §3) declaring its `registry_did`.

Two registries MUST NOT share an authority. The DNS hostname is the unique key.

---

## 4. Resolution

When a consumer encounters an `acdp://other-registry.example/uuid` reference and wishes to retrieve it, resolution proceeds:

### 4.1 Steps

1. **Parse the URI.** Extract `<authority>` and the UUID. Reject URIs that do not match the syntax in RFC-ACDP-0001 §5.4.
2. **Resolve the registry.** Construct the registry's well-known URL: `https://<authority>/.well-known/acdp.json`. Fetch and parse. Verify `acdp_version`, `registry_did`, `supported_signature_algorithms`.
3. **Verify the registry's DID.** Optionally resolve `registry_did` and verify the DID document's web binding matches `<authority>`.
4. **Issue retrieval.** `GET https://<authority>/contexts/{encoded_ctx_id}` per RFC-ACDP-0004 §2.
5. **Verify the body's signature.** Resolve the producing agent's DID document via `body.signature.key_id`, fetch the public key, verify the signature against `body.content_hash`.
6. **Verify the content hash.** Recompute `content_hash` over the JCS-canonicalized body (with the exclusion set from RFC-ACDP-0001 §5.7) and confirm it matches.
7. **Walk further references.** For each entry in `body.derived_from`, repeat from step 1 if the consumer needs the predecessor.

### 4.2 Trust model

The trust split is critical:

- **Registry trust extends only to availability.** The serving registry can be untrusted, compromised, or adversarial — the consumer MUST NOT rely on it for context authenticity.
- **The producing agent's signature is the trust anchor.** A context produced by a trusted agent remains trustworthy even if served by an untrusted registry, because the agent signature is checkable end-to-end against the agent's DID document.

A consumer that finds a `derived_from` reference to a context on a registry it does not recognize SHOULD nonetheless attempt resolution; the producing agent's signature is the deciding factor.

### 4.3 Caching

Bodies are immutable. Consumers MAY cache fetched bodies indefinitely, keyed by `ctx_id` and validated by `content_hash`. Registry state (status) is mutable; consumers MUST NOT cache `registry_state.status` beyond the freshness window appropriate to their use case.

---

## 5. Failure Modes

| Failure | Behavior |
|---|---|
| Authority does not resolve in DNS | Treat the reference as unresolvable. The consumer SHOULD log this and proceed without the predecessor. |
| `/.well-known/acdp.json` returns non-200 | Treat as unresolvable. |
| `acdp_version` is unknown | Apply forward-compatibility (RFC-ACDP-0001 §6) — proceed with the operations the consumer understands. |
| Retrieval returns 404 | The reference is unresolvable. The consumer MUST NOT infer that the context never existed; only that it is not currently retrievable. |
| Signature verification fails | The retrieved body is **untrustworthy**. The consumer MUST NOT use it as evidence regardless of which registry served it. |
| Hash mismatch | Same as signature failure — body is corrupt. |
| Visibility-restricted (404 with `visibility_denied` semantic) | The reference is not accessible to the consumer. |

---

## 6. Out of Scope

The following are not specified by ACDP and are intentional non-goals (RFC-ACDP-0009 may revisit them):

- **Federation peering** between registries.
- **Cross-registry query forwarding** (search/discovery across registries from a single endpoint).
- **Cross-registry caching protocols** beyond plain HTTP caching.
- **Cross-registry supersession** (publishing a v2 on a different registry from v1). Optional for v0.0.1; see RFC-ACDP-0003 §3.1.
- **Server-side traversal** (`/walk`). Reserved in RFC-ACDP-0009.

Registries MAY implement these as private optimizations — but they are not part of the protocol.

---

## 7. Security Considerations

See [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md). Specific to cross-registry resolution:

- The serving registry is **not** a trust anchor. Consumers MUST verify the producing agent's signature on every retrieved context.
- DNS resolution itself is not authenticated unless DNSSEC is in use. **The producer's signature is the actual trust anchor.** An attacker who can spoof DNS or compromise the registry still cannot forge a valid producer signature without the producer's private key.
- Public agent DIDs (`did:web`) are subject to DNS and HTTPS hijacking; consumers SHOULD pin or cache producer keys when feasible.
- A consumer following an `acdp://` reference is making an outbound HTTP request to a hostname controlled by an external party. Consumers operating in restrictive environments SHOULD apply egress policy.

---

## 8. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
- [DID-CORE] W3C, "Decentralized Identifiers (DIDs) v1.0".
- [RFC 1035] Mockapetris, P., "Domain names — implementation and specification".
