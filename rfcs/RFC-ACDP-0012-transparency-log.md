# RFC-ACDP-0012
# Agent Context Distribution Protocol (ACDP) — Registry Transparency Log

**Document:** RFC-ACDP-0012
**Version:** 0.3.0
**Status:** Community Standards Track (Final)

This RFC specifies the **registry transparency log**: a per-registry, append-only Merkle tree (RFC 6962-style) over publish events, with registry-signed checkpoints (tree heads), inclusion proofs, and consistency proofs. It promotes the RFC-ACDP-0009 §2.11 reservation to a full normative specification and is the capstone of the trust-hardening arc begun by RFC-ACDP-0010 (Registry Receipts) and continued by RFC-ACDP-0011 (Lineage-Head Receipts): receipts made registry claims *attributable and non-repudiable*; the log makes mint-time backdating, omission-after-the-fact, and per-consumer equivocation *detectable by any auditor holding checkpoints*. It depends on RFC-ACDP-0001 (Core), RFC-ACDP-0003 (Publish), RFC-ACDP-0004 (Retrieval), RFC-ACDP-0007 (Capabilities & Errors), RFC-ACDP-0008 (Security), and RFC-ACDP-0010 (Registry Receipts).

---

## 1. Status of This Memo

This document is a **Final** ACDP specification (acdp/0.3.0). It is stable for the 0.3.0 line; subsequent breaking changes require a new RFC and a version bump per [VERSIONING.md](../VERSIONING.md). It was promoted from Draft to Final on 2026-07-05, the VERSIONING.md gate having been met: the conformance fixtures it defines (`log-001..004`) pass against two independent interoperating implementations (see [CHANGELOG.md](../CHANGELOG.md) for the promotion record).

This RFC promotes the RFC-ACDP-0009 §2.11 reservation. The reserved names — `log_inclusion`, `log_checkpoint`, `log_id`, `leaf_index`, `inclusion_path`, the profile `acdp-registry-transparency-log`, and the endpoint paths `/log/checkpoint`, `/log/proof`, `/log/entries` — are all adopted with the reserved meanings; §12 records the two places where this document refines the §2.11 *sketch* (the position of `log_inclusion` and the realization of the checkpoint signature member). Nothing in this document invalidates any v0.1.0/0.2.0/0.3.0 body, signature, `content_hash`, RFC-ACDP-0010 receipt, or RFC-ACDP-0011 head receipt.

---

## 2. Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described in BCP 14 ([RFC 2119], [RFC 8174]) when, and only when, they appear in all capitals.

| Term | Definition |
|---|---|
| **Log** | A per-registry, append-only sequence of leaves, organized as an RFC 6962-style binary Merkle tree over SHA-256 (§5). One publish event → one leaf, forever. |
| **Leaf** | The JCS-canonical JSON (RFC 8785) of the closed leaf object of §4, binding one publish event: identifiers, `created_at`, `content_hash`, producer `key_fingerprint`, and the RFC-ACDP-0010 receipt hash. |
| **Leaf hash** | `SHA-256(0x00 ‖ leaf_bytes)` — one byte `0x00` prepended to the leaf's JCS bytes (§5.1). |
| **Checkpoint** (signed tree head) | The closed, registry-signed `log_checkpoint` object of §6: `{checkpoint_version, log_id, tree_size, root_hash, timestamp, signature}`. |
| **Inclusion proof** | A leaf index plus an `inclusion_path` (RFC 6962 §2.1.1 audit path) proving a leaf is in the tree of a stated `tree_size` (§9.1). |
| **Consistency proof** | An RFC 6962 §2.1.2 proof that the tree at one size is a prefix of the tree at a later size — i.e. that no logged history was rewritten (§9.2). |
| **Log instantiation** | One `log_id` value. A registry operates exactly one live instantiation; a new instantiation (new `log_id`) is an explicit, detectable reset (§7.4). |
| **Receipt hash** | Exactly as RFC-ACDP-0010 §2: `"sha256:" + lowercase_hex(SHA-256(receipt preimage))`, the string whose ASCII bytes the registry's receipt signature covers. |
| **Log signing key** | The RFC-ACDP-0010 §2 registry receipt signing key. The log introduces **no new key role** (same posture as RFC-ACDP-0011 §5). |

Hash-valued strings in this document (`root_hash`, `receipt_hash`, `inclusion_path[]` elements, leaf hashes on the wire) use the repository-wide form `"sha256:" + lowercase_hex(...)`. Merkle-internal computation (§5) operates on the raw 32-byte digests those strings encode.

---

## 3. Motivation

RFC-ACDP-0010 §13 states the residual gap precisely: receipts make registry claims attributable and non-repudiable, **not unforgeable at mint time**. A registry can still backdate `created_at` at the moment it first mints a receipt; it can decline to mention contexts it has hidden; and it can equivocate between consumers, detectably only if the conflicting receipts happen to be compared — and "ACDP specifies no comparison infrastructure." RFC-ACDP-0011 head receipts made serve-time claims attributable too, but their §11 concedes the same limit: a registry lying *consistently to everyone* produces no conflicting evidence.

The transparency log closes the *detectability* half of these gaps by making the registry commit, under its receipt signing key, to a single append-only history:

- **Backdating becomes detectable-with-witnesses.** Every publish appends a leaf binding its `created_at` and receipt hash at a fixed position in an append-only history. A checkpoint of `tree_size` *n* commits to exactly the first *n* leaves. A context "published in April" that first appears at a position beyond a July checkpoint is self-evidently minted after that checkpoint — any monitor that retained the July checkpoint can prove it.
- **History rewrites become detectable.** Two checkpoints of the same `log_id` MUST be consistent (§9.2). A registry that rewrites, reorders, or removes a logged leaf cannot produce a valid consistency proof between a pre-rewrite and a post-rewrite checkpoint; refusal or failure to produce one is itself the evidence.
- **Equivocation becomes detectable.** A registry showing different histories to different consumers must sign conflicting checkpoints (same `log_id`, same or overlapping `tree_size`, different `root_hash`) — two such checkpoints are compact, self-contained, non-repudiable proof of split-view. Comparing checkpoints across vantages is deliberately cheap: a checkpoint is a few hundred bytes.
- **Omission becomes detectable by the interested party.** A producer holding its RFC-ACDP-0010 receipt can demand an inclusion proof for its own context; a registry that accepted the publish (and signed the receipt) but keeps it out of the log cannot supply one. The receipt proves acceptance; the missing inclusion proof proves the log lie.

What the log does **not** do is equally definite — see §13.

---

## 4. Leaf Object and Leaf Encoding (NORMATIVE)

One leaf is appended per accepted publish (RFC-ACDP-0003 §2.1), binding the publish event. A leaf is a JSON object with exactly the following members. The canonical schema is [`schemas/json/acdp-log-leaf.schema.json`](../schemas/json/acdp-log-leaf.schema.json) (closed: `additionalProperties: false`).

| Field | Type | Required | Description |
|---|---|---|---|
| `leaf_version` | string | Yes | MUST be exactly `"acdp-log-leaf/1"`. In-object domain separator (the RFC-ACDP-0011 `receipt_version` convention): a leaf can never be mistaken for an RFC-ACDP-0010 receipt preimage or any other JCS-canonicalized ACDP object. |
| `ctx_id` | string | Yes | The registry-assigned context identifier (RFC-ACDP-0001 §5.5). Exactly one leaf per `ctx_id` — bodies are immutable, so a publish event happens once. |
| `lineage_id` | string | Yes | The registry-derived lineage identifier (RFC-ACDP-0001 §5.6). |
| `origin_registry` | string | Yes | The registry-assigned origin authority (bare DNS hostname, RFC-ACDP-0002 §3.1). MUST equal the authority component of `ctx_id` and the method-specific identifier of the log's registry DID. |
| `created_at` | string | Yes | The registry-assigned creation timestamp, canonical millisecond-precision RFC 3339 UTC (RFC-ACDP-0001 §5.3). MUST be byte-identical to `body.created_at` and to `registry_receipt.created_at`. |
| `content_hash` | string | Yes | The body's `content_hash` as verified at publish time (RFC-ACDP-0001 §5.7). |
| `key_fingerprint` | string | Yes | The RFC-ACDP-0010 §6 fingerprint of the producer key resolved at publish time. MUST equal `registry_receipt.key_fingerprint`. |
| `receipt_hash` | string | Yes | The RFC-ACDP-0010 §2 **receipt hash** of this context's registry receipt: `"sha256:" + lowercase_hex(SHA-256(JCS(receipt minus signature)))`. |

The **leaf encoding** — the exact bytes that are hashed — is the JCS canonicalization (RFC 8785) of this object, UTF-8. There is no exclusion set: every member is part of the leaf bytes.

Design notes (normative consequences):

- **The leaf binds the receipt by its hash, not verbatim.** RFC-ACDP-0009 §2.11 reserved "every minted receipt is appended as a leaf"; this document realizes that binding via `receipt_hash` rather than embedding the receipt object (with its signature bytes) in the leaf. The receipt hash *is* the signed statement — the registry's receipt signature covers exactly its ASCII bytes (RFC-ACDP-0010 §5) — so binding the hash binds everything the registry attested, while keeping leaves compact and, critically, **stable across the one sanctioned re-mint**: RFC-ACDP-0010 §9 permits re-signing a receipt under a successor key after receipt-key compromise, attesting the identical fields. The receipt hash excludes `signature`, so the sanctioned re-mint does not change it, and the log history survives receipt-key compromise recovery without any leaf ever being rewritten.
- All leaf fields other than `receipt_hash` duplicate receipt fields **deliberately**: a verifier holding the body and its verified receipt can reconstruct the leaf byte-for-byte with no additional trust in the registry (§9.1 step 1). A leaf whose duplicated fields disagree with the receipt they hash is non-conformant and MUST fail verification.
- Registries MUST NOT log rejected publishes: a leaf asserts an accepted, receipt-bearing publish event.

---

## 5. Merkle Tree Construction (NORMATIVE)

The tree is the binary Merkle tree of RFC 6962 §2.1 over SHA-256, with the RFC 6962 domain-separation prefixes. The bytes, spelled out:

### 5.1 Hashing

```
leaf_hash(leaf)      = SHA-256( 0x00 ‖ JCS(leaf) )          // one prefix byte, value zero
node_hash(left, right) = SHA-256( 0x01 ‖ left ‖ right )      // one prefix byte, value one;
                                                             // left, right are raw 32-byte digests
```

The `0x00`/`0x01` prefixes are REQUIRED. They ensure a second-preimage separation between leaves and interior nodes: without them, an attacker who can choose leaf bytes could present an interior node's 64-byte child concatenation as a "leaf" and forge proofs for entries that were never appended. Implementations MUST NOT hash a leaf without the `0x00` prefix and MUST NOT hash an interior node without the `0x01` prefix.

### 5.2 Merkle tree hash

For an ordered list of *n* leaf hashes `D[n] = {d(0), …, d(n−1)}` (leaves in append order, `leaf_index` 0-based):

```
MTH({})     = SHA-256("")                       // empty tree: the SHA-256 of the empty string,
                                                //   e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
MTH({d})    = d                                 // d is already a leaf hash (0x00-prefixed at §5.1)
MTH(D[n])   = node_hash( MTH(D[0:k]), MTH(D[k:n]) )
              where k is the largest power of two strictly less than n
```

`root_hash` at `tree_size` *n* is `"sha256:" + lowercase_hex(MTH(D[n]))`.

### 5.3 Append-only invariant

The tree is strictly append-only: `leaf_index` values are assigned consecutively from 0 in publish-acceptance order and are never reused, reordered, or deleted. For every pair of checkpoints of the same `log_id` with `tree_size` *m* ≤ *n*, the first *m* leaves under both MUST be identical — this is exactly what a consistency proof (§9.2) demonstrates. Note that append order is acceptance order, **not** `created_at` order: leaves appended by a backfill (§7.3) or by a slow pipeline may carry `created_at` values earlier than their neighbors'. The anti-backdating property (§3) derives from *position relative to checkpoints*, never from leaf ordering.

---

## 6. Checkpoints (Signed Tree Heads) (NORMATIVE)

A checkpoint is a JSON object with exactly the following members. The canonical schema is [`schemas/json/acdp-log-checkpoint.schema.json`](../schemas/json/acdp-log-checkpoint.schema.json) (closed: `additionalProperties: false`).

| Field | Type | Required | Description |
|---|---|---|---|
| `checkpoint_version` | string | Yes | MUST be exactly `"acdp-log/1"`. In-preimage domain separator (the RFC-ACDP-0011 `receipt_version` convention): a checkpoint can never be mistaken for — or replayed as — a context receipt or head receipt. |
| `log_id` | string | Yes | The log instantiation identifier: `"<registry_did>/log/<instance>"`, where `<registry_did>` is the registry's `did:web` DID (the same value as `capabilities.registry_did`, RFC-ACDP-0007 §3.1) and `<instance>` matches `[a-z0-9-]{1,32}` (e.g. `did:web:registry.example.com/log/1`). One live instantiation per registry (§7.4). |
| `tree_size` | integer | Yes | The number of leaves this checkpoint commits to (≥ 0; 0 is a valid, empty log). |
| `root_hash` | string | Yes | `"sha256:" + lowercase_hex(MTH(D[tree_size]))` per §5.2. |
| `timestamp` | string | Yes | The registry-clock time at which this checkpoint was evaluated and signed: canonical millisecond-precision RFC 3339 UTC (RFC-ACDP-0001 §5.3). Registry-asserted — see §13. |
| `signature` | object | Yes | The registry's signature over the checkpoint hash, using the `signature` object shape of RFC-ACDP-0001 §5.8 (`algorithm`, `key_id`, `value`; closed schema). `signature.key_id` MUST be a DID URL under the `registry_did` embedded in `log_id`. |

**Signing construction — RFC-ACDP-0010 §5 verbatim.** Implementations MUST NOT introduce a second canonicalization or signing-input framing:

1. **Preimage.** Remove the `signature` member. JCS-canonicalize (RFC 8785) the remainder.
2. **Hash.** `checkpoint_hash = "sha256:" + lowercase_hex(SHA-256(preimage_bytes))`.
3. **Signing input.** The **ASCII bytes of the full `checkpoint_hash` string**, `sha256:` prefix included (RFC-ACDP-0001 §5.8; RFC-ACDP-0010 §5 step 3).
4. **Signature.** Sign with the registry's **receipt signing key** — the same key material and lifecycle as RFC-ACDP-0010 receipts and RFC-ACDP-0011 head receipts (`ed25519` mandatory-to-implement; `ecdsa-p256` optional, IEEE 1363 r‖s wire form). `signature.value` is the base64-encoded signature bytes.

Checkpoints monotonically advance: a registry MUST NOT sign two checkpoints of the same `log_id` whose `tree_size` values order one way and whose trees order the other (that is precisely the split-view the log exists to expose). Signing a fresh checkpoint at an unchanged `tree_size` (fresh `timestamp`, identical `root_hash`) is conformant and useful as a liveness signal.

The golden vector `log-001-leaf-and-root-golden.json` pins five leaves (leaf 0 is the `rcpt-001` golden receipt's publish event), every leaf hash, the tree-size-5 root, a signed checkpoint under the `rcpt-001` registry test keypair, and an inclusion proof; `log-003-consistency-proof-golden.json` pins the size-3 → size-5 consistency proof with both signed checkpoints. Both are executed arithmetically by `scripts/conformance-runner.py`.

---

## 7. Log Operation

Registries advertising the `acdp-registry-transparency-log` profile (§11):

### 7.1 Append

1. **MUST append the leaf atomically with publish persistence.** RFC-ACDP-0010 §7 rule 1 extends: the body, its receipt, and its leaf commit together, or none does. A registry that persists a body but cannot durably append its leaf MUST fail the publish.
2. **MUST assign `leaf_index` in acceptance order**, consecutively from 0, per §5.3.

There is no `log_unavailable` condition (the RFC-ACDP-0010 §7 posture): a registry advertising the profile MUST log every accepted publish and MUST serve the §8 endpoints; a registry that cannot MUST NOT advertise the profile.

### 7.2 Checkpoint cadence

The current checkpoint served by `GET /log/checkpoint` MUST commit to every publish the registry has acknowledged at the time the checkpoint was evaluated. Because appends are synchronous with publish (§7.1), a registry can always sign a fresh head on demand; it MAY instead reuse a recently evaluated checkpoint across responses within a short window — the claim stays honest because `timestamp` states when it was evaluated — and consumers apply their own freshness policy to `timestamp` (the RFC-ACDP-0011 §6 posture; the same RECOMMENDED 300-second default maximum age applies).

### 7.3 Backfill

A registry enabling the profile SHOULD backfill leaves for contexts published before enablement (it MUST have receipts for them first — RFC-ACDP-0010 §7 backfill). Backfilled leaves are appended in backfill order at then-current positions; per §5.3 their positions prove nothing about their `created_at` claims. The anti-backdating guarantee of §3 therefore applies only to publishes accepted *while the profile is advertised*; verifiers comparing `created_at` against checkpoint history MUST treat leaves whose positions precede the registry's advertised enablement as time-unanchored.

### 7.4 Log instantiation and reset

A registry operates exactly one live log instantiation. If the tree is catastrophically lost, the registry MUST NOT serve a reconstructed history under the same `log_id` (any surviving old checkpoint would then expose it to an unanswerable consistency demand for a tree it no longer has); it MUST start a new instantiation with a new `<instance>` component and SHOULD publish an operational notice. Consistency proofs exist only within one `log_id`; a `log_id` change is loud, explicit, and itself evidence that history continuity was broken — which is the honest failure mode.

---

## 8. Endpoints (NORMATIVE)

Three endpoints, at the paths reserved by RFC-ACDP-0009 §2.11, all under the registry's HTTPS authority, all returning `application/acdp+json`. Errors use the RFC-ACDP-0007 §4 envelope.

### 8.1 `GET /log/checkpoint`

Returns the current `log_checkpoint` object (§6), bare (the checkpoint is the response body). No parameters. Publicly readable wherever capabilities are (the checkpoint reveals only tree size, root, and time).

### 8.2 `GET /log/proof`

One reserved path, two mutually exclusive parameter sets (**this document's resolution of the query-surface question**):

**Inclusion mode** — exactly one of:

- `?ctx_id=<ctx_id>` — the consumer's surface: consumers hold `ctx_id`s, not leaf indexes. Visibility applies exactly as for `GET /contexts/{ctx_id}` (RFC-ACDP-0008 §4.5): a requester not authorized to retrieve the context receives `not_found` (404), indistinguishable from absence.
- `?leaf_index=<n>` — the auditor's surface: monitors iterate positions without knowing `ctx_id`s.

Optionally `&tree_size=<n>` to request the proof against a specific historical tree size (`leaf_index < tree_size ≤` current size); default is the current checkpoint's size. Response — the closed `log_inclusion` object ([`schemas/json/acdp-log-inclusion.schema.json`](../schemas/json/acdp-log-inclusion.schema.json)) plus, in inclusion-mode responses, an OPTIONAL echoed `leaf`:

```json
{
  "log_id": "did:web:registry.example.com/log/1",
  "leaf_index": 0,
  "tree_size": 5,
  "inclusion_path": ["sha256:…", "sha256:…", "sha256:…"],
  "log_checkpoint": { "checkpoint_version": "acdp-log/1", "log_id": "…", "tree_size": 5, "root_hash": "sha256:…", "timestamp": "…", "signature": { … } },
  "leaf": { "leaf_version": "acdp-log-leaf/1", … }
}
```

`inclusion_path` is the RFC 6962 §2.1.1 audit path `PATH(leaf_index, D[tree_size])`, ordered from the lowest tree level upward, each element `"sha256:" + lowercase_hex(node digest)`. `log_checkpoint.tree_size` MUST equal the response's `tree_size` (for a historical `tree_size` the registry serves a checkpoint it signed at that size, or signs one on demand — both roots are equally committed by consistency). `leaf` is echoed **only** when the requester is authorized to retrieve the context (same rule as retrieval); it is a convenience for auditors and MUST NOT be trusted by verifiers, who recompute the leaf from verified material (§9.1 step 1). A `ctx_id` not in the log (or not visible) → `not_found`.

**Consistency mode** — both of:

- `?first=<m>&second=<n>` with `0 < m ≤ n ≤` current tree size.

Response:

```json
{
  "log_id": "did:web:registry.example.com/log/1",
  "first_tree_size": 3,
  "second_tree_size": 5,
  "consistency_path": ["sha256:…", "sha256:…", "sha256:…", "sha256:…"],
  "log_checkpoint": { … }
}
```

`consistency_path` is the RFC 6962 §2.1.2 proof `PROOF(first, D[second])` (empty when `first == second`); `log_checkpoint` is a checkpoint at `second_tree_size`. The requester supplies its own retained checkpoint (root) for `first` — that retained root is the whole point (§9.2). **Consistency mode is REQUIRED**: detecting root rewrites is why the log exists, and a log that serves inclusion proofs but refuses consistency proofs is non-conformant.

Mixing the parameter sets, omitting both, or supplying out-of-range sizes → `schema_violation` (400).

### 8.3 `GET /log/entries`

`?start=<i>&end=<j>` (0-based, `start` inclusive, `end` exclusive, `start < end ≤` current tree size). Returns:

```json
{
  "log_id": "did:web:registry.example.com/log/1",
  "start": 0,
  "entries": [
    { "leaf_index": 0, "leaf_hash": "sha256:…", "leaf": { … } },
    { "leaf_index": 1, "leaf_hash": "sha256:…" }
  ]
}
```

The registry MAY cap the page size (RECOMMENDED cap ≥ 256 entries) by returning fewer entries than requested; callers continue from `start + len(entries)`. `leaf_hash` is always present for every entry — the ordered leaf hashes alone suffice to recompute every root and verify every checkpoint and consistency proof (§5.2), which is what makes third-party auditing possible. `leaf` is present **only** for entries whose context the requester is authorized to retrieve (public contexts: always); for other entries it is absent (never `null` — the absent-vs-null convention of RFC-ACDP-0005 §2.2.1). This is the visibility-preserving audit design: an unauthorized auditor learns that *a* publish occupies position *i* (count and timing metadata — see §15), but none of the leaf's contents.

Out-of-range or malformed parameters → `schema_violation`; the endpoints themselves are never `not_implemented` once the profile is advertised.

---

## 9. Verification Procedures (NORMATIVE)

### 9.1 Inclusion-proof verification

A consumer verifying that a context is logged MUST perform all of the following:

1. **Reconstruct the leaf independently.** Build the §4 leaf object from *verified* material: the accompanying body's identifiers and `created_at`, the consumer's independently recomputed `content_hash` (RFC-ACDP-0001 §5.7 — never the echoed value), the resolved producer key's RFC-ACDP-0010 §6 fingerprint, and the receipt hash recomputed from the receipt that was verified per RFC-ACDP-0010 §8. An echoed `leaf` member MUST NOT be substituted for this reconstruction.
2. **Compute the leaf hash.** `SHA-256(0x00 ‖ JCS(leaf))` (§5.1).
3. **Verify the checkpoint.** Per §9.3.
4. **Check binding.** `log_inclusion.tree_size` MUST equal `log_checkpoint.tree_size`; `log_inclusion.log_id` MUST equal `log_checkpoint.log_id`; `leaf_index < tree_size`.
5. **Fold the audit path** (the RFC 9162 §2.1.3.2 algorithm). Let `fn = leaf_index`, `sn = tree_size − 1`, `r = leaf_hash`. For each element `p` of `inclusion_path` in order:
   1. If `sn == 0`, **fail** (path too long).
   2. If `fn` is odd, or `fn == sn`: set `r = node_hash(p, r)`; then, if `fn` is even, right-shift both `fn` and `sn` until `fn` is odd or `fn == 0`.
   3. Otherwise: set `r = node_hash(r, p)`.
   4. Right-shift both `fn` and `sn` by one.
6. **Compare.** After consuming the whole path, `sn` MUST equal 0 and `r` MUST equal the raw digest encoded by `log_checkpoint.root_hash`. Any leftover path, premature exhaustion, or mismatch **fails**.

### 9.2 Consistency-proof verification

A verifier holding a retained earlier checkpoint (`first_root` at size `first`) and a later checkpoint (`second_root` at size `second`, verified per §9.3) MUST check (the RFC 9162 §2.1.4.2 algorithm):

1. If `first == second`: the path MUST be empty and `first_root` MUST equal `second_root`; done.
2. If `first == 0`, `first > second`, or the path is empty, **fail** (an empty tree is trivially consistent with anything; registries never prove it, verifiers never demand it).
3. If `first` is an exact power of two, prepend `first_root` to the path.
4. Let `fn = first − 1`, `sn = second − 1`. While `fn` is odd, right-shift both by one.
5. Let `fr = sr = path[0]`. For each subsequent element `c`:
   1. If `sn == 0`, **fail**.
   2. If `fn` is odd, or `fn == sn`: set `fr = node_hash(c, fr)` and `sr = node_hash(c, sr)`; then, if `fn` is even, right-shift both `fn` and `sn` until `fn` is odd or `fn == 0`.
   3. Otherwise: set `sr = node_hash(sr, c)`.
   4. Right-shift both `fn` and `sn` by one.
6. **Compare.** `fr` MUST equal `first_root`, `sr` MUST equal `second_root`, and `sn` MUST equal 0.

A failed consistency proof between two *signature-valid* checkpoints of the same `log_id` is not a soft error: it is cryptographic evidence that the registry rewrote logged history, and consumers SHOULD retain both checkpoints and the failing path as evidence (§15).

### 9.3 Checkpoint verification

1. **Schema-closed parse.** The checkpoint MUST parse against the closed schema of §6; `checkpoint_version` MUST be exactly `"acdp-log/1"`.
2. **Recompute and verify the signature.** JCS-recompute the preimage, recompute `checkpoint_hash`, resolve the key referenced by `signature.key_id` from the registry's DID document (RFC-ACDP-0001 §5.11, with the SSRF protections of RFC-ACDP-0008 §4.8), and verify `signature.value` over the ASCII bytes of `checkpoint_hash`. Key acceptance follows RFC-ACDP-0010 §9 (current keys in `assertionMethod`; retired keys verify historical checkpoints from `verificationMethod`).
3. **Registry binding.** The `registry_did` prefix of `log_id` MUST be `did:web:<authority>` where `<authority>` equals the authority the checkpoint was fetched from (and `capabilities.registry_did`); the DID portion of `signature.key_id` MUST equal that DID. Same principle as RFC-ACDP-0010 §8 step 2 / `fed-006`.
4. **Form.** `tree_size` ≥ 0; `root_hash` well-formed; `timestamp` canonical millisecond RFC 3339 UTC and not in the future beyond the RFC-ACDP-0011 §7 step 6 skew allowance (RECOMMENDED 120 seconds).

A failure of any check in §9.1–§9.3 MUST be treated as a verification failure of the proof/checkpoint and surfaced with the `invalid_log_proof` semantic (§11). **Log-proof failure invalidates nothing else**: the body verdict, the RFC-ACDP-0010 receipt verdict, the RFC-ACDP-0011 head-receipt verdict, and the log verdict are independent results and SHOULD be reported independently.

---

## 10. Binding to Retrieval

A full-retrieval response (`GET /contexts/{ctx_id}`, RFC-ACDP-0004 §2.1) from a profile-advertising registry **MAY** carry the top-level member **`log_inclusion`** — the §8.2 inclusion object (without `leaf`; the leaf is reconstructed from the very body and receipt the response carries) — alongside `registry_receipt`. The envelope is open at the top level, so this rides the same openness guarantee as `lineage_head_receipt` (RFC-ACDP-0011 §10); pre-0.3.0 consumers ignore it under RFC-ACDP-0001 §6.

- `log_inclusion` is OUTSIDE the body, never part of any `content_hash` preimage, and MUST NOT appear inside a stored body.
- It MUST NOT be added to the body-only endpoint (`GET /contexts/{ctx_id}/body`) — the same immutable-cache rule as RFC-ACDP-0010 §7 rule 4 and RFC-ACDP-0011 §6 rule 3.
- It is NOT added to the publish response: the publish-response schema is closed, and 0.2.0 already spent the one sanctioned parse-surface change there (RFC-ACDP-0010 §12). A producer wanting immediate proof of logging calls `GET /log/proof?ctx_id=…` after publish; §7.1 atomicity guarantees the proof exists the moment the publish response does.
- Serving `log_inclusion` on retrieval is OPTIONAL per response even for profile-advertising registries (proof generation has a cost the registry may prefer to keep on the dedicated endpoint); the §8 endpoints are the normative surface.

**Placement note (RFC-ACDP-0009 §2.11 refinement).** §2.11 sketched `log_inclusion` as "a member of `registry_receipt`". That placement is unimplementable as reserved: the receipt schema is closed, every receipt member is signed, and receipts MUST be byte-identical across responses (RFC-ACDP-0010 §4) — a mutable, per-tree-size proof inside the receipt would change the receipt bytes and break all three properties. `log_inclusion` is therefore a **sibling** top-level envelope member. The reserved *name* is used exactly as reserved; only its position moved one level up. See §12.

---

## 11. Capabilities, Profile, and Errors

- **Profile.** `acdp-registry-transparency-log` — the name reserved by RFC-ACDP-0009 §2.11 (registered in `registries/profiles.md`; prerequisite **`acdp-registry-receipts`**, and transitively `acdp-registry-core`). The prerequisite is load-bearing twice over: leaves bind receipt hashes (§4), and checkpoints sign with the receipt signing key under the RFC-ACDP-0010 §9 lifecycle (§6). Advertised in `capabilities.profiles`. Advertising the profile is the §7 commitment: log every accepted publish atomically, serve all three endpoints, no degraded mode. Small registries conformantly do not offer the log by simply not advertising the profile (§13).
- **Version.** Registries advertising the profile MUST advertise `acdp_version` ≥ `0.3.0` in capabilities.
- **`supports_transparency_log` is retired unused.** RFC-ACDP-0009 §2.11 reserved this capabilities field name; profile advertisement (the mechanism every 0.2.0/0.3.0 trust feature uses) supersedes a boolean that could only disagree with it. The name remains reserved and MUST NOT be emitted.
- **Error code: `invalid_log_proof` (new wire code, HTTP 502).** An inclusion proof, consistency proof, or checkpoint failed the §9 verification procedures. This is deliberately **not** `invalid_receipt`: a proof failure indicts the *log* (tree membership, history consistency, checkpoint signature), not the receipt, and the two verdicts are independent (§9.3) — collapsing them would violate the single-semantic rule of `registries/error-codes.md`. On the wire it is emitted by a federated resolver (or any registry validating an upstream's proofs on a caller's behalf) — hence 502, the upstream is at fault; it is also the verification-failure category consumer SDKs use for locally failing proofs. Registered per the `registries/error-codes.md` process; added to the RFC-ACDP-0007 §5 table and the `acdp-error.schema.json` wire enum. Implementations declaring `acdp_version` < `0.3.0` MUST NOT emit it. Malformed proof *requests* are `schema_violation`; an unlogged/invisible `ctx_id` is `not_found`; there is no `log_unavailable` (§7.1).
- **Federation.** A federated resolver (`acdp-registry-federated`) that relies on an upstream's `log_inclusion` (or fetches upstream proofs) SHOULD verify them per §9 against the *upstream* authority and surface failure as `invalid_log_proof`, mirroring the `fed-009` rule for receipts.

---

## 12. Compatibility

The log is additive; nothing existing changes:

- **Retrieval envelope.** The new OPTIONAL `log_inclusion` member rides the envelope's existing top-level openness (RFC-ACDP-0001 §6) — no existing parse surface changes, exactly as `lineage_head_receipt` (RFC-ACDP-0011 §10). The publish response is deliberately untouched (§10).
- **Promotion notes against the §2.11 sketch.** The reserved shape is adopted with three recorded refinements: (1) `log_inclusion` is a top-level retrieval-envelope member, not a member of the closed, immutable `registry_receipt` (§10); (2) the sketch's informal `checkpoint_signature` member is realized as the standard `signature` envelope of RFC-ACDP-0001 §5.8, matching every other signed ACDP object — the "remove the `signature` member" preimage rule thereby applies uniformly; (3) `supports_transparency_log` is retired unused in favor of profile advertisement (§11). All reserved *names* that are used (`log_inclusion`, `log_checkpoint`, `log_id`, `leaf_index`, `inclusion_path`, the profile, the three endpoint paths) carry their reserved meanings.
- **Bodies, signatures, hashes, receipts.** Unchanged. No JCS rule, `content_hash` semantic, signature semantic, RFC-ACDP-0010 receipt semantic, or RFC-ACDP-0011 head-receipt semantic is touched; new schemas are additive in the `v0.1.0` namespace (VERSIONING.md).
- **Error enum.** `acdp-error.schema.json` gains `invalid_log_proof` — the same additive-enum posture as `invalid_receipt` in 0.2.0. Strict pre-0.3.0 error decoders that reject unknown codes were already non-conformant (RFC-ACDP-0007 §4 requires tolerating vocabulary growth).
- **Non-advertising registries** are unaffected and remain fully conformant; they MUST NOT emit `log_inclusion` or serve the `/log/*` endpoints as ACDP surfaces.

---

## 13. Scope and Limitations (honest scope)

The log completes a specific promise — *any lie about logged history is detectable by someone holding checkpoints* — and no more:

- **Detection requires witnesses.** Split-view detection needs checkpoints compared across vantages (two consumers, or a consumer and a monitor); history-rewrite detection needs someone to have *retained* an earlier checkpoint and to demand consistency. A consumer that never retains checkpoints and never compares gets attributability (RFC-ACDP-0010) but not detection. This document deliberately specifies **no gossip or witness protocol** — how checkpoints travel between parties was out of scope, reserved as RFC-ACDP-0009 §2.12 (checkpoint witnessing & cosigning). ***(0.4.0)*** That layer has since shipped as [RFC-ACDP-0015 Transparency-Log Witness Cosigning](RFC-ACDP-0015-witness-cosigning.md), promoting the §2.12 reservation: independent witnesses observe checkpoints, verify consistency, and cosign what they saw, so a consumer trusting any one honest witness inherits split-view protection systematically rather than incidentally. It remains out of scope for *this* document; a witness gossip protocol is still deployment-specific (RFC-ACDP-0015 §13).
- **Checkpoint timestamps are registry-asserted.** Nothing external anchors the registry's clock — `timestamp` (like `created_at` and `as_of` before it, RFC-ACDP-0010 §13 / RFC-ACDP-0011 §11) is the registry's own claim, bounded against the consumer's clock only by the §9.3 skew check. What the log adds is *ordering* evidence: a leaf's position relative to externally retained checkpoints bounds when it could have been appended, regardless of what any registry timestamp says. External time anchoring is the witness `witnessed_at` of [RFC-ACDP-0015](RFC-ACDP-0015-witness-cosigning.md) ***(0.4.0)*** (the §2.12 work, since shipped): a witness cosignature bounds when a checkpoint existed against a party the registry does not control.
- **No completeness of search.** An inclusion proof proves a context is logged; nothing proves that a search result set, a lineage listing, or the log itself is *complete* relative to what the registry accepted, except leaf-by-leaf demand by parties (like producers) who hold receipts. The log makes omission detectable *by the interested party*, not globally.
- **No proof of absence.** The log offers no non-membership proofs; consumers MUST NOT interpret a missing or refused inclusion proof as proof a context does not exist — only, when the requester holds a valid receipt for it, as evidence of a log violation (§3).
- **No cross-registry aggregation.** Each log is per-registry, scoped to one `log_id`; nothing here defines merging, mirroring, or cross-registry log queries.
- **Backfilled history is time-unanchored** (§7.3), and log instantiation resets (§7.4) truncate the consistency horizon — loudly, by `log_id` change.
- **Optionality is conformant.** The profile is optional: a small registry that never advertises `acdp-registry-transparency-log` is fully conformant at every ACDP version, and consumers get the 0.2.0 receipt guarantees unchanged. The trust ladder is deliberate: receipts (cheap, mandatory-with-profile) → head receipts (cheap, serve-time) → log (operational machinery, for registries whose consumers need auditable history).

---

## 14. Conformance Fixtures

| ID | What it pins | Runner |
|---|---|---|
| `log-001-leaf-and-root-golden` | Full golden vector: five leaves (leaf 0 = the `rcpt-001` receipt's publish event), JCS leaf encodings, §5.1 leaf hashes (`0x00` prefix), the tree-size-5 root (`0x01` nodes), a checkpoint signed with the `rcpt-001` registry test keypair, and the inclusion proof for leaf 0 at size 5. The `sig-001`-equivalent for the log layer. | Executed arithmetically |
| `log-002-inclusion-proof-mismatch` | The `log-001` proof with one tampered `inclusion_path` element → §9.1 folding yields a root ≠ checkpoint `root_hash` → MUST fail (`invalid_log_proof`); the checkpoint's own signature verifies. | Behavioral (data pinned) |
| `log-003-consistency-proof-golden` | Consistency proof between tree sizes 3 and 5 of the `log-001` tree: both signed checkpoints, the four-element `consistency_path`, §9.2 verification end-to-end. | Executed arithmetically |
| `log-004-checkpoint-signature-invalid` | A checkpoint whose `root_hash` was altered after signing (signature no longer verifies over the recomputed preimage) → §9.3 step 2 MUST fail (`invalid_log_proof`); the analogue of `rcpt-002` one layer up. | Behavioral (data pinned) |

Vectors are generated by `temp/gen-0.3.0-vectors.py` (never hand-written); the generator self-checks the §9.1/§9.2 verification algorithms against brute-force tree recomputation for all tree sizes ≤ 8 and all proof indexes.

---

## 15. Security Considerations

- **Key.** The checkpoint signing key is the RFC-ACDP-0010 receipt signing key; every requirement of RFC-ACDP-0010 §15 and RFC-ACDP-0011 §13 (HSM/KMS boundary, role separation, blast-radius planning for the increased signing rate) applies. A compromised receipt key can now also sign forged checkpoints; the append-only history *limits* what forged checkpoints can claim without tripping consistency checks against pre-compromise checkpoints held by others — retained checkpoints are post-compromise forensic anchors.
- **Second-preimage resistance.** The §5.1 domain-separation prefixes are load-bearing; omitting them re-enables the RFC 6962 §2 leaf/node confusion attack. The closed leaf schema plus `leaf_version` additionally prevents any other ACDP JCS object from being replayed as a leaf.
- **Visibility.** `/log/proof?ctx_id=` applies retrieval visibility (404, RFC-ACDP-0008 §4.5). `/log/entries` never exposes leaf contents for contexts the requester cannot retrieve, but leaf *hashes*, positions, and tree size are public by design — a registry with confidentiality requirements over publication **volume and timing** metadata must weigh that before advertising the profile; this leak is inherent to public auditability and is not mitigable within it.
- **DID fetches.** Checkpoint verification dereferences the registry's `did:web` document; RFC-ACDP-0008 §4.8 SSRF protections apply identically.
- **Evidence handling.** Consumers SHOULD retain: the checkpoints they act on, any inclusion proofs for contexts they rely on, and — on any §9.2 failure — both checkpoints and the failing path. A pair of signature-valid, mutually inconsistent checkpoints of one `log_id` is compact, portable, non-repudiable proof of registry misbehavior; it is the artifact the witness ecosystem of [RFC-ACDP-0015](RFC-ACDP-0015-witness-cosigning.md) (the §2.12 promotion) traffics in — a witness that observes such a pair refuses to cosign and persists it as evidence (RFC-ACDP-0015 §7). ***(0.4.0)***
- **Independence of verdicts.** A verified inclusion proof is evidence that a publish event was *logged* — never of body authenticity (producer signature, RFC-ACDP-0008 §8), receipt validity (RFC-ACDP-0010 §8), or current-ness (RFC-ACDP-0011 §7). The four verdicts MUST be kept distinct.

See RFC-ACDP-0008 §9.1–§9.2 (as amended for 0.3.0) for the threat-model placement.

---

## 16. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0003 Publish](RFC-ACDP-0003-publish.md)
- [RFC-ACDP-0004 Retrieval & Lineage](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0006 Cross-Registry References](RFC-ACDP-0006-cross-registry.md)
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
- [RFC-ACDP-0009 Extensions](RFC-ACDP-0009-extensions.md) — §2.11 (origin of this RFC), §2.12 (witness cosigning, reserved).
- [RFC-ACDP-0010 Registry Receipts](RFC-ACDP-0010-registry-receipts.md) — §2 (receipt hash), §5 (signing construction, reused), §6 (fingerprint encoding), §9 (key lifecycle, reused), §13 (the gap this RFC closes).
- [RFC-ACDP-0011 Lineage-Head Receipts](RFC-ACDP-0011-lineage-head-receipts.md) — the cheap serve-time complement.
- [RFC-ACDP-0015 Transparency-Log Witness Cosigning](RFC-ACDP-0015-witness-cosigning.md) — ***(0.4.0)*** external witnesses that cosign this log's checkpoints, closing the §13 registry-asserted-timestamp and consistent-lie gaps (promotes RFC-ACDP-0009 §2.12).
- [RFC 6962] Laurie, B., Langley, A., and E. Kasper, "Certificate Transparency", RFC 6962, June 2013 — §2.1 (Merkle tree, audit paths, consistency proofs).
- [RFC 9162] Laurie, B., Messeri, E., and R. Stradling, "Certificate Transparency Version 2.0", RFC 9162, December 2021 — §2.1.3.2 / §2.1.4.2 (verification algorithms transcribed in §9).
- [RFC 8785] Rundgren, A., Jordan, B., and S. Erdtman, "JSON Canonicalization Scheme (JCS)", RFC 8785, June 2020.
- [RFC 8032] Josefsson, S. and I. Liusvaara, "Edwards-Curve Digital Signature Algorithm (EdDSA)", RFC 8032, January 2017.
