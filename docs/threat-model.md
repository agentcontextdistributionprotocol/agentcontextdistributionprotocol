# Threat Model — Quick Reference

The full normative threat model is [RFC-ACDP-0008 Security](../rfcs/RFC-ACDP-0008-security.md). This document is a non-normative summary.

## Threats addressed in v0.0.1

| Threat | Mechanism |
|---|---|
| Body tampering | `content_hash` recomputation + producer signature verification. |
| Lineage forgery | Deterministic `lineage_id` derivation; `derived_from` is part of the signed body. |
| Producer impersonation | DID-bound signing key; verifiers resolve from the producer's DID document. |
| Cross-registry impersonation | `origin_registry` is registry-assigned, not producer-controlled. |
| Visibility leakage via similarity | Visibility-scoped similarity index; producers SHOULD omit `embedding` from sensitive contexts. |
| Existence leak via 404 differentiation | `visibility_denied` returns indistinguishable HTTP 404 / `not_found`. |
| Replay of publish requests | Content-addressed bodies; idempotent at the content level. |
| DoS via oversize bodies | `limits.max_payload_bytes` and 64 KB embedded cap. |
| Spam / Sybil | Per-agent rate limiting required. |
| Algorithm downgrade | Algorithm named in body; verifier checks against registry's `supported_signature_algorithms` and the resolved key type. |

## Known gaps in v0.0.1

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
**Result.** The signing key has been removed from the producer's current DID document. The signature won't verify against the producer's *current* keys, and most DID methods don't expose historical key authorization data. v0.0.1 consumers SHOULD verify against the current DID document and either reject the old context (strict) or accept the residual risk (pragmatic). External transparency logs or the registry-receipts mechanism reserved in [RFC-ACDP-0009 §2.7](../rfcs/RFC-ACDP-0009-extensions.md#27-registry-receipts-likely-v01) will close this gap in a future version. See [RFC-ACDP-0008 §9.3](../rfcs/RFC-ACDP-0008-security.md#93-historical-key-validity).

### 4. Replay of a captured publish request
**Result.** Idempotent at the content level — the registry assigns a new `ctx_id` but the body is identical. Producers wishing to suppress duplicates deduplicate locally on `content_hash`.

### 5. Visibility-restricted lookup by an unauthorized consumer
**Result.** Registry returns `not_found` (HTTP 404). Consumer cannot distinguish "doesn't exist" from "exists but you can't see it".

### 6. Embedding-based reconstruction on a restricted context
**Result.** Conformant registry scopes similarity by visibility. Defense-in-depth: producers SHOULD omit `embedding` on highly sensitive contexts.

See [RFC-ACDP-0008 Security](../rfcs/RFC-ACDP-0008-security.md) §7 for the full scenarios.
