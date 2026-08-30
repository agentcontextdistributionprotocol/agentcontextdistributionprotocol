# RFC-ACDP-0016
# Agent Context Distribution Protocol (ACDP) — Typed External Anchors

**Document:** RFC-ACDP-0016
**Version:** 0.5.0-draft
**Status:** Community Standards Track (Draft)

This RFC specifies **typed external anchors**: an optional, producer-signed body field, `anchors`, that lets an ACDP body genesis-link to a **non-ACDP, content-addressed external artifact** — a commitment record, a sealed decision, or any object identified by its own digest. It closes a gap neither `derived_from` (ACDP-internal lineage) nor `data_refs` (data a context describes) covers: a signed, first-class way to say "this fact is about, or descends from, that external artifact." It opens the ACDP 0.5.0 line. It depends on RFC-ACDP-0001 (Core) and RFC-ACDP-0002 (Context Body), and amends RFC-ACDP-0008 (Security) by cross-reference only.

---

## 1. Status of This Memo

This document is a **Draft** ACDP specification, opening the `acdp/0.5.0` line. It is open for substantive change until promoted. Per [VERSIONING.md](../VERSIONING.md), promotion to **Final** requires the conformance fixtures this document defines (`anc-001..005`) to pass against two independent interoperating implementations. Nothing in this document invalidates any v0.1.0/0.2.0/0.3.0/0.4.0 body, signature, `content_hash`, receipt, checkpoint, or cosignature.

This RFC does **not** promote an RFC-ACDP-0009 reservation. External anchors were never reserved in RFC-ACDP-0009; `anchors` is a new producer-controlled field introduced directly here, covered automatically by the RFC-ACDP-0001 §5.7 unknown-producer-field rule even before this document's schema update makes it first-class.

---

## 2. Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described in BCP 14 ([RFC 2119], [RFC 8174]) when, and only when, they appear in all capitals.

| Term | Definition |
|---|---|
| **Anchor** | A single element of the `anchors` array: a typed, content-addressed reference from an ACDP body to an external (non-ACDP) artifact (§4). |
| **Genesis link** | The relationship an anchor expresses: the body attests *about*, or *descends from*, the external artifact identified by the anchor's `content_hash` — distinct from `derived_from` (§3), which links only to other ACDP `ctx_id`s. |
| **Anchor scheme** | The dotted-namespace identifier (`scheme`) naming the external system an anchor's `content_hash` is meaningful within (e.g. `macp.commitment`). Schemes are registered in `registries/anchor-schemes.md`; unknown schemes are not interpreted by core ACDP. |
| **Scheme-aware verifier** | A verifier that understands a particular `scheme` and MAY additionally resolve the anchor against the named external system (§6). Core ACDP verification is never scheme-aware. |

---

## 3. Motivation

An ACDP body can express two kinds of reference today, and neither can anchor to a non-ACDP artifact verifiably:

- **`derived_from`** (RFC-ACDP-0002 §3.5) — epistemic lineage, but its items MUST be ACDP `ctx_id`s (`acdp://<authority>/<uuid>`). A bare content digest of an external artifact cannot go in it.
- **`data_refs`** (RFC-ACDP-0002 §6) — "data the context describes," with a closed `type` enum (`primary_result` / `raw_data` / `supporting_info` / `derived_data`). None of these means "the prior artifact this body attests about, or descends from," and the closed enum forbids adding one without a spec change.

There is consequently no first-class, signed way for a body to say *"this fact genesis-links to the external, content-addressed artifact X."* This is exactly what cross-protocol use needs: an ACDP body — a settlement fact, an agent-action audit fact, any post-decision attestation — anchored to an external commitment or decision record, so an independent verifier can tie the ACDP object to the thing it is about, without ACDP taking on any dependency on the external system's own verification machinery.

`anchors` is deliberately general-purpose: it is not settlement-specific, and it is useful for any cross-system provenance link a producer wants to make signed and immutable.

---

## 4. The `anchors` Field (NORMATIVE)

`anchors` is an OPTIONAL array field on the ACDP body (RFC-ACDP-0002 §3), added as a new field group. It is part of **ProducerContent** — producer-controlled, signed, immutable (§5).

| Field | Type | Required | Description |
|---|---|---|---|
| `anchors` | array of object | No | Typed, content-addressed references to external (non-ACDP) artifacts this body genesis-links to. |

**Absent-when-empty (NORMATIVE).** A producer with no external anchors MUST omit the field entirely — never `[]`, never `null` — so that a body has exactly one canonical form (the RFC-ACDP-0002 §6.8 absent-vs-null convention). This differs from `derived_from`, which is required-even-empty for historical reasons; `anchors` is a later additive field and follows the absent-when-empty convention throughout.

Each element of `anchors` is an object:

| Field | Type | Required | Description |
|---|---|---|---|
| `scheme` | string | Yes | Dotted-namespace identifier of the external artifact's system, e.g. `macp.commitment`, `seam.decision`. Pattern `^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)+$` (the RFC-ACDP-0002 §6.2 structured-locator scheme grammar). Registered in `registries/anchor-schemes.md`; unknown schemes are not interpreted by core ACDP (§6). |
| `content_hash` | string | Yes | The external artifact's own content digest: `"sha256:" + 64 lowercase hex characters`. This is the anchor's genesis identity — see §7 for what each scheme's `content_hash` means and does not mean. |
| `uri` | string | No | Optional locator hint for resolving the artifact, any registered URI scheme. Advisory only — the binding is `content_hash`, not `uri` (§6). |

`minItems: 1`, `maxItems: 100`, `uniqueItems: true` on `anchors`; each item's schema keeps `additionalProperties: true` so a future anchor-scheme-specific field is automatically signed under the §5 rule below without a schema update.

---

## 5. Content-Hash Inclusion (NORMATIVE)

`anchors` is producer-controlled and is included in **ProducerContent** (RFC-ACDP-0001 §5.7) — it is **not** in the exclusion set, so the producer signature covers it and it is immutable once published. By the §5.7 unknown-body-field rule, `anchors` is signed even by producers or verifiers predating this RFC; this document's schema update (§9) makes it first-class, not signed for the first time. Consumers and registries recomputing `content_hash` MUST retain `anchors`, and every element inside it, byte-exactly through JCS canonicalization — dropping or reordering an anchor before hash recomputation is the same class of conformance failure as dropping any other unknown producer field (RFC-ACDP-0001 §5.7).

---

## 6. Semantics Are a Producer Claim (NORMATIVE)

An anchor is an **authenticated assertion by the producer** — exactly like `data_refs` and `derived_from`. Core ACDP verification (`acdp-verify`, RFC-ACDP-0001 §5.11) confirms that an anchor is signed and immutable; it **MUST NOT** be required to resolve the external system, and it **MUST NOT** be required to confirm that `content_hash` names a real artifact. Whether an anchor points at a genuine, live external object is out of scope for ACDP and is the anchoring system's concern.

**Verification hook (OPTIONAL, for scheme-aware verifiers).** A verifier that understands a given `scheme` MAY additionally *resolve* the anchor: fetch the artifact identified by `content_hash` from the named external system (by whatever means that system defines — `uri` is at most a hint, never a requirement) and confirm the digest matches. A verifier that performs this step and it fails MUST treat the body as anchor-invalid **for its own purpose**; this has no effect on the body's ACDP-level verification verdict (signature, `content_hash`, receipts, log evidence remain independently valid — §10). A verifier that does not understand `scheme` MUST ignore the anchor for resolution purposes while still treating it as signed content it retains and re-serves byte-exactly.

**`uri` MUST NOT be dereferenced by registries or consumers as part of ACDP-level verification (NORMATIVE).** This is a stricter rule than RFC-ACDP-0008 §4.9's DataRef-location posture, which permits a guarded consumer-side fetch: `anchors[].uri` is advisory only, and no ACDP-level verification step — registry-side publish validation or consumer-side body verification — MAY fetch it. `uri` exists solely as a locator hint an application or a scheme-aware verifier MAY choose to use, entirely outside ACDP's own verification path and entirely governed by that application's or verifier's own SSRF posture, not this RFC's. This closes the outbound-fetch SSRF surface (RFC-ACDP-0008 §4.9) at the ACDP layer by construction: there is no code path in core verification that ever reads `anchors[].uri`.

---

## 7. Relationship to Other Digests (Non-Normative)

Anchors are deliberately opaque to core ACDP: `content_hash` inside an anchor means whatever the named `scheme`'s external system defines it to mean, and ACDP defines no mapping between schemes. As of this writing, three related-but-distinct digest constructions exist in the wider ecosystem, recorded here so implementers do not assume interchangeability:

- **`macp.commitment`** anchors carry the MACP canonical commitment hash (RFC-MACP-0013) — `"sha256:" + hex(SHA-256("macp-commitment-hash/1:" || JCS(CommitmentPayload)))`, a hash over a fixed, RFC-MACP-0013-enumerated field set.
- **`seam.decision`** anchors carry a Seam sealed-decision-record audit digest (`audit_entry.digest`) — a distinct, length-prefixed tuple construction (`seam-commitment-digest:v1`), not a JCS preimage.
- The MACP commitment hash MAY appear as an opaque substring **inside** a Seam decision digest's own preimage (a Seam `Commitment.supersedes` string embeds a MACP `commitment_hash`) — this is containment, one way, not equivalence. A change to either construction's versioned label is that construction's own breaking change; it is never triggered by, and never triggers, a change here.

ACDP's contract is limited to: the anchor's `content_hash` is exactly what the named scheme says it is, byte-for-byte, immutable once signed. Resolving what that digest means, and whether two digests from different schemes relate, is entirely the concern of the systems that define those schemes — never of core ACDP verification.

---

## 8. Multiple Anchors and Multi-Party Attestation (Non-Normative)

A body MAY carry several anchors — for example, a fact referencing both an originating decision and a counterparty artifact. Because ACDP supersession is single-signer-per-lineage (RFC-ACDP-0003 §2.1), independent parties attesting about the same external artifact publish **separate lineages that share an anchor `content_hash`**, cross-linked by the common anchor rather than by one supersession chain. Comparing anchors across lineages to reconstruct such cross-links is a consumer-side concern; ACDP provides no dedicated query surface for it in this document.

---

## 9. Schema and Registry

- **Schema.** `anchors` is added to `schemas/json/acdp-context-body.schema.json` (open, `additionalProperties: true`, so this is a tightening rather than a wire change) and mirrored into `schemas/json/acdp-publish-request.schema.json` (closed, `additionalProperties: false` — without the mirror, every anchored publish would be rejected). Both schemas stay in the `v0.1.0` namespace per the VERSIONING.md additive-minor rule.
- **Registry.** Anchor schemes are registered in `registries/anchor-schemes.md`, status per the house convention (`Proposed` / `Provisional` / `Stable` / `Deprecated`). `macp.commitment` and `seam.decision` are seeded there at `Provisional`; seeding was tracked separately from, and was never a precondition for, this RFC's own conformance gate.

---

## 10. Capabilities, Profile, and Errors

- **No new profile.** `anchors` is a body field, not a registry surface; conformance is folded into `acdp-consumer` (the fixtures are verification-side — RFC-ACDP-0001 §9.1). No registry advertises a dedicated anchors profile.
- **Version.** Registries and consumers advertising or requiring `anchors` acceptance/verification behavior use `acdp_version` ≥ `0.5.0`. Per VERSIONING.md, "Registries MUST reject publish requests containing fields not defined in the version they implement": a registry advertising `acdp_version` < `0.5.0` MUST reject a publish carrying `anchors` with `schema_violation`, exactly as it would any other field its declared version does not define.
- **No new error code.** A malformed anchor (bad `content_hash` shape, empty `anchors` array, an unrecognized `scheme` grammar violation) is rejected with the existing `schema_violation` (`registries/error-codes.md`) — the same code every other closed-schema or absent-vs-null violation uses. Minting a dedicated `invalid_anchor` code was considered and rejected: unlike `invalid_log_proof` or `invalid_witness_cosignature`, an anchor failure is a structural schema failure, not an independent cryptographic verdict, so the anti-overloading rule that justifies those two distinct codes does not apply here.

---

## 11. Compatibility

`anchors` is additive; nothing existing changes:

- **New optional field, `v0.1.0` schema namespace.** Same additive-minor posture as every field added since 0.2.0.
- **No change to `derived_from`, `data_refs`, or any other body field's semantics.** Anchors are a new, distinct relationship type (§3); they do not reinterpret or replace either existing reference mechanism.
- **No change to JCS, content-hash, or signature semantics.** `anchors` participates in the existing RFC-ACDP-0001 §5.7 unknown-field rule; no exclusion-set change, no new signing construction.
- **Non-participating deployments are unaffected.** A producer that never sets `anchors`, a registry that never sees one, and a consumer that ignores the field entirely (RFC-ACDP-0001 §6 unknown-field tolerance) are all fully conformant at every ACDP version, including versions predating this RFC.

---

## 12. Non-Goals

This RFC does not introduce audit-grade **time** anchoring. `docs/non-goals.md` §16 is amended:

> *Non-goal: audit-grade **time** anchoring — `created_at` remains the registry's clock, and ACDP does not integrate time-stamp authorities or blockchain anchoring. Typed **content** anchors (RFC-ACDP-0016) are in scope: they are opaque, never-dereferenced producer claims about external artifacts, not time attestations.*

An anchor's `content_hash` says nothing about *when* the external artifact was created — only that the producer is claiming a link to an artifact with that digest. Producers wanting a time claim about an anchored artifact publish it through the anchored system's own mechanisms, entirely outside ACDP.

---

## 13. Conformance Fixtures

| ID | What it pins | Runner |
|---|---|---|
| `anc-001-well-formed-anchor` | Accept: a body carrying one well-formed `macp.commitment` anchor — valid `scheme` grammar, valid `content_hash` shape — publishes and verifies normally. | Behavioral |
| `anc-002-malformed-content-hash` | Reject `schema_violation`: an anchor whose `content_hash` does not match the `"sha256:" + 64-lowercase-hex` shape. | Behavioral |
| `anc-003-empty-anchors-array` | Reject `schema_violation`: `anchors: []` — the field MUST be omitted when there is nothing to anchor, never sent as an empty array (§4). | Behavioral |
| `anc-004-content-hash-with-anchors` | Executed arithmetic golden: `content_hash` over a body carrying `anchors`, proving the field enters the JCS preimage exactly as any other producer-controlled field would (§5). The `can-*`-equivalent for this RFC. | Executed arithmetically |
| `anc-005-scheme-unaware-verifier-ignores-anchor` | Behavioral: a verifier that does not understand the anchor's `scheme` ignores it for resolution purposes (§6) while the body's signature and `content_hash` still verify normally. | Behavioral |

Vectors are generated by `scripts/gen-0.5.0-vectors.py` (never hand-written), following `scripts/gen-0.4.0-vectors.py`; the generator uses the same `jcs` library as the runner.

**Numbering note.** The `macp.commitment` example anchor scenario originally proposed as "anc-004" in the source use-case draft (`scheme-unaware verifier ignores the anchor`) is `anc-005` in this fixture set; `anc-004` here is the executed content-hash golden vector, added to give this RFC an arithmetic vector matching the `can-*` pattern every prior RFC introducing a new signed/hashed field has carried.

---

## 14. Security Considerations

- **`anchors` widens no attack surface by itself.** It is an opaque, signed string pair; core ACDP never dereferences `content_hash` and — per §6 — MUST NOT dereference `uri`. A malicious `uri` value is inert at the ACDP layer by construction.
- **Scheme-aware resolution is the resolving party's own responsibility.** Any system that chooses to fetch an anchor's `uri`, or otherwise resolve `content_hash` against an external system, does so entirely outside this RFC's normative scope and MUST apply its own SSRF and integrity posture — the same boundary RFC-ACDP-0008 §4.9 draws around `data_refs[].location`, drawn one layer further out here because core ACDP never initiates the fetch at all.
- **An anchor is a claim, not a proof.** A producer can anchor to a `content_hash` that does not correspond to any real external artifact; ACDP-level verification never asserts otherwise (§6). Consumers relying on an anchor for anything beyond "the producer signed this claim" MUST perform their own scheme-aware resolution and treat its result as a verdict independent of ACDP verification.
- **Registries MUST still enforce version gating.** Accepting `anchors` from a producer whose declared `acdp_version` predates `0.5.0` would let a producer depend on registry-specific behavior undefined in its own declared version (VERSIONING.md) — §10's `schema_violation` rejection is the existing mechanism, not a new one.

---

## 15. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md) — §5.6 (`derived_from`), §5.7 (content-hash exclusion set, unknown-field rule), §5.11 (verification), §6 (unknown-field tolerance), §9.1 (profiles).
- [RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md) — §3.5 (`derived_from`), §6 (`data_refs`), §6.2 (structured-locator scheme grammar), §6.8 (absent-vs-null convention).
- [RFC-ACDP-0003 Publish & Supersession](RFC-ACDP-0003-publish.md) — §2.1 (single-signer-per-lineage supersession).
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md) — §4 (error envelope), §5 (error registry, `schema_violation`).
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md) — §4.9 (DataRef-location SSRF protection; the posture this RFC draws a stricter line around).
- [VERSIONING.md](../VERSIONING.md) — additive-minor schema-namespace rule; the registry version-gating requirement cited in §10.
- [RFC 8785] Rundgren, A., Jordan, B., and S. Erdtman, "JSON Canonicalization Scheme (JCS)", RFC 8785, June 2020.
