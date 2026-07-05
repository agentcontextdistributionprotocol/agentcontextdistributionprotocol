# RFC-ACDP-0011
# Agent Context Distribution Protocol (ACDP) — Lineage-Head Receipts

**Document:** RFC-ACDP-0011
**Version:** 0.3.0-draft
**Status:** Community Standards Track (Draft)

This RFC specifies **lineage-head receipts**: registry-signed attestations of the *current* state of a lineage — "as of time T, the head of lineage L is context X at version N with status S." It extends the receipt trust layer introduced by RFC-ACDP-0010 (Registry Receipts) from publish-time facts to serve-time claims, and is the anchor of the ACDP 0.3.0 program. It depends on RFC-ACDP-0001 (Core), RFC-ACDP-0004 (Retrieval & Lineage), RFC-ACDP-0007 (Capabilities & Errors), and RFC-ACDP-0010 (Registry Receipts).

---

## 1. Status of This Memo

This document is a **Draft** ACDP specification targeting acdp/0.3.0. It follows the governance lifecycle in [governance/RFC-PROCESS.md](../governance/RFC-PROCESS.md) (Draft → Review → Final); per [VERSIONING.md](../VERSIONING.md) it is promoted to Final once the conformance fixtures it defines (`lhr-001..004`) pass against at least two independent interoperating implementations.

Unlike RFC-ACDP-0010, this RFC **promotes no RFC-ACDP-0009 reservation**: the lineage-head receipt was never reserved in v0.1.0, and no v0.1.0 library carries a preserve-verbatim obligation for it. It is a direct extension of RFC-ACDP-0010 — the same signing key, the same signing construction, the same key lifecycle — applied to a new, ephemeral object. Nothing in this document invalidates any v0.1.0/0.2.0 body, signature, `content_hash`, or RFC-ACDP-0010 receipt.

---

## 2. Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described in BCP 14 ([RFC 2119], [RFC 8174]) when, and only when, they appear in all capitals.

| Term | Definition |
|---|---|
| **Lineage-head receipt** (head receipt) | A registry-signed JSON object attesting that, at a stated time, a stated context version was the current head of a stated lineage with a stated status. |
| **Head** | The current version of a lineage per RFC-ACDP-0004 §5.2: the newest non-superseded version — as visible to the requester per RFC-ACDP-0004 §5.4. |
| **Receipt preimage / receipt hash** | Exactly as RFC-ACDP-0010 §2: the object minus `signature`, JCS-canonicalized (RFC 8785); `"sha256:" + lowercase_hex(SHA-256(preimage))`. |
| **Receipt signing key** | The RFC-ACDP-0010 §2 registry receipt signing key. Head receipts introduce **no new key role**. |
| **`as_of`** | The registry-clock time at which the head claim was evaluated and the receipt minted. A head receipt is evidence *about that instant only*. |

---

## 3. Motivation

RFC-ACDP-0010 receipts bind **publish-time** facts: identifiers, `created_at`, the content hash, and the producer key resolved at publish time. Nothing in ACDP 0.2.0 attests **current-ness**. `status` is derived by the registry from its own supersession index and clock, and is explicitly *not independently verifiable* (RFC-ACDP-0004 §4): a registry can serve a stale `status: active` on a long-superseded context, or serve a stale head from `GET /lineages/{lineage_id}/current`, and no signed evidence contradicts it. The RFC-ACDP-0010 receipt accompanying the stale response verifies perfectly — it attests publish-time facts that remain true. RFC-ACDP-0010 §13 already concedes that receipts do not prevent mint-time lying; the stale-head problem is the serve-time analogue, and it is untouched by 0.2.0.

A lineage-head receipt closes the *attributability* half of this gap. It is the registry's signed, timestamped commitment: **"as of `as_of`, the head of `lineage_id` is `head_ctx_id` at `head_version` with `head_status`."** A registry that serves a stale head under a head receipt has produced signed evidence of the stale claim; a registry that shows different heads to different consumers has produced conflicting signed evidence (the same non-repudiation property as RFC-ACDP-0010 §13). The claim itself can still be false — see §11 — but it is no longer deniable, and it is timestamped, so replaying it later is bounded by `as_of`.

This is deliberately the **cheap complement** to the transparency log reserved by RFC-ACDP-0009 §2.11 (since specified as RFC-ACDP-0012), not a replacement: the log makes stale-head serving and equivocation *detectable by any auditor*; the head receipt makes each serve-time claim *attributable and non-repudiable* today, with nothing but the RFC-ACDP-0010 key plumbing that receipts-profile registries already operate.

---

## 4. Lineage-Head Receipt Object

A lineage-head receipt is a JSON object with exactly the following members. The canonical schema is [`schemas/json/acdp-lineage-head-receipt.schema.json`](../schemas/json/acdp-lineage-head-receipt.schema.json) (closed: `additionalProperties: false`).

| Field | Type | Required | Description |
|---|---|---|---|
| `receipt_version` | string | Yes | The head-receipt envelope version. MUST be exactly `"acdp-lhr/1"`. Doubles as a domain separator inside the signed preimage: a head receipt can never be mistaken for (or replayed as) an RFC-ACDP-0010 context receipt, whose preimage carries no such member. |
| `registry_did` | string | Yes | The attesting registry's DID. Same rules as RFC-ACDP-0010 §4: MUST be `did:web:<authority>` where `<authority>` equals the registry's serving authority (the same value as `capabilities.registry_did`, RFC-ACDP-0007 §3.1). `did:web`-only. |
| `lineage_id` | string | Yes | The attested lineage identifier (RFC-ACDP-0001 §5.6). |
| `head_ctx_id` | string | Yes | The `ctx_id` of the head version (RFC-ACDP-0001 §5.5). Its authority component MUST equal the method-specific identifier of `registry_did` (lineages are single-registry in v0.1.0+, RFC-ACDP-0004 §5.3). |
| `head_version` | integer | Yes | The head's `body.version` (≥ 1). |
| `head_status` | string | Yes | The head's registry-derived `status` at `as_of` (RFC-ACDP-0004 §4). MUST match the RFC-ACDP-0004 §4.1 pattern (`^[a-z][a-z0-9_]*$`, 1–64 chars). MUST NOT be `superseded` — a superseded version is never the head (RFC-ACDP-0004 §5.2) — and MUST NOT be `retracted` — a retracted version is never served as head (RFC-ACDP-0013 §8.3, on registries that also advertise `acdp-registry-lifecycle`); in practice this is `active` or `expired` (an expired head is a valid head). |
| `as_of` | string | Yes | The registry's response-time clock reading when the head claim was evaluated: canonical millisecond-precision RFC 3339 UTC (RFC-ACDP-0001 §5.3, `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$`). |
| `signature` | object | Yes | The registry's signature over the receipt hash, using the `signature` object shape of RFC-ACDP-0001 §5.8 (`algorithm`, `key_id`, `value`; closed schema) — the same envelope as RFC-ACDP-0010 §4. `signature.key_id` MUST be a DID URL under `registry_did`. |

All fields other than `signature` are covered by the receipt signature. There is no exclusion set beyond `signature` itself.

Unlike RFC-ACDP-0010 receipts, head receipts are **ephemeral, not immutable**: the head of a lineage changes on every supersession and the head's status changes with the clock, so a registry mints a fresh receipt (fresh `as_of`) per response. A registry MAY reuse a recently minted receipt across responses within a short window — the claim remains honest, because `as_of` states when it was evaluated — but MUST NOT serve a receipt whose head fields no longer match what the same response reports (§7 step 5 makes such a response self-contradictory).

Head receipts are requester-relative where visibility applies: the attested head is the newest non-superseded version **the requester is authorized to retrieve** (RFC-ACDP-0004 §5.4). A registry MUST NOT mint a head receipt that names a context the requester could not retrieve — that would convert the receipt into an existence leak (RFC-ACDP-0008 §4.5). See §11 for the equivocation-detection consequence.

---

## 5. Signing Construction

The head-receipt signing construction **reuses RFC-ACDP-0010 §5 verbatim**; implementations MUST NOT introduce a second canonicalization or signing-input framing:

1. **Preimage.** Remove the `signature` member. JCS-canonicalize (RFC 8785) the remainder.
2. **Hash.** `receipt_hash = "sha256:" + lowercase_hex(SHA-256(preimage_bytes))`.
3. **Signing input.** The **ASCII bytes of the full `receipt_hash` string**, `sha256:` prefix included (RFC-ACDP-0001 §5.8; RFC-ACDP-0010 §5 step 3).
4. **Signature.** Sign with the registry's **receipt signing key** — the same key material as RFC-ACDP-0010 receipts. `signature.algorithm` follows RFC-ACDP-0001 §5.10 (`ed25519` mandatory-to-implement; `ecdsa-p256` optional, IEEE 1363 r‖s wire form). `signature.value` is the base64-encoded signature bytes.

The key identified by `signature.key_id` MUST satisfy every RFC-ACDP-0010 receipt-key requirement (§6 fingerprint encoding where fingerprinted, §9 lifecycle, current keys in `assertionMethod`), and SHOULD be the identical key the registry uses for RFC-ACDP-0010 receipts — the profile of §9 deliberately requires no new key, no new DID-document entry, and no new rotation procedure.

The golden vector `lhr-001-lineage-head-receipt-golden.json` pins the canonical preimage bytes, the receipt hash, and an Ed25519 signature end-to-end under the same registry test keypair as `rcpt-001`; it is executed arithmetically by `scripts/conformance-runner.py`.

---

## 6. Issuance

Registries advertising the `acdp-registry-head-receipts` profile (§9):

1. **MUST return a head receipt on `GET /lineages/{lineage_id}/current`** (RFC-ACDP-0004 §5.2) as the top-level `lineage_head_receipt` member of the full-retrieval envelope, outside `body` and `registry_state` — the envelope is open at the top level (RFC-ACDP-0004 §2.1, `acdp-context.schema.json`), so this is an additive member. The receipt MUST describe the very head being served: §7 step 5 byte-match applies.
2. **MAY attach a head receipt to full retrieval** (`GET /contexts/{ctx_id}`), attesting the current head of the retrieved context's lineage at response time. This is how a consumer holding an old version learns — under signature — that (and by what) it has been superseded. When the retrieved context is not the head, the consistency rule of §7 step 5b applies.
3. **MUST NOT attach head receipts to body-only retrieval** (`GET /contexts/{ctx_id}/body`) — the same rule, for the same immutable-cache reason, as RFC-ACDP-0010 §7 rule 4. Head receipts are the *most* mutable object in ACDP; the body-only endpoint stays receipt-free of every kind.
4. `GET /lineages/{lineage_id}` (the array form, RFC-ACDP-0004 §5.1) carries no head receipt — its response is a JSON array with no top-level object to extend.

`as_of` MUST be the registry's clock at response time, truncated to milliseconds (RFC-ACDP-0001 §5.3). Minting requires no persistence: the receipt is derived from the same supersession query that answers `/current` and can be signed on the fly. There is no `receipt_unavailable` condition (same posture as RFC-ACDP-0010 §7): a registry advertising the profile MUST always mint on `/current`; a registry that cannot MUST NOT advertise the profile.

**Freshness and replay.** A head receipt proves the claim was made at `as_of`; it promises nothing about any later instant. This is what bounds replay: an attacker (or a stale cache) replaying an old head receipt cannot forge a fresh `as_of`, so the receipt is exactly as convincing as its age. Consumers MUST therefore treat `as_of` staleness according to their own freshness policy, and SHOULD enforce a maximum acceptable age for any decision that depends on current-ness; a RECOMMENDED default maximum age is **300 seconds**, aligned with the registry-state cache guidance of RFC-ACDP-0004 §6.3. Staleness beyond policy is a *freshness* verdict, distinct from the verification failures of §7 (the receipt may be perfectly genuine — merely old).

---

## 7. Verification Procedure (NORMATIVE)

A consumer verifying a lineage-head receipt MUST perform **all** of the following checks. As with RFC-ACDP-0010 §8, the cross-checks are the security value.

1. **Schema-closed parse.** The receipt MUST parse against the closed schema of §4; `receipt_version` MUST be exactly `"acdp-lhr/1"`. Unknown members, missing members, or a different `receipt_version` fail verification (every member is signed, so an unknown member changes the preimage).
2. **Recompute and verify the signature.** JCS-recompute the preimage (§5), recompute the receipt hash, resolve the key referenced by `signature.key_id` from the registry's DID document (RFC-ACDP-0001 §5.11, including the SSRF protections of RFC-ACDP-0008 §4.8), and verify `signature.value` over the ASCII bytes of the receipt hash. Key acceptance follows RFC-ACDP-0010 §9: current receipt keys MUST be in `assertionMethod`; retired receipt keys MAY verify historical receipts from `verificationMethod` alone.
3. **Registry binding.** `registry_did` MUST be `did:web:<authority>` where `<authority>` equals the authority the response was fetched from AND equals `capabilities.registry_did` (RFC-ACDP-0007 §3.1); the DID portion of `signature.key_id` MUST equal `registry_did`; and the authority component of `head_ctx_id` MUST equal the method-specific identifier of `registry_did`. Same principle as RFC-ACDP-0010 §8 step 2 and fixture `fed-006`.
4. **Lineage binding.** `lineage_id` MUST equal the lineage the consumer requested (on `/current`) or the accompanying `body.lineage_id` (on full retrieval), byte-for-byte.
5. **Head binding.** When the accompanying response serves the head itself (always on `/current`; on full retrieval when `head_ctx_id` equals the retrieved `body.ctx_id`): `head_ctx_id` MUST equal `body.ctx_id` byte-for-byte, `head_version` MUST equal `body.version` numerically, and `head_status` MUST equal `registry_state.status` byte-for-byte.
   **5b.** On full retrieval where `head_ctx_id` ≠ the retrieved `body.ctx_id`, the receipt claims the retrieved context is not current: `head_version` MUST be strictly greater than `body.version`, and the retrieved context's `registry_state.status` MUST be `superseded` — or `retracted`, on a registry also advertising `acdp-registry-lifecycle` (a superseded-and-retracted version reports `retracted` under the RFC-ACDP-0013 §7.2 precedence). A receipt naming a different head alongside a `status: active` (or `expired`) response is self-contradictory and MUST fail.
6. **`as_of` well-formedness and skew.** `as_of` MUST match the canonical millisecond form (§4) and MUST NOT be in the future relative to the consumer's clock beyond a small skew allowance (RECOMMENDED: **120 seconds**). A future-dated `as_of` is a forged freshness claim and MUST fail verification (fixture `lhr-004`).

A failure of any step MUST be treated as a verification failure of the head receipt. SDKs surfacing the failure use the existing `invalid_receipt` semantic (RFC-ACDP-0007 §5, RFC-ACDP-0010 §11); **this RFC introduces no new wire code** (§9). Freshness policy (§6) is evaluated *after* — and reported distinctly from — these checks.

**Head-receipt failure invalidates nothing else.** The body verdict (producer signature + recomputed `content_hash`), the RFC-ACDP-0010 context-receipt verdict, and the head-receipt verdict are three independent results and SHOULD be reported independently.

---

## 8. Registry Key Lifecycle

Head receipts add **nothing** to key lifecycle: the signing key is the RFC-ACDP-0010 receipt signing key, and RFC-ACDP-0010 §9 applies in full (retired keys stay in `verificationMethod` indefinitely; rotation removes from `assertionMethod` only; removal from `verificationMethod` only on confirmed compromise). One consequence is pleasant: because head receipts are ephemeral, post-compromise recovery needs no re-minting campaign — fresh responses simply carry receipts under the successor key. Head receipts a consumer persisted as evidence (§13) remain verifiable through `verificationMethod` retention, exactly like historical RFC-ACDP-0010 receipts.

---

## 9. Capabilities, Profile, and Errors

- **Profile.** `acdp-registry-head-receipts` (registered in `registries/profiles.md`; prerequisite **`acdp-registry-receipts`** — and transitively `acdp-registry-core`). Advertised in `capabilities.profiles`. The prerequisite is load-bearing: the head receipt reuses the receipts profile's signing key, DID-document plumbing, and key lifecycle wholesale; there is nothing to operate for this profile that RFC-ACDP-0010 has not already required.
- **Version.** Registries advertising the profile MUST advertise `acdp_version` ≥ `0.3.0` in capabilities.
- **Error code.** **No new wire code is introduced.** A failing head receipt reuses `invalid_receipt` exactly as registered for RFC-ACDP-0010 §11 (HTTP 502 when emitted by a resolver/registry about an upstream's head receipt; the consumer-facing verification-failure category otherwise). There is deliberately no `head_receipt_unavailable` and no freshness error code — staleness is consumer policy (§6), not a wire condition.
- **Federation.** A federated resolver (`acdp-registry-federated`) querying `/current` on a head-receipts-advertising upstream SHOULD verify the upstream's head receipt per §7 against the *upstream* authority and surface failure as `invalid_receipt`, mirroring the RFC-ACDP-0010 §11 / `fed-009` rule for context receipts.

---

## 10. Compatibility

Head receipts are additive; they motivate the `acdp_version: 0.3.0` minor:

- **`/current` response.** `GET /lineages/{lineage_id}/current` returns the full-retrieval envelope of RFC-ACDP-0004 §2.1, whose schema (`acdp-context.schema.json`) is **open at the top level** (`additionalProperties: true`). The new `lineage_head_receipt` member therefore rides an existing openness guarantee: 0.1.0 and 0.2.0 consumers ignore the unknown member under RFC-ACDP-0001 §6, and — unlike the RFC-ACDP-0010 §12 publish-response caveat — **no existing parse surface changes**. A consumer whose retrieval-envelope decoder rejects unknown top-level members was already non-conformant with RFC-ACDP-0001 §6.
- **No reservation, no preserve-verbatim history.** `lineage_head_receipt` was never a reserved field name (contrast `registry_receipt`, RFC-ACDP-0009 §2.7). 0.1.0/0.2.0 libraries carry no preserve-verbatim obligation for it; the general unknown-field tolerance rule applies. Libraries that re-serialize retrieval envelopes SHOULD preserve it like any unknown member, but a head receipt is ephemeral evidence about one response instant — dropping it degrades evidence, not correctness.
- **Bodies, signatures, hashes, context receipts.** Unchanged. No JCS rule, `content_hash` semantic, signature semantic, or RFC-ACDP-0010 receipt semantic is touched; the canonical schemas stay in the `v0.1.0` namespace with additive edits (VERSIONING.md).
- **Non-advertising registries** are unaffected and remain fully conformant; they MUST NOT emit `lineage_head_receipt`.

---

## 11. Scope and Limitations (honest scope)

A head receipt makes the registry's serve-time head claim **attributable, timestamped, and non-repudiable** — it does not make it **true**:

- **Stale-head serving is detected only comparatively.** A consumer holding a single receipt learns nothing about staleness beyond `as_of`; detection requires a *fresher* receipt for the same lineage, a cross-check against another consumer's receipt, or out-of-band knowledge of a newer version. A registry that serves the same stale head **to everyone, consistently**, produces no conflicting evidence — making that detectable by any auditor is precisely the job of the transparency log reserved as RFC-ACDP-0009 §2.11 — since specified as [RFC-ACDP-0012](RFC-ACDP-0012-transparency-log.md) — of which this RFC is the cheap complement, not the replacement.
- **Split-view becomes evidence.** A registry showing different heads to *equally authorized* consumers at overlapping `as_of` instants has signed conflicting claims — non-repudiable when the receipts are compared, the same property (and the same "ACDP specifies no comparison infrastructure" caveat) as RFC-ACDP-0010 §13. The visibility qualifier matters: under RFC-ACDP-0004 §5.4 two *differently* authorized consumers can legitimately receive different heads, so conflicting receipts indict the registry only for public lineages or between requesters of equal authorization.
- **`as_of` is the registry's unanchored clock.** Nothing external attests it (the same limitation as RFC-ACDP-0010 §13 for `created_at`); the skew check of §7 step 6 bounds forward-dating against the consumer's clock, and backdating an `as_of` only makes the receipt *less* useful to the registry, but a consistent clock lie is not detectable from receipts alone.
- **Absence proves nothing.** A head receipt attests what the head *is claimed to be*; it cannot prove that no newer version was hidden from the supersession index — that, again, is log territory.

Deployments needing stronger serve-time guarantees today SHOULD combine head receipts with multi-vantage cross-checking (fetch `/current` from independent network vantages and compare receipts) and receipt persistence (§13).

---

## 12. Conformance Fixtures

| ID | What it pins | Runner |
|---|---|---|
| `lhr-001-lineage-head-receipt-golden` | Full golden vector: registry test keypair (shared with `rcpt-001`), head-receipt preimage canonical bytes, receipt hash, Ed25519 signature, version-1 lineage derivation cross-check. | Executed arithmetically |
| `lhr-002-stale-head-mismatch` | Receipt attests head v1 while the served `/current` response carries v2 → §7 step 5 byte-match MUST fail (`invalid_receipt`). | Behavioral |
| `lhr-003-registry-did-mismatch` | `registry_did` ≠ serving authority → §7 step 3 MUST fail — same authority-binding principle as `rcpt-004` / `fed-006`. | Behavioral |
| `lhr-004-future-as-of` | Validly signed receipt whose `as_of` is beyond the clock-skew allowance → §7 step 6 MUST fail (the failure is the freshness forgery, not the cryptography). | Behavioral |

---

## 13. Security Considerations

- The head-receipt signing key is the RFC-ACDP-0010 receipt signing key; every key-handling requirement of RFC-ACDP-0010 §15 (HSM/KMS boundary, role separation from TLS/producer keys) applies unchanged. Head receipts increase that key's signing *rate* (one signature per `/current` response rather than per publish); registries SHOULD account for this in key-compromise blast-radius planning — a compromised receipt key can now also forge current-ness.
- Head-receipt verification dereferences the registry's `did:web` document; the SSRF protections of RFC-ACDP-0008 §4.8 apply to that fetch identically.
- A verified head receipt MUST NOT be treated as evidence of body authenticity (producer signature only, RFC-ACDP-0008 §8) nor of the RFC-ACDP-0010 publish-time bindings (context receipt only). The three verdicts are independent (§7).
- Consumers SHOULD persist head receipts alongside the decisions they informed: a stored head receipt is the consumer's durable evidence that "the registry told me X was current at T" in any later dispute, and pairs of receipts from different vantages or times are the raw material for stale-head and split-view detection (§11).
- Registries MUST apply the §4 visibility rule when minting: a head receipt naming an unauthorized-for-the-requester context is an existence leak (RFC-ACDP-0008 §4.5).
- Because head receipts are ephemeral and requester-relative, caches and proxies MUST NOT reuse a `/current` response (with its embedded receipt) across requesters with different authorization; the `Cache-Control: private` posture of RFC-ACDP-0004 §6.2 already covers non-public heads.

---

## 14. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0004 Retrieval & Lineage](RFC-ACDP-0004-retrieval.md) — §4 (status derivation), §5.2 (`/current` semantics), §5.4 (lineage visibility).
- [RFC-ACDP-0006 Cross-Registry References](RFC-ACDP-0006-cross-registry.md)
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
- [RFC-ACDP-0009 Extensions](RFC-ACDP-0009-extensions.md) — §2.11 (transparency-log reservation, promoted to RFC-ACDP-0012; this RFC's stronger sibling).
- [RFC-ACDP-0010 Registry Receipts](RFC-ACDP-0010-registry-receipts.md) — §5 (signing construction, reused), §6 (fingerprint encoding), §9 (key lifecycle, reused), §11 (`invalid_receipt`), §13 (honest scope of receipts).
- [RFC-ACDP-0013 Lifecycle Events & Retraction](RFC-ACDP-0013-lifecycle-events.md) — §8.3 (a retracted version is never a head; `head_status` can never be `retracted`; the §7 step 5b amendment).
- [RFC 8032] Josefsson, S. and I. Liusvaara, "Edwards-Curve Digital Signature Algorithm (EdDSA)", RFC 8032, January 2017.
- [RFC 8785] Rundgren, A., Jordan, B., and S. Erdtman, "JSON Canonicalization Scheme (JCS)", RFC 8785, June 2020.
