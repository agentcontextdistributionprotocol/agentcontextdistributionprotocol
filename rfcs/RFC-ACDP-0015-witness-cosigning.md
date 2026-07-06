# RFC-ACDP-0015
# Agent Context Distribution Protocol (ACDP) — Transparency-Log Witness Cosigning

**Document:** RFC-ACDP-0015
**Version:** 0.4.0-draft
**Status:** Community Standards Track (Draft)

This RFC specifies **transparency-log witness cosigning**: independent parties (**witnesses**) that observe an RFC-ACDP-0012 registry's checkpoints, verify each checkpoint's signature and its consistency against the witness's retained head, and **cosign** the checkpoints they have verified. A consumer that trusts any one honest witness inherits split-view protection: a checkpoint is believed only when it was also seen, consistency-checked, and signed by parties the registry does not control. It promotes the RFC-ACDP-0009 §2.12 reservation to a full normative specification and opens the ACDP 0.4.0 line. It depends on RFC-ACDP-0001 (Core), RFC-ACDP-0007 (Capabilities & Errors), RFC-ACDP-0008 (Security), RFC-ACDP-0010 (Registry Receipts), and RFC-ACDP-0012 (Registry Transparency Log).

---

## 1. Status of This Memo

This document is a **Draft** ACDP specification (acdp/0.4.0). It is open for substantive change until promoted to Final per [VERSIONING.md](../VERSIONING.md); its `Version:` header reads `0.4.0-draft`. It goes Final once the conformance fixtures it defines (`wit-001..004`) pass against two independent interoperating implementations (see [CHANGELOG.md](../CHANGELOG.md)). It is the first document of the 0.4.0 line.

This RFC promotes the RFC-ACDP-0009 §2.12 reservation. The reserved names — the array member `witness_signatures`, the cosignature member `witnessed_checkpoint`, `witness_id`, `witnessed_at`, the profile `acdp-log-witness`, and the endpoint path `/log/witness` — are all adopted with their reserved meanings; §12 records the one place this document refines the §2.12 *sketch* (grouping the observed checkpoint's committed tuple under the reserved `witnessed_checkpoint` member rather than restating its fields flat). Nothing in this document invalidates any v0.1.0/0.2.0/0.3.0 body, signature, `content_hash`, RFC-ACDP-0010 receipt, RFC-ACDP-0011 head receipt, or RFC-ACDP-0012 checkpoint, proof, or log.

---

## 2. Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described in BCP 14 ([RFC 2119], [RFC 8174]) when, and only when, they appear in all capitals.

| Term | Definition |
|---|---|
| **Witness** | An independent party — identified by its own DID — that retains a registry's RFC-ACDP-0012 checkpoints over time, verifies each new one against its retained head, and cosigns the ones that pass. A witness is **not** a registry: it has no publish surface and mints no receipts (§3). |
| **Cosignature** | The closed, witness-signed `acdp-log-cosignature` object of §4: the witness's attestation that it observed a specific checkpoint tuple and verified it before signing. |
| **Witnessed checkpoint** | The identity-bearing subset of an RFC-ACDP-0012 §6 checkpoint the witness observed: `{log_id, tree_size, root_hash, timestamp}` (the `witnessed_checkpoint` member). |
| **N-witnessed** | A checkpoint is *N-witnessed* (for a consumer) when *N* distinct witness DIDs the consumer trusts have each produced a cosignature that verifies over the same `(log_id, tree_size, root_hash)` (§8). |
| **Retained head** | The most recent checkpoint of a given `log_id` a witness has itself verified and stored; the anchor a new checkpoint's consistency proof (RFC-ACDP-0012 §9.2) is checked against before cosigning (§7). |
| **Cosignature preimage / hash** | Exactly as RFC-ACDP-0010 §2, applied to the §4 object: the object minus `signature`, JCS-canonicalized (RFC 8785); `"sha256:" + lowercase_hex(SHA-256(preimage))`. |

Hash-valued strings use the repository-wide form `"sha256:" + lowercase_hex(...)`.

---

## 3. Motivation

RFC-ACDP-0012 §13 concedes two residual gaps by design, both rooted in the registry being the *sole* vantage:

- **Checkpoint timestamps are registry-asserted.** A checkpoint's `timestamp` (RFC-ACDP-0012 §6) is the registry's own clock reading; nothing external anchors it. The log adds *ordering* evidence (a leaf's position relative to retained checkpoints) but not *time* evidence.
- **Split-view detection requires comparing checkpoints across vantages.** A registry that lies *consistently to everyone* — presenting one internally-consistent but fabricated history — produces no conflicting evidence for a consumer that has no other vantage. RFC-ACDP-0012 makes such lies *detectable by someone holding checkpoints*, but "ACDP specifies no comparison infrastructure" and "how checkpoints travel between parties is out of scope."

Witnesses close both gaps by *being* the standing external vantages, systematically:

- A witness cosignature binds the witness's **own** observation time (`witnessed_at`) alongside the registry's claimed `timestamp`. This anchors *when the checkpoint was witnessed* against a party the registry does not control (§4 states precisely what this does and does not prove).
- A witness that refuses to cosign a checkpoint failing consistency against its retained head (§7) turns a silent equivocation into a visible, attributable refusal — and a consumer requiring *N* witnesses gets a fabricated history only if the registry can also subvert *N* independent witnesses (§13).

This is the systematic form of the ad-hoc "any party that retains checkpoints is a witness" observation in RFC-ACDP-0012 §13. Prior art in the broader ecosystem — sigsum's witness cosigning, Certificate Transparency gossip, Trillian's witness model, and the C2SP `tlog-witness` note — informs this design but is **not** a normative dependency; the constructions here are ACDP's own (RFC-ACDP-0010 §5 signing, RFC-ACDP-0012 §9 verification).

---

## 4. Cosignature Object (NORMATIVE)

A cosignature is a JSON object with exactly the following members. The canonical schema is [`schemas/json/acdp-log-cosignature.schema.json`](../schemas/json/acdp-log-cosignature.schema.json) (closed: `additionalProperties: false`).

| Field | Type | Required | Description |
|---|---|---|---|
| `cosignature_version` | string | Yes | MUST be exactly `"acdp-cosig/1"`. In-preimage domain separator (the RFC-ACDP-0012 `checkpoint_version` convention): a cosignature can never be mistaken for — or replayed as — a checkpoint, a receipt, or any other JCS-canonicalized ACDP object. |
| `witness_id` | string | Yes | The witness's DID (`did:web` or `did:key`). This is the witness's **own** identity, distinct from the registry's `registry_did`; witnesses are not registries (§3). The reserved RFC-ACDP-0009 §2.12 name (the sketch's `witness_id`; **not** `witness_did`). |
| `witnessed_checkpoint` | object | Yes | The identity-bearing subset of the RFC-ACDP-0012 §6 checkpoint the witness observed: closed `{log_id, tree_size, root_hash, timestamp}`, copied verbatim from the verified checkpoint. `timestamp` is the **registry's** claimed checkpoint time (see below). The reserved RFC-ACDP-0009 §2.12 name. |
| `witnessed_at` | string | Yes | The **witness-clock** time at which the witness observed and cosigned the checkpoint: canonical millisecond-precision RFC 3339 UTC (RFC-ACDP-0001 §5.3). The reserved RFC-ACDP-0009 §2.12 name. |
| `signature` | object | Yes | The **witness's** signature over the cosignature hash, using the `signature` object shape of RFC-ACDP-0001 §5.8 (`algorithm`, `key_id`, `value`; closed schema). `signature.key_id` MUST be a DID URL under `witness_id`. |

All members other than `signature` are covered by the cosignature signature. There is no exclusion set beyond `signature` itself.

**What `witnessed_at` proves — precisely.** Binding the witness's own observation time alongside the registry's claimed `witnessed_checkpoint.timestamp` proves that **the checkpoint (this exact `root_hash` at this `tree_size`) existed and was signature- and consistency-valid no later than `witnessed_at`, according to a clock the registry does not control.** It therefore bounds *how far the registry could have backdated the checkpoint's `timestamp`* and *when a given tree state was first exposed to an external party*. It does **not** prove that `timestamp` is accurate (it remains registry-asserted — the witness copies it, does not vouch for it), does **not** prove the checkpoint was created *at* `witnessed_at` (only that it existed *by* then), and does **not** prove anything about leaves appended after the witnessed `tree_size`. Anti-backdating and anti-equivocation follow from *many* witnesses at *many* times, not from any single cosignature (§13).

Cosignatures are **ephemeral, per-observation** evidence (the RFC-ACDP-0011 §4 posture, not the RFC-ACDP-0010 §4 immutability posture): a witness produces a fresh cosignature (fresh `witnessed_at`) each time it re-observes the log, including a fresh cosignature at an unchanged `tree_size` as a liveness signal.

---

## 5. Signing Construction (NORMATIVE)

The cosignature signing construction **reuses RFC-ACDP-0010 §5 verbatim**; implementations MUST NOT introduce a second canonicalization or signing-input framing:

1. **Preimage.** Remove the `signature` member. JCS-canonicalize (RFC 8785) the remainder.
2. **Hash.** `cosignature_hash = "sha256:" + lowercase_hex(SHA-256(preimage_bytes))`.
3. **Signing input.** The **ASCII bytes of the full `cosignature_hash` string**, `sha256:` prefix included (RFC-ACDP-0001 §5.8; RFC-ACDP-0010 §5 step 3).
4. **Signature.** Sign with the **witness's** signing key — the key referenced by `signature.key_id`, published in the witness's DID document's `assertionMethod` (§9). `signature.algorithm` follows RFC-ACDP-0001 §5.10 (`ed25519` mandatory-to-implement; `ecdsa-p256` optional, IEEE 1363 r‖s wire form). `signature.value` is the base64-encoded signature bytes. The `key_fingerprint` encoding of RFC-ACDP-0010 §6 applies wherever a witness key is fingerprinted.

The one departure from RFC-ACDP-0010/0011/0012, which all sign with the registry receipt key, is deliberate and load-bearing: **the signer is the witness, under the witness's own DID and key.** The whole value of a cosignature is that it is *not* the registry's signature — a checkpoint the registry could forge for itself is worthless as an external vantage. Witnesses therefore introduce a new key role (their own), unlike RFC-ACDP-0011/0012, which reuse the registry receipt key.

The golden vector `wit-001-cosignature-golden.json` pins the canonical preimage bytes, the cosignature hash, and an Ed25519 signature end-to-end under a distinct witness test keypair (seed `0x33` repeated 32×), over the `log-001` golden checkpoint (so the vectors chain); it is executed arithmetically by `scripts/conformance-runner.py`.

---

## 6. Distribution (NORMATIVE)

A cosignature reaches a consumer by either of two paths; both are OPTIONAL for any given deployment, and a consumer MAY use either or both.

### 6.1 Registry aggregation

A registry advertising `acdp-registry-transparency-log` **MAY** aggregate cosignatures it has collected from witnesses and serve them alongside its checkpoint, as the top-level member **`witness_signatures`** — an array of §4 cosignature objects — of the response body it attaches to:

- On `GET /log/checkpoint` (RFC-ACDP-0012 §8.1): the response MAY carry `witness_signatures` as a **sibling** of the checkpoint members, under the same top-level-openness discipline as `log_inclusion` on retrieval (RFC-ACDP-0012 §10). Because the bare checkpoint *is* the `GET /log/checkpoint` body and its schema is closed, a registry electing to serve cosignatures on this endpoint returns an envelope `{ "log_checkpoint": { … }, "witness_signatures": [ … ] }` rather than embedding the array inside the closed checkpoint object.
- On full retrieval carrying `log_inclusion` (RFC-ACDP-0012 §10): `witness_signatures` MAY appear as a top-level sibling of `log_inclusion` and `registry_receipt`, cosigning the checkpoint embedded in `log_inclusion.log_checkpoint`.

`witness_signatures` is OUTSIDE every signed object, is never part of any `content_hash`, receipt, checkpoint, or leaf preimage, and MUST NOT appear inside a stored body, a checkpoint, or a receipt. Aggregation is a convenience: a registry that aggregates has no ability to forge a cosignature (it is not the witness's key), and a registry MAY refuse to serve, or selectively omit, cosignatures — which is exactly why consumers may go direct (§6.2). The reserved RFC-ACDP-0009 §2.12 name `witness_signatures` is used exactly as reserved.

### 6.2 Direct-from-witness

A witness **SHOULD** serve its own cosignature history at **`GET /log/witness`** on its HTTPS authority (the reserved RFC-ACDP-0009 §2.12 endpoint path), returning `application/acdp+json`. The endpoint returns the witness's cosignatures, most-recent first, OPTIONALLY filtered by `?log_id=<log_id>`:

```json
{
  "witness_id": "did:web:witness.example.org",
  "witness_signatures": [
    { "cosignature_version": "acdp-cosig/1", "witness_id": "did:web:witness.example.org", "witnessed_checkpoint": { … }, "witnessed_at": "…", "signature": { … } }
  ]
}
```

Fetching direct from a witness removes the registry from the trust path entirely: the consumer learns what the witness saw without the registry able to withhold or filter it. All SSRF protections of RFC-ACDP-0008 §4.8 apply to the witness fetch, and a witness capabilities document (§9) tells a consumer which logs a witness covers. Out-of-range or malformed parameters → `schema_violation`.

---

## 7. Witness Obligations (NORMATIVE)

Before producing a cosignature for a checkpoint C of `log_id` L, a witness **MUST**:

1. **Verify C's checkpoint signature** per RFC-ACDP-0012 §9.3 (closed parse; signature recomputed and verified against the registry's DID key resolved under the SSRF protections of RFC-ACDP-0008 §4.8; registry binding; form). A witness MUST NOT cosign a checkpoint whose own signature does not verify.
2. **Verify consistency from its retained head.** If the witness holds a retained head H for L at `tree_size` *h* ≤ C's `tree_size`, it MUST obtain and verify an RFC-ACDP-0012 §9.2 consistency proof between H and C (against H's retained `root_hash`). A witness **MUST NOT cosign a checkpoint that fails consistency against its retained head** — this refusal is the entire point of witnessing; a witness that cosigns a root-rewrite provides negative security value. If the witness holds no prior head for L, C becomes its first retained head after step 1 (a witness's first observation of a log anchors, but proves no consistency — the anti-rewrite guarantee accrues from the *second* observation onward, the RFC-ACDP-0012 §7.3 backfill posture one level up).
3. **Only then cosign** C per §5, copying C's `{log_id, tree_size, root_hash, timestamp}` verbatim into `witnessed_checkpoint` and stamping `witnessed_at` from its own clock.

On a consistency failure (a signature-valid C that is not consistent with a signature-valid retained H of the same L), the witness:

- **MUST NOT** emit a cosignature for C;
- **MUST** persist both checkpoints and the failing proof as evidence (the RFC-ACDP-0012 §15 evidence-handling posture — a pair of signature-valid, mutually inconsistent checkpoints of one `log_id` is compact, portable, non-repudiable proof of registry misbehavior);
- **SHOULD** make that evidence discoverable (e.g. an operational notice, or a distinct non-cosigning status on `GET /log/witness`).

A witness **SHOULD** update its retained head to C after cosigning, so that its next observation's consistency check spans the shortest gap. A witness **SHOULD** re-observe each covered log periodically (its cadence is its own operational policy) and **SHOULD** serve its cosignature history per §6.2.

Witnesses are stateless with respect to leaf contents: a witness verifies signatures, roots, and consistency only, and never needs leaf bodies (it MAY operate entirely from `GET /log/checkpoint` and `GET /log/proof?first=…&second=…`). A witness therefore learns only publication *volume and timing* metadata (RFC-ACDP-0012 §15), never context contents.

---

## 8. Consumer Verification Procedure (NORMATIVE)

A consumer evaluating witness evidence for a checkpoint it has itself verified (RFC-ACDP-0012 §9.3) MUST, for **each** cosignature it considers:

1. **Schema-closed parse.** The cosignature MUST parse against the closed schema of §4; `cosignature_version` MUST be exactly `"acdp-cosig/1"`. Unknown members, missing members, or a different `cosignature_version` fail verification (every member is signed).
2. **Recompute and verify the witness signature.** JCS-recompute the preimage (§5), recompute the cosignature hash, resolve the key referenced by `signature.key_id` from the **witness's** DID document (RFC-ACDP-0001 §5.11, with the SSRF protections of RFC-ACDP-0008 §4.8), and verify `signature.value` over the ASCII bytes of the cosignature hash. The resolved key MUST be in the witness DID's `assertionMethod` (§9); a key found only in `verificationMethod` verifies *historical* cosignatures (the RFC-ACDP-0010 §9 lifecycle, applied to the witness's own key).
3. **Witness binding.** The DID portion of `signature.key_id` MUST equal `witness_id`. `witness_id` MUST be a witness the consumer trusts (trust bootstrapping is deployment policy — §13).
4. **Checkpoint binding.** `witnessed_checkpoint.log_id`, `witnessed_checkpoint.tree_size`, and `witnessed_checkpoint.root_hash` MUST equal, byte-for-byte / numerically, the corresponding fields of the checkpoint the consumer is evaluating. A cosignature over a *different* `(log_id, tree_size, root_hash)` is evidence about a different checkpoint and MUST NOT be counted for this one.
5. **`witnessed_at` well-formedness and skew.** `witnessed_at` MUST match the canonical millisecond form (§4) and MUST NOT be in the future relative to the consumer's clock beyond a small skew allowance (RECOMMENDED: **120 seconds**, the RFC-ACDP-0011 §7 step 6 allowance).

A checkpoint is then **N-witnessed** for the consumer where *N* is the number of **distinct `witness_id` values** whose cosignatures passed steps 1–5 over that checkpoint's `(log_id, tree_size, root_hash)`. Multiple cosignatures from the same `witness_id` count once. The consumer then applies its local quorum and freshness policy (§8.1).

A failure of any of steps 1–5 for a given cosignature MUST be treated as a verification failure **of that cosignature** and surfaced with the `invalid_witness_cosignature` semantic (§10); it does not, by itself, fail the checkpoint (the checkpoint verdict is RFC-ACDP-0012 §9.3) — it simply does not count toward *N*. **Witness verdicts are independent** of the body, receipt, head-receipt, and log verdicts and SHOULD be reported separately (RFC-ACDP-0012 §9.3 extended by one).

### 8.1 Consumer policy surface (RECOMMENDED)

Quorum and freshness are **local consumer policy**, not wire-visible requirements, mirroring the RFC-ACDP-0011 §6 freshness stance:

- **Minimum witnesses (`N`).** The consumer decides how many distinct trusted witnesses a checkpoint must carry before it is relied upon. RECOMMENDED default: **1** distinct trusted witness for split-view protection (one honest witness suffices to expose a fork); deployments with stronger requirements SHOULD raise it.
- **Maximum cosignature age.** The consumer decides the maximum acceptable `witnessed_at` staleness for a decision that depends on the checkpoint being *current*. RECOMMENDED default: **300 seconds** for current-ness-sensitive decisions (aligned with RFC-ACDP-0011 §6 / RFC-ACDP-0012 §7.2); for the anti-backdating/anti-rewrite use a witness cosignature never expires (an old cosignature is *stronger* evidence that a tree state existed early).

Staleness beyond policy is a *freshness* verdict, distinct from the §8 verification failures (a cosignature may be perfectly genuine — merely old).

---

## 9. Witness Identity, Keys, and Capabilities (NORMATIVE)

- **Identity.** A witness is identified by a DID — `did:web` or `did:key` — with signing keys in the DID document's `assertionMethod`. A witness is **not** a registry: it advertises no publish endpoints and mints no receipts. `did:web` witnesses resolve under the SSRF protections of RFC-ACDP-0008 §4.8; `did:key` witnesses need no resolution (the RFC-ACDP-0001 §5.11.1 posture).
- **Key lifecycle.** The witness key lifecycle is the RFC-ACDP-0010 §9 registry-receipt-key lifecycle applied to the witness's own key: retired witness keys remain in `verificationMethod` indefinitely so historical cosignatures stay verifiable; rotation removes a key from `assertionMethod` only; removal from `verificationMethod` (invalidating cosignatures under that key) only on confirmed compromise. Because cosignatures are ephemeral (§4), post-compromise recovery needs no re-issuance campaign — fresh observations simply carry the successor key.
- **Capabilities document.** A witness SHOULD serve a witness capabilities document at **`/.well-known/acdp-witness.json`** describing itself. RFC-ACDP-0009 §2.12 reserved no well-known path, so this document adopts one by analogy with `/.well-known/acdp.json` (RFC-ACDP-0007 §3); it is advisory, not a wire dependency of §8 (a consumer verifies cosignatures against the witness DID regardless). RECOMMENDED members:

```json
{
  "witness_id": "did:web:witness.example.org",
  "profiles": ["acdp-log-witness"],
  "covered_logs": ["did:web:registry.example.com/log/1"],
  "cosignature_endpoint": "/log/witness"
}
```

`covered_logs` is advisory (a witness MAY cosign any log; the list states which it commits to observing). Unknown members MUST be tolerated (RFC-ACDP-0001 §6).

---

## 10. Capabilities, Profile, and Errors

- **Profile.** `acdp-log-witness` — the name reserved by RFC-ACDP-0009 §2.12 (registered in `registries/profiles.md`). It is a **witness** profile, not a registry profile: it has no prerequisite registry profile (a witness is not a registry) and its conformance is the §5/§7/§9 obligations plus the `wit-*` fixtures. Advertised in the witness capabilities document's `profiles` (§9). A registry does **not** advertise `acdp-log-witness`; a registry that *aggregates* cosignatures (§6.1) does so under its existing `acdp-registry-transparency-log` profile, which §11 (RFC-ACDP-0012) amends by one optional member.
- **Version.** Witnesses and cosignature-aware consumers advertise/require `acdp_version` ≥ `0.4.0` for cosignature behavior.
- **Error code: `invalid_witness_cosignature` (new wire code, HTTP 502).** A witness cosignature failed the §8 verification procedure (closed parse, witness-key signature, witness binding, checkpoint binding, or the `witnessed_at` skew check). This is deliberately **not** `invalid_log_proof`: an `invalid_log_proof` indicts the *log* (tree membership, history consistency, the registry's checkpoint signature — RFC-ACDP-0012 §11); an `invalid_witness_cosignature` indicts a *witness's* attestation, an independent verdict over an independent signer. Collapsing them would overload a single semantic, violating the anti-overloading rule of `registries/error-codes.md` — the same argument by which RFC-ACDP-0012 §11 kept `invalid_log_proof` distinct from `invalid_receipt`. On the wire it is emitted by a registry aggregating cosignatures on a caller's behalf, or by a resolver validating a witness's cosignatures (HTTP 502 — the cosignature came from an upstream party); it is also the verification-failure category consumer SDKs use for a locally failing cosignature. Registered per the `registries/error-codes.md` process; added to the RFC-ACDP-0007 §5 table and the `acdp-error.schema.json` wire enum. Implementations declaring `acdp_version` < `0.4.0` MUST NOT emit it. A cosignature that verifies but is merely *stale* is consumer freshness policy (§8.1), never this code. A checkpoint that is simply un-witnessed (0-witnessed) is **not** an error — it carries no cosignatures, and the consumer's quorum policy decides whether to rely on it.
- **No new registry error surface for aggregation.** A registry that cannot serve cosignatures simply omits `witness_signatures`; there is no `witness_unavailable` — witnessing is an ecosystem overlay, not a registry commitment (contrast RFC-ACDP-0012 §7.1's no-`log_unavailable` rule, which *is* a commitment because the log profile promises it).

---

## 11. Compatibility

Witness cosigning is additive; nothing existing changes:

- **New schema, `v0.1.0` namespace.** `acdp-log-cosignature.schema.json` (closed) is additive in the `v0.1.0` schema namespace (VERSIONING.md), like every 0.2.0/0.3.0 schema.
- **Checkpoint and retrieval envelopes.** The OPTIONAL `witness_signatures` array (§6.1) rides existing top-level openness — on `GET /log/checkpoint` via an envelope around the closed checkpoint, and on retrieval as a sibling of `log_inclusion`/`registry_receipt` (RFC-ACDP-0012 §10). No closed object gains a member; no existing parse surface changes. Pre-0.4.0 consumers ignore `witness_signatures` under RFC-ACDP-0001 §6.
- **No change to checkpoints, proofs, receipts, bodies.** No RFC-ACDP-0012 checkpoint/leaf/proof semantic, no RFC-ACDP-0010/0011 receipt semantic, no JCS rule, `content_hash`, or signature semantic is touched. The witness signs a *new* object with a *new* key; it does not re-sign or alter anything.
- **Error enum.** `acdp-error.schema.json` gains `invalid_witness_cosignature` — the same additive-enum posture as `invalid_log_proof` in 0.3.0. Strict pre-0.4.0 decoders that reject unknown codes were already non-conformant (RFC-ACDP-0007 §4 requires tolerating vocabulary growth).
- **Non-participating deployments** are unaffected: a registry that never aggregates, a log with no witnesses, and a consumer that ignores cosignatures are all fully conformant at every ACDP version. Witnessing strictly adds evidence.

---

## 12. Promotion Notes Against the §2.12 Sketch

The RFC-ACDP-0009 §2.12 reservation is adopted with its reserved *names* carrying their reserved meanings; one refinement of the sketch is recorded:

- **`witnessed_checkpoint` is a grouping object.** The sketch reserved `witnessed_checkpoint`, `witness_id`, and `witnessed_at` as sibling names. This document groups the observed checkpoint's committed tuple (`log_id`, `tree_size`, `root_hash`, `timestamp`) *under* the reserved `witnessed_checkpoint` member, rather than restating those four checkpoint fields flat at the top level. This keeps the cosignature's top level to exactly the witness's own assertions (`witness_id`, `witnessed_at`, `signature`, the version tag) plus the one grouped thing-observed, and lets the `witnessed_checkpoint` sub-object mirror the RFC-ACDP-0012 §6 checkpoint shape one-to-one. All four reserved names (`witness_signatures`, `witnessed_checkpoint`, `witness_id`, `witnessed_at`), the profile `acdp-log-witness`, and the endpoint `/log/witness` are used exactly as reserved.
- **The signer is the witness, not the registry.** RFC-ACDP-0011 and RFC-ACDP-0012 reuse the registry receipt key; §5 here uses the witness's own key. This is not a refinement of the sketch (the sketch implied it — "parties the registry does not control") but is called out because it is the one construction that departs from the receipt-key reuse pattern of the rest of the trust arc.

---

## 13. Scope and Limitations (honest scope)

Witness cosigning closes the "consistent lie to everyone" gap of RFC-ACDP-0012 §13 — and no more:

- **Witnesses prove observation, not completeness or validity.** A cosignature proves a witness saw and consistency-checked a checkpoint by `witnessed_at`. It proves nothing about *inclusion completeness* (whether the log omits contexts the registry accepted — that is still leaf-by-leaf demand by receipt-holders, RFC-ACDP-0012 §13) and nothing about *data validity* (producer signatures, receipts — independent verdicts, §8).
- **Total collusion defeats it.** A consumer requiring *N* witnesses is protected only if fewer than *N* of its trusted witnesses collude with the registry. If *all* of a consumer's trusted witnesses collude with the registry, they can cosign a fabricated-but-consistent history and the consumer has no vantage left. Witnessing raises the cost of undetected equivocation from "control the registry" to "control the registry **and** *N* independent witnesses"; it does not make it impossible. Choosing genuinely independent witnesses is the consumer's security-critical deployment decision.
- **Witness discovery and trust bootstrapping are deployment policy.** How a consumer learns which witnesses exist and decides which to trust is out of scope — the same "no comparison infrastructure specified" boundary RFC-ACDP-0012 §13 drew, moved one step. A **registry-of-witnesses** (a discovery directory) is explicitly out of scope and reserves **no new name**; deployments use their own trust anchors (a curated witness list, a policy file, an org's shared configuration). This document adds only the names RFC-ACDP-0009 §2.12 already reserved.
- **A single cosignature is weak; the ecosystem is the strength.** One witness at one instant bounds one tree state's existence time. Anti-backdating, anti-rewrite, and anti-equivocation accrue from *many* witnesses observing at *many* times and *comparing* — which is why §6.2 (direct-from-witness) and §7 (retained-head consistency, evidence-on-failure) matter more than any one signature.
- **No gossip protocol is specified.** How witnesses discover each other or exchange observations to detect a registry showing different histories to different *witnesses* is not specified here; it is a natural next layer and remains deployment-specific for 0.4.0.
- **Optionality is conformant.** Witnessing is an optional overlay: a registry that never aggregates, a log with no witnesses, and a consumer that ignores cosignatures are each fully conformant. Witnesses strictly add evidence to the RFC-ACDP-0012 log; they never gate it.

---

## 14. Conformance Fixtures

| ID | What it pins | Runner |
|---|---|---|
| `wit-001-cosignature-golden` | Full golden vector: a distinct witness test keypair (Ed25519 seed `0x33`×32), the cosignature preimage canonical bytes, the cosignature hash, and the Ed25519 signature end-to-end, over the `log-001` golden checkpoint (`tree_size` 5, `root_hash` `sha256:0b5978…`) so the vectors chain. The `sig-001`-equivalent for the witness layer. | Executed arithmetically |
| `wit-002-consistency-refusal` | Behavioral: a witness holding the `log-003` size-3 retained head is presented a signature-valid size-5 checkpoint whose `root_hash` was rewritten (≠ the genuine `log-001` root) → §7 step 2 consistency fails → the witness MUST NOT cosign and MUST persist evidence. The entire point of witnessing. | Behavioral (data pinned) |
| `wit-003-quorum-verification` | Two distinct witnesses (seeds `0x33` and `0x44`) cosign the *same* `log-001` checkpoint tuple → §8 yields **2-witnessed**. Both cosignatures executed arithmetically; the runner asserts distinct `witness_id`s over one `(log_id, tree_size, root_hash)`. | Executed arithmetically |
| `wit-004-cosignature-key-mismatch` | Behavioral: a cosignature whose `signature.value` was produced by the *wrong* witness key (witness B's key over witness A's body, so it does not verify under witness A's resolved `assertionMethod` key) → §8 step 2 MUST fail (`invalid_witness_cosignature`); the analogue of `rcpt-003`/`log-004` for the witness layer. | Behavioral (data pinned) |

Vectors are generated by `temp/gen-0.4.0-vectors.py` (never hand-written), following `temp/gen-0.3.0-vectors.py`; the generator uses the same `jcs` + `cryptography` libraries as the runner and the `log-001` golden checkpoint as the cosigned material.

---

## 15. Security Considerations

- **Witness independence is the whole game.** A cosignature is worth exactly the independence of its signer from the registry. Consumers MUST choose witnesses that do not share failure domains with the registry (operator, hosting, jurisdiction, key custody); §13's total-collusion limit is otherwise reached silently.
- **Witness key is a signing identity.** Every RFC-ACDP-0010 §15 / RFC-ACDP-0012 §15 key-handling requirement (HSM/KMS boundary, role separation) applies to the witness's own key. A compromised witness key lets an attacker forge that witness's cosignatures — but only that one witness's; the *N*-witness quorum is the blast-radius control.
- **DID fetches.** Cosignature verification dereferences the witness's `did:web` document; the SSRF protections of RFC-ACDP-0008 §4.8 apply identically. Direct-from-witness fetches (§6.2) are producer-uncontrolled but still SSRF-guarded.
- **A witness never sees leaf contents.** Witnessing operates on checkpoints, roots, and consistency proofs only (§7); it exposes the witness to the same publication volume/timing metadata as any auditor (RFC-ACDP-0012 §15) and to nothing more. This keeps the witness ecosystem privacy-compatible with restricted contexts.
- **Refusal is evidence, not silence.** A witness that declines to cosign a failing checkpoint MUST persist and SHOULD surface the failing pair (§7); a witness that silently stops cosigning is indistinguishable from one that is merely offline, degrading the signal. Consumers SHOULD treat a witness that *stops* cosigning a previously-covered log as a prompt to seek other vantages.
- **Independence of verdicts.** A verified cosignature is evidence that a witness observed a checkpoint — never of body authenticity, receipt validity, head current-ness, or log inclusion. The five verdicts (body, context receipt, head receipt, log, witness) MUST be kept distinct.

See RFC-ACDP-0008 §9.1–§9.2 (as amended for 0.3.0; the checkpoint-timestamp assurance level rises from Medium toward High for a checkpoint carrying trusted, fresh cosignatures) for the threat-model placement.

---

## 16. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md) — §5.8 (signature), §5.10 (algorithms), §5.11 / §5.11.1 (key resolution, did:key), §6 (unknown-field tolerance), §9.1 (profiles).
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md) — §4 (error envelope), §5 (error registry).
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md) — §4.8 (DID-resolution SSRF), §9 (threat model).
- [RFC-ACDP-0009 Extensions](RFC-ACDP-0009-extensions.md) — §2.12 (origin of this RFC).
- [RFC-ACDP-0010 Registry Receipts](RFC-ACDP-0010-registry-receipts.md) — §5 (signing construction, reused), §6 (fingerprint encoding), §9 (key lifecycle, applied to the witness key).
- [RFC-ACDP-0011 Lineage-Head Receipts](RFC-ACDP-0011-lineage-head-receipts.md) — the ephemeral-evidence and consumer-freshness-policy posture reused here.
- [RFC-ACDP-0012 Registry Transparency Log](RFC-ACDP-0012-transparency-log.md) — §6 (checkpoints), §9.2 (consistency verification), §9.3 (checkpoint verification), §10 (retrieval binding), §13 (the gaps this RFC closes), §15 (evidence handling).
- [RFC 8785] Rundgren, A., Jordan, B., and S. Erdtman, "JSON Canonicalization Scheme (JCS)", RFC 8785, June 2020.
- [RFC 8032] Josefsson, S. and I. Liusvaara, "Edwards-Curve Digital Signature Algorithm (EdDSA)", RFC 8032, January 2017.
- Inspiration (non-normative): sigsum witness cosigning; Certificate Transparency gossip; Trillian witness model; C2SP `tlog-witness`.
