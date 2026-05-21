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

## Known gaps in v0.1.0

| Gap | Mitigation |
|---|---|
| No retraction | Use supersession; RFC-ACDP-0009 reserves a formal lifecycle-events mechanism. |
| No real-time key revocation push | Pull-based; consumers consult DID documents on retrieval. |
| No third-party attestations | RFC-ACDP-0009 reserves `attestations` in registry state. |
| No third-party `builds_on` claims | `derived_from` is producer-only. |
| No push subscriptions | Polling only; RFC-ACDP-0009 reserves push semantics. |
| No federation peering | Cross-registry resolution via `acdp://` is the federation primitive. |
| No multi-party / threshold signatures | Use `contributors` for joint authorship. |
| No quality scoring by registries | Consumers compute their own trust from DID + signature evidence. |

## Attack scenarios (summary)

### 1. Hostile registry serves a tampered body
**Result.** Consumer recomputes `content_hash` → mismatch ⇒ rejected. Or signature verification fails against the producer's DID document ⇒ rejected.

### 2. DNS spoof against a producer DID
**Result.** TLS validation at the producer's HTTPS endpoint catches the spoof unless the attacker also has a valid TLS cert. Even with a forged DID document, the attacker still needs the real private key to sign anything.

### 3. Producer rotates keys; old context
**Result.** The signing key has been removed from the producer's current DID document. The signature won't verify against the producer's *current* keys, and most DID methods don't expose historical key authorization data. v0.1.0 consumers SHOULD verify against the current DID document and either reject the old context (strict) or accept the residual risk (pragmatic). External transparency logs or the registry-receipts mechanism reserved in [RFC-ACDP-0009 §2.7](../rfcs/RFC-ACDP-0009-extensions.md#27-registry-receipts) will close this gap in a future version. See [RFC-ACDP-0008 §9.3](../rfcs/RFC-ACDP-0008-security.md#93-historical-key-validity).

### 4. Replay of a captured publish request
**Result.** Idempotent at the content level — the registry assigns a new `ctx_id` but the body is identical. Producers wishing to suppress duplicates deduplicate locally on `content_hash`.

### 5. Visibility-restricted lookup by an unauthorized consumer
**Result.** Registry returns `not_found` (HTTP 404). Consumer cannot distinguish "doesn't exist" from "exists but you can't see it".

Scenarios 1–5 above are the [RFC-ACDP-0008 §7](../rfcs/RFC-ACDP-0008-security.md#7-attack-scenarios) attack scenarios. One further class is worth calling out:

### 6. SSRF via a producer-controlled URL
**Setup.** A producer publishes a body whose `agent_id`/`signature.key_id` or `data_refs[].location` points at an internal address — e.g. `did:web:169.254.169.254` (cloud metadata) or `https://data-host.example/x` whose DNS resolves to `127.0.0.1`. A registry verifying the publish, or a consumer verifying end-to-end and fetching the DataRef, is induced to make the request.
**Result.** The resolver/fetcher resolves the hostname, rejects it because a resolved IP falls in a private/loopback/link-local/IMDS range, and refuses before connecting. The resolved IP is pinned so a second DNS lookup cannot rebind to an internal target, and a cross-authority redirect is refused. A registry refusing a producer DID fails the publish with `key_resolution_failed`; a consumer treats the context (or the DataRef) as unverifiable. See [RFC-ACDP-0008 §4.7–§4.9](../rfcs/RFC-ACDP-0008-security.md#48-producer-did-resolution-ssrf-protection) and [RFC-ACDP-0006 §7](../rfcs/RFC-ACDP-0006-cross-registry.md#7-server-side-request-forgery-ssrf-protections).
