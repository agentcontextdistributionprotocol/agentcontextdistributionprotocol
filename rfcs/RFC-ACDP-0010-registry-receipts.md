# RFC-ACDP-0010
# Agent Context Distribution Protocol (ACDP) — Registry Receipts

**Document:** RFC-ACDP-0010
**Version:** 0.2.0
**Status:** Community Standards Track (Final)

This RFC specifies **registry receipts**: registry-signed attestations that bind the registry-assigned identifiers of a context (`ctx_id`, `lineage_id`, `origin_registry`, `created_at`) and the producer's `content_hash` and signing-key fingerprint to the registry's DID. It promotes the RFC-ACDP-0009 §2.7 reservation to a full normative specification and is the anchor of the ACDP 0.2.0 Trust & Hardening program. It depends on RFC-ACDP-0001 (Core), RFC-ACDP-0003 (Publish), RFC-ACDP-0004 (Retrieval), and RFC-ACDP-0007 (Capabilities & Errors).

---

## 1. Status of This Memo

This document is a **Final** ACDP specification (acdp/0.2.0). It is stable for the 0.2.0 line; subsequent breaking changes require a new RFC and a version bump per [VERSIONING.md](../VERSIONING.md). It was promoted from Draft to Final on 2026-07-05, the VERSIONING.md gate having been met: the conformance fixtures it defines (`rcpt-001..004`, `fp-001`, `rot-001`, `fed-009`) pass against two independent interoperating implementations (see [CHANGELOG.md](../CHANGELOG.md) for the promotion record).

The wire shape specified here is byte-identical to the shape reserved by RFC-ACDP-0009 §2.7 since v0.1.0. v0.1.0 libraries already carry the preserve-verbatim obligation for `registry_receipt` (RFC-ACDP-0009 §2.7); nothing in this document invalidates any v0.1.0 body, signature, or `content_hash`.

---

## 2. Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described in BCP 14 ([RFC 2119], [RFC 8174]) when, and only when, they appear in all capitals.

| Term | Definition |
|---|---|
| **Receipt** | A registry-signed JSON object binding the registry-assigned identity fields of one context, the producer's `content_hash`, and the fingerprint of the producer key the registry resolved at publish time, to the registry's DID. |
| **Receipt preimage** | The receipt object with the `signature` member removed, JCS-canonicalized (RFC 8785). The input to the receipt hash. |
| **Receipt hash** | `"sha256:" + lowercase_hex(SHA-256(receipt preimage))`. The string whose ASCII bytes are signed. |
| **Key fingerprint** | `"sha256:" + lowercase_hex(SHA-256(raw_public_key_bytes))` over the algorithm-specific raw public-key encoding of §6. |
| **Receipt signing key** | An Ed25519 or ECDSA-P256 key published in the registry's DID document and referenced by `registry_receipt.signature.key_id`. Distinct in role (and SHOULD be distinct in key material) from any TLS or producer key. |

---

## 3. Motivation

ACDP v0.1.0 producer signatures bind producer-controlled content but do not bind `ctx_id`, `lineage_id`, `origin_registry`, or `created_at` (RFC-ACDP-0001 §5.9, RFC-ACDP-0008 §9.1). A malicious or compromised registry can republish a producer's signed content under a different identifier, attribute it to a different registry, or backdate it — and producer-signature verification still passes. Timestamps and registry attribution are assertions, not proofs.

A verified receipt closes this gap for the response it accompanies: the registry has cryptographically committed, under its own DID-bound key, to *exactly this binding* of identifiers, time, content hash, and producer key. The registry can still lie at mint time (see §13), but it can no longer lie *differently to different consumers* without producing conflicting signed evidence, and its claims become attributable and non-repudiable.

The receipt's `key_fingerprint` additionally records **which producer key the registry resolved and verified at publish time**, which is the missing input for verifying historical contexts after producer key rotation (RFC-ACDP-0008 §9.3). See §10.

---

## 4. Receipt Object

A receipt is a JSON object with exactly the following members. The canonical schema is [`schemas/json/acdp-registry-receipt.schema.json`](../schemas/json/acdp-registry-receipt.schema.json) (closed: `additionalProperties: false`).

| Field | Type | Required | Description |
|---|---|---|---|
| `registry_did` | string | Yes | The minting registry's DID. MUST be `did:web:<authority>` where `<authority>` equals the registry's serving authority (the same value as `capabilities.registry_did`, RFC-ACDP-0007 §3.1). Registries are DNS-bound servers; `registry_did` remains `did:web`-only in 0.2.0 even though producers may use `did:key` (RFC-ACDP-0001 §5.4). |
| `ctx_id` | string | Yes | The registry-assigned context identifier (RFC-ACDP-0001 §5.5). |
| `lineage_id` | string | Yes | The registry-derived lineage identifier (RFC-ACDP-0001 §5.6). |
| `origin_registry` | string | Yes | The registry-assigned origin authority (bare DNS hostname, RFC-ACDP-0002 §3.1). MUST equal the authority component of `ctx_id` and the method-specific identifier of `registry_did`. |
| `created_at` | string | Yes | The registry-assigned creation timestamp, canonical millisecond-precision RFC 3339 UTC (RFC-ACDP-0001 §5.3). MUST be byte-identical to `body.created_at`. |
| `content_hash` | string | Yes | The body's `content_hash` as verified by the registry at publish time (RFC-ACDP-0001 §5.7). |
| `key_fingerprint` | string | Yes | The §6 fingerprint of the producer public key the registry resolved for `body.signature.key_id` and used to verify the body signature at publish time. |
| `signature` | object | Yes | The registry's signature over the receipt hash, using the `signature` object shape of RFC-ACDP-0001 §5.8 (`algorithm`, `key_id`, `value`; closed schema). `signature.key_id` MUST be a DID URL under `registry_did`. |

All receipt fields other than `signature` are covered by the receipt signature. There is no exclusion set for receipts other than `signature` itself — the receipt is minted by the registry after identifier assignment, so every field is known to the signer.

Receipts are **immutable once minted**: a registry MUST return the identical receipt (byte-identical after JCS canonicalization) for the same `ctx_id` on every response that carries one. Re-minting with a different `created_at`, fingerprint, or signature is non-conformant.

---

## 5. Signing Construction

The receipt signing construction **reuses the producer construction of RFC-ACDP-0001 §5.7–§5.8 exactly**. Implementations MUST NOT introduce a second canonicalization or signing-input framing:

1. **Preimage.** Remove the `signature` member from the receipt object. JCS-canonicalize (RFC 8785) the remainder.
2. **Hash.** `receipt_hash = "sha256:" + lowercase_hex(SHA-256(preimage_bytes))`.
3. **Signing input.** The **ASCII bytes of the full `receipt_hash` string** — `sha256:` prefix included. Implementations MUST NOT sign the raw 32-byte digest and MUST NOT sign the hex substring without the prefix (the same rule as RFC-ACDP-0001 §5.8).
4. **Signature.** Sign with the registry's receipt signing key. `signature.algorithm` follows the RFC-ACDP-0001 §5.10 vocabulary (`ed25519` mandatory-to-implement; `ecdsa-p256` optional, IEEE 1363 r‖s wire form per `registries/signature-algorithms.md`). `signature.value` is the base64-encoded signature bytes.

The golden vector `rcpt-001-receipt-golden.json` pins the canonical preimage bytes, the receipt hash, and an Ed25519 signature end-to-end; it is executed arithmetically by `scripts/conformance-runner.py`, exactly like `sig-001`.

---

## 6. Key Fingerprint Encoding (NORMATIVE)

`key_fingerprint` (in receipts, and anywhere a future version reuses it) is computed **byte-for-byte** as:

```
key_fingerprint = "sha256:" + lowercase_hex(SHA-256(raw_public_key_bytes))
```

where `raw_public_key_bytes` is the algorithm-specific raw encoding:

| Algorithm | `raw_public_key_bytes` | Length |
|---|---|---|
| `ed25519` | The raw Ed25519 public key (RFC 8032 encoding). | 32 bytes |
| `ecdsa-p256` | The **SEC1 compressed point**: `0x02` or `0x03` parity prefix followed by the 32-byte big-endian affine `x` coordinate. | 33 bytes |

Notes:

- For `ecdsa-p256` the fingerprint input is the *compressed* point even though v0.1.0 DID documents publish the uncompressed `(x, y)` JWK pair (`registries/signature-algorithms.md`). Verifiers MUST compress the resolved point before fingerprinting: prefix `0x02` when `y` is even, `0x03` when `y` is odd. This makes the fingerprint independent of the DID document's serialization choices.
- The fingerprint input is the key bytes alone — no multicodec prefix, no DER/SPKI framing, no base64. A fingerprint computed over a 44-byte SPKI prefix-wrapped key, a `z`-multibase string, or a JWK serialization is **wrong** and will fail `fp-001`.
- The hex MUST be lowercase; the prefix MUST be exactly `sha256:`.

Divergence in this encoding is the receipt-layer equivalent of the timestamp-precision hash bug — it would produce verifiers that reject every honest receipt. The fixture `fp-001-key-fingerprint-vectors.json` pins one test vector per algorithm and is executed arithmetically by the conformance runner. Every SDK MUST reproduce it byte-for-byte before claiming receipt support.

---

## 7. Issuance

Registries advertising the `acdp-registry-receipts` profile (§11):

1. **MUST mint the receipt at publish time**, atomically with persistence (RFC-ACDP-0003 §2.1 step 12): the body and its receipt commit together, or neither does. A registry that persists a body but cannot durably store/derive its receipt MUST fail the publish.
2. **MUST return the receipt in the publish response** as the optional top-level `registry_receipt` member (RFC-ACDP-0003 §4). The producer thereby gains immediate possession of its proof of publication — it does not have to trust a later retrieval to obtain it.
3. **MUST return the receipt on `GET /contexts/{ctx_id}`** as the top-level `registry_receipt` member of the full-retrieval envelope, outside `body` and `registry_state` (RFC-ACDP-0004 §2.1) — the position reserved since v0.1.0 (RFC-ACDP-0009 §2.7).
4. **MUST NOT add the receipt to `GET /contexts/{ctx_id}/body`.** The body-only endpoint returns the bare signed body and keeps its immutable-cache story unchanged (RFC-ACDP-0004 §2.2).

There is **no `receipt_unavailable` condition**: a registry advertising the profile MUST always mint and always serve receipts for contexts published while the profile was advertised, and SHOULD backfill receipts for previously published contexts (a backfilled receipt attests the stored `created_at`, not the backfill time). A registry that cannot meet this MUST NOT advertise the profile. Consumers therefore treat a missing receipt from a profile-advertising registry as a registry fault, not a soft degradation.

The receipt is OUTSIDE the body. It is never part of the producer's `content_hash` preimage (RFC-ACDP-0001 §5.7 exclusion-set registry), and `registry_receipt` MUST NOT appear inside a stored body.

---

## 8. Verification Procedure (NORMATIVE)

A consumer verifying a receipt MUST perform **all** of the following checks. The cross-checks (steps 2–5) are the security value — a receipt whose signature verifies but whose bindings are not cross-checked proves nothing.

1. **Recompute and verify the receipt signature.** JCS-recompute the receipt preimage (§5), recompute the receipt hash, resolve the key referenced by `registry_receipt.signature.key_id` from the registry's DID document (RFC-ACDP-0001 §5.11, including the SSRF protections of RFC-ACDP-0008 §4.8), and verify `signature.value` over the ASCII bytes of the receipt hash. For receipt keys, the `assertionMethod` requirement is replaced by the lifecycle rule of §9: current receipt keys MUST be in `assertionMethod`; retired receipt keys MAY verify historical receipts from `verificationMethod` alone.
2. **Registry binding.** `registry_did` MUST be `did:web:<authority>` where `<authority>` equals the authority the context (or publish response) was fetched from, and the DID portion of `signature.key_id` MUST equal `registry_did`. This is the same authority-binding rule as RFC-ACDP-0006 §4.1 step 3 and fixture `fed-006`.
3. **Context binding.** `receipt.ctx_id` MUST equal the `ctx_id` the consumer requested (or, on publish, the `ctx_id` in the publish response), and `receipt.lineage_id`, `receipt.origin_registry`, and `receipt.created_at` MUST equal the corresponding body/response fields byte-for-byte.
4. **Content binding.** `receipt.content_hash` MUST equal the consumer's **independently recomputed** ProducerContent hash of the accompanying body (RFC-ACDP-0001 §5.7) — NOT the echoed `body.content_hash`. A receipt over an unrecomputed hash binds nothing.
5. **Key binding.** `receipt.key_fingerprint` MUST equal the §6 fingerprint of the producer public key the consumer resolved for `body.signature.key_id` — or, when the producer has rotated keys, of a historically retained key per §10.
6. **Timestamp form.** `receipt.created_at` MUST be well-formed canonical millisecond-precision RFC 3339 UTC (`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$`).

A failure of any step MUST be treated as a verification failure of the receipt. SDKs surfacing the failure SHOULD use the `invalid_receipt` semantic (RFC-ACDP-0007 §5); a registry-side endpoint that validates receipts on behalf of callers (e.g. a federated resolver, RFC-ACDP-0006) emits the wire code `invalid_receipt` (HTTP 502 when the failing receipt came from an upstream registry).

**Receipt failure does not invalidate the body.** A body whose producer signature and `content_hash` verify but whose receipt fails verification remains producer-authentic; what is lost is the registry's binding of identifiers and time. Verification reports SHOULD carry the body verdict and the receipt verdict separately (the `registry_receipt` stage name reserved by RFC-ACDP-0001 §5.11 is now active for 0.2.0 reports).

---

## 9. Registry Receipt-Key Lifecycle (NORMATIVE)

Receipts are long-lived; registry keys are not. To keep every previously minted receipt verifiable:

- Retired receipt signing keys MUST remain in the registry DID document's `verificationMethod` array **indefinitely**.
- Rotation removes the retired key from `assertionMethod` **only**. Removal from `assertionMethod` stops the key from authenticating *new* receipts; retention in `verificationMethod` keeps *old* receipts verifiable.
- A verifier evaluating a receipt MUST accept a receipt key found in `verificationMethod` even when it is absent from `assertionMethod`, and SHOULD report such verification with a *historically authorized* status (mirroring §10). A receipt key absent from `verificationMethod` entirely fails step 1 of §8.
- Registries MUST NOT remove a receipt signing key from `verificationMethod` except on confirmed key compromise; on compromise, removal is the explicit, intended mechanism for invalidating receipts minted under the compromised key, and the registry SHOULD re-mint affected receipts under the successor key — re-minting after compromise is the one sanctioned exception to §4 immutability, and the re-minted receipt MUST attest the original stored `created_at`.

Without this rule, receipt-key rotation would recreate the historical-key-validity problem (RFC-ACDP-0008 §9.3) one level up.

---

## 10. Historical Producer-Key Verification (Workstream B)

The receipt's `key_fingerprint` carries the registry's publish-time attestation of *which producer key verified the body*. This enables a distinguishable verification status for contexts whose producer keys have since rotated:

**Rule (NORMATIVE for receipt-aware verifiers).** If a consumer verifies a receipt per §8 (steps 1–4 and 6 pass), and `receipt.key_fingerprint` equals the §6 fingerprint of a key present in the producer's **current** DID document's `verificationMethod` array — even when that key is no longer referenced by `assertionMethod` — then the body signature SHOULD be verified against that key, and on success the verification result MUST be reported with the distinguishable status **historically authorized (receipt-attested)** rather than fully current.

- Producers correspondingly SHOULD retain rotated keys in `verificationMethod` indefinitely, removing them from `assertionMethod` only (RFC-ACDP-0001 §5.11). A producer key removed from `verificationMethod` entirely remains unverifiable; removal is the producer's compromise-revocation signal, and verifiers MUST then fail closed regardless of any receipt.
- **Without a verified receipt, behavior is unchanged from v0.1.0**: the strict-or-pragmatic choice of RFC-ACDP-0008 §7.3 applies, with its documented residual risk. The receipt is what upgrades "this key used to be in the DID document, trust me" to "the registry attested under its own signature that this exact key verified this exact content at publish time."
- `did:key` producers are exempt by construction: the key is the identity, there is no rotation, and verification never consults a DID document (RFC-ACDP-0001 §5.11).

The fixture `rot-001-historical-key-receipt.json` pins both halves: with a valid receipt attesting K1's fingerprint and K1 retained in `verificationMethod`, verification succeeds as *historically authorized*; the identical scenario without a receipt fails closed under the strict profile.

---

## 11. Capabilities, Profile, and Errors

- **Profile.** `acdp-registry-receipts` (registered in `registries/profiles.md`; prerequisite `acdp-registry-core`). Advertised in `capabilities.profiles`. Advertising the profile is the commitment described in §7 — always mint, always serve, no degraded mode.
- **Version.** Registries advertising the profile MUST advertise `acdp_version` ≥ `0.2.0` in capabilities.
- **Error code.** `invalid_receipt` (HTTP 502 when emitted by a registry/resolver about an upstream receipt; the consumer-facing verification-failure category otherwise). Registered in `registries/error-codes.md`; wire enum in `acdp-error.schema.json`. There is deliberately no `receipt_unavailable` (§7).
- **Federation.** A federated resolver (`acdp-registry-federated`) retrieving a context from a receipts-advertising upstream MUST verify the upstream's receipt per §8 against the *upstream* authority and MUST surface verification failure as `invalid_receipt` rather than silently dropping the receipt. Fixture `fed-009-cross-registry-receipt.json` pins this.

---

## 12. Compatibility

Receipts are the minor-version event that motivates `acdp_version: 0.2.0` (a new top-level retrieval member and a second signing identity — VERSIONING.md change classes):

- **Retrieval envelope.** `acdp-context.schema.json` is open at the top level and has reserved `registry_receipt` since v0.1.0; v0.1.0 consumers already tolerate and preserve it (RFC-ACDP-0009 §2.7). No migration needed.
- **Publish response.** The publish-response schema is closed and gains the OPTIONAL `registry_receipt` member. A v0.1.0 consumer with a strict (`deny_unknown_fields`) publish-response decoder will fail to parse a 0.2.0 receipt-bearing publish response. **Migration note:** v0.1.0 producer libraries publishing to receipts-advertising registries MUST be upgraded to a publish-response model that accepts the optional `registry_receipt` before those registries enable the profile; registry operators SHOULD coordinate the rollout with their producers. This is the one place 0.2.0 alters the parse surface of an existing v0.1.0 response shape.
- **Bodies, signatures, hashes.** Unchanged. Every v0.1.0 body, signature, and `content_hash` remains valid; the receipt is strictly additive evidence.
- **v0.1.0 registries** that do not advertise the profile are unaffected and remain fully conformant.

---

## 13. Scope and Limitations (honest scope)

Receipts make registry claims **attributable and non-repudiable** — they do not make them **unforgeable at mint time**. A registry can still:

- backdate `created_at` *at the moment it first mints* a receipt (nothing external anchors the registry's clock);
- decline to mention contexts it has hidden (a receipt proves what was published, not what wasn't);
- equivocate between consumers only at the cost of producing conflicting signed receipts — detectable when receipts are compared, but ACDP 0.2.0 specifies no comparison infrastructure.

The next layer — an append-only, registry-signed publication log with Merkle-tree checkpoints, making backdating and equivocation detectable by any auditor — is named future work, reserved as [RFC-ACDP-0009 §2.11](RFC-ACDP-0009-extensions.md#211-transparency-log). It is deliberately out of scope for this document. ***(0.3.0)*** That layer has since shipped as [RFC-ACDP-0012 Registry Transparency Log](RFC-ACDP-0012-transparency-log.md), promoting the §2.11 reservation; it remains out of scope for *this* document.

Deployments needing stronger-than-receipt guarantees today SHOULD continue the v0.1.0 mitigations (external transparency logs, multi-registry replication with consumer-side comparison — RFC-ACDP-0008 §9.2).

---

## 14. Conformance Fixtures

| ID | What it pins | Runner |
|---|---|---|
| `rcpt-001-receipt-golden` | Full golden vector: registry test keypair, receipt preimage canonical bytes, receipt hash, Ed25519 signature, producer-key fingerprint. The `sig-001`-equivalent every SDK pins. | Executed arithmetically |
| `rcpt-002-tampered-created-at` | One-byte `created_at` tamper → receipt hash diverges → signature verification MUST fail. | Behavioral (data pinned) |
| `rcpt-003-key-fingerprint-mismatch` | `receipt.key_fingerprint` ≠ fingerprint of the resolved producer key → §8 step 5 MUST fail. | Behavioral |
| `rcpt-004-registry-did-mismatch` | `receipt.registry_did` ≠ serving authority → §8 step 2 MUST fail. | Behavioral |
| `fp-001-key-fingerprint-vectors` | §6 fingerprint encoding, one vector per algorithm (Ed25519 raw 32 bytes; P-256 SEC1 compressed 33 bytes). | Executed arithmetically |
| `rot-001-historical-key-receipt` | §10 historically-authorized-with-receipt vs fail-closed-without-receipt. | Behavioral |
| `fed-009-cross-registry-receipt` | Federated resolver verifies the upstream registry's receipt against the upstream authority. | Behavioral |

---

## 15. Security Considerations

- The receipt signing key is a high-value, long-lived signing identity. The key-generation and key-storage requirements of RFC-ACDP-0001 §5.8 apply in full; registries SHOULD keep the receipt key in an HSM/KMS boundary and SHOULD use a key distinct from any other signing duty.
- Receipt verification dereferences the registry's `did:web` document — the SSRF protections of RFC-ACDP-0008 §4.8 apply to that fetch identically.
- A verified receipt MUST NOT be treated as evidence of body authenticity; only the producer signature establishes authorship (RFC-ACDP-0008 §8). The two verdicts are independent and MUST be reported independently (§8).
- Consumers SHOULD persist receipts alongside retrieved bodies: a stored receipt is the consumer's durable evidence in any later dispute with the registry, and the raw material for cross-consumer equivocation detection.

See RFC-ACDP-0008 §9.1–§9.3 (as amended for 0.2.0) for the threat-model placement.

---

## 16. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0003 Publish](RFC-ACDP-0003-publish.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0006 Cross-Registry References](RFC-ACDP-0006-cross-registry.md)
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
- [RFC-ACDP-0009 Extensions](RFC-ACDP-0009-extensions.md) — §2.7 (origin of this RFC), §2.11 (transparency-log reservation, since promoted to RFC-ACDP-0012).
- [RFC 8032] Josefsson, S. and I. Liusvaara, "Edwards-Curve Digital Signature Algorithm (EdDSA)", RFC 8032, January 2017.
- [RFC 8785] Rundgren, A., Jordan, B., and S. Erdtman, "JSON Canonicalization Scheme (JCS)", RFC 8785, June 2020.
- [SEC1] Standards for Efficient Cryptography Group, "SEC 1: Elliptic Curve Cryptography", Version 2.0, May 2009.
