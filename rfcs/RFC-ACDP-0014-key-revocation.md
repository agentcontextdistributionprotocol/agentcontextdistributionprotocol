# RFC-ACDP-0014
# Agent Context Distribution Protocol (ACDP) — Producer Key-Revocation Signal

**Document:** RFC-ACDP-0014
**Version:** 0.3.0-draft
**Status:** Community Standards Track (Draft)

This RFC specifies a **producer key-revocation signal**: a normative context type, `key-revocation`, through which a producer declares that one of its signing keys is compromised **as of a stated time** — and the consumer semantics that turn that declaration into a time-scoped verification boundary. It makes normative the "publish a 'this key is compromised' context as a soft signal" mitigation acknowledged as a gap since v0.1.0 (RFC-ACDP-0008 §5, §9.3), and integrates with RFC-ACDP-0010 §10 historical verification: receipt-attested publish times are what let a verifier separate contexts signed *before* the compromise (still historically authorized) from those signed *at or after* it (fail closed). It depends on RFC-ACDP-0001 (Core), RFC-ACDP-0002 (Context Body), RFC-ACDP-0003 (Publish), RFC-ACDP-0005 (Discovery), and RFC-ACDP-0010 (Registry Receipts); RFC-ACDP-0013 (Lifecycle Events) is its sibling — key compromise is a canonical reason to retract affected contexts.

**Revocation is a time-scoped statement; rotation is not revocation.** A clean rotation says "stop *accepting new* signatures from this key" (remove from `assertionMethod`, keep in `verificationMethod` — RFC-ACDP-0001 §5.11). A revocation says "signatures from this key are untrustworthy **from time T onward**". Removing the key from `verificationMethod` entirely remains the blunt total-kill signal that fails *everything* closed (RFC-ACDP-0001 §5.11, `rot-001` scenario C); this RFC provides the scalpel that preserves the pre-compromise history.

---

## 1. Status of This Memo

This document is a **Draft** ACDP specification targeting acdp/0.3.0. It follows the governance lifecycle in [governance/RFC-PROCESS.md](../governance/RFC-PROCESS.md) (Draft → Review → Final); per [VERSIONING.md](../VERSIONING.md) it is promoted to Final once the conformance fixtures it defines (`rev-001..002`) pass against at least two independent interoperating implementations.

This RFC promotes no RFC-ACDP-0009 reservation; it activates the soft-signal mitigation named in RFC-ACDP-0008 §5 ("No real-time key revocation push") and closes the time-scoping half of §9.3. Nothing in this document invalidates any v0.1.0/0.2.0 body, signature, `content_hash`, or receipt. The signal remains **pull-based**: real-time revocation *push* stays out of scope for the substrate (RFC-ACDP-0008 §5), and §8's discovery semantics are honest about what pull can and cannot guarantee.

---

## 2. Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described in BCP 14 ([RFC 2119], [RFC 8174]) when, and only when, they appear in all capitals.

| Term | Definition |
|---|---|
| **Revocation context** | An ACDP context of type `key-revocation` (§4): an ordinary signed, permanent, content-addressed body whose metadata declares a key compromised since a stated time. |
| **Revoked key** | The key identified by `metadata.revoked_key_fingerprint` (RFC-ACDP-0010 §6 encoding). |
| **Compromise boundary (T)** | `metadata.compromised_since`: the earliest instant at which the producer believes the key may have been under attacker control. Signatures made before T are attributable to the producer; at or after T, to the producer *or the attacker* — indistinguishably. |
| **Producer-signed revocation** | A revocation context signed by the producer's own current, non-revoked key (§5). The stronger trust class. |
| **Registry-attested revocation** | A revocation context published under the registry's identity on the producer's behalf after out-of-band verification (§6). The weaker trust class — the lost-everything fallback. |
| **Verified revocation** | A revocation context that passed the applicable §5/§6 verification, including the strict-profile body pipeline of RFC-ACDP-0001 §5.11. |

---

## 3. Motivation

ACDP v0.1.0 acknowledged two related gaps (RFC-ACDP-0008 §5, §9.3): no revocation mechanism, and no reliable answer to "was this key valid when this context was signed?". 0.2.0 closed the second half where receipts are deployed — the receipt's `key_fingerprint` plus `verificationMethod` retention yields *historically authorized (receipt-attested)* verification after clean rotation (RFC-ACDP-0010 §10). But 0.2.0's only compromise signal is total: removing the key from `verificationMethod` fails **every** context ever signed by it, including years of legitimate pre-compromise history (`rot-001` scenario C). Producers face a false choice: keep a compromised key verifiable, or destroy their own verifiable history.

The missing piece is **time scoping**. A compromise has a start. Before it, signatures are the producer's; after it, they are unattributable. What is needed is a producer-attributable, permanent, discoverable statement of that boundary — which is exactly what an ACDP context already is. This RFC therefore introduces no new wire object, endpoint, or signing construction: the revocation *is* a context — signed, content-addressed, permanent (a revocation that could be quietly deleted would be worthless), visibility-`public`, and discoverable through ordinary search. What is new is its normative shape (§4), its trust rules (§5–§6), and the consumer verification semantics it triggers (§7).

---

## 4. The `key-revocation` Context Type

`key-revocation` is registered as a standard context type in [`registries/context-types.md`](../registries/context-types.md) and added to the `context_type` vocabulary in `acdp-common.schema.json`. A revocation context is an ordinary body (RFC-ACDP-0002) with the following constraints:

| Field | Constraint |
|---|---|
| `type` | MUST be `key-revocation`. |
| `visibility` | MUST be `public`. A revocation is a safety broadcast; an audience-restricted revocation protects nobody outside the audience and MUST be rejected at publish (`schema_violation`). |
| `metadata.revoked_key_fingerprint` | REQUIRED. The fingerprint of the revoked public key, in the RFC-ACDP-0010 §6 encoding byte-for-byte (`"sha256:" + lowercase_hex(SHA-256(raw_public_key_bytes))`; raw 32-byte Ed25519 key or 33-byte SEC1-compressed P-256 point). Fingerprint form — not `key_id` — so the statement survives DID-document edits and matches what receipts record. |
| `metadata.compromised_since` | REQUIRED. The compromise boundary T: canonical millisecond-precision RFC 3339 UTC (RFC-ACDP-0001 §5.3). Producers SHOULD choose T conservatively early — every signature at or after T fails closed (§7); an optimistically late T is the one non-recoverable mistake. |
| `metadata.revoked_key_id` | OPTIONAL. The DID URL of the revoked verification method, for human traceability. The fingerprint is authoritative; on any disagreement the fingerprint governs. |
| `metadata.revoked_key_controller` | The producer DID that controls the revoked key. OPTIONAL on producer-signed revocations (defaults to `body.agent_id`; if present MUST equal it). REQUIRED on registry-attested revocations (§6), where `body.agent_id` is the registry. |
| `metadata.reason` | OPTIONAL. Human-readable circumstances (max 1024 characters). Informational only. |
| `supersedes` | A revocation context MAY be superseded only by another `key-revocation` context from the same signer class (e.g. to widen — never narrow — the compromise window by moving T earlier). Consumers MUST treat the earliest `compromised_since` across a revocation lineage as effective. |

Registries advertising `acdp_version` ≥ `0.3.0` MUST validate these constraints at publish time for bodies with `type: key-revocation` and reject violations with `schema_violation` (this is metadata whose shape is fixed by the type, uniformly enforceable per the `registries/context-types.md` admission rule). Pre-0.3.0 registries cannot: their `context_type` vocabulary predates the type (§10 gives the interim form).

Like every body, a revocation context is **permanent** — there is no un-revoking a key. A producer who published a mistaken revocation supersedes it with a corrected one; the mistake remains on the record, and consumers apply the earliest-T rule above (a supersession can therefore never quietly shrink a compromise window).

---

## 5. Producer-Signed Revocation (NORMATIVE)

The primary trust class. A producer-signed revocation context MUST satisfy, and consumers MUST verify, all of the following (on top of the strict body pipeline of RFC-ACDP-0001 §5.11):

1. **Signed by the producer.** `body.agent_id` is the producer's DID, and the body signature verifies under the resolved key per §5.11 — including the `assertionMethod` authorization check: the signing key MUST be **currently authorized** for the producer at verification time. (If the producer later rotates the revocation-signing key *cleanly*, the revocation remains verifiable via `verificationMethod` retention with the *historically authorized (receipt-attested)* rule of RFC-ACDP-0010 §10 — a receipt-attested historical authorization satisfies this step.)
2. **Not self-signed by the revoked key.** The RFC-ACDP-0010 §6 fingerprint of the resolved signing key MUST NOT equal `metadata.revoked_key_fingerprint`. A revocation signed by the very key it revokes proves only possession of that (by hypothesis, attacker-held) key; whoever holds it could mint or suppress such statements at will. Registries at `acdp_version` ≥ `0.3.0` MUST reject the publish with `key_not_authorized` (the key is not authorized *for this statement*); consumers encountering one anyway MUST treat it as **unverified** (it is at most a hint to seek a real signal).
3. **Controller binding.** `metadata.revoked_key_controller`, if present, equals `body.agent_id`. The revoked fingerprint SHOULD correspond to a key present in (or historically present in) the producer's DID document; consumers MUST NOT, however, require the revoked key to still be resolvable — §9.

A verified producer-signed revocation carries the producer's own authority: the same trust anchor as every ACDP body (RFC-ACDP-0008 §8). It is the class consumers act on without further judgment (§7).

**The remaining-key requirement is real.** Step 1 presupposes the producer still controls *some* non-revoked, currently-authorized key. Producers SHOULD provision for this day in advance — at minimum two independently stored signing keys, or a cold recovery key listed in `assertionMethod` (the two-tier pattern of RFC-ACDP-0001 Appendix B). `did:key` producers can never issue a producer-signed revocation for their own identity: the key *is* the identity; a compromised `did:key` producer abandons the identity, and only §6 or out-of-band channels can warn its consumers.

---

## 6. Registry-Attested Revocation (the lost-everything case, NORMATIVE)

Honesty requires naming the hard case: **a producer whose only authorized key is compromised cannot sign a trustworthy revocation at all.** The attacker holds everything the producer could sign with; any "revocation" the producer produces, the attacker could equally produce (or front-run with a revocation of the *replacement* key). Cryptography cannot distinguish the two parties at this point — recovery necessarily passes through an out-of-band, non-cryptographic identity check.

ACDP's fallback places that check with the registry, which already operates an authenticated relationship with the producer:

1. The producer (or its operator) convinces the registry operator out of band — by whatever deployment-policy evidence the registry demands (organizational identity, DNS control of the `did:web` authority, contractual channels). The bar for this evidence is registry policy, not protocol.
2. The registry publishes a `key-revocation` context **under its own identity**: `body.agent_id` = the registry's DID (`capabilities.registry_did`), signed per RFC-ACDP-0003 like any publish — a registry advertising `acdp-registry-receipts` SHOULD sign with its receipt signing key (which RFC-ACDP-0010 §9 already requires to be in its `assertionMethod`; no new key role, the RFC-ACDP-0011/0013 precedent). `metadata.revoked_key_controller` (REQUIRED here) names the affected producer DID.
3. Consumers verify it as an ordinary body published by the registry, then classify it as **registry-attested**: a distinct, weaker trust class that MUST be reported distinguishably from producer-signed (§7).

**Why weaker — spelled out.** A producer-signed revocation is backed by the producer's own key: trusting it adds no new trusted party. A registry-attested revocation is backed by (a) the registry's honesty and (b) the quality of its out-of-band check — a hostile or deceived registry can fabricate one, and a fabricated revocation is a targeted denial-of-service against the producer's post-T history. Consumers MUST therefore treat the two classes differently: act on producer-signed revocations unconditionally (§7); for registry-attested ones, the strict profile default is to apply §7 for contexts *served by or receipted by that same registry* (which the registry could already withhold — no new trust is granted), and SHOULD seek producer-side or out-of-band corroboration before applying it globally. Deployments MAY configure stricter or looser policy; the classification itself MUST NOT be collapsed.

---

## 7. Consumer Semantics (NORMATIVE)

When a consumer holds a **verified revocation** for fingerprint **F** with compromise boundary **T**, and verifies a context whose body signature resolves to a key with fingerprint F:

1. **Establish the publish time — verifiably.** The only publish time this RFC accepts is a **receipt-attested** one: `created_at` from a registry receipt verified per RFC-ACDP-0010 §8 (whose step 5 also confirms the receipt attests F itself). The body's bare `created_at` is registry-assigned, unsigned-by-producer, and unverifiable without a receipt (RFC-ACDP-0008 §9.1) — it MUST NOT be used as the boundary input.
2. **Before T:** receipt-attested `created_at` **strictly earlier than** T → the context was published while the key was still the producer's. Verification proceeds under the RFC-ACDP-0010 §10 historical rule and, on success, MUST be reported with the distinguishable status **historically authorized (pre-compromise, receipt-attested)**.
3. **At or after T — fail closed.** Receipt-attested `created_at` equal to or later than T → the signature is not attributable to the producer. Verification MUST fail under the strict profile (RFC-ACDP-0001 §5.11 / §9.2 `StrictV010` and successors), regardless of `assertionMethod`/`verificationMethod` state and regardless of any valid receipt — the receipt proves *when the registry accepted it*, which is precisely what places it in the compromise window.
4. **Publish time unverifiable — fail closed.** No receipt, or a receipt that fails RFC-ACDP-0010 §8 → the context cannot be placed relative to T, and a revoked key's signature without a provable time is exactly the artifact an attacker can mint freely (and backdate at will — bare `created_at` is attacker-influenceable via a colluding registry). The strict profile MUST fail closed. A deployment MAY expose a non-default, explicitly-named pragmatic mode that accepts other time evidence (external transparency-log inclusion, archived receipts); such a mode is **non-conformant with the strict profile** and MUST follow the RFC-ACDP-0001 §5.11 opt-in rules.

The resulting rotated-key verification landscape, completing RFC-ACDP-0008 §7.3 / `rot-001`:

| Scenario | Key state | Revocation | Receipt | Verdict |
|---|---|---|---|---|
| **Rotated clean** | in `verificationMethod`, not `assertionMethod` | none | verified, attests F | historically authorized (receipt-attested) — RFC-ACDP-0010 §10 |
| **Rotated clean, no receipt** | same | none | none | fail closed (strict) — `rot-001` B, unchanged |
| **Compromised, before T** | in `verificationMethod` | verified, boundary T | verified, `created_at` < T | **historically authorized (pre-compromise, receipt-attested)** |
| **Compromised, at/after T** | any | verified, boundary T | any | **fail closed** |
| **Compromised, time unverifiable** | any | verified, boundary T | none / failing | **fail closed** (strict) |
| **Total kill** | removed from `verificationMethod` | n/a | any | fail closed — RFC-ACDP-0001 §5.11, `rot-001` C, unchanged |

Consumers SHOULD cache verified revocations indefinitely (the statement is permanent) and MUST apply the earliest-T rule of §4 across a revocation lineage. Verification reports SHOULD carry the revocation check as its own stage (suggested stage identifier: `key_revocation`, extending the RFC-ACDP-0001 §5.11 stage vocabulary) with the trust class (producer-signed / registry-attested) recorded.

---

## 8. Discovery (NORMATIVE, and honest)

- Consumers SHOULD check for revocations before relying on a context from a rotated or unfamiliar key — and at minimum whenever verification encounters a key outside `assertionMethod` — via ordinary search (RFC-ACDP-0005): `GET /contexts/search?type=key-revocation&agent_id=<producer-did>` on the registries serving that producer's contexts (for registry-attested revocations, additionally `type=key-revocation` with the registry's own `agent_id`, matching `metadata.revoked_key_controller` client-side). Revocation contexts are `public` (§4), so they are visible to any requester the registry serves at all.
- **The honest caveat:** search is served by the registry, and **a malicious registry can hide a revocation** exactly as it can hide any context — absence of search results is *not* evidence of absence (RFC-ACDP-0010 §13: a receipt proves what was published, not what wasn't). A registry colluding with a key thief can simultaneously serve the stolen key's contexts and suppress the revocation. Within the protocol, the mitigation is the append-only transparency log reserved as RFC-ACDP-0009 §2.11 — a suppressed-yet-logged revocation becomes auditor-detectable; until it ships, consumers SHOULD query more than one vantage (the producer's other registries, a federated resolver) where the stakes warrant it.
- Consumers MAY accept revocations **out of band** — handed over by the producer directly, mirrored in an external log, or embedded in deployment configuration. A revocation context is self-contained (signed, content-addressed); it verifies identically wherever it came from, and out-of-band delivery is precisely the channel a registry cannot suppress.
- Producers SHOULD publish the revocation on **every** registry where contexts signed by the revoked key live, SHOULD retract (RFC-ACDP-0013) contexts known to be attacker-published in the compromise window, and SHOULD reference the revocation context from those retractions' `reason`.

---

## 9. DID-Document Interaction (NORMATIVE)

- **Revocation does NOT require removing the revoked key from `verificationMethod`** — and producers SHOULD NOT remove it. Historical verification of the pre-T record *needs* the key material resolvable (RFC-ACDP-0010 §9/§10); the revocation plus receipts is what makes retaining it safe: everything at/after T fails closed anyway (§7). Removal from `verificationMethod` remains the total-kill signal and now carries an explicit meaning: *no* signature by this key is trustworthy, **at any time** — appropriate when the compromise window cannot be bounded at all.
- **Rotation is not revocation.** Removing a key from `assertionMethod` (clean rotation) makes no compromise claim, triggers none of §7, and leaves history in the RFC-ACDP-0010 §10 regime. Consumers MUST NOT infer compromise from rotation.
- The revoked key's `assertionMethod` membership becomes irrelevant to §7 — the boundary rule supersedes it for that fingerprint. Producers SHOULD nonetheless remove the revoked key from `assertionMethod` promptly (belt and braces: pre-0.3.0 registries keep rejecting new publishes under it).

---

## 10. Capabilities, Profile, Errors, and Compatibility

- **No new profile — deliberately.** A profile advertises a *server* capability surface; a revocation is carried entirely by surfaces that already exist: publish (`acdp-registry-core`), search (`acdp-registry-discovery`), receipts (`acdp-registry-receipts`) for the §7 time anchor. There is no endpoint to advertise, no degraded mode to forbid, and a registry cannot meaningfully "not support" a context type. The obligations land where the behavior lives instead: the §4 publish-time validation binds to `acdp_version` ≥ `0.3.0`, and the §7 consumer semantics bind to the `acdp-consumer` profile at 0.3.0 (fixtures `rev-001`/`rev-002`; a 0.1.0/0.2.0-pinned consumer is unaffected). Contrast RFC-ACDP-0013, whose endpoints and status derivation are a genuine optional server surface and get `acdp-registry-lifecycle`.
- **No new wire error code.** Publish-side rejections reuse `schema_violation` (§4 shape) and `key_not_authorized` (§5 step 2). Consumer-side, a §7 fail-closed is a *verification verdict*, not a wire condition — SDKs surface it via the `key_revocation` stage/status (§7), not an error envelope.
- **Schema.** `acdp-common.schema.json#/$defs/context_type` gains `key-revocation` in the standard enum (additive, `v0.1.0` namespace per VERSIONING.md). No other schema changes: the metadata constraints of §4 are type-conditional semantics (like DataRef invariants), normative in prose and pinned by fixture.
- **Interim form on pre-0.3.0 registries.** A pre-0.3.0 registry's `context_type` vocabulary rejects the bare `key-revocation` (standard values are a closed enum in v0.1.0 schemas). Producers needing to signal on such registries SHOULD publish the identical §4 metadata under the custom type **`acdp:key-revocation`** (valid under the v0.1.0 namespaced-type pattern); 0.3.0 consumers MUST treat `acdp:key-revocation` as equivalent to `key-revocation` when it satisfies §4–§5. New publications on 0.3.0 registries MUST use the standard form.
- **Compatibility.** Nothing changes for existing bodies, signatures, hashes, or receipts. Pre-0.3.0 consumers ignore revocation contexts (they are ordinary contexts of an unknown type) and keep v0.1.0/0.2.0 verification behavior — the same honest upgrade posture as RFC-ACDP-0013 §9: the protection binds when the consumer upgrades.

---

## 11. Scope and Limitations (honest scope)

- **T is the producer's claim.** Nothing proves the compromise actually began at `compromised_since`; a producer can (deliberately or through poor forensics) choose T to disown inconvenient signatures made while the key was still theirs. The receipt-attested publish time is cryptographic; the boundary it is compared against is testimony. Disputes about T are a governance matter, outside the protocol.
- **A revocation reaches only consumers who look** (§8). No push, no propagation guarantee, no revocation-freshness proof. The window between compromise and consumer awareness is bounded by consumer polling policy, not by this RFC.
- **The lost-everything fallback imports registry trust** (§6) — stated plainly rather than hidden: where the producer has no key left, *someone* must vouch out of band, and ACDP names the registry as that someone with a distinct, weaker trust class.
- **Fail-closed has a cost.** §7 step 4 renders receipt-less post-rotation contexts signed by a revoked key unverifiable even if honestly published pre-compromise. This is the correct default (the alternative accepts attacker-mintable artifacts) but it makes receipts (RFC-ACDP-0010) the effective prerequisite for compromise-surviving history — an explicit design pressure, not an accident.

---

## 12. Conformance Fixtures

| ID | What it pins | Runner |
|---|---|---|
| `rev-001-revocation-context-golden` | Full golden vector: a producer-signed `key-revocation` body (revoking the `sig-001` key K1, fingerprint from `rot-001`/`fp-001`) signed by the current key K2 (the `sig-003` test seed, matching `rot-001`'s K2) — canonical form, `content_hash`, Ed25519 signature, §5 constraints (signer ≠ revoked fingerprint, `public` visibility, §4 metadata shape). | Executed arithmetically |
| `rev-002-before-after-boundary` | §7 boundary semantics against the `rot-001` scenario set: receipt-attested `created_at` before T → *historically authorized (pre-compromise, receipt-attested)*; at/after T → fail closed despite valid receipt; no receipt → fail closed under strict; classification of producer-signed vs registry-attested trust classes. | Behavioral |

---

## 13. Security Considerations

- **Revocation as a weapon.** A forged or coerced revocation is a targeted DoS on a producer's post-T history. Defenses: §5's current-key + not-self-signed rules (an attacker holding only the compromised key cannot mint a producer-signed revocation of anything), §6's explicit weaker classification for registry-attested claims, and the earliest-T monotonicity of §4 (an attacker who *does* obtain a current key can widen but never quietly shrink a window — and widening is loud: it is a signed public context).
- **Front-running.** An attacker holding the producer's only key may revoke the producer's *new* key the moment it appears. This is the lost-everything case (§6) in another costume; the resolution is out-of-band identity, not more signatures. Producers with a provisioned second key (§5) never enter this race.
- **Registry collusion** suppresses discovery (§8) and can backdate receipts at mint time (RFC-ACDP-0010 §13), which under §7 could smuggle an attacker context under the boundary. The backdating risk existed before this RFC (it defeats §10 historical verification generally); the reserved transparency log (RFC-ACDP-0009 §2.11) is the systemic answer, and consumers SHOULD persist receipts and revocations as comparison evidence meanwhile.
- **Clock discipline.** T and receipt `created_at` are compared directly; both are canonical millisecond UTC (RFC-ACDP-0001 §5.3). Producers choosing T SHOULD subtract their full forensic uncertainty *plus* clock-skew margin.
- Revocation contexts are `public` and search-indexed: the RFC-ACDP-0005 injection and the RFC-ACDP-0007 §6 output-hygiene rules apply to `metadata.reason` as to any indexed producer text.

---

## 14. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md) — §5.3 (time), §5.11 (key resolution, retention, total-kill removal, stage vocabulary), Appendix B (two-tier identity).
- [RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md) — body shape, metadata limits, context types (§5).
- [RFC-ACDP-0003 Publish](RFC-ACDP-0003-publish.md)
- [RFC-ACDP-0005 Discovery](RFC-ACDP-0005-discovery.md) — the §8 search surface.
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md) — §5 (the acknowledged gap this RFC closes), §7.3, §9.3.
- [RFC-ACDP-0009 Extensions](RFC-ACDP-0009-extensions.md) — §2.11 (transparency log: the discovery-suppression mitigation).
- [RFC-ACDP-0010 Registry Receipts](RFC-ACDP-0010-registry-receipts.md) — §6 (fingerprint encoding), §8 (receipt verification), §10 (historical verification this RFC time-scopes).
- [RFC-ACDP-0013 Lifecycle Events & Retraction](RFC-ACDP-0013-lifecycle-events.md) — retraction of attacker-window contexts.
- Fixtures: [`rot-001-historical-key-receipt.json`](../schemas/conformance/rot-001-historical-key-receipt.json) (the scenario set §7 completes), [`fp-001-key-fingerprint-vectors.json`](../schemas/conformance/fp-001-key-fingerprint-vectors.json).
- [RFC 8032] Josefsson, S. and I. Liusvaara, "Edwards-Curve Digital Signature Algorithm (EdDSA)", RFC 8032, January 2017.
- [RFC 8785] Rundgren, A., Jordan, B., and S. Erdtman, "JSON Canonicalization Scheme (JCS)", RFC 8785, June 2020.
