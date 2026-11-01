# RFC-ACDP-0018
# Agent Context Distribution Protocol (ACDP) — Retraction Recall: the Changes Feed and Change Hints

**Document:** RFC-ACDP-0018
**Version:** 0.5.0-draft
**Status:** Community Standards Track (Draft)

This RFC specifies **retraction recall**: how a consumer that relied on a context learns, later, that it should no longer rely on it. Retractions, supersessions and key revocations are already recorded and verifiable (RFC-ACDP-0013, RFC-ACDP-0003, RFC-ACDP-0014), but only a consumer that goes back and looks ever sees them. This document adds:

- the **changes feed** (`GET /changes`): a registry-local, append-only, sequenced log of every reliance-changing change. Each entry (`acdp-change/1`) carries the signed evidence for the change, so a consumer verifies it rather than believing it;
- **watch filters**: stateless query filters by `ctx_id`, `lineage_id`, producer `agent_id` and change kind, plus *(0.5.0, 2026-11-01)* OPTIONAL **bucket filters** that select by a hash prefix, so the registry learns a bucket rather than the watched value (§6.1);
- **change hints** (`acdp-change-hint/1`): an OPTIONAL webhook saying only "there are new changes for you, pull now".

The feed is the normative channel and the hint is an optimization. A lost hint loses nothing, because the next pull returns every entry since the consumer's cursor. Indirect impact (contexts *derived from* a retracted one) is found through the existing `derived_from` search (RFC-ACDP-0005 §2) or by re-running chain verification (RFC-ACDP-0017). The registry keeps no fan-out state.

It depends on RFC-ACDP-0001, -0003, -0004, -0005, -0006, -0008, -0010, -0013, -0014 and -0017. It promotes RFC-ACDP-0009 §2.10 (the webhook event profile, reshaped as the §8 hint, under its reserved name `acdp-registry-events`). RFC-ACDP-0009 §2.4 (push of new *search matches*, `acdp-registry-push`) and §2.5 (server-side walks) stay reserved.

---

## 1. Status of This Memo

This document is a **Draft** ACDP specification on the `acdp/0.5.0` line. It is open for substantive change until it is promoted. Per [VERSIONING.md](../VERSIONING.md), promotion to **Final** requires the conformance fixtures this document defines (`rec-001`..`rec-010`) to pass against two independent interoperating implementations.

Promotion is split by side, as for RFC-ACDP-0021:

- **Consumer side** (§7, the `acdp-consumer-recall` profile, and the consumer fixtures `rec-006`, `rec-007` D–E, `rec-009` and `rec-010` G–I): promoted when a second consumer implementation, independent of the first, passes those fixtures against an SDK carrying the 2026-11-01 clarifications in this document.
- **Registry side** (§4–§6, §8, the `acdp-registry-changes` and `acdp-registry-events` profiles, and the registry fixtures): stays Draft until a second registry implementation passes the registry fixtures.

Nothing is promoted by this paragraph; it states the criteria.

All three profiles it defines (§9) are OPTIONAL. A registry or consumer that claims none of them is unaffected.

Nothing in this document invalidates any existing body, signature, `content_hash`, receipt or lifecycle event. A change entry carries existing signed objects verbatim and adds no new signature.

---

## 2. Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described in BCP 14 ([RFC 2119], [RFC 8174]) when, and only when, they appear in all capitals.

| Term | Definition |
|---|---|
| **Reliance** | A consumer's decision to act on a context: to cite it, seal it, or feed it to a model. |
| **Reliance-changing change** | A recorded change after which a consumer that relied on a context SHOULD re-evaluate that reliance (§3). |
| **Change entry** | One `acdp-change/1` object in the feed, describing one reliance-changing change and carrying its evidence (§4). |
| **Affected context** | The context whose reliance the change touches: the `ctx_id` of a change entry. |
| **Sequence number (`seq`)** | A registry-wide, strictly increasing integer assigned to each change entry at commit (§5.3). |
| **Feed cursor** | An opaque, durable position in the feed (§5.4). |
| **Watch filter** | The set of `ctx_id`, `lineage_id`, `agent_id`, `kind`, `lineage_bucket` and `agent_bucket` values a consumer passes to select entries (§6). |
| **Bucket** | The first *n* lowercase hex digits of SHA-256 over a `lineage_id` or `agent_id` (§6.1). |
| **Change hint** | A webhook delivery that carries no change content, only the fact that new matching entries exist (§8). |

---

## 3. What Counts as a Reliance-Changing Change (NORMATIVE)

A registry claiming `acdp-registry-changes` MUST record exactly one change entry for each of these, and for nothing else:

| `kind` | Recorded when | Affected `ctx_id` | Why reliance changes |
|---|---|---|---|
| `lifecycle` | A lifecycle event is appended to a context's `lifecycle_events` (RFC-ACDP-0013 §4.1), whatever its `event_type` | The context the event belongs to | A retraction withdraws the context; a republication restores it. Unknown event types are recorded too (RFC-ACDP-0013 §7.3). |
| `superseded` | A body whose `supersedes` names a context is accepted (RFC-ACDP-0003 §3.1) | The superseded (older) context | A newer version exists, and `/current` no longer returns this one (RFC-ACDP-0004 §5). |
| `key_revocation` | A `key-revocation` context is accepted (RFC-ACDP-0014 §4), producer-signed or registry-attested | The revocation context itself | Every context its producer signed with the revoked key at or after `compromised_since` loses its authority (RFC-ACDP-0014 §7). |

A plain publication with no `supersedes` and no `key-revocation` type records no entry. RFC-ACDP-0009 §2.4 subscriptions to new search matches remain reserved.

---

## 4. The Change Entry: `acdp-change/1` (NORMATIVE)

The entry is validated by [`acdp-change.schema.json`](../schemas/json/acdp-change.schema.json). It is closed: implementations MUST NOT add members.

```json
{
  "change_version": "acdp-change/1",
  "seq": 1042,
  "kind": "lifecycle",
  "ctx_id": "acdp://registry.example.com/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  "lineage_id": "lin:sha256:a3cb…",
  "agent_id": "did:key:z6MkiTBz…",
  "recorded_at": "2026-10-03T00:00:01.000Z",
  "event": { "event_id": "…", "event_type": "retracted", "…": "the stored event, verbatim" },
  "event_receipt": { "receipt_type": "acdp-event-receipt/1", "index": 0, "…": "…" }
}
```

Common members:

- **`seq`**: the entry's sequence number (§5.3).
- **`kind`**: `lifecycle`, `superseded` or `key_revocation` (§3).
- **`ctx_id`**, **`lineage_id`**: the affected context and its lineage.
- **`agent_id`**: the producer whose reliance the change touches. For `lifecycle` and `superseded` it is the affected context's `body.agent_id`. For `key_revocation` it is the revoked key's controller: `metadata.revoked_key_controller` when present, else the revocation body's `agent_id` (RFC-ACDP-0014 §4). A `key_revocation` entry is therefore a hint **keyed by controller**, not by key: it does not name the revoked key. The revoked key is named by the producer-signed `metadata.revoked_key_fingerprint` of the revocation body the consumer retrieves (RFC-ACDP-0014 §4), and RFC-ACDP-0014 §7 matching is done against that signed value (§7 step 3). An entry copy of the fingerprint would be an unsigned duplicate that the consumer would have to re-check anyway, so the entry deliberately carries none.
- **`recorded_at`**: the registry's clock at commit. It equals the evidence's own registry time, as below, so it adds no new claim.

Evidence members, by kind:

| `kind` | Evidence members | `recorded_at` equals |
|---|---|---|
| `lifecycle` | `event`: the stored lifecycle event, byte-for-byte as served in `lifecycle_events`. `event_receipt`: its `acdp-event-receipt/1` (RFC-ACDP-0017 §10). | `event_receipt.accepted_at` |
| `superseded` | `superseded_by`: the new version's `ctx_id`. `registry_receipt`: the new version's receipt (RFC-ACDP-0010). | `registry_receipt.created_at` |
| `key_revocation` | `registry_receipt`: the revocation context's receipt. | `registry_receipt.created_at` |

The entry carries **evidence, not verdicts**. Nothing in it is believed because the registry served it (§7). The `superseded` and `key_revocation` entries do not carry the new body. The consumer retrieves it, which keeps entries small and keeps body visibility under the retrieval rules (RFC-ACDP-0008 §4.5).

---

## 5. The Changes Feed: `GET /changes` (NORMATIVE)

### 5.1 Request

| Parameter | Type | Meaning |
|---|---|---|
| `since` | string | A feed cursor from an earlier response. Absent: start at the oldest retained entry. The literal `head`: return no entries and a cursor at the current head (§5.4). |
| `limit` | integer | Maximum entries to return. Default 100. A registry MUST accept any value up to `limits.max_changes_page` (§9). *(clarified 2026-11-01)* A larger value is not an error: the registry MUST clamp it to `limits.max_changes_page`, and `has_more` / `next_cursor` (§5.2) carry the rest. |
| `ctx_id` | string, repeatable | Watch filter (§6). |
| `lineage_id` | string, repeatable | Watch filter (§6). |
| `agent_id` | string, repeatable | Watch filter (§6). |
| `kind` | string, repeatable | Restrict to these kinds (§6). |
| `lineage_bucket` | string, repeatable | *(2026-11-01)* Bucket filter over `lineage_id` (§6.1). |
| `agent_bucket` | string, repeatable | *(2026-11-01)* Bucket filter over `agent_id` (§6.1). |

A request carrying more filter values in total than `limits.max_change_filters` MUST fail with `schema_violation` (400). Every value of every filter parameter above counts. So MUST an unknown `kind` value, a `limit` below 1, or a malformed bucket value (§6.1).

Because a `limit` may be clamped, and because filtering and visibility thin a page (§5.2, §5.5), a consumer MUST NOT infer that it has reached the head from a page shorter than the `limit` it sent. Only `has_more: false` says that no committed entry lies past `next_cursor`.

### 5.2 Response

The response is validated by [`acdp-changes-response.schema.json`](../schemas/json/acdp-changes-response.schema.json):

```json
{ "changes": [ { "change_version": "acdp-change/1", "seq": 1042, "…": "…" } ],
  "next_cursor": "c2VxOjEwNDI",
  "has_more": false }
```

- **`changes`**: the matching, visible entries after `since`, in ascending `seq` order.
- **`next_cursor`**: ALWAYS present, unlike search (RFC-ACDP-0005 §2.5). The feed is a tail: the cursor names the position after the last entry scanned, so a consumer at the head keeps polling with it.
- **`has_more`**: `true` when entries past `next_cursor` were already committed when the response was built. A consumer that sees `true` SHOULD request again at once.

An empty `changes` with `has_more: true` is not the end of the feed. The RFC-ACDP-0005 §2.5 post-filtering rule applies unchanged: visibility filtering MUST NOT end a page early.

*(2026-11-01)* **Page size in bytes.** A page of `limit` entries can be larger than a consumer's response bound, because entries carry their evidence verbatim (about 1–1.5 KB each).

- A registry SHOULD keep the serialized response body at or below **1 MiB** (1048576 bytes, measured before any content coding). It MAY end a page early to do so, with `has_more: true` and `next_cursor` after the last included entry. As with every short page (§5.1), this does not signal the head. A single entry larger than the bound is still returned, alone on its page.
- A consumer MUST accept a response body of up to 1 MiB. On a response larger than it accepts, a consumer SHOULD request the same `since` again with a smaller `limit`. It SHOULD NOT repeat the unchanged request, which would fail the same way forever.

*(2026-11-01)* **Compression.** A registry SHOULD honour `Accept-Encoding: gzip` on `GET /changes` with `Content-Encoding: gzip`, and a consumer SHOULD send it. The 1 MiB bound above applies to the decoded body, and a consumer MUST bound the decoded size it is willing to read, so a compressed response cannot exhaust it.

### 5.3 Sequence and atomicity

- `seq` is assigned at commit, is strictly increasing across the whole registry, and is never reused while any cursor issued before the reuse is still honoured. *(clarified 2026-11-01)* A registry that resets its sequence (for example by restoring the feed from a backup that predates entries it already served) MUST refuse **every** cursor issued before the reset with `cursor_expired` (§5.4). It MUST NOT go on honouring such a cursor, because a consumer holding one would silently skip the entries that reuse its numbers. Rotating the cursor-protection key at the reset is one way to meet this.
- Gaps are permitted. Filtering and visibility (§6, §5.5) remove entries, and a registry MAY skip values. A consumer MUST NOT infer completeness from contiguity.
- An entry is immutable. A registry MUST serve the same object for a given `seq` on every read.
- An entry is committed **atomically** with the change it records: in the same transaction as the appended event and its event receipt, or the accepted body and its receipt. A registry MUST NOT expose a change in `registry_state` (or `/current`) without its feed entry, nor a feed entry without the change.

### 5.4 Cursors and retention

Feed cursors are **durable**. This overrides the one-hour session bound of RFC-ACDP-0005 §2.5.4 for `/changes` only. Every other §2.5.4 rule applies: cursors are opaque, MUST NOT leak visibility information, and MUST be re-scoped to the current requester on every request.

- A registry MUST retain entries, and honour cursors pointing at them, for at least `limits.change_retention_seconds` (§9), which MUST be ≥ 2592000 (30 days).
- A cursor pointing before the oldest retained entry MUST fail with `cursor_expired` (400). A cursor the registry cannot parse MUST fail with `invalid_cursor` (400).
- *(clarified 2026-11-01)* A well-formed cursor that this registry issued but can no longer place MUST fail with `cursor_expired`, not `invalid_cursor`. That covers a cursor protected under a rotated key, one issued before a sequence reset (§5.3), one beyond the current head after a restore, and one invalidated by any other rebuild of the feed. `invalid_cursor` is reserved for a cursor that is unparseable or forged, one the registry could never have issued. The distinction tells the consumer what to do: `cursor_expired` means "you missed entries, resync" (§7).
- `since=head` lets a new consumer start at the present without replaying history. It returns `changes: []` and the head cursor.

### 5.5 Visibility

An entry appears for a requester exactly when the requester may retrieve the relevant context under RFC-ACDP-0008 §4.5:

- `lifecycle`: the affected context;
- `superseded`: the **new** version (`superseded_by`), whose retrieval is what the consumer needs in order to verify;
- `key_revocation`: always, since revocation contexts are `public` (RFC-ACDP-0014 §4).

A hidden entry is omitted entirely. It never appears redacted.

---

## 6. Watching and Dependents (NORMATIVE)

A **watch** is the filter a consumer passes to `/changes`. The registry stores nothing per watch.

- Values within one parameter are OR'd. `ctx_id`, `lineage_id` and `agent_id` are OR'd with each other: an entry matches when any of them matches. `kind` is AND'd with that result. With no `ctx_id`, `lineage_id`, `agent_id`, `lineage_bucket` or `agent_bucket` value (§6.1), every visible entry matches.
- `ctx_id=X` matches an entry whose `ctx_id` is X. It ALSO matches a `key_revocation` entry whose `agent_id` equals the `agent_id` of context X, when the registry holds X. Revoking a producer's key is a reliance change for every context that producer signed, so a consumer watching a context hears about its producer's revocations without watching the producer separately.
- `lineage_id=L` matches every entry whose `lineage_id` is L. That covers every version's retraction and every supersession in the lineage.
- `agent_id=D` matches every entry whose `agent_id` is D.

**Dependents.** A change to context X can matter to a consumer that relied on a context derived from X, and that consumer may never have watched X. ACDP answers this without registry fan-out:

- A producer or consumer that wants to know what was built on X queries `GET /contexts/search?derived_from=X` (RFC-ACDP-0005 §2), under its visibility rules (RFC-ACDP-0005 §3).
- A consumer that holds evidence for a whole chain re-runs `verify_chain` (RFC-ACDP-0017) on it. The latest pass reports `retracted_after_as_of` and `revoked_after_as_of` drift for every affected node at any depth.

A consumer relying on a derived context SHOULD watch the `lineage_id`s of the contexts it transitively depends on, or the producers of those contexts. That is the cheap way to hear about indirect changes. Server-side traversal (RFC-ACDP-0009 §2.5) stays reserved.

### 6.1 Bucket filters *(0.5.0, 2026-11-01)*

An exact watch filter tells the registry which contexts, lineages and producers a consumer relies on (§10). A bucket filter tells it only a **bucket**: a short prefix of a hash of the watched value, which many unrelated values share. The registry returns every entry in the bucket, and the consumer picks out its own.

**Derivation.** The bucket of length *n* of a value *v* is the first *n* characters of lowercase hex(SHA-256(UTF-8(*v*))). *v* is the `lineage_id` or `agent_id` string exactly as it appears in change entries, prefix and percent-encoding included (`lin:sha256:…`, `did:web:…%3A8443`). `rec-010` pins known answers.

**Registry (OPTIONAL).** A registry that supports bucket filters MUST advertise `limits.max_change_bucket_length` (§9). It then MUST:

- accept `lineage_bucket` and `agent_bucket` values of 1 to `max_change_bucket_length` lowercase hex digits (`[0-9a-f]`), and refuse any other value with `schema_violation` (400);
- match `lineage_bucket=b` against every entry whose `lineage_id` has a bucket starting with `b`, and `agent_bucket=b` against every entry whose `agent_id` does. A `key_revocation` entry's `agent_id` is the revoked key's controller (§4), so a producer's bucket hears its revocations;
- combine bucket values exactly like the §6 watch members: OR'd with each other and with `ctx_id`, `lineage_id` and `agent_id`, and AND'd with `kind`. A bucket matches only the entry's own `lineage_id` or `agent_id`: the §6 rule by which `ctx_id=X` also matches its producer's key revocations has no bucket counterpart;
- return the **whole** bucket. A registry MUST NOT narrow a bucket result, and every §5 rule (cursors, `has_more`, visibility) applies unchanged.

Bucket filters apply to `GET /changes` only; a subscription filter (§8.1) carries no bucket member. A consumer that watches by bucket and wants hints SHOULD subscribe with a filter of `kind` values only, which reveals nothing about what it watches. It then pulls with its bucket filter, as §8.2 permits.

A registry that does not advertise `max_change_bucket_length` SHOULD refuse a bucket parameter with `schema_violation`, so that a consumer is never silently given an unfiltered or wrongly filtered page.

**Consumer.** A consumer MUST NOT send a bucket parameter to a registry that does not advertise `max_change_bucket_length`, nor a bucket longer than the advertised value. A bucket response is a **candidate set**: the consumer MUST apply its own exact match to each entry, under the §6 rules for the exact values it watches (including the `ctx_id` rule for its producers' key revocations), before §7 verification. An entry outside its watch MUST NOT change any reliance decision. A consumer that watches contexts by bucket instead of by `ctx_id` MUST also send the `agent_bucket` of each of their producers, or it stops hearing those producers' key revocations.

**What a bucket hides (informative).** The registry learns the set of buckets, not the values. With *N* distinct values of that kind known to the registry, a bucket of length *n* covers about *N* / 16ⁿ of them, so a consumer chooses *n* for the crowd it wants to hide in. Some limits apply:

- **Crowd size.** A consumer SHOULD choose *n* so that each bucket is expected to hold at least *k* values for a *k* it documents in its own deployment; 100 is a reasonable floor. A consumer cannot verify *N*. It can estimate it from the distinct `lineage_id` and `agent_id` values in an unfiltered read of the feed.
- **Intersection.** A registry that sees a consumer's bucket set change over time can intersect the sets to narrow down the values that persist. A consumer SHOULD therefore send the same bucket set on every request, add buckets as it starts to rely on new values, and drop buckets only rarely. It SHOULD NOT send exact filters for values it also watches by bucket.
- **Large watch sets.** A consumer watching about 16ⁿ values or more covers nearly every bucket and gains nothing over an unfiltered read, which it SHOULD use instead. The `max_change_filters` limit bounds the bucket set in the same way.
- **Small populations.** The crowd is the population of that kind of value, not of all values. A registry may know only tens of producers, and then an `agent_bucket` of any length hides little.
- **Correlated buckets.** The registry knows which lineages belong to which producer. A consumer that sends both a `lineage_bucket` and the matching `agent_bucket` lets the registry intersect the two, so the effective crowd is much smaller than either estimate.
- **Fingerprinting.** A stable bucket set is itself a persistent fingerprint: it links every request that carries it, which works against making requests unlinkable (§10). Stability defends against intersection, not against linking.
- **Retrieval.** Bucket filters hide nothing from a registry that also sees the consumer retrieve, under a linkable identity, the contexts it relies on, for example during §7 verification or scheduled re-verification. See §10.

---

## 7. Consumer Processing (NORMATIVE)

A change entry is a **hint until verified**. A consumer claiming `acdp-consumer-recall` MUST verify an entry before it changes any reliance decision, as follows:

1. **`lifecycle`.**
   - Verify `event` under RFC-ACDP-0013 §5.
   - Verify `event_receipt` under RFC-ACDP-0017 §10.3 against that event, with *i* = `event_receipt.index` and the affected context's `created_at`.
   - Then re-derive the context's retraction state over its **full** event list (RFC-ACDP-0013 §7.1). The consumer either re-retrieves the context (RFC-ACDP-0004 §2) or uses the events it already holds. It MAY apply the entry's event directly only when it already holds and has verified every earlier event of that context (indexes `0` to `index − 1`).
   - When it re-retrieves, the served `lifecycle_events[index]` MUST be byte-equal (under JCS) to the entry's `event`. Otherwise the registry is inconsistent and the entry is rejected.
2. **`superseded`.**
   - Retrieve `superseded_by` and verify it under RFC-ACDP-0001 §5.11. Verify its served `registry_receipt` under RFC-ACDP-0010 §8; the entry's `registry_receipt` MUST be JCS-equal to it.
   - Confirm that its `supersedes` equals the entry's `ctx_id`, its `lineage_id` equals the entry's `lineage_id`, and its `agent_id` equals the entry's `agent_id` (supersession keeps the producer, RFC-ACDP-0003 §3.1).
   - Whether reliance moves to the new version is the consumer's policy.
3. **`key_revocation`.**
   - Retrieve the revocation context and verify it under RFC-ACDP-0014 §5 (producer-signed) or §6 (registry-attested).
   - Verify its served `registry_receipt` under RFC-ACDP-0010 §8, whichever arm applies; the entry's `registry_receipt` MUST be JCS-equal to it. Equality with a verified served receipt is sufficient: the entry's copy needs no separate signature check.
   - Apply RFC-ACDP-0014 §7: the producer scope, the compromise boundary and the earliest-`compromised_since` fold over its lineage.
   - Match the revoked key using the retrieved, verified revocation's `metadata.revoked_key_fingerprint`, never a value from the entry (§4). The entry names only the controller, so one entry can concern any of that controller's keys, and a consumer MUST check which of its relied contexts were signed by the revoked key before changing any reliance decision.
   - (Informative) To make that check local, a consumer SHOULD record the signing-key fingerprint of each context at the time it relies on it. A consumer that did not can recover it by re-retrieving the relied context.

The remaining rules apply to every kind:

- **Envelope consistency.** `recorded_at` MUST equal the evidence time given in §4: `event_receipt.accepted_at` for a lifecycle entry, `registry_receipt.created_at` otherwise. The evidence MUST name the entry's context. For `lifecycle`, `event.ctx_id` and `event_receipt.ctx_id` equal `ctx_id`. For `superseded`, `registry_receipt.ctx_id` equals `superseded_by`, `superseded_by` ≠ `ctx_id`, and `registry_receipt.lineage_id` equals `lineage_id`. For `key_revocation`, `registry_receipt.ctx_id` equals `ctx_id`. A mismatch rejects the entry.
- **Origin binding.** For every kind, the retrieved body (the affected context, `superseded_by`, or the revocation context) MUST have `origin_registry` equal to the authority serving the feed. The feed is registry-local, and supersession never crosses registries (RFC-ACDP-0003).
- **Held prefix.** "Already holds and has verified" (step 1) is the caller's assertion: a held event list covering indexes `0` to `index − 1`. With no such list, the consumer re-retrieves, and the byte-equality rule applies.
- **Failure.** An entry that fails verification MUST NOT change any reliance decision. Failure is itself a signal: the registry or the path to it may be faulty. The consumer SHOULD re-verify the affected context directly from its own retrieval, since a faulty source could equally drop a real entry.
- **Idempotency.** Delivery is at-least-once, because a consumer may re-read after a crash. *(clarified 2026-11-01)* Consumers MUST process entries idempotently: applying the same verified entry twice MUST leave the same reliance state as applying it once. A consumer MAY additionally deduplicate by (`registry authority`, `seq`), but only between resyncs: `seq` can be reused after a sequence reset (§5.3), so a consumer that keeps (authority, `seq`) dedup state MUST clear it for that authority on every resync. After a resync, an entry whose `seq` was seen before the resync is a new entry.
- **Cursor persistence.** A consumer SHOULD persist `next_cursor` only after it has processed every entry before it.
- **Resync.** On `cursor_expired`, the consumer has missed an unknown set of entries. It MUST re-verify every watched context directly (RFC-ACDP-0004 retrieval, or `verify_chain`), then resume from `since=head`. *(clarified 2026-11-01)* A consumer MUST resync the same way on `invalid_cursor` returned for a cursor that it persisted from an earlier response: the registry issued that cursor, so the answer means the registry can no longer place it, whatever code the registry chose (§5.4). It also MUST clear any (authority, `seq`) dedup state for that authority (Idempotency, above).
- **Registry-local revocations.** The feed carries only key revocations that **this** registry accepted (Origin binding, above). A producer may publish its revocation to a different registry, and RFC-ACDP-0014 §6 scopes a registry-attested revocation to that registry's own contexts. The absence of a `key_revocation` entry is therefore not evidence that a key is unrevoked. A consumer claiming `acdp-consumer-recall` MUST also run RFC-ACDP-0014 §8 discovery on a schedule for the producers of the contexts it relies on. Mirroring other registries' revocations into a feed is reserved (RFC-ACDP-0009 §2.16).
- **Completeness is not proven.** The feed is a notification channel, not a completeness proof (§10). A consumer whose reliance is high-stakes SHOULD also re-verify on a schedule. RFC-ACDP-0017's `as_of_digest` lets it prove what it knew when it relied.

---

## 8. Change Hints (webhooks) (NORMATIVE for `acdp-registry-events`)

A registry claiming `acdp-registry-events` lets an authenticated requester register a webhook. The webhook tells the requester when new entries match its filter. A hint carries **no change content**: the consumer always pulls the feed (§5), and everything it acts on is verified there (§7).

### 8.1 Subscriptions

- **`POST /subscriptions`** with an [`acdp-subscription-request`](../schemas/json/acdp-subscription-request.schema.json) body:
  ```json
  { "filter": { "lineage_id": ["lin:sha256:…"], "kind": ["lifecycle", "key_revocation"] },
    "callback_url": "https://consumer.example.com/acdp/hints" }
  ```
  `filter` has the §6 semantics. The registry returns `201` with an [`acdp-subscription`](../schemas/json/acdp-subscription.schema.json) object: `subscription_id`, the `filter`, `callback_url`, `created_at`, `status` (`active`), and `secret`, a base64 string of at least 32 random bytes. The `secret` is returned **only** in this response and is never served again.
- **`GET /subscriptions/{subscription_id}`** returns the object without `secret`. **`DELETE /subscriptions/{subscription_id}`** removes it and returns `204`.
- Subscriptions are **owned by the requester DID** that created them. Every request MUST be authenticated (RFC-ACDP-0008 §6.2); an unauthenticated one fails with `not_authorized` (403). Another requester's subscription is `not_found` (404), never `not_authorized`, so ids leak nothing.
- A requester MUST NOT hold more than `limits.max_subscriptions_per_requester` subscriptions. Over-limit creation, an invalid `filter`, or a `callback_url` rejected under §8.3 fails with `schema_violation` (400), with `details.field` naming the member.

### 8.2 The hint

When one or more entries committed after the last hint match a subscription's filter, **and** are visible to the subscription's owner (§5.5, evaluated as that requester), the registry POSTs an [`acdp-change-hint/1`](../schemas/json/acdp-change-hint.schema.json) to `callback_url`:

```json
{ "hint_version": "acdp-change-hint/1",
  "subscription_id": "6f1c…",
  "registry_authority": "registry.example.com",
  "head_cursor": "c2VxOjEwNDI" }
```

- **Authentication.** The registry signs the request with header `ACDP-Signature: t=<unix seconds>,v1=<hex>`, where `v1` = lowercase hex(HMAC-SHA-256(*key*, `<t>` + `.` + the raw request body bytes)).
  - The HMAC *key* is the **UTF-8 bytes of the `secret` string exactly as served**, not its base64 decoding. Receivers store and use the string verbatim.
  - The header is a comma-separated list of `key=value` pairs. Receivers MUST accept the pairs in any order, MUST ignore unknown keys, and MUST accept the request when **any** `v1` value matches. That leaves room for a registry to send several `v1` values during secret rotation, and for a future `v2` scheme.
  - Receivers MUST compare in constant time and MUST reject a `t` more than 300 seconds from their clock.
  - `rec-007` carries a known-answer vector (`hint-hmac-001`), which `scripts/conformance-runner.py` executes. This authenticates the hint to its subscriber. It is **not** a producer or registry signature and conveys no authenticity for any change (RFC-ACDP-0009 §2.10).
- **Coalescing.** A registry MAY send one hint for many entries and MAY drop a hint while an earlier one for the same subscription is undelivered. A hint is "pull now", not "one change happened".
- **Delivery.** Delivery is best-effort. A registry SHOULD retry a failed delivery (a non-2xx response or a timeout) with exponential backoff for at least one hour. It MAY disable a subscription that has failed for 72 hours, and then MUST answer `GET` on it with `"status": "disabled"`.
- **Receiver duty.** On a hint, the receiver pulls `GET /changes?since=<its own persisted cursor>` with the subscription's filter, or with any filter that selects at least the same entries, such as a §6.1 bucket filter combined with the subscription's `kind` values. It MUST NOT jump to `head_cursor`, which is informational, or it skips entries. It MUST NOT treat the absence of hints as the absence of changes.

### 8.3 Callback safety

The registry makes outbound requests to consumer-chosen URLs, so the RFC-ACDP-0006 §7 SSRF protections apply to every delivery:

- `https` only, with certificate validation;
- the host resolves only to public unicast addresses, re-checked at **every delivery** (DNS rebinding);
- no redirects followed;
- connect and response timeouts of at most 10 seconds;
- response bodies are not read beyond 1 KiB.

A `callback_url` failing these rules at creation is rejected (§8.1).

---

## 9. Profiles and Capabilities

- **`acdp-registry-changes`**, prerequisites `acdp-registry-lifecycle` and `acdp-registry-receipts`, at `acdp_version` ≥ `0.5.0`.
  - Endpoint: `GET /changes`.
  - Obligations: §3–§6.
  - Fixtures: `rec-001`..`rec-005` and `rec-008`.
  - Its `capabilities.limits` MUST carry:
    - `change_retention_seconds` (≥ 2592000);
    - `max_change_filters` (≥ 100);
    - `max_changes_page` (≥ 100).
  - *(2026-11-01)* OPTIONAL bucket filters (§6.1): a registry that supports them advertises `limits.max_change_bucket_length` (4 to 16) and is then also bound by `rec-010` A–F.
- **`acdp-registry-events`**, prerequisite `acdp-registry-changes`. This is the name RFC-ACDP-0009 §2.10 reserved, now defined as §8.
  - Endpoints: `POST /subscriptions`, `GET /subscriptions/{id}` and `DELETE /subscriptions/{id}`.
  - Fixture: `rec-007`.
  - Its `capabilities.limits` MUST carry `max_subscriptions_per_requester` (≥ 1).
- **`acdp-consumer-recall`**, prerequisite `acdp-consumer`.
  - Obligations: §7, and the §8.2 receiver duty when it uses hints.
  - Fixtures: `rec-006`, `rec-009`, and `rec-007` scenarios D–E; `rec-010` G–I when it uses bucket filters.
- A registry not advertising a profile MUST answer its endpoints with `not_implemented` (501).
- **Errors.** None new. The document uses `schema_violation`, `cursor_expired`, `invalid_cursor`, `not_authorized`, `not_found` and `not_implemented`.

---

## 10. Security Considerations

- **The feed can omit, but cannot forge.** Every entry carries producer- and registry-signed evidence that the consumer verifies (§7). A faulty registry can still **withhold** entries. The mitigations:
  - an event receipt's `index` exposes a missing earlier event of the same context, because §7 step 1 needs the full list;
  - a consumer can re-verify directly, or verify against the transparency log (RFC-ACDP-0012) where the registry advertises it;
  - high-stakes reliance re-verifies on a schedule (§7).

  The leaf kind RFC-ACDP-0017 §12 reserves for events would make lifecycle withholding detectable.
- **Visibility.** The feed is a search-like surface. §5.5 keeps it no wider than retrieval, so a cursor or a hint never reveals a hidden context. A hint is sent only for entries visible to the owner and carries no content, so even a leaked hint body reveals only that *something* matched.
- **Watch filters reveal interest.** *(revised 2026-11-01)* An exact watch filter tells the registry which contexts, lineages and producers a consumer relies on. A consumer can poll an unfiltered feed and filter locally, at the cost of bandwidth, or use bucket filters (§6.1), which reveal only buckets. Neither hides the reliance set on its own: the registry also sees the consumer **retrieve** the contexts it relies on, during §7 verification of a matching entry and during any scheduled re-verification. A registry that can link those reads to one consumer, by source address or by authenticated identity (RFC-ACDP-0008 §6.2), reconstructs the set from them, whatever the feed filter was. A consumer that needs to hide its reliance set from the registry operator SHOULD make its retrievals unlinkable as well, for example anonymous reads from shared egress addresses. That is possible only for `public` contexts: restricted and private contexts need authenticated reads (RFC-ACDP-0008 §6.2), which identify the consumer. Stronger designs (client-sent compact filters, private retrieval, feed mirrors) are reserved in RFC-ACDP-0009 §2.17 and §2.18.
- **Webhooks are outbound requests to attacker-chosen URLs.** §8.3 is mandatory for that reason. The HMAC `t` bound limits replay. Secrets are shown once and SHOULD be stored hashed or encrypted at rest.
- **Hints are not evidence.** A forged or replayed hint can only cause an extra pull, which is harmless.

---

## 11. Conformance Fixtures

| Fixture | Covers |
|---|---|
| `rec-001` | Feed mechanics: ascending `seq`, entry immutability across reads, `next_cursor` always present, `has_more`, `since=head`, polling at the head, an over-maximum `limit` clamped, a page kept under 1 MiB (§5.1–§5.4) |
| `rec-002` | One entry per reliance-changing change and none otherwise: retract and republish give `lifecycle`, a superseding publish gives `superseded`, a `key-revocation` gives `key_revocation`, a plain publish gives nothing. The evidence is byte-identical to the served objects (§3, §4) |
| `rec-003` | Watch filters: OR within and across `ctx_id`/`lineage_id`/`agent_id`, AND with `kind`; a `ctx_id` watch hears its producer's key revocation; over-limit or unknown filters give `schema_violation` (§5.1, §6) |
| `rec-004` | Visibility: restricted and private entries hidden, `superseded` visible only with the new version, an empty page with `has_more`, a cursor replayed by another requester re-scoped (§5.5) |
| `rec-005` | Retention: a cursor before the oldest retained entry gives `cursor_expired`, a malformed one gives `invalid_cursor`; cursors stay valid past one hour; an issued cursor the registry can no longer place, or one from before a sequence reset, gives `cursor_expired` (self-test) (§5.3, §5.4) |
| `rec-006` | Consumer verification (consumer): a bad event signature, a failing event receipt, a `superseded_by` that does not supersede, and a revocation out of producer scope each change nothing; valid entries trigger re-evaluation; duplicates processed once; `cursor_expired`, or `invalid_cursor` on a persisted cursor, forces a resync that clears `seq` dedup; a revocation matched by the retrieved fingerprint; feed silence is not non-revocation; a short page is not the head; an oversized page is retried with a smaller `limit` (§5.1, §5.2, §7) |
| `rec-007` | Hints: subscription create, get and delete, `secret` shown once, owner scoping, HMAC header verification, stale `t` rejected, SSRF rejections of `callback_url`, no change content in the hint, receiver pulls from its own cursor (§8) |
| `rec-008` | Atomicity: every event receipt in `registry_state` has its feed entry; a context's events appear in index order; no entry without its change (§5.3) |
| `rec-009` | Entry envelope consistency (consumer, executable): known answers for the §7 envelope rules (`recorded_at` equality, per-kind `ctx_id` and `lineage_id`, no self-supersession, JCS equality of the entry's evidence with the served copy), each `{entry, served} → accept \| reject(reason)` (§7) |
| `rec-010` | Bucket filters: derivation known answers (executable); a bucket returns every entry in it and only those; longer buckets narrow; `agent_bucket` hears revocations by controller; OR/AND combination and the `max_change_filters` count; malformed values give `schema_violation`; cursors and visibility unchanged (registry A–F, when `max_change_bucket_length` is advertised); the consumer filters a bucket response locally and sends no bucket to a registry that does not advertise support (consumer G–I) (§6.1) |

All are **behavioral** in this Draft, except `rec-007`'s HMAC known-answer vector `hint-hmac-001`, the `rec-009` envelope known answers and the `rec-010` bucket derivations, which the runner executes.

---

## 12. References

- RFC-ACDP-0001 §5.11 — verification pipeline
- RFC-ACDP-0003 §3.1 — supersession
- RFC-ACDP-0004 §2, §5 — retrieval, lineages and `/current`
- RFC-ACDP-0005 §2, §2.5, §3 — search, `derived_from`, cursors, visibility
- RFC-ACDP-0006 §7 — SSRF protections
- RFC-ACDP-0008 §4.5, §6.2 — visibility, authenticated reads
- RFC-ACDP-0009 §2.4, §2.5, §2.10, §2.17, §2.18 — reserved subscriptions, walks, the webhook profile, private watch filters and feed mirrors
- RFC-ACDP-0010 — registry receipts
- RFC-ACDP-0012 — transparency log
- RFC-ACDP-0013 §4–§7 — lifecycle events and retraction state
- RFC-ACDP-0014 §4–§7 — key revocation
- RFC-ACDP-0017 §10, §12 — event receipts, reserved event leaves
