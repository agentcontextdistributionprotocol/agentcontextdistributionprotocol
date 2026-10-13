# Proposal: Consumer Revocation-Discovery Completeness and Verification Bindings

**Target path:** `rfcs/proposals/consumer-revocation-and-verification-2026-10.md`
**Status:** Pre-Draft proposal. It targets the **acdp/0.5.0 Draft line**. If accepted, each change below lands as an in-prose ***(0.5.0)*** amendment to the RFC it names, following the RFC-ACDP-0014 §4/§10 precedent.
**Amends:** RFC-ACDP-0001 §5.11, RFC-ACDP-0002 §3.1/§4.2, RFC-ACDP-0004 §2.1, RFC-ACDP-0005 §2.3, RFC-ACDP-0010 §8/§9, RFC-ACDP-0014 §5/§6/§8, and `registries/profiles.md` (`acdp-consumer`).
**Spec pin:** `agentcontextdistributionprotocol` origin/HEAD `f4a19a1` (2026-10-08). **Evidence pin:** `acdp-rs` origin/HEAD `424253b` (crate `acdp` 0.14.5).

> **Process note.** `governance/RFC-PROCESS.md` defines a Draft as a PR against `rfcs/RFC-ACDP-XXXX-*.md`. It has no `rfcs/proposals/` stage. This file is a review vehicle to settle the text before the per-RFC amendment PRs are opened. If maintainers would rather review the amendments in place, fold each section below into its target RFC as a *(0.5.0)* passage and drop this file. The README index needs no change, because no new RFC number is requested.

---

## Summary

This proposal makes eight consumer-side changes on the 0.5.0 Draft line. Six close gaps through which a conformant `acdp-consumer` can record **"not revoked" when the honest answer is "could not tell"**, or can accept a registry-assigned binding it never checked:

1. **Revocation-discovery outcome classes.** Discovery yields `revoked`, `not-revoked (complete)` or `unknown`. `not-revoked` is allowed only when the answer is complete. A candidate that fails only because its signer key has since rotated, or only for a transient reason, never counts as absent.
2. **Truncation is not completeness.** A consumer that stops paginating while `next_cursor` is present MUST NOT treat the result as complete.
3. **Unanswerable discovery.** A 403 from `anonymous_public_reads: false`, or a 501 from a core-only registry, yields `unknown`.
4. **DID-cache refresh** is made concrete for discovery and for "key not found / not in `assertionMethod`" failures.
5. **Receipt-key status.** The RFC-ACDP-0010 §8 step 1 / §9 tension is resolved and the receipt-key status is reported.
6. **Receipt verdict reported separately.** RFC-ACDP-0010 §8 is aligned with the `acdp-consumer` manifest and `fed-011`.
7. **Consumer binding of `lineage_id` and `origin_registry`.** These are SHOULD-level checks parallel to the `ctx_id` binding.
8. **Editorial: the RFC-ACDP-0014 §6 "served by or receipted by" scope.**

It also adds conformance vectors for the consumer profile, including one raw-JSON hashing vector that existing `can-*` vectors do not cover.

## Motivation

A consumer that seals decisions against ACDP contexts must **never record a false "not revoked."** A "not revoked" written into a durable record is a positive claim, and it outlives the discovery call that produced it. Downstream readers treat it as evidence.

RFC-ACDP-0014 §8 already says honestly that absence of search results is not evidence of absence. That bullet is about a *malicious* registry. The spec says nothing about the more common, non-adversarial ways an honest consumer can still conclude absence wrongly:

- **The revocation's own signer rotated.** The revocation is found, then dropped because its signer is no longer in `assertionMethod`. §5 step 1 explicitly permits it via the RFC-ACDP-0010 §10 historical rule, but nothing requires discovery to apply that rule (see P1). This is the *normal* lifecycle: §5 tells producers to keep two keys, and §9 tells them to rotate.
- **The signer's DID host returns 5xx.** RFC-ACDP-0001 §5.11 step 3 classifies this as transient. Nothing in RFC-ACDP-0014 says a transient candidate failure makes the discovery answer `unknown`.
- **The signer key is new and the DID document is cached.** The cache can be up to 24 h old under §5.11 "Caching". The "refresh on any verification failure that could plausibly be due to key rotation" MUST does not say which failures, or that discovery is covered.
- **The search was cut off by the consumer's own page budget**, or refused (403/501). RFC-ACDP-0005 §2.3 binds only registries ("`next_cursor` is the only correct signal").

Each of these yields a fact that is false yet looks complete. None of them requires a misbehaving registry: they follow from ordinary key rotation, ordinary outages and ordinary client budgets. Some implementations already handle a subset in code (for example truncation and retracted revocations), but the spec text that would make every implementation do so is missing.

---

## P1. Revocation-discovery outcome classes *(0.5.0)*

### Problem

- **RFC-ACDP-0014 §5 step 1** (L77): *"a receipt-attested historical authorization satisfies this step."* Nothing requires a **discovering** consumer to attempt that path before discarding a candidate.
- **RFC-ACDP-0014 §8** (L133–134) describes the search and the malicious-registry caveat. It defines no outcome when a candidate cannot be verified.
- **RFC-ACDP-0001 §5.11 step 3** (L378): *"HTTP non-2xx response … MUST be reported as `key_resolution_unreachable`"* (transient). RFC-ACDP-0014 never connects a transient candidate failure to the discovery verdict.

**Consequence for an implementation that follows the current text literally.** A consumer that verifies discovery candidates with the strict current-`assertionMethod` rule, and treats every verification failure as "this candidate is not a revocation", drops a rotated-signer revocation, and drops any candidate whose signer's DID host is briefly unavailable. It then returns a confident, complete-looking empty result, and a consumer that caches discovery results caches that negative too.

### Proposed normative text

Add to **RFC-ACDP-0014 §8**, after the first bullet:

> *(0.5.0)* **Discovery outcome (NORMATIVE).** A consumer performing revocation discovery for a producer P (and, where applicable, a registry controller R) at a vantage V MUST arrive at exactly one of the following outcomes and MUST NOT collapse them:
>
> - **`revoked`**: at least one candidate verified per §5 (or §6) names the fingerprint in question. §7 applies.
> - **`not-revoked (complete)`**: discovery at V completed (P2), was answerable (P3), and **every** candidate returned was classified as one of the following:
>   - verified per §5/§6 but naming a different fingerprint;
>   - **permanently invalid**, meaning a failed `content_hash`, an invalid signature, a §4 shape violation, a self-signature (§5 step 2), or a signing key absent from the signer's `verificationMethod` *after a fresh DID-document fetch* (RFC-ACDP-0001 §5.11 "Caching").
> - **`unknown`**: any other case.
>
> A consumer MUST NOT record, cache, or report `not-revoked` for an `unknown` outcome. What a consumer does with `unknown` (fail closed, or proceed and report) is deployment policy, but the outcome itself MUST be reported distinguishably.
>
> *(0.5.0)* **The §5 step 1 historical arm applies to discovery.** A candidate whose signing key is present in the signer's `verificationMethod` but absent from `assertionMethod` MUST NOT be classified as permanently invalid until the consumer has attempted the RFC-ACDP-0010 §10 receipt-attested historical rule on it. The consumer retrieves the candidate with its `registry_receipt` and verifies that receipt per RFC-ACDP-0010 §8. If the historical rule succeeds, the candidate is a verified revocation. If no receipt is served, or the receipt fails, the candidate is **unverified** and the outcome is `unknown`, not `not-revoked`. A revocation whose signer has rotated out has lost provability, not validity.
>
> *(0.5.0)* **Transient candidate failures.** A candidate whose verification fails for a reason RFC-ACDP-0001 §5.11 step 3 classifies as transient (`key_resolution_unreachable`, including any non-2xx DID-document response), or whose retrieval fails transiently (`rate_limited`, `registry_internal`, transport error), makes the outcome `unknown`.

### Conformance vectors to add (consumer profile)

**`rev-005-discovery-outcome-classes`** (behavioral; REQUIRED for 0.5.0 consumers, unconditional like `rev-002`). Fixed producer DID P with keys K1 (revoked), K2 and K3.

| Scenario | Setup | Expected outcome |
|---|---|---|
| A | Revocation of K1 signed by K2. K2 has since moved from `assertionMethod` to `verificationMethod` only. The candidate carries a valid receipt attesting K2. | `revoked`, trust class producer-signed |
| B | As A, but the response carries no receipt. | `unknown` (never `not-revoked`) |
| C | Revocation of K1 signed by K2. P's DID host answers 503 (and, separately, 404). | `unknown` |
| D | Revocation of K1 signed by K3, where K3 was added to P's DID document after the consumer cached it. | The consumer re-fetches, then `revoked` |
| E | Revocation of K1 signed by K2, but K2 is absent from `verificationMethod` even after a fresh fetch. | The candidate is permanently invalid. With no other candidates, `not-revoked (complete)` |

## P2. Truncation is not completeness *(0.5.0)*

### Problem

**RFC-ACDP-0005 §2.3** (L104–112) binds registries only: *"`next_cursor` is the only correct signal for 'there are more results'"* and *"Post-filtering MUST NOT terminate a cursor sequence early"*. Nothing binds a consumer that stops on its own page or byte budget.

RFC-ACDP-0005 §2.3 explicitly permits empty post-filtered pages that still carry `next_cursor`. Such pages consume a consumer's page budget without yielding anything. A capped consumer therefore sees a truncated set that looks complete.

`acdp-rs` fixed this in code: `AcdpError::SearchTruncated` at `revocation.rs:553-575`, plus `MAX_LINEAGE_WALKS`. Older pins (`acdp` ≤ 0.11) return a partial `Ok`. Other implementations have no normative text to follow.

### Proposed normative text

Append to **RFC-ACDP-0005 §2.3**:

> *(0.5.0)* **Consumer-side completeness (NORMATIVE).** A client that stops following `next_cursor` while one is still present, whether because of a page cap, byte cap, time budget, or error, has a **truncated** result. It MUST NOT present or rely on that result as complete. Where completeness is semantically load-bearing, the client MUST surface truncation as a distinct outcome rather than returning the partial set as if it were whole. The prime example is RFC-ACDP-0014 §8 revocation discovery, where an absent match is read as "not revoked". A page with empty `matches[]` and a non-empty `next_cursor` is not an end-of-results signal (above).

And to **RFC-ACDP-0014 §8**:

> *(0.5.0)* A truncated discovery (RFC-ACDP-0005 §2.3) has outcome `unknown`. The same applies to a lineage walk bounded by a client cap before the full lineage was obtained (§7 "Assembling the lineage").

### Conformance vectors to add

`rev-005` scenario F: a registry serves 11 pages of empty `matches[]`, each with `next_cursor`, then one page carrying a matching revocation of K1. A consumer with a page cap below 12 MUST report `unknown`, never `not-revoked`. A consumer that follows the cursor to the end reports `revoked`.

## P3. Unanswerable discovery: authorization and core-only registries *(0.5.0)*

### Problem

**RFC-ACDP-0014 §8** (L133): *"Revocation contexts are `public` (§4), so they are visible to any requester the registry serves at all."* That is accurate, but it hides two cases:

- **Anonymous requests to a non-anonymous registry.** **RFC-ACDP-0005 §2.5.5** (L177): with `anonymous_public_reads: false`, which is the default, a registry *"MUST reject an anonymous (unauthenticated) search request with `not_authorized` (HTTP 403)"*. An unauthenticated consumer cannot discover revocations there at all.
- **Core-only registries.** `registries/profiles.md` (`acdp-registry-core`) permits `not_implemented` (501) on `GET /contexts/search` for registries that do not advertise discovery.

In both cases the spec is silent on the outcome. A consumer that treats an empty or failed search as "nothing found" records `not-revoked` for a large class of registries. Separately, read authentication (`bearer_jwt`, RFC-ACDP-0008 §6.2 *(0.5.0)*) is the only way to make the 403 case answerable. The spec should say so.

### Proposed normative text

Replace the last sentence of the first bullet of **RFC-ACDP-0014 §8** with:

> Revocation contexts are `public` (§4), so they are visible to any requester the registry serves at all. *(0.5.0)* That set excludes anonymous requesters when the registry advertises `anonymous_public_reads: false` (RFC-ACDP-0005 §2.5.5). A discovery search answered with `not_authorized`, or with `not_implemented` by a registry not advertising `acdp-registry-discovery`, is **unanswerable at that vantage**, and its outcome is `unknown`, never `not-revoked`. A consumer that needs answerable discovery against such a registry authenticates its reads (RFC-ACDP-0008 §6.2, `registries/auth-methods.md`), or obtains revocations out of band (third bullet below). It can also fall back to the lineage endpoint for revocations it already knows the lineage of. That fallback does not discover new revocations.

### Conformance vectors to add

`rev-005` scenario G: search answered 403 `not_authorized` → `unknown`. Scenario H: search answered 501 `not_implemented` → `unknown`.

## P4. DID-cache refresh, made concrete *(0.5.0)*

### Problem

**RFC-ACDP-0001 §5.11 "Caching"** (L393): *"Implementations MUST refresh on any verification failure that could plausibly be due to key rotation."* "Plausibly" is not testable. Neither the RFC nor any fixture says which failures qualify or that revocation discovery is covered.

A verifier that refreshes only on an undefined subset of failures can hold a cached document for the full cache lifetime (up to 24 h). A revocation signed by a key added after the document was cached then fails with a permanent-looking "no verificationMethod matches", and under the current text nothing stops discovery from dropping it (P1).

### Proposed normative text

Replace the last sentence of **RFC-ACDP-0001 §5.11 "Caching"** with:

> Implementations MUST refresh on any verification failure that could plausibly be due to key rotation. *(0.5.0)* At minimum, a verifier holding a cached DID document MUST re-fetch it once, bypassing the cache, before it reports `key_resolution_failed` because no `verificationMethod` matches the fragment (step 4) or `key_not_authorized` (step 5), and before it classifies a revocation candidate as permanently invalid (RFC-ACDP-0014 §8). It then re-runs steps 4–7 against the fresh document. The verdict from the fresh document is final for that verification. A verifier MAY rate-limit forced re-fetches per DID.

### Conformance vectors to add

`rev-005` scenario D (above). Also **`rot-002-stale-did-cache`** (behavioral, consumer): the consumer first resolves P's DID with only K1. P then adds K2 and publishes a body signed by K2. Verification MUST succeed after one forced re-fetch, not fail with `key_resolution_failed`.

## P5. Receipt-key status *(0.5.0)*

### Problem

**RFC-ACDP-0010 §8 step 1** (L122): *"current receipt keys MUST be in `assertionMethod`; retired receipt keys MAY verify historical receipts from `verificationMethod` alone."*

**§9** (L141): *"A verifier evaluating a receipt MUST accept a receipt key found in `verificationMethod` even when it is absent from `assertionMethod`, and SHOULD report such verification with a *historically authorized* status."*

From a consumer's point of view a "retired" key and a key that was **never** a receipt key look the same: both are in `verificationMethod` and absent from `assertionMethod`. So the step 1 MUST cannot be enforced, and §9's MUST-accept wins.

This matters more since RFC-ACDP-0014. A receipt's `created_at` is the **only** time anchor §7 step 1 accepts. A receipt from a non-asserted key can therefore place an attacker's context *before* T, giving "historically authorized (pre-compromise)". Because the §9 status is only a SHOULD, a consumer can accept such a receipt without reporting anything that distinguishes it from a current-key receipt.

### Proposed normative text

Replace the last sentence of **RFC-ACDP-0010 §8 step 1** with:

> For receipt keys, the `assertionMethod` requirement is replaced by the lifecycle rule of §9. *(0.5.0)* A verifier MUST determine and report the **receipt-key status**:
>
> - **current**: the key is referenced by the registry DID document's `assertionMethod`.
> - **historical**: the key is present in `verificationMethod` only.
>
> A receipt verified under a *historical* key MUST be reported as such and MUST NOT be presented as a currently-authorized registry attestation.

Add to **RFC-ACDP-0014 §7 step 1**:

> *(0.5.0)* The receipt's key status (RFC-ACDP-0010 §8 step 1) MUST be carried into the `key_revocation` stage report. A deployment MAY require a *current* receipt key (or corroborating RFC-ACDP-0012 log inclusion) before it accepts a receipt-attested time that places a context *before* T. Under the strict default, a historical receipt key remains sufficient, as RFC-ACDP-0010 §9 already provides.

### Conformance vectors to add

**`rcpt-005-receipt-key-status`** (behavioral, consumer):

- A: the receipt is signed by a key in both `verificationMethod` and `assertionMethod` → valid, status `current`.
- B: the key is in `verificationMethod` only → valid, status `historical`.
- C: the key is absent from `verificationMethod` → `invalid_receipt`.

## P6. Receipt verdict reported separately *(0.5.0)*

### Problem

**RFC-ACDP-0010 §8** (L131): *"Verification reports SHOULD carry the body verdict and the receipt verdict separately."*

Two other documents state this more strongly:

- **`registries/profiles.md` `acdp-consumer`** (L127) lists *"with the receipt verdict reported separately from the body verdict *(0.2.0)*"* as a required behavioural requirement.
- **`fed-011`** says *"both verdicts are produced and reported"* and *"the two checks are reported as distinct verdicts, not collapsed into one"*.

The RFC is SHOULD, and the manifest and fixture read as MUST.

`acdp-rs` 0.14.5 aborts the whole retrieval on a receipt failure. In `verified.rs:1076-1104` the `verify_receipt_value(..).await?` propagates, so no "body valid, receipt invalid" outcome is representable. That is fail-closed and consistent with `fed-009` for a *resolver*, but not with §8's "does not invalidate the body" for a *consumer*.

### Proposed normative text

Replace the last sentence of the **RFC-ACDP-0010 §8** "Receipt failure" paragraph with:

> *(0.5.0)* An `acdp-consumer` MUST report the body verdict and the receipt verdict separately. The `registry_receipt` stage name reserved by RFC-ACDP-0001 §5.11 is active for 0.2.0 reports. A failing receipt MUST then be treated exactly as an absent one for every rule that consumes receipt-attested facts:
>
> - the RFC-ACDP-0010 §10 historical-key rule, which then does not apply;
> - RFC-ACDP-0014 §7 step 4, which then fails closed;
> - `lineage_id` / `origin_registry` binding (P7).
>
> A consumer MUST NOT present a body whose receipt failed as receipt-attested. A federated resolver's wire behavior (`invalid_receipt`, HTTP 502, `fed-009`) is unchanged.

### Conformance vectors to add

Extend **`rcpt-004`** (or add `rcpt-006`). The body is valid and the receipt's `ctx_id` is mismatched. Expected: body verdict *valid*, receipt verdict *invalid_receipt*. With the signer key in `verificationMethod` only, the overall result fails closed because the historical rule is unavailable.

## P7. Consumer binding of `lineage_id` and `origin_registry` *(0.5.0)*

### Problem

- **RFC-ACDP-0001 §5.6** (L201–217) binds only the *registry* to the lineage derivation.
- **RFC-ACDP-0002 §4.2** (L162–164): *"A context's `lineage_id` MUST be derived deterministically per RFC-ACDP-0001 §5.6."* No consumer obligation follows.
- **RFC-ACDP-0002 §3.1** constrains `origin_registry` to a hostname form. It does not require a consumer to check it against the `ctx_id` authority.

Both fields are registry-assigned and sit in the §5.7 exclusion set, so neither the signature nor `content_hash` covers them. Without a receipt (RFC-ACDP-0010 §8 step 3), nothing binds them.

The same reasoning produced the RFC-ACDP-0004 §2.1 / RFC-ACDP-0006 §4.1 step 7 `ctx_id` erratum (L60). RFC-ACDP-0014 §7's lineage fold is keyed on `lineage_id`, and consumers seal these fields.

For a first version (`supersedes: null`) the check is offline and costs one hash.

### Proposed normative text

Add to **RFC-ACDP-0004 §2.1**, after "Bind the resolved identity":

> *(0.5.0)* **Bind the registry-assigned lineage and origin (consumer SHOULD).** A consumer that relies on `lineage_id` or `origin_registry` SHOULD verify:
>
> 1. For a body with `supersedes: null`, that `lineage_id` equals the RFC-ACDP-0001 §5.6 derivation from `body.ctx_id`.
> 2. That `origin_registry` equals the `ctx_id` authority.
>
> A mismatch SHOULD be treated as `schema_violation` for the retrieved body. For a body with `supersedes ≠ null`, the derivation needs the version-1 `ctx_id`. A consumer SHOULD obtain it from a verified receipt (RFC-ACDP-0010 §8 step 3) or from a lineage walk ending at a `supersedes: null` member, and otherwise SHOULD report `lineage_id` as registry-asserted (unbound).

And to **RFC-ACDP-0002 §4.2**:

> *(0.5.0)* Consumers SHOULD verify the derivation where it is checkable (RFC-ACDP-0004 §2.1).

### Conformance vectors to add

**`lin-002-consumer-lineage-binding`** (behavioral, consumer):

- A: a v1 body with a correct `lineage_id` → accepted.
- B: a v1 body whose `lineage_id` is the derivation of a different `ctx_id` → rejected `schema_violation`.
- C: a v2 body with no receipt → accepted with `lineage_id` reported unbound.

**`body-003`**: `origin_registry` ≠ `ctx_id` authority → rejected `schema_violation`.

## P8. RFC-ACDP-0014 §6 scope: "served by or receipted by" (editorial) *(0.5.0)*

### Problem

**RFC-ACDP-0014 §6** (L97): *"the strict profile default is to apply §7 for contexts *served by or receipted by that same registry*."*

Today a receipt's `registry_did` MUST equal the serving authority (RFC-ACDP-0010 §8 step 2), which makes "receipted by" a subset of "served by". `acdp-rs` scopes registry-attested facts by serving vantage only (`revocation_cache.rs`).

The two readings diverge once a receipt travels with a body served from a different authority. `fed-009` already requires a federated resolver to preserve the upstream receipt verbatim. **Verdict: UNCERTAIN** whether any conformant path reaches the divergence today. The proposal is a clarification only.

### Proposed normative text

> *(0.5.0)* "Receipted by" means: the context carries a receipt whose `registry_did` is that registry and which verifies per RFC-ACDP-0010 §8 against that registry's authority. Where the serving authority and the receipting registry differ, either one brings the context into the default scope. A consumer that scopes by serving authority only is conformant but narrower, and SHOULD document that.

---

## Additional conformance vector: raw-JSON hashing of canonical whole-second timestamps

This is not a normative change, because RFC-ACDP-0001 §5.7 (L279) is already a MUST. It is a coverage gap.

`can-006` and `can-012` pin nanosecond and microsecond inputs. No vector pins a **canonical** millisecond timestamp whose fraction is `.000`.

A typed round-trip loses that spelling. `acdp-rs` 0.14.5 recomputes the hash from `serde_json::to_value(body)` (`crates/acdp-verify/src/lib.rs:96-99`). It types `expires_at` and `data_period.{start,end}` as `chrono::DateTime<Utc>`, and the default serde form re-emits `2026-12-31T23:59:59.000Z` as `2026-12-31T23:59:59Z`. That was reproduced locally with chrono 0.4. The result is a false `hash_mismatch` on a conformant body. It is fail-closed, so there is no trust hole, but it is an interop break.

**`can-013-canonical-zero-millis-timestamp`** (executed arithmetically): a body with `expires_at: "2026-12-31T23:59:59.000Z"` and `data_period: {"start": "2026-01-01T00:00:00.000Z", "end": "2026-12-31T23:59:59.000Z"}`, with its pinned canonical form and `sha256_hex`. Consumers MUST reproduce the hash.

## Compatibility

- **No wire, schema, body, hash, signature or receipt change.** All changes are consumer-side verdict semantics plus one SHOULD-level binding (P7). Every new MUST is marked *(0.5.0)* and binds only consumers claiming the 0.5.0 `acdp-consumer` profile. 0.1.0–0.4.0-pinned consumers are unaffected, following the RFC-ACDP-0014 §10 and RFC-ACDP-0016 precedent.
- **These are tightenings, not loosenings.** P1–P4 forbid an outcome (`not-revoked`) that some consumers emit today, and P5/P6 add reporting. Per the CHANGELOG precedent (2026-07-05 errata; RFC-ACDP-0007 §4.1), a Final-line tightening is not permitted, which is why everything here is *(0.5.0)*.
- **Availability.** P1–P3 turn some former `not-revoked` answers into `unknown`. Under a fail-closed discovery policy, verification of contexts from producers whose revocation discovery is unanswerable will fail where it previously passed. That is the intended safety property, and policy remains the deployment's choice (P1: "fail closed, or proceed and report"). P4 adds at most one extra DID fetch per failing verification, and implementations may rate-limit it.
- **Registries:** no new obligation.
- **Two-implementation gate:** the new vectors (`rev-005`, `rot-002`, `rcpt-005`, `lin-002`, `body-003`, `can-013`, the `rcpt-004`/`-006` extension) join the 0.5.0 consumer manifest and gate 0.5.0 Final alongside `anc-*`.

## Open questions

1. Should P7's SHOULD be a MUST for `supersedes: null` bodies, where the check is offline, total and free?
2. Should `unknown` (P1) get a suggested report token in the RFC-ACDP-0001 §5.11 stage vocabulary (e.g. `key_revocation: unknown`), with a reason sub-code (`truncated`, `unanswerable`, `transient`, `unverifiable_candidate`)?
3. P5: should a 0.5.0 strict default require a *current* receipt key for a pre-T placement under RFC-ACDP-0014 §7, rather than leaving it to deployment policy?
