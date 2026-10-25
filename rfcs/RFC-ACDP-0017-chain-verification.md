# RFC-ACDP-0017
# Agent Context Distribution Protocol (ACDP) — Chain Verification and Evidence Bundles

**Document:** RFC-ACDP-0017
**Version:** 0.5.0-draft
**Status:** Community Standards Track (Draft)

This RFC specifies **chain verification**: one consumer-side algorithm that verifies a whole `derived_from` graph, **offline**, **as of a past instant T**, and emits a **deterministic, digestible verdict**. It defines three objects:

- the **evidence bundle** (`acdp-evidence/1`): a self-describing, untrusted container for everything the algorithm consumes;
- the **chain verdict** (`acdp-chain-verdict/1`): a JCS-canonical report with two digests, one sealable at T and one over the full result;
- the **event receipt** (`acdp-event-receipt/1`): a registry-signed acceptance time for a lifecycle event. This one is a wire amendment to RFC-ACDP-0013.

The algorithm runs identically online and offline. The two modes differ only in where the evidence comes from. It depends on RFC-ACDP-0001, -0004, -0006, -0010, -0012, -0013, -0014 and -0015. It amends RFC-ACDP-0013 (§10 of this document) and RFC-ACDP-0004 §5.1 (§11).

---

## 1. Status of This Memo

This document is a **Draft** ACDP specification on the `acdp/0.5.0` line. It is open for substantive change until it is promoted. Per [VERSIONING.md](../VERSIONING.md), promotion to **Final** requires the conformance fixtures this document defines (`chain-001`..`chain-010`) to pass against two independent interoperating implementations.

The `acdp-consumer-chain` profile (§13) is OPTIONAL. A consumer that never verifies chains is unaffected. The registry-side amendments in §10 and §11 bind only registries that advertise `acdp-registry-receipts` and declare `acdp_version` ≥ `0.5.0`.

Nothing in this document invalidates any existing body, signature, `content_hash`, receipt, checkpoint or cosignature. §10 adds a new signed object; it changes none.

---

## 2. Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described in BCP 14 ([RFC 2119], [RFC 8174]) when, and only when, they appear in all capitals.

| Term | Definition |
|---|---|
| **Root** | A `ctx_id` the walk starts from. A walk has one or more roots. |
| **Node** | A context reached from a root through zero or more `derived_from` edges. |
| **Evidence** | Any input a check consumes: bodies, registry receipts, lifecycle events, event receipts, log inclusions, DID-document snapshots, revocation-discovery records, checkpoints, cosignatures. |
| **Evidence time** | The earliest instant at which a piece of evidence is *provably* known to have existed (§5.1). Some evidence has no evidence time. |
| **As-of instant (T)** | A caller-supplied instant. The **as-of pass** uses only evidence whose evidence time is ≤ T. |
| **Horizon** | The greatest evidence time in the bundle (§5.4). The **latest pass** evaluates as of the horizon, using all evidence. |
| **Pass** | One evaluation of every node: the as-of pass (filtered to ≤ T) or the latest pass (unfiltered). |
| **Trust basis** | The kind of trust a stage result rests on. Exactly one of: `self` (hash or signature arithmetic only, e.g. `did:key`, `content_hash`); `pinned` (a key or document the caller supplied out of band, §6.3); `registry` (signed by a registry key resolved from a pinned or observed basis); `observed` (an unsigned snapshot that an exporter asserts it saw at a stated time). |
| **Drift** | A per-node difference between the as-of and latest passes (§8.4). |

Timestamps are canonical millisecond-precision RFC 3339 UTC (RFC-ACDP-0001 §5.3). Every comparison in this document is between such timestamps, and compares instants.

---

## 3. Motivation

Before this RFC, ACDP could verify **one body, online, now**. An auditor of an agent decision needs to verify **the graph of contexts behind it, offline, at the instant the decision was made**. There were four gaps:

1. **No chain primitive.** RFC-ACDP-0006 §4.1 step 8 bounds a `derived_from` walk and requires partial-walk reporting (`fed-010`). But it defines no consumer report shape, and no reusable algorithm.
2. **No offline evidence format.** Every trust check reaches the network: did:web resolution (RFC-ACDP-0001 §5.11), receipt keys (RFC-ACDP-0010 §8), revocation discovery (RFC-ACDP-0014 §8), lifecycle state (RFC-ACDP-0013 §4.1). A party holding only an exported bundle could run none of them.
3. **No time other than "now".** RFC-ACDP-0014 compromise windows are retroactive by design. A revocation published *after* a decision makes a body invalid *now* that was correctly accepted *then*, and before this RFC both cases collapsed into a single `revoked`. Retractions had no provable time at all, because `occurred_at` is claimed by the actor and array order carries no clock.
4. **No deterministic verdict.** There was nothing a decision system could seal, and nothing an auditor could recompute and byte-compare.

---

## 4. The Evidence Bundle: `acdp-evidence/1` (NORMATIVE)

An evidence bundle is a single JSON object, validated by [`acdp-evidence.schema.json`](../schemas/json/acdp-evidence.schema.json).

```json
{
  "evidence_version": "acdp-evidence/1",
  "roots": ["acdp://registry.example.com/11111111-1111-4111-8111-111111111111"],
  "exported_at": "2026-10-24T12:00:00.000Z",
  "contexts": {
    "acdp://registry.example.com/11111111-1111-4111-8111-111111111111": {
      "body": { "...": "..." },
      "registry_receipt": { "...": "..." },
      "lifecycle_events": [],
      "event_receipts": [],
      "log_inclusion": { "...": "..." }
    }
  },
  "did_documents": {
    "did:web:agents.example.com:producer": [
      {
        "document": { "...": "..." },
        "observed_at": "2026-10-24T11:59:58.000Z",
        "observed_by": "seam-runtime",
        "source": "https://agents.example.com/producer/did.json"
      }
    ]
  },
  "revocation_discovery": {
    "did:web:agents.example.com:producer": [
      {
        "vantage": "registry.example.com",
        "outcome": "not-revoked-complete",
        "completed_at": "2026-10-24T11:59:59.000Z"
      }
    ]
  },
  "checkpoints": [ { "checkpoint": { "...": "..." }, "cosignatures": [] } ],
  "omitted": [
    { "ctx_id": "acdp://registry.example.com/22222222-2222-4222-8222-222222222222", "reason": "withheld" }
  ]
}
```

### 4.1 Posture

The bundle is **unsigned and untrusted**. A verifier MUST NOT believe any member because it is present. Every stage (§7) re-derives its result from content, and the trust basis of every result says what that result ultimately rests on. A bundle that fails schema validation MUST be rejected as a whole. A verifier MUST NOT verify the parts of it that happen to parse.

### 4.2 Members

- **`contexts`** is keyed by `ctx_id`. Each entry carries the context's `body` and, where the exporter obtained them, the context's `registry_receipt`, `lifecycle_events`, `event_receipts` (§10) and `log_inclusion`. The map key is a claim: the identity stage (§7.2) checks it against `body.ctx_id` and `registry_receipt.ctx_id`. Key-revocation contexts (RFC-ACDP-0014 §4) that the verifier should apply are carried here like any other context. They do not need to be reachable through `derived_from`.
- **`did_documents`** is keyed by DID and holds a **history**: an array of snapshots, each with the `document` as fetched, `observed_at`, and optionally `observed_by` and `source`. Several snapshots per DID let the as-of pass choose the one in force at T (§6.2). `did:key` DIDs MUST NOT appear, because they resolve arithmetically. Registry DID documents (for receipt, event-receipt and checkpoint keys) and witness DID documents go in the same map.
- **`revocation_discovery`** is keyed by producer DID and holds observed RFC-ACDP-0014 §8 discovery records. Each record has a `vantage` (the registry authority queried), an `outcome` (`revoked`, `not-revoked-complete` or `unknown`) and a `completed_at`. A producer with no record has discovery outcome `unknown`. Its outcome is never `not-revoked`.
- **`checkpoints`** holds RFC-ACDP-0012 checkpoints with any RFC-ACDP-0015 cosignatures. **`consistency_proofs`** MAY carry RFC-ACDP-0012 §9.2 proofs between them.
- **`omitted`** is the exporter's honest list of contexts it deliberately left out, each with a `reason`: `withheld` (left out by policy, e.g. visibility), `not_retrievable` (the fetch failed) or `limit` (an export budget fired).
- **`roots`** and **`exported_at`** are informational. The verifier takes its roots from the caller (§6), and `exported_at` plays no part in any pass.

### 4.3 Exporting

An exporter collects a bundle by walking online under the §6.1 rules. It fetches each node with its receipt, lifecycle events, event receipts and log inclusion; snapshots every DID document it resolved, recording `observed_at`; and runs RFC-ACDP-0014 §8 discovery once per distinct producer, recording the outcome. Collecting and verifying are separate. An exporter MAY collect without trusting what it collects.

Exporters SHOULD prefer the receipt-bearing lineage listing (§11) to per-context retrieval, and SHOULD include every member of any key-revocation lineage they discovered (RFC-ACDP-0014 §7 requires the whole lineage for the earliest-`compromised_since` fold).

### 4.4 Embedding

A host format MAY carry an `acdp-evidence/1` object as a file. Seam's evidence bundle does this, for example, with an `acdp-evidence.json` listed in its manifest. The host's own integrity mechanism, not ACDP's, protects the file. The verdict (§9) binds to the bundle bytes through `evidence_digest`.

---

## 5. Time Semantics (NORMATIVE)

### 5.1 Evidence time, by kind

| Evidence | Evidence time | Basis |
|---|---|---|
| Body with a receipt that verifies (RFC-ACDP-0010 §8) | `registry_receipt.created_at` | `registry` |
| Body with no receipt, or whose receipt fails | **none** (a bare `created_at` is unsigned, RFC-ACDP-0008 §9.1) | — |
| Key-revocation context | the evidence time of its own body, per the two rows above | `registry` |
| Lifecycle event with a verified event receipt (§10) | `event_receipt.accepted_at` | `registry` |
| Lifecycle event with no verified event receipt | **none** (`occurred_at` is claimed by the actor) | — |
| DID-document snapshot | `observed_at` | `observed` (`pinned` when the caller pins it, §6.3) |
| Revocation-discovery record | `completed_at` | `observed` |
| Checkpoint (and the leaves it covers) | `checkpoint.timestamp`, with cosignature `witnessed_at` values as independent bounds | `registry` (+ witnesses) |

### 5.2 The two passes

- **As-of pass (T).** Every stage is evaluated using **only evidence whose evidence time is ≤ T**. Evidence with no evidence time counts as **not known at T**, with the two exceptions §7 states: bodies, and unattested events when `require_attested_events` is false. This conservative rule makes a backdated retraction harmless, and a later revocation non-retroactive in the as-of answer.
- **Latest pass.** Every stage is evaluated using all evidence.

The as-of pass runs only when the caller supplies T. The latest pass always runs.

### 5.3 Revocation at T

A key-revocation context is **applied** in the as-of pass only if its own evidence time is ≤ T. Once it is applied, RFC-ACDP-0014 §7 runs unchanged: the compromise-boundary comparison, the earliest-`compromised_since` fold over the applied members of the revocation lineage, producer scope, and attribution precedence. A revocation that is not applied in the as-of pass is reported as drift (§8.4) when the latest pass applies it.

### 5.4 Horizon

The horizon is the greatest evidence time over all evidence in the bundle that has one. A bundle with no timed evidence has a `null` horizon. The verifier MUST NOT read a wall clock in either pass. Offline there is no "now", and the report states the horizon in its place.

---

## 6. The Algorithm (NORMATIVE)

```
verify_chain(roots, evidence, options) -> acdp-chain-verdict/1
options = { as_of: T | null, limits, pinned, require_attested_events }
```

### 6.1 Walk

The verifier walks breadth-first from the roots over `derived_from`. The order is deterministic:

1. The roots are deduplicated, sorted by `ctx_id` in ascending byte order of their UTF-8 encoding, and assigned depth 0.
2. Nodes are expanded in order of increasing depth. Within one depth, they are expanded in ascending `ctx_id` byte order.
3. A node's `derived_from` entries are considered in array order. A `ctx_id` already admitted is a **DAG join**: it adds an edge and admits no new node.
4. The RFC-ACDP-0006 §4.1 controls apply, combined with AND. `limits` carries `max_depth`, `max_nodes` and `max_fanout`, which default to 10, 500 and 100. A caller MAY lower them and MUST NOT raise them above those defaults. Each limit **truncates** rather than aborts, as follows:
   - **`max_depth`.** A node at depth `max_depth` is verified but not expanded.
   - **`max_fanout`.** Only the first `max_fanout` distinct entries of a node's `derived_from` are admitted.
   - **`max_nodes`.** Once `max_nodes` nodes have been admitted, no further node is admitted.

   Every `ctx_id` that is referenced but not admitted joins the **frontier**. The report sets `complete: false` and names the first control that fired, in walk order.
5. The verifier MAY also enforce a wall-clock **time budget**. A verdict produced under a fired time budget MUST set `control: "timeout"` and `complete: false`, and is **exempt from the determinism requirement** (§9.3).
6. A **cycle** is a `derived_from` path from a node back to itself. It is reported as stage `presence: cycle` on every node that lies on the cycle. Honest registries cannot produce one, because `derived_from` can name only `ctx_id`s that already exist, so a cycle is evidence of a forged body or a forged bundle.

A node is resolved from `evidence.contexts`. A `ctx_id` the walk admits but `contexts` does not carry has presence `withheld` when `omitted` lists it with reason `withheld`, `unresolved` when `omitted` lists it with any other reason, and `absent` when `omitted` does not list it. An online verifier collects first (§4.3) and then runs the same algorithm over what it collected. It MUST NOT fetch evidence during a pass.

### 6.2 DID-document selection

For a `did:web` key:

- In the **as-of pass**, the verifier uses the snapshot with the greatest `observed_at` ≤ T. Ties are broken by array position, and the later entry wins. With no such snapshot, the key stage is `unknown` with reason `no_evidence_at_as_of`.
- In the **latest pass**, it uses the snapshot with the greatest `observed_at`.

The chosen snapshot is evaluated under RFC-ACDP-0001 §5.11 as though it were the fetched document. There is no forced re-fetch offline. An online verifier performs the §5.11 re-fetch **while collecting**, and the bundle records the result.

`did:key` resolves arithmetically (RFC-ACDP-0001 §5.11.1) with basis `self` in both passes.

### 6.3 Pinned trust

`pinned` is a caller-supplied set containing any of:

- DID-document snapshots, each bound to the instant at which the caller vouches for it;
- registry DIDs whose receipt keys the caller trusts;
- witness DIDs.

A pinned snapshot takes part in §6.2 selection like an observed one, but its basis is `pinned`. Pinning promotes a basis. It never overrides a failed check: a pinned key that does not verify a signature is still `signature: invalid`.

`pinned` contributes to the verdict through `options_digest` (§9.1).

### 6.4 Attested events

`require_attested_events` defaults to `true`. When `true`, the as-of pass considers only lifecycle events with a verified event receipt (§10). When `false`, an as-of pass MAY also consider an event without one, provided its signature verifies and its `occurred_at` is ≤ T. Such an event is labelled basis `observed`.

---

## 7. Per-Node Stages (NORMATIVE)

Each stage reports a `value`. Where the stage defines them, it also reports a `basis`, an `evidence_time` and a `reason`. Stages run in the order below, in both passes, over the evidence that pass admits. Stage values are the closed vocabularies in [`acdp-chain-verdict.schema.json`](../schemas/json/acdp-chain-verdict.schema.json).

### 7.1 `presence`

`present`, `withheld`, `unresolved`, `absent`, `truncated`, `cycle`, or `not_yet_published`.

- `not_yet_published` applies in the **as-of pass only**: the node's receipt verifies and its `created_at` is later than T. A chain that is honest at T cannot reference such a node.
- A node with no evidence time is `present` in the as-of pass, with the caveat `undated` (§8.1). Its content verifies arithmetically, but its existence at T is unproven.

A node that is not `present` runs no further stages.

### 7.2 `identity`

`ok`, `unbound`, or `mismatch`.

- **`mismatch`** when the bundle key ≠ `body.ctx_id`, when a present receipt's `ctx_id`, `lineage_id`, `origin_registry` or `created_at` disagrees with the body, or when the RFC-ACDP-0004 §2.1 first-version `lineage_id` derivation fails. This is the `fed-011` binding, carried offline.
- **`unbound`** when the body has no verified receipt. Its identity fields are then unattested.

### 7.3 `content_hash`

`ok` or `mismatch`, by recomputing under RFC-ACDP-0001 §5.7 over the exclusion-stripped body. Basis `self`.

### 7.4 `signature`

`ok`, `invalid`, or `unresolvable`, under RFC-ACDP-0001 §5.8. It uses the key the `key` stage resolves.

### 7.5 `registry_receipt`

`absent`, `ok`, or `invalid`, under RFC-ACDP-0010 §8, with the registry DID document chosen per §6.2. An `ok` value carries `key_status`: `current` or `historical`.

A receipt that fails is **treated as absent everywhere downstream**, as RFC-ACDP-0010 §8 requires.

### 7.6 `key`

`current`, `historical_receipt_attested`, `revoked`, `unplaceable`, `unresolvable`, or `unknown`.

- **`current`**: the signing key is in the chosen snapshot's `assertionMethod`, or the key is a `did:key`.
- **`historical_receipt_attested`**: RFC-ACDP-0010 §10 applies against the chosen snapshot.
- **`revoked`** and **`unplaceable`**: these come from `key_revocation` (§7.9). A revocation verdict overrides this stage.
- **`unresolvable`**: no snapshot, or a snapshot that cannot be evaluated under §5.11, in the **latest** pass. The as-of-pass equivalent is `unknown`, with reason `no_evidence_at_as_of`.

### 7.7 `log`

`absent`, `included`, `cannot_verify`, or `invalid`, under RFC-ACDP-0012 §9 and §9.1. An `included` value carries `tree_size`, `checkpoint_time` and `witnesses`. `witnesses` is the count of distinct trusted witness DIDs whose cosignatures verify under RFC-ACDP-0015 §8, over a verified checkpoint. A witness is trusted when it is pinned (§6.3).

In the as-of pass, a checkpoint counts only if its `timestamp` ≤ T.

### 7.8 `retraction`

`not_retracted`, `retracted`, `invalid`, or `unknown`.

1. **Admitting events.** The pass admits a prefix of `lifecycle_events`: the longest prefix whose every event is admitted under §6.4 (as-of) or carries a verified signature (latest, RFC-ACDP-0013 §5).
2. **Deriving the state.** RFC-ACDP-0013 §7.1 retraction state is derived over the admitted prefix.
3. **`unknown`** in the as-of pass when an event that is not admitted precedes an admitted one. The prefix is then unprovable.
4. **`invalid`** when event receipts disagree with the event array: a mismatched `index` or `event_hash`, or `accepted_at` values that decrease with index (§10.3).

### 7.9 `key_revocation`

`not-revoked`, `pre-compromise`, `revoked`, `unplaceable`, or `unknown`. RFC-ACDP-0014 §7–§8 applies, with these rules:

- **Applying revocations.** The verifier applies the key-revocation contexts the pass admits (§5.3).
- **Discovery records.** It considers the discovery records the pass admits. A record is admitted when its `completed_at` ≤ T in the as-of pass, and always in the latest pass.
- **Producer outcomes.** A producer has a **`revoked`** discovery outcome when any admitted revocation applies to it. It has **`not-revoked`** only when an admitted record says `not-revoked-complete`. Otherwise its outcome is **`unknown`**.
- **Precedence** is RFC-ACDP-0014's own: refusal, then `unknown`, then `pre-compromise`, then `not-revoked`.
- **Basis.** The value carries the basis of the evidence that decided it. A revocation that decided it is `registry`. A discovery record that decided it is `observed`.

---

## 8. Verdicts and Aggregation (NORMATIVE)

### 8.1 Node verdict

Each pass yields one node verdict. The first rule that matches decides it:

1. **`refused`** when any of these hold:
   - `presence` is `cycle` or `not_yet_published`;
   - `identity: mismatch`;
   - `content_hash: mismatch`;
   - `signature` is `invalid` or `unresolvable`;
   - `key` is `revoked`, `unplaceable` or `unresolvable`;
   - `key_revocation` is `revoked` or `unplaceable`.
2. **`unknown`** when any of these hold:
   - `presence` is `withheld`, `unresolved`, `absent` or `truncated`;
   - `key: unknown`;
   - `key_revocation: unknown`;
   - `retraction` is `unknown` or `invalid`;
   - `registry_receipt: invalid` or `log: invalid`.
3. **`ok_with_caveats`** when any **caveat** holds. The caveats are:
   - `undated`;
   - `identity: unbound`;
   - `key` is `historical_receipt_attested`;
   - `key_revocation: pre-compromise`;
   - `registry_receipt.key_status: historical`;
   - `retraction: retracted`;
   - `log: cannot_verify`;
   - any stage resting on basis `observed`.

   The verdict lists the caveats that hold, sorted, as the schema's tokens: `undated`, `identity_unbound`, `historical_key`, `pre_compromise`, `historical_receipt_key`, `retracted`, `log_cannot_verify` and `observed_basis`, in the order of the list above.
4. **`ok`** otherwise.

`retracted` is a **caveat, not a refusal**. A retracted body stays valid and retrievable (RFC-ACDP-0013 §8.1). Whether to rely on it is the consumer's policy, and §8.3 supplies what that policy needs.

### 8.2 Chain verdict

Each pass also yields one chain verdict: the worst node verdict, in the order `refused` > `unknown` > `ok_with_caveats` > `ok`. A pass with `complete: false` has a chain verdict no better than `unknown`.

### 8.3 Tainted paths

For each node whose node verdict is `refused`, or whose `retraction` is `retracted`, the verdict lists one **tainted path**: the shortest path from any root to that node, as a `ctx_id` array. Ties are broken by comparing the arrays lexicographically, element by element, in UTF-8 byte order.

Tainted paths do not change any node verdict. A descendant of a retracted or refused node keeps its own verdict, and policy acts on ancestry without re-walking.

### 8.4 Drift

When both passes run, the verifier emits one drift entry, `{ctx_id, kind}`, for each kind below that holds for a node. A stage difference that matches no kind and leaves the node verdict unchanged emits no entry. The kinds are:

| Kind | Meaning |
|---|---|
| `published_after_as_of` | The node is `not_yet_published` as of T. |
| `revoked_after_as_of` | `key_revocation` becomes `revoked` or `unplaceable` only in the latest pass. |
| `retracted_after_as_of` | `retraction` becomes `retracted` only in the latest pass. |
| `republished_after_as_of` | `retraction` returns to `not_retracted` only in the latest pass. |
| `backdated_event` | An event whose `occurred_at` ≤ T but whose `accepted_at` > T. This is reported in addition to the retraction kinds; the backdating is **reported, not believed**. |
| `as_of_unprovable` | A stage is `unknown` as of T for want of evidence (`no_evidence_at_as_of`), and decided in the latest pass. |
| `verdict_changed` | The node verdict differs between the passes and no kind above holds for the node. |

A clean key rotation after T is **not** drift. Rotation is not compromise (RFC-ACDP-0014 §9). It shows up as `key: current` as of T and `historical_receipt_attested` latest, which is a caveat change and therefore `verdict_changed` only if the node verdict itself changes.

---

## 9. The Verdict Object: `acdp-chain-verdict/1` (NORMATIVE)

### 9.1 Shape

The verdict is validated by [`acdp-chain-verdict.schema.json`](../schemas/json/acdp-chain-verdict.schema.json). Its members are:

- `verdict_version`: the literal `acdp-chain-verdict/1`.
- `roots`: sorted and deduplicated.
- `as_of`: T, or `null`.
- `horizon`.
- `limits`: `max_depth`, `max_nodes` and `max_fanout`.
- `require_attested_events`.
- `options_digest`: `sha256:` + hex(SHA-256(JCS(`pinned`))), or `null` when nothing is pinned.
- `evidence_digest`: `sha256:` + hex(SHA-256(JCS(bundle))).
- `complete`, `control` and `frontier` (sorted).
- `nodes`: sorted by `ctx_id`. Each node carries `depth` (the shortest distance from a root), `derived_from` (as in the body), and an `as_of` and a `latest` object. Each pass object holds the §7 stages and the §8.1 verdict and caveats.
- `chain`: `{as_of, latest}` chain verdicts.
- `tainted_paths`: under `as_of` and `latest`, each sorted.
- `drift`: sorted by `ctx_id`, then by `kind`.
- `as_of_digest` and `verdict_digest`.

When `as_of` is `null`, every `as_of` member is `null` and `drift` is empty. A member that does not apply (for example, the stages of a node that is not `present`, or `key_status` on a failed receipt) is omitted, never `null`. The only `null`able members are those the schema declares nullable. This keeps the JCS bytes unique.

### 9.2 Digests

- **`verdict_digest`** = `sha256:` + hex(SHA-256(JCS(verdict without `as_of_digest` and `verdict_digest`))). It identifies the full result, over this exact bundle.
- **`as_of_digest`** = `sha256:` + hex(SHA-256(JCS(the **as-of projection**))). The projection is the object made of these members only:
  - `verdict_version`, `roots`, `as_of`, `limits`, `require_attested_events` and `options_digest`;
  - `complete`, `control` and `frontier`;
  - `nodes`, each reduced to `ctx_id`, `depth`, `derived_from` and `as_of`;
  - `chain.as_of` and `tainted_paths.as_of`.

  It is `null` when `as_of` is `null`.

**`as_of_digest` is the value to seal at T.** It omits `evidence_digest`, `horizon` and everything from the latest pass, so it is stable as evidence accumulates after T. The bodies themselves are immutable, and later receipts, events, revocations and snapshots fall outside the as-of pass. An auditor holding a later bundle reruns `verify_chain` with the same T, limits and options, and compares `as_of_digest`.

A mismatch means the auditor's bundle differs from the sealer's *in evidence dated ≤ T*. The as-of projection pins exactly the stages that rest on that evidence, so the mismatch names what to examine. Evidence dated ≤ T that rests on basis `observed` can be fabricated by whoever produced the bundle. That is why such evidence is labelled, and why a sealer that witnessed the evidence SHOULD pin it (§6.3).

### 9.3 Determinism (NORMATIVE)

Given the same roots, bundle bytes and options, and no fired time budget, every conformant implementation MUST emit a verdict whose JCS serialization is byte-identical. In particular, its `as_of_digest` and `verdict_digest` MUST be equal.

Implementations MUST NOT add members to the verdict object. Diagnostics, durations and fetch logs belong outside it.

---

## 10. Lifecycle Event Receipts (amends RFC-ACDP-0013, NORMATIVE) *(0.5.0)*

### 10.1 Issuance

A registry that advertises both `acdp-registry-lifecycle` and `acdp-registry-receipts`, and declares `acdp_version` ≥ `0.5.0`, MUST mint an **event receipt** when it appends any lifecycle event: producer-initiated (RFC-ACDP-0013 §6) or registry-initiated. The receipt is minted atomically with the append.

```json
{
  "receipt_type": "acdp-event-receipt/1",
  "registry_did": "did:web:registry.example.com",
  "ctx_id": "acdp://registry.example.com/12345678-1234-4321-8123-123456781234",
  "event_id": "018f6d0a-7b2e-7c4d-9e1f-3a5b7c9d1e2f",
  "event_hash": "sha256:…",
  "index": 0,
  "accepted_at": "2026-07-04T09:15:43.120Z",
  "signature": { "algorithm": "ed25519", "key_id": "did:web:registry.example.com#receipt-key-1", "value": "…" }
}
```

The members are:

- **`event_hash`**: `sha256:` + hex(SHA-256(JCS(the event, *including* its `signature`))). It binds the exact event object as stored.
- **`index`**: the event's zero-based position in `lifecycle_events`.
- **`accepted_at`**: the registry's clock when it accepted the event. The registry MUST NOT backdate it; it MUST be ≥ the `accepted_at` of the event at `index - 1`, and ≥ the context's `created_at`.
- **`signature`**: under the RFC-ACDP-0010 §5 construction, verbatim, with the receipt signing key. The preimage is the JCS canonicalization of the object minus `signature`.

The object is closed ([`acdp-event-receipt.schema.json`](../schemas/json/acdp-event-receipt.schema.json)).

### 10.2 Serving

The registry serves event receipts in `registry_state.event_receipts`, an array **parallel** to `lifecycle_events`: element *i* is the receipt for event *i*. A registry bound by §10.1 MUST include `event_receipts` wherever it serves `lifecycle_events`.

The array is append-only under the same discipline as `lifecycle_events` (RFC-ACDP-0013 §4.1). An idempotent retry (RFC-ACDP-0013 §6) returns the receipt already minted. It MUST NOT mint a second one.

### 10.3 Verification

A consumer verifies event receipt *i* against event *i*:

1. The schema validates and `receipt_type` matches.
2. `registry_did` is `did:web:<authority>`, where `<authority>` equals the context's `origin_registry`.
3. `ctx_id` equals the context's `ctx_id`.
4. `event_id` equals the event's `event_id`.
5. `index` equals *i*.
6. `event_hash` recomputes.
7. The signature verifies under a key in the registry DID document's `verificationMethod`, chosen per §6.2. The RFC-ACDP-0010 §9 receipt-key lifecycle applies.
8. `accepted_at` is non-decreasing in *i*.

A receipt that fails any step is treated as absent. Step 8 failing on any pair makes the context's `retraction` stage `invalid` (§7.8).

### 10.4 What this fixes

An event receipt gives a lifecycle event a **provable evidence time** (§5.1). With it, as-of retraction state has a meaning. Without it, `occurred_at` is a claim by the actor and array order carries no clock, so as-of retraction state is `unknown` under the default `require_attested_events: true`.

---

## 11. Receipts on Lineage Members (amends RFC-ACDP-0004 §5.1, NORMATIVE) *(0.5.0)*

A registry that advertises `acdp-registry-receipts` and declares `acdp_version` ≥ `0.5.0` MUST include `registry_receipt` in every member of `GET /lineages/{lineage_id}`, exactly as in full retrieval (RFC-ACDP-0004 §2.1).

A consumer folding a key-revocation lineage (RFC-ACDP-0014 §7), or an exporter (§4.3), then needs one request instead of one per member. The RFC-ACDP-0014 §8 re-retrieve-by-`ctx_id` path remains the fallback for registries below 0.5.0.

---

## 12. Reserved: event leaves in the transparency log (NON-NORMATIVE)

A future amendment to RFC-ACDP-0012 MAY add a leaf kind that binds an event receipt's hash. That would make lifecycle events visible to log auditors as publishes already are. It is deliberately not specified here: the as-of semantics of this document depend only on §10. It is recorded in RFC-ACDP-0009 terms as deferred, for this reason: a leaf-format change regenerates the `log-*` goldens and should travel with its own fixtures.

---

## 13. Profile and Capabilities

- **Profile.** `acdp-consumer-chain`, registered in [`registries/profiles.md`](../registries/profiles.md), with prerequisite `acdp-consumer`. It is OPTIONAL. Claiming it commits a consumer to:
  - §4 bundle handling;
  - §6 walk determinism;
  - the §7 stages;
  - the §8 aggregation;
  - the §9 verdict and digests.
- **Registries.** The §10 and §11 obligations bind registries through `acdp_version` ≥ `0.5.0` together with their existing profiles. There is no new registry profile and no new capability field.
- **Errors.** None. Chain verification is consumer-side and has no wire surface beyond §10 and §11.

---

## 14. Conformance Fixtures

| Fixture | Covers |
|---|---|
| `chain-001` | 3-node DAG with a join, all `did:key`, receipts and complete discovery: both passes `ok`, no drift (§6.1, §8) |
| `chain-002` | Revocation published after T: as-of `ok_with_caveats` (observed discovery), latest `refused`, drift `revoked_after_as_of` (§5.3) |
| `chain-003` | Retraction with an event receipt after T: as-of `not_retracted`, latest `retracted`, drift `retracted_after_as_of` (§7.8, §10) |
| `chain-004` | Backdated retraction (`occurred_at` ≤ T < `accepted_at`): same as `chain-003`, plus `backdated_event` (§8.4) |
| `chain-005` | A cycle is `presence: cycle`, `refused`; a DAG join is not a cycle (§6.1) |
| `chain-006` | Fanout truncation: `complete: false`, `control: max_fanout`, frontier pinned (§6.1; offline `fed-010`) |
| `chain-007` | did:web snapshot selection before and after T; `observed` vs `pinned` basis; `no_evidence_at_as_of` (§6.2, §6.3) |
| `chain-008` | Tampered body, key ≠ `body.ctx_id`, and a node missing from `contexts` and absent from `omitted`: `content_hash: mismatch`, `identity: mismatch`, `absent` vs `withheld` (§4.2, §7) |
| `chain-009` | Event-receipt verification: wrong index, wrong `event_hash`, decreasing `accepted_at`; idempotent retry mints no second receipt (§10) |
| `chain-010` | Digest stability: the same bundle and options give the same `verdict_digest` across implementations and across online/offline modes; evidence added after T changes `verdict_digest` but not `as_of_digest` (§9) |

All are **behavioral** in this Draft. Promotion requires pinned known-answer verdict digests, generated by two independent implementations and then executed by `scripts/conformance-runner.py`.

---

## 15. Security Considerations

- **Bundles are adversarial input.** Size limits matter. Verifiers SHOULD bound the bundle byte size and the number of snapshots per DID, and MUST apply the §6.1 walk limits regardless of how many contexts the bundle carries.
- **`observed` is the weak point, and it is labelled.** A DID document has no signature and no history, so ACDP cannot prove what a `did:web` document said at T. Whoever produced the bundle can fabricate a snapshot dated ≤ T. Mitigations:
  - the `observed` caveat;
  - pinning by a party that actually witnessed the snapshot (§6.3);
  - `did:key` producers, whose keys are `self`.
- **Backdating is reported, not believed.** `occurred_at` never orders anything (RFC-ACDP-0013 §4.1). §10 gives events a registry-attested clock. A registry that backdates `accepted_at` is caught by the §10.1 monotonicity rule only relative to its own earlier receipts. The transparency-log leaf kind reserved in §12 would close the rest of that gap.
- **No wall clock.** A verifier that substitutes its own clock for the horizon makes verdicts depend on when they are computed. That breaks §9.3, and with it the auditor's ability to recompute.

---

## 16. References

- RFC-ACDP-0001 §5.3, §5.6, §5.7, §5.8, §5.11 — time, lineage, content hash, signature, key resolution
- RFC-ACDP-0004 §2.1, §5.1 — retrieval, lineage listing
- RFC-ACDP-0006 §4.1 — traversal controls, partial-walk reporting
- RFC-ACDP-0010 §5, §8, §9, §10 — receipt construction, verification, key lifecycle, historical keys
- RFC-ACDP-0012 §9 — log verification
- RFC-ACDP-0013 §4–§8 — lifecycle events and retraction
- RFC-ACDP-0014 §7–§9 — revocation semantics, discovery
- RFC-ACDP-0015 §8 — witness cosignature verification
- [RFC 8785] JSON Canonicalization Scheme
- [RFC 2119], [RFC 8174]
