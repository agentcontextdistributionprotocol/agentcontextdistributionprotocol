# DECISIONS.md

Durable record of `/reconcile` decisions on `ASSUMPTIONS.md` entries. One entry per assumption, dated. `/ship` and any later reconciliation read this file instead of replaying the conversation that produced it.

---

## 2026-09-21 — Plan: open-issues-2026-09

### Phase 1 — `invalid_witness_cosignature` erratum classification

- **Assumption:** An already-shipped error code's registry-table row can be restored/corrected via a CHANGELOG erratum entry without a version bump.
- **Analysis (Opus):** CONFIRMED. `registries/error-codes.md:132` already reads `Stable` and has since commit `d56c1f5`, predating this plan — correct per `registries/README.md`'s two-interoperating-implementations bar (RFC-ACDP-0015 promoted Final/0.4.0 on 2026-08-28 after `acdp-rs` and `acdp-verifier-py` both ran `wit-001..004`). The actual Phase-1 change (commit `108ff76`) restored a row missing from RFC-ACDP-0007 §5's table and added a `*(0.4.0)*` graduation sentence — it never touched `error-codes.md`'s Status cell. Zero implementation-behavior change, consistent with the CHANGELOG entry's own claim.
- **Decided by:** Opus (auto-settled, low blast radius).
- **Status:** CONFIRMED (2026-09-21).

### Phase 1 — RFC §5 Meaning cell condensed

- **Assumption:** A registry table's prose "Meaning" cell can be condensed for readability without dropping any MUST/SHOULD/MAY condition.
- **Analysis (Opus):** CONFIRMED. Diff at commit `108ff76`, `rfcs/RFC-ACDP-0007-capabilities.md:281` (`invalid_witness_cosignature` row) preserves all five enumerated §8 failure modes, the not-`invalid_log_proof` distinction and its rationale, the 502-upstream-fault rationale, and both carve-outs verbatim/near-verbatim against `registries/error-codes.md:132`. What was dropped (the version-gate sentence, the fixture pointer, two rhetorical asides) was relocated to the trailing blockquote (line 289) or was non-normative rhetoric — consistent with every other version-marked row in the same table, none of which repeats the gate sentence in-cell.
- **Decided by:** Opus (auto-settled, low blast radius).
- **Status:** CONFIRMED (2026-09-21).

### Phase 2 — 415 scoped to body-bearing methods, 405 out of scope

- **Assumption:** `unsupported_media_type` (415) applies only to body-bearing requests; method-not-allowed (405) is a separate, out-of-scope concern.
- **Analysis (Opus):** CONFIRMED. RFC-ACDP-0007-capabilities.md §4.1 lines 219-245 write the scoping directly into normative text (body-bearing gate at line 223, explicit GET/body-less exclusion at line 243, explicit 405-out-of-scope paragraph with its own reasoning at line 245). Fixture `err-002-unsupported-media-type.json` matches: `input.endpoint` is `POST /contexts` only, and its `notes` field states the same exclusions.
- **Decided by:** Opus (auto-settled, low blast radius).
- **Status:** CONFIRMED (2026-09-21).

### Phase 3 — RFC-ACDP-0002 §6.6 NORMATIVE scoping paragraph

- **Assumption:** RFC-ACDP-0002 §6.6's existing prose was ambiguous about whether a validation check was mandatory in all cases; the fix (a new `(NORMATIVE)` scoping paragraph) is a loosening, not a tightening, so it's safe unmarked on the Final line.
- **Analysis (Opus):** CONFIRMED. The new paragraph (`rfcs/RFC-ACDP-0002-context-body.md:296`) has three normative arms, all checked individually: (1) "check 8 does not require verifying a root `content_hash` at publish" removes an obligation that §6.1 never actually stated (the ambiguity was referential, not a walked-back MUST); (2) "a registry MAY additionally verify... and reject" is a new permission, tightens nothing; (3) "MUST NOT reject a publish merely because both fields are present" forecloses a rejection, narrowing only a registry's grounds to reject — the same "forbids a rejection rather than adding one" pattern the repo already treats as permitted Final-line loosening (precedent cited in `CHANGELOG.md:80`, the 2026-07-05 errata). No arm adds a producer obligation or narrows a consumer/registry right. Fixture `data-ref-007` and cross-references in RFC-ACDP-0007 §5 / `registries/error-codes.md` are mutually consistent with the scoping. `make validate` green at branch tip (165/165 JSON, 53/53 arithmetic, 146 fixtures, consistency clean).
- **Decided by:** Opus (auto-settled, low blast radius — confirmed genuinely a loosening, not escalated).
- **Status:** CONFIRMED (2026-09-21).

### Phase 2 — "either" outcome vocabulary in err-002

- **Assumption:** A conformance fixture may express "the registry MAY do either A or B" via an `"outcome": "either"` field when the spec genuinely leaves the choice to registry discretion.
- **Analysis (Opus):** CONFIRMED. `err-002` scenarios D/E use `"outcome": "either"` with explicit prose that a harness MUST NOT assert one outcome — internally coherent and justified against RFC-ACDP-0007 §4.1. Two prior discretionary-outcome precedents already exist in the corpus (`tolerated_outcomes`, `alternative_error_code`), but both express a different axis of discretion (which concrete shape, given a path is already chosen) than err-002's axis (whether to reject at all) — so this isn't redundant invention. No script chokes on it (`err-*` is behavioral, not executed by the runner; `check-consistency.py` doesn't validate `outcome` contents). Fixture correctly wired in all three required places.
- **Note (non-blocking):** `schemas/conformance/README.md`'s Fixture Format vocabulary list (lines 85-88) doesn't mention `"either"` or `alternative_error_code` — a documentation nicety, not a defect, left as optional future cleanup.
- **Decided by:** Opus (auto-settled, low blast radius).
- **Status:** CONFIRMED (2026-09-21).

### Finalization — new `rev-004` fixture for retrieval-continuity half of §10's interim-form retirement

- **Assumption:** §10's interim-form retirement rule has two independent obligation axes — (1) rejecting NEW publications under the interim form at >=0.5.0 (covered by `rev-003` Q), and (2) continuing to serve already-published interim-form bodies unfiltered (retrieval-continuity) — different enough in request shape and obligation direction to warrant a separate fixture file rather than extending `rev-003`.
- **Analysis (Opus):** CONFIRMED, independently re-derived from scratch (fourth review of this specific question, after finalization verifier rounds 1-3). `rev-003` Q is `POST /contexts` expecting rejection (`schema_violation`); `rev-004`'s three scenarios are `GET` (direct retrieval, search, lineage walk) against a pre-existing interim-typed body, all expecting unfiltered `success` — genuinely different obligation direction and HTTP method, not redundant. Three-file wiring confirmed present and correct (`registries/profiles.json:152-156`, `profiles.md:333,335`, `README.md:333`); `python3 scripts/check-consistency.py` passes at 146 fixtures; `conformance-runner.py` passes cleanly. Scenario B's `applies_when` discovery-profile conditionality verified verbatim against `profiles.json:159-161`'s `not_implemented_permitted_on` allowance. Noted and verified as non-contradictory: Phase 7's own entry rejected a new sibling file for O-R (same `POST` publish shape as A-N); this is a different scenario set with a different request shape, so the earlier decision isn't being silently reopened — confirmed by inspecting the actual fixture content.
- **Decided by:** Opus (auto-settled, low blast radius — fixture organizational choice, confirmed sound on independent re-derivation).
- **Status:** CONFIRMED (2026-09-21).

---

## Pending

### Phase 2 — `unsupported_media_type` lands on the 0.5.0 Draft line

- **Assumption:** A new wire error code cannot ride a Final line; 0.5.0 Draft is the correct vehicle. Minted `unsupported_media_type` (415, Provisional) gated `>= 0.5.0`, amended `VERSIONING.md`, added fixture `err-002` to the 0.5.0 promotion gate.
- **Analysis (Fable):** Confirm as-is. The name and semantic are already a de facto commitment regardless of Draft/Final status — `acdp-registry-rs` shipped the code in released crate `acdp-registry-server/v0.1.3` one day *before* the spec minted it, and `acdp-rs` typed it as a public enum variant in `acdp-primitives v0.13.2` (removing a `#[non_exhaustive]` variant is itself treated as breaking by that repo's own decision record). Every rejected alternative (Reserved-table, a 0.6.0 line) would now actively forbid behavior that's already shipping. The one known emitter (`acdp-registry-rs`) has advertised `acdp_version` unconditionally `0.5.0` since 2026-08-29 — two weeks before this code was minted — so the "ahead of its declared version" framing in the original CHANGELOG entry was factually wrong at the time it was written.
- **Follow-ups applied:** (1) Corrected `CHANGELOG.md`'s "Transitional emitters" bullet, which falsely claimed an implementation emits the code while advertising `< 0.5.0` — none does. (2) Closed [acdp-registry-rs#333](https://github.com/agentcontextdistributionprotocol/acdp-registry-rs/issues/333) as already-resolved — the registry chose "advertise 0.5.0" three weeks before the issue asked it to choose.
- **Decided by:** User (confirmed as-is, 2026-09-21).
- **Status:** CONFIRMED (2026-09-21).

### Phase 4 — `dk-001`/`dk-002` partial revocation of tolerated alternative

- **Assumption:** `dk-002`'s unscoped carve-out tolerating `schema_violation` for case 3 (bad multicodec prefix) was itself a fixture bug, since RFC-ACDP-0001 §5.11.1 step 3 already required `key_resolution_failed` for that case. Narrowed the carve-out to exclude case 3.
- **Analysis (Opus, then escalated to Fable):** Opus found real, non-hypothetical impact — `acdp-registry-rs` is pinned via `.spec-pin` to the exact commit that narrowed this, and its conformance test (`tests/conformance.rs:12880-13027`) justifies passing by quoting the now-removed carve-out text. Escalated to Fable given the concrete impact. Fable: confirm the tightening as-is — the affected registry's own SDK dependency (`acdp-rs`) already classifies this case correctly in its resolver (`acdp-did/src/key.rs`); a validation wrapper just relabels the error, and the registry's own maintainer filed the ambiguity as spec issue #62 ("your call") before the spec answered it. The pinned test is stale in the *opposite* direction too (its `dk-004` gap note is now a sanctioned pass, not a gap) and needs editing regardless of which way this decision went; restoring the carve-out would have saved no actual work.
- **Follow-ups applied:** (1) Filed [acdp-registry-rs#334](https://github.com/agentcontextdistributionprotocol/acdp-registry-rs/issues/334) — the pinned test is stale in both directions and doesn't structurally read the fixtures' expected-outcome fields. (2) Commented on [acdp-rs#285](https://github.com/agentcontextdistributionprotocol/acdp-rs/issues/285#issuecomment-5770007360) noting `dk-002` case 3 is in scope of that issue's fix, alongside `dk-001`. (3) Added a sentence to `CHANGELOG.md` naming the affected implementation and both tracking issues.
- **Decided by:** User (confirmed as-is, 2026-09-21).
- **Status:** CONFIRMED (2026-09-21).

### Phase 5 + Finalization §7 — anti-disarm rule binds at 0.3.0, Final-line

- **Assumption (Phase 5):** The anti-disarm rule ("a superseding context that is not itself a revocation must be disregarded for revocation-effectiveness") is a clarification of an existing 0.3.0 obligation, not a new one, so it's unmarked/Final rather than `*(0.5.0)*`-gated.
- **Assumption (Finalization §7):** Broadening "a revocation" to include the §10 interim form is likewise unmarked/Final, grounded in §10's pre-existing equivalence rule.
- **Analysis (Fable, on Phase 5):** Confirm as-is. §4's pre-existing, unmarked Final permanence paragraph already said "a supersession can therefore never quietly shrink a compromise window" — full disarming is the zero-limit case of that. The only two implementers who read the original text independently concluded the same thing and filed bugs against their *own* code for not doing it (acdp-rs issue #61 and #226) — neither read it as permitting disarm. The repo has made this exact kind of retroactive security fix at least three times before (RFC-ACDP-0006 §4.1, RFC-ACDP-0004 §2.1, the 2026-05-21 SSRF errata). No currently-shipped implementation is actually broken: `acdp-rs`'s lineage-walk already folds correctly; `acdp-verifier-py` hasn't run these scenarios yet; both registries already reject the attack at the source.
- **Analysis (Opus, independent 4th review, on Finalization §7):** Confirmed independently from scratch. §10's equivalence sentence ("0.3.0 consumers MUST treat `acdp:key-revocation` as equivalent to `key-revocation` when it satisfies §4–§5") is real, unmarked, Final, and unqualified — nothing in its text restricts it to a narrower use than the §7 disarm-clause comparison, and §4's own `*(0.5.0)*` predecessor-keyed rule already independently relies on the identical definition for a parallel registry-side check.
- **Follow-ups applied:** (1) Corrected the RFC's self-justification in §1 and §7 — the anti-disarm rule itself is now grounded in §4's permanence paragraph (not §10, which only grounds the interim-form extension specifically). (2) Retitled the CHANGELOG heading from "clarification" to "erratum," matching house style for this class of fix (`RFC-ACDP-0006`, `RFC-ACDP-0004`, `RFC-ACDP-0014 §13` precedents), and added the honest admission that a literal-reading consumer was never actually conformant with §4/§10 — mirroring the `dk-002` entry's own precedent ("'the fixture said otherwise' is exactly the defence an implementer would reasonably raise").
- **Decided by:** User (confirmed as-is, 2026-09-21).
- **Status:** CONFIRMED (2026-09-21).
