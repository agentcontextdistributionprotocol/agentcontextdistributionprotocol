# Threat Model — Quick Reference

The full normative threat model is [RFC-ACDP-0008 Security](../rfcs/RFC-ACDP-0008-security.md). This document is a non-normative summary.

## Threats addressed in v0.1.0

| Threat | Mechanism |
|---|---|
| Body tampering | `content_hash` recomputation + producer signature verification. |
| Lineage forgery | Deterministic `lineage_id` derivation; `derived_from` is part of the signed body. |
| Producer impersonation | DID-bound signing key; verifiers resolve from the producer's DID document. |
| Cross-registry impersonation | `origin_registry` is registry-assigned, not producer-controlled. |
| Existence leak via 404 differentiation | Visibility-restricted contexts return `not_found` (HTTP 404) indistinguishably from genuinely missing contexts. `visibility_denied` is internal logging only. |
| Replay of publish requests | Content-addressed bodies; idempotent at the content level. |
| DoS via oversize bodies | `limits.max_payload_bytes` and 64 KB embedded cap. |
| Spam / Sybil | Per-agent rate limiting required. |
| Algorithm downgrade | Algorithm named in body; verifier checks against registry's `supported_signature_algorithms` and the resolved key type. |
| Race on supersession | Registry serializes supersession events; the loser of a race gets `superseded_target`. |
| Server-side request forgery (SSRF) | Producer `did:web` resolution, cross-registry `acdp://` resolution, and external `data_refs[].location` fetches all dereference producer-controlled URLs. Each applies HTTPS-only, DNS-level IP-range filtering on every resolved address, IP pinning against rebinding, and same-authority redirect caps. See RFC-ACDP-0008 §4.7–§4.9 and RFC-ACDP-0006 §7. |
| Cross-tenant authorization bypass | ACDP defines no protocol-level tenant identifier. Where a deployment partitions by tenant, attribution MUST rest on an authenticated signal (deployment policy at a trust boundary, an authenticating gateway that stamps the tenant, or signed token claims) — never an unauthenticated `X-Tenant` header, hostname, or path segment. The §4.5 visibility checks run *after* tenant attribution and cannot catch a forged one. See RFC-ACDP-0008 §6.4. |
| Cross-registry leak of non-public contexts | Cross-registry `acdp://` resolution is public-only in v0.1.0 — no credential is forwarded to the remote registry, so `restricted`/`private` contexts return `not_found` (404) rather than leaking to an unauthenticated cross-registry caller. See RFC-ACDP-0006 §4.4. |

## Known gaps in v0.1.0

| Gap | Mitigation |
|---|---|
| No retraction | Use supersession; RFC-ACDP-0009 reserves a formal lifecycle-events mechanism. *(0.3.0)* Closed on registries advertising `acdp-registry-lifecycle`: RFC-ACDP-0013 specifies signed retraction/republication events, `status: retracted`, mark-not-delete. |
| No real-time key revocation push | Pull-based; consumers consult DID documents on retrieval. *(0.3.0)* RFC-ACDP-0014 makes the "this key is compromised" context normative (`key-revocation` type, time-scoped fail-closed semantics against receipt-attested publish times); still pull-based — a hiding registry remains detectable only where the RFC-ACDP-0012 transparency log is advertised. |
| No third-party attestations | RFC-ACDP-0009 reserves `attestations` in registry state. |
| No third-party `builds_on` claims | `derived_from` is producer-only. |
| No push subscriptions | Polling only; RFC-ACDP-0009 reserves push semantics. |
| No federation peering | Cross-registry resolution via `acdp://` is the federation primitive. |
| Registry-assigned fields bound only by registry honesty | *(0.2.0–0.4.0)* Closed incrementally where the optional trust profiles are advertised: registry receipts attest the assigned fields at publish (RFC-ACDP-0010); lineage-head receipts attest serve-time currency (RFC-ACDP-0011); the transparency log makes publish history append-only and provable (RFC-ACDP-0012); witness cosigning defends against a registry serving split views (RFC-ACDP-0015, Draft). |
| No multi-party / threshold signatures | Use `contributors` for joint authorship. |
| No quality scoring by registries | Consumers compute their own trust from DID + signature evidence. |

## Attack scenarios (summary)

### 1. Hostile registry serves a tampered body
**Result.** Consumer recomputes `content_hash` → mismatch ⇒ rejected. Or signature verification fails against the producer's DID document ⇒ rejected.

### 2. DNS spoof against a producer DID
**Result.** TLS validation at the producer's HTTPS endpoint catches the spoof unless the attacker also has a valid TLS cert. Even with a forged DID document, the attacker still needs the real private key to sign anything.

### 3. Producer rotates keys; old context
**Result.** The signing key has been removed from the producer's current DID document. The signature won't verify against the producer's *current* keys, and most DID methods don't expose historical key authorization data. v0.1.0 consumers SHOULD verify against the current DID document and either reject the old context (strict) or accept the residual risk (pragmatic). Under acdp/0.2.0, registry receipts close this gap where deployed: the receipt's `key_fingerprint` attests which key verified the body at publish time, and a rotated key the producer retained in `verificationMethod` then verifies with the distinguishable *historically authorized (receipt-attested)* status ([RFC-ACDP-0010 §10](../rfcs/RFC-ACDP-0010-registry-receipts.md)); receipt-less deployments still rely on external transparency logs. See RFC-ACDP-0008 §9.3.

### 4. Replay of a captured publish request
**Result.** Idempotent at the content level — the registry assigns a new `ctx_id` but the body is identical. Producers wishing to suppress duplicates deduplicate locally on `content_hash`.

### 5. Visibility-restricted lookup by an unauthorized consumer
**Result.** Registry returns `not_found` (HTTP 404). Consumer cannot distinguish "doesn't exist" from "exists but you can't see it".

Scenarios 1–5 above are the [RFC-ACDP-0008 §7](../rfcs/RFC-ACDP-0008-security.md#7-attack-scenarios) attack scenarios. One further class is worth calling out:

### 6. SSRF via a producer-controlled URL
**Setup.** A producer publishes a body whose `agent_id`/`signature.key_id` or `data_refs[].location` points at an internal address — e.g. `did:web:169.254.169.254` (cloud metadata) or `https://data-host.example/x` whose DNS resolves to `127.0.0.1`. A registry verifying the publish, or a consumer verifying end-to-end and fetching the DataRef, is induced to make the request.
**Result.** The resolver/fetcher resolves the hostname, rejects it because a resolved IP falls in a private/loopback/link-local/IMDS range, and refuses before connecting. The resolved IP is pinned so a second DNS lookup cannot rebind to an internal target, and a cross-authority redirect is refused. When DNS returns several addresses and *any* is forbidden, the **entire** resolution is rejected — filtering out the bad answers and connecting to the rest ("filter and proceed") is non-conformant (RFC-ACDP-0006 §7.1). "Same authority" for the redirect cap is scheme + host + effective port, so a redirect to the same host on a different port is refused (§7.5). A registry refusing a producer DID fails the publish with `key_resolution_failed`; a consumer treats the context (or the DataRef) as unverifiable. See [RFC-ACDP-0008 §4.7–§4.9](../rfcs/RFC-ACDP-0008-security.md#48-producer-did-resolution-ssrf-protection) and [RFC-ACDP-0006 §7](../rfcs/RFC-ACDP-0006-cross-registry.md#7-server-side-request-forgery-ssrf-protections).

### 7. Cross-tenant access via a forged tenant header
**Setup.** A multi-tenant deployment scopes contexts by tenant. An attacker authenticated to tenant A sets an `X-Tenant: B` header (or targets a path/hostname segment) hoping the registry attributes the request to tenant B before running visibility checks.
**Result.** A conformant deployment never trusts a client-supplied tenant indicator. Tenant attribution is established from an authenticated signal — deployment policy at a trust boundary, an authenticating gateway that stamps the tenant after authentication, or a signed token claim bound to the requester's DID — and any client-supplied value is stripped or overwritten. The §4.5 visibility checks then run *within* the correctly-attributed tenant. ACDP defines no protocol-level tenant field; this is a deployment obligation. See [RFC-ACDP-0008 §6.4](../rfcs/RFC-ACDP-0008-security.md#64-multi-tenancy-implementation-note).
