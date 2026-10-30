# RFC-ACDP-0020
# Agent Context Distribution Protocol (ACDP) — Registry Trust Lists

**Document:** RFC-ACDP-0020
**Version:** 0.5.0
**Status:** Community Standards Track (Final)

This RFC specifies **registry trust lists**: a signed, consumer-side document that says which registries a consumer relies on, for which producers and context types, and during which period. A tenant, an organization or a consortium publishes one. Any number of consumers apply it the same way, online or offline. It answers the question every ACDP signature leaves open: the producer signature proves who wrote a body, and the registry receipt proves which registry accepted it, but neither says whether *that registry* is one this consumer should rely on. Until now each adopter answered that with private configuration. This document gives that configuration one signed, versioned, portable shape. It depends on RFC-ACDP-0001 (Core), RFC-ACDP-0002 (Context Body), RFC-ACDP-0010 (Registry Receipts), RFC-ACDP-0013 (Lifecycle Events) and RFC-ACDP-0014 (Key Revocation), and adds an optional companion report to RFC-ACDP-0017 (Chain Verification).

---

## 1. Status of This Memo

This document is a **Final** ACDP specification at version `0.5.0`, promoted 2026-10-30, ahead of the `acdp/0.5.0` line, which as a whole remains Draft (VERSIONING.md). Breaking changes now require a new RFC and a version bump.

**Promotion evidence.** The conformance fixtures this document defines (`trust-001`..`trust-007`, profile `acdp-consumer-trust-list`) pass against two independent interoperating implementations, both run at spec `546b8c8`:
- acdp-rs 0.18.2 (`acdp-mcp-proxy`, `acdp-chain`);
- acdp-verifier-py at `3928ee1`, written from this text alone.

Both reproduce `trust-001` byte for byte: the golden list's canonical form, `content_hash` and Ed25519 signature, and the pinned outcome, reason and entry of every case in the evaluation table. Both also pass the behavioral scenarios `trust-002`..`trust-007`, including the trust report bound to `verdict_digest`.

The `acdp-consumer-trust-list` profile (§9) is OPTIONAL. A consumer that does not apply trust lists is unaffected. Registries have no new obligation: a trust list is an ordinary body, published, served and retracted like any other.

Nothing in this document invalidates any existing body, signature, `content_hash`, receipt, checkpoint, cosignature or verdict. It changes no Final text. In particular RFC-ACDP-0017's `acdp-chain-verdict/1` object is unchanged; the trust result travels in a separate object (§8).

---

## 2. Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described in BCP 14 ([RFC 2119], [RFC 8174]) when, and only when, they appear in all capitals.

| Term | Definition |
|---|---|
| **Trust list** | A body of type `acdp:trust-list` whose `metadata` is an `acdp-trust-list/1` object (§4). |
| **Issuer** | The trust list's producer, `body.agent_id`. The producer signature is the trust-list signature. |
| **Issuer pin** | Consumer configuration naming an issuer DID and a `list_id` the consumer accepts lists from (§5.1). It is the root of trust, and it lives outside ACDP. |
| **List series** | Every trust list one issuer has signed under one `list_id`, ordered by `serial`. |
| **Entry** | One element of `entries`: a registry the issuer trusts, with optional pins, scope and validity window (§4.2). |
| **Evaluation time (T)** | The instant a trust decision is made for. In the latest pass it is now; in an as-of pass it is the as-of instant, as in RFC-ACDP-0017. |
| **Outcome** | The result of evaluating one body: `trusted`, `expired`, `out_of_scope`, `untrusted_registry` or `list_invalid` (§6). |

---

## 3. Motivation and Design Choices

A consumer that resolves `acdp://` references accepts bodies from many registries. Producer signatures make every body attributable, but an attacker who runs a registry can still publish bodies from producers it controls, and a misconfigured consumer can rely on them. Seam, the first adopter, runs one policy per tenant: each tenant trusts its own registry plus a few partners, and an auditor must later reproduce which registries the tenant trusted when a decision was sealed. That needs a policy that is signed, versioned, time-bounded and portable into an evidence bundle.

Choices, each with its reason:

- **A trust list is an ordinary ACDP body.** No new signing construction, endpoint or registry obligation. The producer signature authenticates it, supersession versions it, RFC-ACDP-0013 retraction withdraws it, RFC-ACDP-0014 revocation handles a compromised issuer key, and it is carried in an RFC-ACDP-0017 evidence bundle exactly like any other context.
- **The root of trust is configuration.** A consumer pins the issuers it accepts (§5.1). A trust list never makes its own issuer trusted, and no list can admit another list. There is no transitive trust and no federation graph.
- **Identity inside the signature.** `lineage_id` and `ctx_id` are registry-assigned and sit outside `content_hash` (RFC-ACDP-0001 §5.7). A list series is therefore named by the signed pair (issuer, `list_id`), and ordered by the signed `serial`, so the series survives republication at another registry and offline carriage. `lineage_id` remains the convenient registry-side handle.
- **Closed and small.** Every field is evaluated deterministically and offline. Policy that cannot be checked from the list, the body and the receipt alone (such as required registry profiles) is explicit about it (§6.3).

---

## 4. The Trust-List Body (NORMATIVE)

### 4.1 Body constraints

A trust list is a body (RFC-ACDP-0002) with:

| Field | Constraint |
|---|---|
| `type` | MUST be `acdp:trust-list`. The namespaced form is used so that every existing registry accepts the type today, with no vocabulary change. It is registered in [`registries/context-types.md`](../registries/context-types.md). |
| `metadata` | MUST be an `acdp-trust-list/1` object valid against [`acdp-trust-list.schema.json`](../schemas/json/acdp-trust-list.schema.json) (§4.2). |
| `schema_uri` | SHOULD be `https://schemas.acdp.io/v0.1.0/acdp-trust-list.schema.json`. |
| `visibility` | Any. A tenant's list MAY be `private` or `restricted`; a consortium list SHOULD be `public`. |
| `derived_from`, `data_refs` | SHOULD be empty. They carry no trust meaning. |
| `supersedes` | A new version of a list series SHOULD supersede the previous one at the same registry. Supersession is a convenience; ordering comes from `serial` (§5.3). |

Registries do not validate trust lists beyond ordinary publish rules. Validation is the consumer's (§5.2).

### 4.2 The `acdp-trust-list/1` object

```json
{
  "trust_list_version": "acdp-trust-list/1",
  "list_id": "tenant-acme.production",
  "serial": 7,
  "issued_at": "2026-10-26T00:00:00.000Z",
  "valid_from": "2026-10-01T00:00:00.000Z",
  "valid_until": "2027-04-01T00:00:00.000Z",
  "entries": [
    {
      "registry_did": "did:web:registry.example.com",
      "origin": "registry.example.com",
      "receipt_key_fingerprints": ["sha256:10ba682c8ad13513971e8b56881aab8bd702bb807796eca81932c735a94d6e6d"],
      "required_profiles": ["acdp-registry-receipts", "acdp-registry-lifecycle"]
    },
    {
      "registry_did": "did:web:partner.example.org",
      "origin": "partner.example.org",
      "scope": { "agent_id_prefixes": ["did:web:agents.partner.example.org:"], "types": ["analysis", "data_snapshot"] },
      "valid_until": "2026-12-01T00:00:00.000Z"
    }
  ]
}
```

| Member | Type | Req. | Meaning and reason |
|---|---|---|---|
| `trust_list_version` | string | Yes | `"acdp-trust-list/1"`. Lets a later version change the shape without ambiguity. |
| `list_id` | string | Yes | The issuer-chosen name of the series, `^[a-z0-9][a-z0-9._-]{0,127}$`. With the issuer DID it names the series inside the signature (§3). |
| `serial` | integer ≥ 1 | Yes | Strictly increasing within the series. It orders versions and defeats rollback (§5.3). |
| `issued_at` | timestamp | Yes | When the issuer signed this version. Used for as-of selection (§5.4). The issuer is the root of trust, so its own clock is accepted for its own list. |
| `valid_from`, `valid_until` | timestamp | Yes | The version applies for `valid_from` ≤ T < `valid_until`. `valid_until` is mandatory so a list that stops being refreshed stops working rather than trusting forever. `valid_from` MUST be before `valid_until`. |
| `entries` | array (0–1000) | Yes | The trusted registries. An empty array is valid and trusts nothing, which is how an issuer withdraws all trust without retracting. |

Each **entry**:

| Member | Type | Req. | Meaning and reason |
|---|---|---|---|
| `registry_did` | string | Yes | The registry's `did:web` DID. It is what receipts (`registry_receipt.registry_did`) and capabilities documents name. MUST equal `did:web:` + `origin` (the RFC-ACDP-0010 §4 binding), so the two cannot disagree. |
| `origin` | string | Yes | The registry authority as bodies name it: a lowercase hostname (§4.3), matched against `origin_registry` and the `acdp://` authority of `ctx_id`. Kept separately from `registry_did` because bodies carry the hostname, not the DID. |
| `receipt_key_fingerprints` | array of RFC-ACDP-0010 §6 fingerprints | No | Pins the keys the registry may sign receipts with. When present, a body is trusted only with a verified receipt signed by one of these keys. It defends against a registry DID document taken over at the web host. |
| `required_profiles` | array of profile names | No | Profiles the registry must advertise. `acdp-registry-receipts` here also means a verified receipt is required, which is checkable offline. The other names are checked only when the consumer holds the registry's capabilities document (§6.3). |
| `scope` | object | No | Limits which bodies from this registry are trusted. Absent: all bodies. Members: `agent_ids` (exact DIDs), `agent_id_prefixes` (string prefixes of `agent_id`), `did_methods` (e.g. `did:web`, `did:key`) and `types` (exact `type` values). Each present member is a constraint and all of them must hold. `agent_ids` and `agent_id_prefixes` together form one constraint, satisfied by either. Each array has at least one item. |
| `valid_from`, `valid_until` | timestamp | No | Narrows the list window for this entry, so one registry can be added or retired without reissuing the window of the others. |

No other member is allowed at either level (`additionalProperties: false`). Every timestamp is canonical millisecond RFC 3339 UTC (RFC-ACDP-0001 §5.3). The same registry MAY appear in several entries, for example with different scopes; the entries are combined as a union (§6.2).

### 4.3 Origins and hosts

- `origin` uses the `hostname` grammar of `acdp-common.schema.json`: lowercase LDH labels, an A-label for an internationalized name, and **no port**. ACDP authorities never carry a port (the `ctx_id` and `origin_registry` grammars, RFC-ACDP-0002 §3.1; a registry is always reached at `https://<authority>/`, RFC-ACDP-0006). A port-qualified origin is therefore invalid in a list, and could never match a body.
- Consumers compare a body's `origin_registry` and `ctx_id` authority with `origin` case-insensitively (ASCII). For schema-valid bodies this is plain equality; the case fold is defence in depth for consumers that accept bodies before schema validation.

---

## 5. Verifying and Selecting a List (NORMATIVE)

### 5.1 Issuer pins

A consumer applying trust lists holds a set of **issuer pins**, each an `issuer` DID and a `list_id`, optionally with `issuer_key_fingerprints` (RFC-ACDP-0010 §6 form) that restrict which of the issuer's keys may sign the list. Pins come from configuration: a file, a deployment secret, a tenant record. They are the root of trust. A consumer MUST NOT accept a pin from a trust list, a registry, a capabilities document or an evidence bundle.

### 5.2 Verifying one list version

A candidate list body L is **valid for a pin** P only if all hold:

1. L passes the RFC-ACDP-0001 §5.11 strict body pipeline (`content_hash` and producer signature). L may be a retrieved body or, out of band (§7), a publish-request body (ProducerContent with its `content_hash` and `signature`). Both verify identically, because the registry-assigned fields are outside the hash; a publish-request body simply has no `ctx_id`. In an as-of pass, the issuer's DID document is selected as of T per RFC-ACDP-0017 §6.2 instead of being fetched now.
2. `L.agent_id` equals `P.issuer`, `L.type` is `acdp:trust-list`, and `L.metadata.list_id` equals `P.list_id`.
3. If `P.issuer_key_fingerprints` is present, the RFC-ACDP-0010 §6 fingerprint of the issuer key that verified L's signature is in it.
4. `L.metadata` is valid against `acdp-trust-list.schema.json`, `valid_from` < `valid_until`, and every entry's `registry_did` equals `did:web:` + its `origin`.
5. The issuer key is not revoked for L under RFC-ACDP-0014 §7, with revocations admitted as the pass admits them. Only an applied revocation (`revoked` or `unplaceable`) fails this step. `unknown` (no discovery evidence, the usual offline case) does not: the issuer is already pinned by the consumer's own configuration (§5.1), and failing closed on `unknown` would make every offline list unusable. A consumer MAY refuse lists whose issuer-key revocation status is `unknown`, by local policy.

A version failing any step is ignored, as if absent. Where the consumer has no valid version for P at all, P contributes `list_invalid` with reason `no_valid_version` (§6.2).

### 5.3 Series state: rollback and equivocation

Within one series, versions are ordered by `serial`.

- **Rollback.** A consumer MUST persist, per pin, the highest `serial` it has accepted as valid (its **floor**). A version below the floor is never used, even when no other version is at hand. A replayed old list therefore cannot restore a registry the issuer has since dropped. When every version the consumer holds is below its floor, P contributes `list_invalid` with reason `rollback`.
- **Equivocation.** Two valid versions with the same `serial` and different `content_hash` are proof the issuer key signed conflicting lists. The consumer MUST treat P as `list_invalid` (reason `equivocation`) until a valid version with a higher `serial` arrives, and SHOULD alert.
- **Retraction.** A version withdrawn by an admitted RFC-ACDP-0013 `retracted` event, whose `actor` is the issuer DID and which is signed by the issuer, is not used. A registry-actor retraction is not trusted to withdraw a list. The version stays usable, and an implementation MAY log the retraction; `acdp-trust-report/1` does not carry it. An out-of-band list (§7) has no lifecycle channel, so its retractions are the issuer-signed `retracted` events supplied with it. With none supplied, it is not retracted, and staleness is the consumer's risk; refreshing online removes it. Retracting the version at the floor does **not** revert to a lower serial, because that would be a rollback. P is `list_invalid` (reason `retracted`) until the issuer publishes a higher serial. An issuer that wants an older policy back republishes it under a new serial.

### 5.4 Selecting the version for T

For pin P at evaluation time T:

1. Take the valid versions of P (§5.2), **retracted ones included**.
   - In the **latest** pass, take all of them, together with the persisted floor.
   - In an **as-of** pass, take only versions whose `issued_at` ≤ T, and count only the retractions the pass admits as of T, per RFC-ACDP-0017 §6.4 (attested events) and §7.8 (retraction evidence time). The floor for an as-of pass is the highest `serial` among those versions, retracted ones included, never the consumer's present-day floor, so a historical evaluation reproduces what was knowable at T.
2. The **top version** is the one with the highest `serial`. The checks below run in this order, and the first that applies decides P:
   1. No valid version: `list_invalid` (`no_valid_version`).
   2. The top version is below the floor (latest pass): `list_invalid` (`rollback`).
   3. Two valid versions share the top serial with different `content_hash`: `list_invalid` (`equivocation`), whether or not either is retracted.
   4. The top version is retracted: `list_invalid` (`retracted`). Retraction never selects a lower serial (§5.3).
   5. T is outside the top version's `valid_from` ≤ T < `valid_until`: `expired` (`list_window`). A consumer MUST NOT fall back to an older serial whose window covers T.
   6. Otherwise the top version is the **selected version**.

---

## 6. Evaluating a Body (NORMATIVE)

### 6.1 Inputs

- B: a body that already passed RFC-ACDP-0001 §5.11. Trust evaluation decides whether to rely on a verified body; it never makes an unverified body acceptable.
- R: B's registry receipt, *if* it verified under RFC-ACDP-0010 §8; otherwise R is absent. The receipt inputs are its `registry_did` and its **registry key fingerprint**: the RFC-ACDP-0010 §6 fingerprint of the registry key that signed the receipt. This is not the receipt's `key_fingerprint` member, which names the producer's key. The closed RFC-ACDP-0017 verdict does not carry it, so a verifier takes it from its own receipt verification.
- C: optionally, the set of profiles the registry of B advertises, from a capabilities document the consumer fetched (RFC-ACDP-0007). Offline, C is usually absent.
- T, and the pins with their selected versions (§5.4).

### 6.2 Algorithm

1. **Binding.** Let `a` be the lowercased authority of `B.ctx_id` and `o` the lowercased `B.origin_registry`. If `a ≠ o`, the outcome is `untrusted_registry` (reason `origin_mismatch`) and evaluation stops. A body whose identity claims two registries is not trusted through either.
2. For each pin with a selected, in-window version, evaluate each entry E in array order. The first failing check below gives the entry's outcome:
   1. `E.origin ≠ o`: the entry does not apply (no outcome).
   2. R is present and `R.registry_did ≠ E.registry_did`: `untrusted_registry` (`registry_mismatch`).
   3. A receipt is required (`E.receipt_key_fingerprints` is present, or `E.required_profiles` contains `acdp-registry-receipts`) and R is absent: `untrusted_registry` (`receipt_required`).
   4. `E.receipt_key_fingerprints` is present and R's signing-key fingerprint is not in it: `untrusted_registry` (`receipt_key_unpinned`).
   5. C is present and some name in `E.required_profiles` is not in C: `untrusted_registry` (`profile_missing`).
   6. T is outside the entry window (`E.valid_from` ≤ T < `E.valid_until`, each bound applying only when present): `expired` (`entry_window`).
   7. `E.scope` is present and B fails it: `out_of_scope`, with reason `scope_agent` (`agent_id` neither in `agent_ids` nor starting with any of `agent_id_prefixes`), `scope_did_method` (the `did:<method>` prefix of `agent_id` not in `did_methods`) or `scope_type` (`type` not in `types`), checked in that order.
   8. Otherwise: `trusted`.
3. **Per list.** The list's outcome is the best entry outcome under the precedence `trusted` > `expired` > `out_of_scope` > `untrusted_registry`, ties broken by the lowest entry index, which also supplies the reason. If no entry applies, the outcome is `untrusted_registry` (`no_entry`). A pin without a usable version contributes `expired` or `list_invalid` from §5.
4. **Across lists.** With no pins at all, the outcome is `list_invalid` (`no_valid_version`). Otherwise the final outcome is the best per-pin outcome under `trusted` > `expired` > `out_of_scope` > `untrusted_registry` > `list_invalid`. Ties are broken by the pin order (issuer, then `list_id`, by code point). This is a plain union: any one pinned list that trusts B is enough, and no list can widen or narrow another.

Only `trusted` permits reliance. Every other outcome is a refusal; the outcome and reason say why, for operators and auditors.

### 6.3 What the offline evaluation cannot check

`profiles_checked` is `true` exactly when C was supplied, whatever the entries name. `required_profiles` other than `acdp-registry-receipts` need the registry's capabilities document, which an evidence bundle does not carry. When C is absent those names are not checked, and the result records `profiles_checked: false` (§8). A consumer that requires them MUST fetch the capabilities document online, or treat `profiles_checked: false` as a refusal by local policy.

---

## 7. Carriage

- **At a registry.** A trust list is published, retrieved, superseded and retracted like any body. A consumer refreshes it by retrieving the series' `/current` or by watching its `lineage_id` on the RFC-ACDP-0018 changes feed.
- **Out of band.** The same signed body MAY be shipped as a file or with the consumer's configuration. It verifies identically, because nothing in §5–§6 needs the registry.
- **In an evidence bundle.** An RFC-ACDP-0017 `acdp-evidence/1` bundle MAY carry trust-list bodies in `contexts`, with their `lifecycle_events` and receipts, exactly as it carries key-revocation contexts. `verify_chain` does not reach them through `derived_from` and they do not alter the verdict object; like any extra context, they change `evidence_digest`. They also move the verdict's `horizon` (RFC-ACDP-0017 §5.4) when their timed evidence is later than the rest of the bundle, so `verdict_digest` changes too. `as_of_digest` never changes (RFC-ACDP-0017 §9.3). A verifier applying trust lists reads them from the same bundle, so one file reproduces both the chain verdict and the trust decision at T.

---

## 8. The Trust Report (OPTIONAL companion to RFC-ACDP-0017)

RFC-ACDP-0017 is Final and its verdict object is closed, so a verifier that applies trust lists to a chain reports the result in a separate **`acdp-trust-report/1`** object ([`acdp-trust-report.schema.json`](../schemas/json/acdp-trust-report.schema.json)). It is JCS-canonical and deterministic:

| Member | Meaning |
|---|---|
| `trust_report_version` | `"acdp-trust-report/1"`. |
| `pass` | `latest` or `as_of`, matching the RFC-ACDP-0017 pass it applies to. A verifier evaluating both passes emits two reports. |
| `evaluated_at` | T. |
| `verdict_digest` | The `verdict_digest` of the RFC-ACDP-0017 verdict whose nodes it evaluates. OPTIONAL: a report for single bodies outside a chain omits it. |
| `evidence_digest` | The bundle digest, when the lists came from a bundle. OPTIONAL. |
| `lists` | One element per pin, sorted by (`issuer`, `list_id`): `issuer`, `list_id`, `status` (`used`, `expired` or `invalid`), and, for `used` and `expired` only, the version's `serial`, `content_hash` and, if known, `ctx_id`; `reason` when not `used`. |
| `nodes` | One element per evaluated body, sorted by `ctx_id`: `ctx_id`, `outcome`, `reason` (absent for `trusted`), `profiles_checked`, and the deciding `issuer`, `list_id` and `entry_index` only when an entry decided the outcome (`trusted`, or an entry-level refusal). They are absent for `no_entry`, `origin_mismatch` and pin-level outcomes (`list_window`, `list_invalid`). |
| `report_digest` | `sha256:` + hex(SHA-256(JCS(report without `report_digest`))). |

For a chain, the inputs for each node are the node's body, its receipt only when the verdict's `registry_receipt` stage for that pass is `ok`, and the pass's T. The trust report never changes the chain verdict: an untrusted node does not taint the RFC-ACDP-0017 graph. Combining the two (for example, "refuse if any node is not trusted") is the consumer's policy.

---

## 9. Profile

**`acdp-consumer-trust-list`** *(0.5.0, Final, OPTIONAL)*, prerequisite `acdp-consumer`. A consumer claiming it:

- holds issuer pins only from configuration (§5.1);
- verifies and selects list versions per §5, persisting the per-pin floor;
- evaluates bodies per §6 and permits reliance only on `trusted`;
- when it applies lists to RFC-ACDP-0017 chains, emits `acdp-trust-report/1` per §8;
- passes `trust-001`..`trust-007`.

No registry profile is added. **Errors:** none new; a trust decision is local and is never sent on the wire.

---

## 10. Security Considerations

- **Issuer key compromise.** The issuer revokes the key with an RFC-ACDP-0014 `key-revocation` context. §5.2 step 5 then rejects lists signed with it at or after `compromised_since`, and the issuer reissues the series with a new key and a higher serial. Consumers SHOULD set `issuer_key_fingerprints` in their pins for high-value lists, so a DID-document takeover at the issuer's web host cannot mint lists.
- **Rollback.** A stale list replayed by a registry, a cache or an attacker is defeated by the per-pin floor (§5.3), and by refusing to fall back to an older serial when the selected one expires (§5.4). A consumer that loses its floor (new install) is exposed until it sees the current version; it SHOULD be provisioned with the expected minimum serial.
- **Freeze.** An attacker who suppresses new versions keeps the consumer on an old one. Mandatory `valid_until` bounds the damage; issuers SHOULD keep windows short and refresh often.
- **Origin vs DID mismatch.** A body claiming one registry in `ctx_id` and another in `origin_registry` is refused outright (§6.2 step 1). An entry whose `registry_did` and `origin` disagree makes the whole version invalid (§5.2 step 4). A verified receipt naming a different registry DID than the entry is refused (§6.2 step 2.2). Each closes a path to being trusted via one registry while claiming another.
- **Registry-actor retraction.** A registry could try to withdraw a list it serves. Only issuer-signed retractions count (§5.3), and a withdrawn floor never reverts to an older, wider list.
- **Scope is about producers, not truth.** A trusted registry may still serve a wrong body from an in-scope producer. Trust lists decide *where* a consumer accepts bodies from; producer signatures, receipts, lifecycle and revocation remain the checks on *what* was published.
- **Privacy.** A tenant's list reveals its partners. Publish it `private` or carry it out of band.

---

## 11. Conformance Fixtures

| Fixture | Covers |
|---|---|
| `trust-001` | Known answer, executed by the runner: a golden trust-list body (JCS, `content_hash`, Ed25519 signature by the `did:key` test issuer) and an evaluation table of body, receipt, capabilities and T to outcome, reason and entry (§4, §6) |
| `trust-002` | List validation: bad signature, wrong issuer, wrong `list_id`, unpinned issuer key, schema failure, `registry_did`/`origin` disagreement, revoked issuer key → the version is ignored, `list_invalid` (§5.2) |
| `trust-003` | Series state: rollback below the floor, equivocation at one serial, recovery by a higher serial (§5.3) |
| `trust-004` | Retraction: issuer-signed retraction withdraws a version without reverting; a registry-actor retraction does not withdraw it (§5.3) |
| `trust-005` | As-of selection: the version issued by T, as-of retractions, the as-of floor, an expired selected version with no fallback (§5.4) |
| `trust-006` | Several pins: union, precedence, tie-break by pin order, no transitive inclusion (§6.2) |
| `trust-007` | Carriage and report: lists carried in an evidence bundle leave the RFC-ACDP-0017 verdict unchanged; the trust report is deterministic, binds `verdict_digest`, and uses a node's receipt only when its receipt stage is `ok` (§7, §8) |

`trust-001` is executed; `trust-002`..`trust-007` are **behavioral**.

---

## 12. References

- RFC-ACDP-0001 §5.3, §5.7, §5.11 — timestamps, the hash exclusion set, the verification pipeline
- RFC-ACDP-0002 — the context body
- RFC-ACDP-0007 — capabilities
- RFC-ACDP-0010 §4, §6, §8 — receipt binding, key fingerprints, receipt verification
- RFC-ACDP-0013 — lifecycle events and retraction
- RFC-ACDP-0014 §7 — key revocation
- RFC-ACDP-0017 §6.2, §6.4, §7.8, §9 — as-of DID documents, attested events, retraction evidence time, the verdict
- RFC-ACDP-0018 — the changes feed
- [RFC 2119], [RFC 8174], [RFC 8785]
