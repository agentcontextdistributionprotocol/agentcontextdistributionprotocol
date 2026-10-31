# ACDP Rule Anchors

Stable names for the behaviors implementations most often need to cite, so that a downstream project can say "conforms to `acdp.rule.content-hash`" instead of pointing at an SDK source line or a section number that later edits may move. Each anchor names one rule, the normative text that defines it, and the known-answer fixtures that pin it.

**Rules for this registry.**
- An anchor's meaning never changes. When the behavior it names changes, the change mints a new anchor (`<name>.v2`) and the old one becomes `Deprecated`. It stays listed, still pointing at the text and fixtures that defined it.
- Editorial moves of the defining text update the **Defined by** column only.
- `Stable` anchors point at Final text. `Provisional` anchors point at Draft text (the *(0.5.0)* line) and can still change before their RFC is Final.
- A **Pinned by** fixture is an executed known-answer fixture: `scripts/conformance-runner.py` recomputes it, so an implementation that reproduces it reproduces the rule.

| Anchor | Status | Rule | Defined by | Pinned by |
|---|---|---|---|---|
| `acdp.rule.jcs` | Stable | Canonical JSON is RFC 8785 JCS, including its number serialization | [RFC-ACDP-0001 §5.2](../rfcs/RFC-ACDP-0001-core.md#52-canonicalization) | `can-001`, `can-002`, `can-011`, `can-012` |
| `acdp.rule.content-hash` | Stable | The `content_hash` preimage: the body minus the §5.7 exclusion set, stripped by field name, unknown producer fields kept, JCS, SHA-256, `sha256:` + lowercase hex | [RFC-ACDP-0001 §5.7](../rfcs/RFC-ACDP-0001-core.md#57-content-hash) | `can-003`..`can-005`, `can-007`..`can-010` |
| `acdp.rule.timestamp` | Stable | Timestamps are UTC RFC 3339 with exactly three fractional digits and `Z` | [RFC-ACDP-0001 §5.3](../rfcs/RFC-ACDP-0001-core.md#53-time-format) | `can-006`, `can-013` |
| `acdp.rule.lineage-id` | Stable | `lineage_id` = `lin:sha256:` + hex(SHA-256(UTF-8 of the first version's `ctx_id`)) | [RFC-ACDP-0001 §5.6](../rfcs/RFC-ACDP-0001-core.md#56-lineage-identifier-derivation) | `lin-001` |
| `acdp.rule.producer-signature` | Stable | The producer signature over the content hash, per algorithm | [RFC-ACDP-0001 §5.8](../rfcs/RFC-ACDP-0001-core.md#58-signature) | `sig-001`..`sig-004` |
| `acdp.rule.key-fingerprint` | Stable | Key fingerprint encoding | [RFC-ACDP-0010 §6](../rfcs/RFC-ACDP-0010-registry-receipts.md#6-key-fingerprint-encoding-normative) | `fp-001` |
| `acdp.rule.receipt-verification` | Stable | Registry receipt construction and the verification procedure | [RFC-ACDP-0010 §5, §8](../rfcs/RFC-ACDP-0010-registry-receipts.md#8-verification-procedure-normative) | `rcpt-001` |
| `acdp.rule.revocation-classification` | Provisional | A context signed by a revoked key: pre-compromise only with a verified current-key receipt dated strictly before T; revoked at or after T; unplaceable without a usable receipt | [RFC-ACDP-0014 §7](../rfcs/RFC-ACDP-0014-key-revocation.md#7-consumer-semantics-normative) steps 1–4 | `rev-007` |
| `acdp.rule.revocation-fold` | Stable | T is the earliest `compromised_since` across the revocation lineage; retracted members count; non-revocation successors never disarm; the interim type counts | [RFC-ACDP-0014 §4, §7, §10](../rfcs/RFC-ACDP-0014-key-revocation.md#7-consumer-semantics-normative) | `rev-007` (vectors 09–13) |
| `acdp.rule.revocation-scope` | Provisional | A revocation applies only within producer scope (signer, or registry-attested controller) | [RFC-ACDP-0014 §7](../rfcs/RFC-ACDP-0014-key-revocation.md#7-consumer-semantics-normative) "Producer scope" | `rev-007` (vectors 14–17) |
| `acdp.rule.revocation-precedence` | Provisional | Combining lookups: refusal > unknown > pre-compromise > not-revoked | [RFC-ACDP-0014 §7](../rfcs/RFC-ACDP-0014-key-revocation.md#7-consumer-semantics-normative) "Precedence across lookups" | `rev-007` (vectors 02, 18–20) |
| `acdp.rule.revocation-signal` | Stable | The revocation context's shape and signature | [RFC-ACDP-0014 §4, §5](../rfcs/RFC-ACDP-0014-key-revocation.md) | `rev-001` |
| `acdp.rule.chain-verdict` | Stable | `verify_chain` verdicts and their `evidence_digest`, `as_of_digest` and `verdict_digest` | [RFC-ACDP-0017 §6–§9](../rfcs/RFC-ACDP-0017-chain-verification.md#9-the-verdict-object-acdp-chain-verdict1-normative) | `chain-001`, `chain-002`, `chain-003`, `chain-010`, `chain-011` |
| `acdp.rule.sealed-as-of` | Stable | The as-of projection and `as_of_digest`, stable when post-T evidence changes | [RFC-ACDP-0017 §9.2](../rfcs/RFC-ACDP-0017-chain-verification.md#92-digests) | `chain-010` |
| `acdp.rule.keyless-key-id` | Stable | A keyless key id is `<controller>#acdp-kl-<h>`, where `<h>` is the 64 hex characters of the attested key's RFC-ACDP-0010 §6 fingerprint | [RFC-ACDP-0021 §6.1](../rfcs/RFC-ACDP-0021-keyless-signing.md#61-the-keyless-key-id-normative) | `kl-001` (vectors 1, 2) |
| `acdp.rule.keyless-verification` | Stable | Verifying a keyless signature: attestation valid, attester accepted, bindings, placement by the body receipt, window, ephemeral signature, withdrawal, revocations, then the identity now. The first failure decides, and the outcome maps onto the three existing key statuses | [RFC-ACDP-0021 §8](../rfcs/RFC-ACDP-0021-keyless-signing.md#8-consumer-verification) | `kl-001` (vectors 1, 2, 4) |
| `acdp.rule.change-hint-hmac` | Provisional | The `ACDP-Signature` HMAC over a change hint | [RFC-ACDP-0018 §8](../rfcs/RFC-ACDP-0018-retraction-recall.md#8-change-hints-webhooks-normative-for-acdp-registry-events) | `rec-007` |
