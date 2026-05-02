# RFC-ACDP-0008
# Agent Context Description Protocol (ACDP) — Security & Threat Model

**Document:** RFC-ACDP-0008
**Version:** 0.0.1-draft
**Status:** Community Standards Track (Draft)

This RFC specifies the threat model for ACDP v0.0.1 and the defenses every implementation MUST provide. It depends on the entire core RFC stack (0001–0007).

---

## 1. Status of This Memo

Draft. Backward-incompatible changes remain possible until Final.

---

## 2. Threat Surface

ACDP exists in an environment where:

- Producers and consumers are autonomous agents acting on behalf of organizations.
- Registries are distributed services, possibly operated by different parties.
- Cross-registry references mean a consumer may pull data from a registry it does not control.
- Networks are partially adversarial (DNS spoofing, MitM on non-TLS hops, hostile intermediaries).
- Identities are pluggable; both producer DIDs and registry DIDs are subject to standard PKI risks.

The threat surface is therefore: **the entire path from producer's signing key, through the registry, across the network, to the consumer's verification logic — plus the surrounding metadata operations (discovery, capabilities, errors).**

---

## 3. Threats Addressed in v0.0.1

| Threat | Mechanism |
|---|---|
| **3.1 Body tampering** | `content_hash` is recomputed on retrieval; signature is verified against the producer's DID document. Any modification to a non-excluded field changes the hash. |
| **3.2 Lineage forgery** | `lineage_id` is deterministically derived from the first version's `ctx_id`. The registry verifies producer-supplied `lineage_id` matches the derived value. The chain is part of the signed body. |
| **3.3 Producer impersonation** | The signing key is bound to a DID. Verifiers resolve the key from the producer's DID document (e.g. `did:web` over HTTPS, with TLS verification). |
| **3.4 Cross-registry impersonation** | `origin_registry` is a registry-assigned field, not producer-controlled. The serving registry's authority must match the URI authority. |
| **3.5 Visibility leakage via similarity** | Embeddings can leak content. Restricted/private contexts SHOULD omit `embedding`; registries MUST scope similarity results by visibility. |
| **3.6 Existence-leak via 404 differentiation** | Visibility-restricted contexts return `not_found`/HTTP 404 indistinguishably from genuinely missing contexts. |
| **3.7 Replay of publish requests** | Bodies are content-addressed; "the same body twice" is idempotent at the content level (the registry assigns a new `ctx_id`, but the content is identical). Producer-side deduplication uses `content_hash`. TLS prevents on-wire replay reordering. |
| **3.8 DoS by oversize bodies** | `limits.max_payload_bytes` and `embedded_too_large` (64 KB cap) enforce upper bounds. |
| **3.9 Spam / Sybil** | Per-agent rate limiting is REQUIRED (§4). |
| **3.10 Algorithm downgrade** | Signature algorithm is named in the body (`signature.algorithm`) and MUST be in the registry's `supported_signature_algorithms`. Verifiers determine the algorithm from the resolved key — this prevents downgrade attacks where an attacker substitutes a weaker algorithm. |
| **3.11 Race on supersession** | The registry serializes supersession events: a `superseded_target` error is returned for the loser of a race. |

---

## 4. Required Defenses

### 4.1 Cryptographic core

- Implementations MUST support `ed25519` ([RFC 8032]).
- Implementations MUST use a cryptographically secure RNG for UUIDs (`ctx_id` UUID component).
- Private keys MUST be stored in secure storage (HSM, key vault, OS keystore).
- Implementations MUST fail closed on signature verification errors — there is no `soft_fail` mode in v0.0.1.

### 4.2 Input validation

- All inputs MUST be validated against the JSON Schemas before processing.
- Implementations MUST reject any publish request that does not validate against `acdp-publish-request.schema.json`.
- Implementations MUST reject any request whose body exceeds `limits.max_payload_bytes`.
- Implementations MUST reject embedded data exceeding 64 KB decoded.

### 4.3 Rate limiting

- Registries MUST rate-limit `POST /contexts` per `agent_id` (the signing producer).
- Registries SHOULD rate-limit retrieval and search endpoints per requesting principal.
- Rate-limit responses MUST use `rate_limited` (HTTP 429) and SHOULD include a `Retry-After` header when bounded.

### 4.4 Signature verification

- Registries MUST verify producer signatures at publish time. Verification failures MUST result in rejection with `invalid_signature`.
- Consumers MUST verify producer signatures on every retrieved context they rely on. Trusting the registry alone is **not** sufficient.
- When a producer rotates keys, prior signatures remain valid as long as the old key was valid at the operation's `created_at`. Verifiers MUST consult the producer's DID document for key validity windows.

### 4.5 Visibility enforcement

- Registries MUST scope discovery and retrieval responses by the requesting agent's effective visibility.
- For `visibility: restricted` and `private`, registries MUST return `not_found` (HTTP 404) to non-audience requesters. The `visibility_denied` semantic is internal logging only.
- Registries MUST NOT include restricted/private contexts in `total_estimate`.

### 4.6 Transport

- Production deployments MUST use TLS for all ACDP endpoints.
- Registries SHOULD set strong cache headers on body responses (immutable) and short cache headers on registry-state responses.
- Registries MUST NOT echo unsanitized request content in `error.message`.

### 4.7 Cross-registry

- Consumers resolving `acdp://` references MUST verify the producing agent's signature on every retrieved context. They MUST NOT trust the serving registry to vouch for context authenticity. Registry trust extends only to availability.
- DNS spoofing or registry compromise MUST NOT be sufficient to forge a context — the producer's signature is the trust anchor.

---

## 5. Known Gaps (Acknowledged)

| Gap | Reason | Mitigation in v0.0.1 |
|---|---|---|
| **No retraction** | Permanent publication is the v0.0.1 invariant. | Use supersession to publish corrections. RFC-ACDP-0009 reserves a formal lifecycle-events mechanism. |
| **No real-time key revocation push** | Out of scope for the substrate. | Pull-based; consumers consult DID documents. Producers can publish a "this key is compromised" context as a soft signal. |
| **No third-party attestations** | Out of scope for v0.0.1. | RFC-ACDP-0009 reserves `attestations` in registry state. |
| **No third-party `builds_on` claims** | Out of scope for v0.0.1. | `derived_from` is producer-only; downstream consumers can publish their own `derived_from` context. |
| **No push subscriptions** | Polling is the v0.0.1 model. | RFC-ACDP-0009 reserves push semantics. |
| **No federation peering** | Out of scope. | Cross-registry resolution via `acdp://` is the federation primitive. |
| **No multi-party / threshold signatures** | Out of scope. | Use `contributors` for joint authorship; the single signing identity is one of them. |
| **No quality scoring by registries** | Out of scope. | Consumers compute their own trust models from DID + signature evidence. |
| **No audit-grade time anchoring** | Out of scope. | `created_at` is registry clock; producers wishing strong time guarantees use external time-stamp services and embed those as `data_refs`. |

---

## 6. Attack Scenarios

### 6.1 Hostile registry serves a tampered body

**Setup.** A consumer fetches `acdp://hostile.example/uuid`. The registry returns a modified body.

**Result.** The consumer recomputes `content_hash` over the JCS-canonicalized body and compares against `body.content_hash`. Mismatch ⇒ rejected. **Or**, the consumer verifies `body.signature` against the producer's resolved public key and gets a verification failure ⇒ rejected.

### 6.2 DNS spoof against a producer DID

**Setup.** An attacker spoofs DNS for `did:web:producer.example`. The consumer resolves what the attacker wants.

**Result.** TLS certificate validation at the producer's HTTPS endpoint catches the spoof unless the attacker has also obtained a valid TLS cert for the hostname. With DNSSEC + cert pinning, both are required to forge a context. Even with a forged DID document, the attacker must also produce a signature under the **real** producer's private key for any context the consumer is asking to verify — the existing signed contexts are tamper-evident.

### 6.3 Producer rotates keys; old context still valid

**Setup.** Producer P signed `ctx://reg/abc` with key K1 at `created_at=t1`. P later rotates to K2; K1 is removed from P's DID document at `t2`.

**Result.** A consumer at `t3 > t2` verifying the context resolves P's DID document, finds the historical key validity window for K1 (`[t0, t2]`), confirms `created_at=t1` falls within it, and verifies the signature with K1. The context remains valid.

### 6.4 Replay of a captured publish

**Setup.** An attacker captures a producer's `POST /contexts` request and replays it.

**Result.** Replay produces a duplicate publication. The body is content-addressed; the duplicate has identical `content_hash`. The registry assigns a new `ctx_id` (collision is statistically impossible). Idempotent at the content level. Producers wishing to suppress duplicate publication SHOULD deduplicate locally on `content_hash`.

### 6.5 Visibility-restricted lookup by unauthorized consumer

**Setup.** Consumer C requests `GET /contexts/{ctx_id}` for a context with `visibility: restricted` and `audience` not including C's DID.

**Result.** Registry returns `not_found` (HTTP 404). C cannot distinguish "doesn't exist" from "exists but you can't see it".

### 6.6 Embedding-based content reconstruction on a restricted context

**Setup.** A restricted context includes an `embedding`. An unauthorized consumer crafts similarity queries to reconstruct the underlying content.

**Result.** Conformant registries scope similarity search by visibility. The unauthorized consumer's `POST /contexts/similar` requests will not surface the restricted context in results. **Producers SHOULD additionally omit embeddings from highly sensitive contexts, even on conformant registries, as defense in depth.**

---

## 7. Security Considerations Summary

ACDP's security model rests on three pillars:

1. **Content addressing.** Bodies are JCS-canonicalized and SHA-256 hashed; any change is detectable.
2. **Producer signatures.** The trust anchor is the producer's DID document, not the registry. Registries are availability layers.
3. **Visibility scoping.** Registries enforce audience-based visibility on discovery and retrieval; embeddings are not exempt.

These three pillars are the minimum. Implementations MUST NOT relax any of them. Operators deploying ACDP in regulated environments SHOULD layer additional controls (egress policy, DID-document pinning, hardware-backed signing keys) on top of the protocol minimum.

---

## 8. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md)
- [RFC-ACDP-0003 Publish](RFC-ACDP-0003-publish.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0005 Discovery](RFC-ACDP-0005-discovery.md)
- [RFC-ACDP-0006 Cross-Registry References](RFC-ACDP-0006-cross-registry.md)
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md)
- [docs/threat-model.md](../docs/threat-model.md) — non-normative summary.
- [DID-CORE] W3C, "Decentralized Identifiers (DIDs) v1.0".
- [RFC 8032] Josefsson, S. and I. Liusvaara, "Edwards-Curve Digital Signature Algorithm (EdDSA)".
