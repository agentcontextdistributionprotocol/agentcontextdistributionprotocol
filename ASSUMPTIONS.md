# Assumptions

Decisions taken during implementation where something was ambiguous but a clearly-best option
existed. Each is `UNCONFIRMED` until reconciled (`/reconcile`). Entries are tagged with the plan
they belong to, so a reconcile pass can scope itself to one feature.

Plan names are working titles, not paths: this repo gitignores `plans/`, so the planning documents
these entries reference are local to the authoring workspace and deliberately absent from the
published tree. Each entry below is written to stand on its own without them.

---

## Phase 1 — `invalid_witness_cosignature` treated as a 0.4.0 erratum

- **Plan:** open-issues-2026-09 (local planning doc; `plans/` is gitignored and not part of the published tree)
- **Assumed:** Restoring the missing RFC-ACDP-0007 §5 row is documentation catching up to
  shipped reality, not a new normative addition.
- **Chose:** A `## v0.4.0 — erratum …` CHANGELOG heading. The code, its HTTP status (502), and
  its version gate were already live in `registries/error-codes.md:30` and the wire enum; only
  the RFC table — which `RFC-ACDP-0015` §10 already *claimed* contained it — was missing. No
  implementation behavior changes, so this is not an addition under `VERSIONING.md:30`.
- **Alternatives:** Treating it as a 0.5.0 addition (wrong — it would imply implementations may
  only emit the code from 0.5.0, contradicting the shipped 0.4.0 gate).
- **Blast radius if wrong:** A CHANGELOG heading under the wrong version line. Cosmetic;
  one-line fix.
- **Status:** CONFIRMED (2026-09-21) — see `DECISIONS.md`

## Phase 1 — RFC §5 Meaning cell condensed rather than copied verbatim

- **Plan:** open-issues-2026-09 (local planning doc; `plans/` is gitignored and not part of the published tree)
- **Assumed:** RFC-ACDP-0007 §5's table is a summary surface; `registries/error-codes.md`
  remains authoritative on detail.
- **Chose:** Condensed the Meaning cell from `error-codes.md:30`, preserving all five §8 failure
  modes, the "not `invalid_log_proof`" distinction, the 502-because-upstream rationale, and both
  carve-outs — while dropping the `MUST NOT be emitted … < 0.4.0` sentence (it lives in the §5
  blockquote for every other version-marked code) and the `Fixture wit-004` pointer (the RFC
  table never cites fixtures). This matches how `invalid_log_proof` *(0.3.0)* is handled at
  `RFC-ACDP-0007:247`.
- **Alternatives:** Copying the registry cell verbatim — would have duplicated the version-gate
  sentence that the blockquote already carries, and introduced a fixture citation the table has
  no precedent for.
- **Blast radius if wrong:** Prose-only; the three-way guard compares code *names*, not cell text.
- **Status:** CONFIRMED (2026-09-21) — see `DECISIONS.md`

## Phase 2 — `unsupported_media_type` lands on the 0.5.0 Draft line

- **Plan:** open-issues-2026-09 (local planning doc; `plans/` is gitignored and not part of the published tree)
- **Assumed:** A new wire error code is a backward-compatible addition (`VERSIONING.md`), so it
  cannot ride a Final line, and 0.5.0 — `Draft`, i.e. "open for substantive change" — is the
  correct vehicle.
- **Chose:** Mint it on 0.5.0, `Provisional`, gated `MUST NOT be emitted … < 0.5.0`. Amended
  `VERSIONING.md`'s 0.5.0 scope paragraph, which previously claimed the line adds no new error
  code, and added `err-002` to that line's promotion gate.
- **Alternatives:** (a) reserve it in the "Reserved future codes" table — rejected as worse than
  the status quo, since that table's "MUST NOT emit" rule would turn already-shipping
  implementation behavior from *unspecified* into *forbidden*; (b) a dedicated 0.6.0 line —
  no precedent, and doubles the two-implementation promotion gate; (c) reuse `schema_violation`
  with a `details` key — rejected on the project's own anti-overloading rule.
- **Blast radius if wrong:** Minting a wire code is effectively irreversible once emitted. But
  the *choice of line* is not: nothing in a Draft line has shipped, so re-splitting to a later
  line before 0.5.0 promotion is cheap.
- **Status:** CONFIRMED (2026-09-21) — see `DECISIONS.md`

## Phase 2 — 415 scoped to body-bearing methods; 405 explicitly out of scope

- **Plan:** open-issues-2026-09 (local planning doc; `plans/` is gitignored and not part of the published tree)
- **Assumed:** A request media type only exists where there is a request body, and minting 415
  should not open a general transport-4xx category.
- **Chose:** Scoped §4.1 to body-bearing methods (GET explicitly excluded) and ruled 405 out of
  scope **in the RFC prose**, on the principle that ACDP governs the media type (it has a
  media-types registry, an IANA request, and normative acceptance prose) but registers no method
  vocabulary. Stated explicitly so the boundary is not re-litigated per-implementation.
- **Alternatives:** Silence on 405 — would leave the same ambiguity one layer over; minting 405
  too — no registry, no rule to violate, pure scope creep.
- **Blast radius if wrong:** If 405 is later wanted, this paragraph must be revised — prose-only.
- **Status:** CONFIRMED (2026-09-21) — see `DECISIONS.md`

## Phase 2 — `"outcome": "either"` for registry-latitude scenarios in `err-002`

- **Plan:** open-issues-2026-09 (local planning doc; `plans/` is gitignored and not part of the published tree)
- **Assumed:** Scenarios D (`application/json`) and E (absent `Content-Type`) pin *latitude*, not
  behavior — both outcomes are conformant — and a fixture must say so machine-readably or it
  will be misread as "reject everything that is not `application/acdp+json`".
- **Chose:** `"outcome": "either"` plus a `behavior` string stating both arms are conformant.
- **Alternatives:** `pub-008`'s `alternative_error_code` idiom (models a *preferred* code with a
  tolerated second — wrong here, since neither arm is preferred and one arm is success, not an
  error); `idem-006`'s `tolerated_outcomes` profile wiring (wrong granularity — it marks a whole
  fixture tolerated, not two of five scenarios).
- **Blast radius if wrong:** If `"either"` is judged a novel vocabulary the repo should not grow,
  the fix is fixture-local — split D/E into their own fixture, or re-express as prose-only
  scenarios. No wire or schema impact; conformance fixtures are syntax-checked only.
- **Status:** CONFIRMED (2026-09-21) — see `DECISIONS.md`

## Phase 3 — RFC-ACDP-0002 §6.6 gains a NORMATIVE scoping paragraph on a Final line

- **Plan:** open-issues-2026-09 (local planning doc; `plans/` is gitignored and not part of the published tree)
- **Assumed:** Naming each site precisely exposed a question the vaguer wording had hidden — what a
  registry does with a DataRef-root `content_hash` on an *embedded* DataRef — and leaving it open
  was worse than answering it, because the same phase adds an example of exactly that shape.
- **Chose:** A NORMATIVE paragraph scoping check 8 to `embedded.content_hash`: no publish-time
  obligation for the root field, a MAY to verify it anyway, and a MUST NOT reject merely because
  both are present. Every arm either removes an obligation or forbids a rejection, so it is a
  Final-line loosening, which the plan's governing principle permits.
- **Alternatives:** Silence (leaves an implementer to guess, and the new example makes the question
  unavoidable); a MUST to verify the root field (a new registry obligation on a Final line —
  forbidden outright).
- **Blast radius if wrong:** The MAY arm blesses an A-accepts/B-rejects divergence, but only for
  bodies already self-inconsistent under §6.1 (root and embedded hashes disagreeing over the same
  decoded bytes). No honest producer is caught. Reversible as prose.
- **Status:** CONFIRMED (2026-09-21) — see `DECISIONS.md`

## Phase 4 — `dk-001` keeps no tolerated alternative

- **Plan:** open-issues-2026-09 (local planning doc; `plans/` is gitignored and not part of the published tree)
- **Assumed:** A fixture that accepts any rejection stops verifying the thing it exists to verify.
- **Chose:** `dk-002` (cases 1-2) and `dk-004` gain `alternative_error_code`; `dk-001` does not. The
  discriminator is what the fault is *about* — steps 1-2 are stated wholly over characters of the
  identifier, steps 3-4 cannot be stated without the decoded bytes and a curve parameter — **not**
  detectability, which was the first draft's basis and is empirically false (a curve-allowlist
  grammar catches `dk-001` lexically, since `0xed01` keys always render `z6Mk…` and `0xe701` keys
  `z6Dt…`).
- **Alternatives:** Widen `dk-001` too (leaves nothing verifying an implementation distinguishes
  `0xe701` from `0xed01`); widen nothing (would revoke `dk-002`'s pre-existing prose carve-out — a
  Final-line tightening).
- **Partial revocation, stated:** scoping `dk-002`'s carve-out to cases 1-2 *does* revoke it for case 3, which `main`'s unscoped prose had granted. Listed here because the same entry rejects "widen nothing" as a Final-line tightening — the chosen path performs a narrow one. Justified because `main` was self-contradictory there (§5.11.1 step 3 already required `key_resolution_failed` for a bad multicodec prefix, which is what `z6Mk` is), so this resolves a conflict rather than tightening a settled rule.
- **Blast radius if wrong:** An implementation rejecting `dk-001` with `schema_violation` is
  non-conformant under a rule that was already a MUST on `main`, so this narrows nothing new. If the
  encoding-vs-key-material line is later judged arbitrary, the fix is fixture metadata and prose.
- **Status:** CONFIRMED (2026-09-21) — see `DECISIONS.md`

## Phase 5 — the anti-disarm rule binds at 0.3.0, consumer-side, rather than riding 0.5.0

- **Plan:** open-issues-2026-09 (local planning doc; `plans/` is gitignored and not part of the published tree)
- **Assumed:** Adding "a superseding context that is not itself a same-signer-class `key-revocation`
  MUST be disregarded for revocation-effectiveness" to RFC-ACDP-0014 §7 — a **Final** 0.3.0
  document — is a permitted clarification, not a Final-line tightening that needs a version gate.
- **Chose:** Unconditional at 0.3.0. It is directed at consumers only and adds no registry
  obligation, which is the governing principle this plan settled: a Final-line clarification may add
  consumer-side verification obligations and may loosen registry latitude, but may never add a
  registry-side publish rejection. It also closes the hole *now*, on consumer upgrade, without
  needing any registry to adopt anything — whereas the registry-side companion (Phase 7, gated at
  `acdp_version` ≥ 0.5.0) reaches only registries that adopt it. §4 already required the earliest-T
  fold; what was missing was how to obtain the lineage, and three ways the obvious implementation
  fails open.
- **Alternatives:** Gate the whole rule at 0.5.0 (leaves the hole open on every deployed 0.3.0/0.4.0
  consumer, for a rule that costs a registry nothing); state it non-normatively (a SHOULD is not
  enough for a defence whose failure mode is an attacker silently neutralizing a safety broadcast).
- **Tension worth naming:** a consumer that was conformant at 0.3.0 and folded by reading the head
  is non-conformant under the new text. That is a genuine tightening — but of a *verification*
  obligation, which the governing principle explicitly permits, and §4's earliest-T MUST arguably
  already required it. The new text says how, not whether.
- **Empirical hedge:** RFC-ACDP-0014 §7 and `rev-002`'s L2 note say such a supersession "is accepted
  by registries today", meaning the spec requires no rejection. At least one implementation
  (`acdp-rs`, per issue #61) already rejects it. Both texts carry the hedge that a consumer MUST NOT
  assume a registry filtered it out, so the claim is load-bearing only as "the spec does not require
  rejection" — which is true.
- **Blast radius if wrong:** Prose in one RFC section plus three behavioral scenarios. No schema, no
  wire, no fixture wiring. Reversible by moving the paragraph behind a version marker.
- **Status:** CONFIRMED (2026-09-21) — see `DECISIONS.md`

## Phase 7 — `rev-003`'s shared `registry_capabilities` bumped to 0.5.0 rather than given per-scenario overrides

- **Plan:** open-issues-2026-09 (local planning doc; `plans/` is gitignored and not part of the published tree)
- **Assumed:** `rev-003`'s new scenarios O–R pin obligations that bind only at `acdp_version` ≥ 0.5.0, while
  scenarios A–N's obligations bind from 0.3.0 — two genuinely different version gates inside one fixture file.
- **Chose:** Bump the fixture-level `input.registry_capabilities.acdp_version` from `0.3.0` to `0.5.0` (one
  shared declaration for the whole file) rather than giving O–R their own scenario-level
  `registry_capabilities` override. This is sound because 0.5.0 obligations are a superset of 0.3.0's — a
  registry advertising 0.5.0 is still bound by every A–N rule — so raising the shared declaration does not
  weaken A–N's requirement, only adds context for O–R. Added a new per-scenario `applies_when` string
  (documented in `schemas/conformance/README.md`'s Fixture Format section, parallel to `harness` and
  `control`/`differs_from_control`) on O–R so a registry conformance-testing below 0.5.0 does not misread
  them as demanding a rejection it is forbidden to perform.
- **Alternatives:** A scenario-level `registry_capabilities` override object on O–R only — rejected as a
  heavier, unprecedented structural addition for a problem the shared-bump-plus-`applies_when` combination
  already solves cleanly; a new sibling fixture file (`rev-004`) for the 0.5.0-only scenarios — rejected
  because the plan's own Phase 7 "Files" list specifies extending `rev-003`, and `CLAUDE.md`'s "consistency
  tracks fixture files, not scenarios" convention makes in-file extension the established pattern (Phase 5
  used it for `rev-002`'s scenarios E/F/G).
- **Blast radius if wrong:** Fixture-local JSON plus two prose paragraphs (this file's notes, and
  `schemas/conformance/README.md`'s Fixture Format section). No schema, wire, or profiles.json structural
  change beyond the new conditional_fixtures entry, which is independently correct regardless of this
  choice. Reversible by splitting O–R into their own file later.
- **Status:** CONFIRMED (2026-09-21) — see `DECISIONS.md`

## Phase 7 — `revocation_type_mismatch` is a `superseded_target` reason token, not a new wire error code

- **Plan:** open-issues-2026-09 (local planning doc; `plans/` is gitignored and not part of the published tree)
- **Assumed:** The registry-side predecessor-keyed supersession rejection needs a machine-readable
  discriminator, but RFC-ACDP-0014 §10's "No new wire error code" bullet constrains how it can be minted.
- **Chose:** A new row in the `superseded_target` reason-code table (`registries/error-codes.md`), returned
  as `details.reason: "revocation_type_mismatch"` alongside the existing `error_code: "superseded_target"`.
  Verified this does not trip `scripts/check-consistency.py`'s `check_error_code_registry_sync` guard (added
  Phase 1, 2026-09-13): that guard scopes to RFC-ACDP-0007 §5's table and `error-codes.md`'s *main* v0.1.0
  codes section only, both of which stop scanning at the next `##` heading — the reason-code table sits
  under its own `##` heading and is out of both scopes. Ran `make consistency` after the edit to confirm
  empirically rather than relying on reading the guard's source alone.
- **Alternatives:** `schema_violation` — considered and rejected in the plan itself (the incoming body is
  structurally valid; what fails is its relationship to the supersession target, which `schema_violation`'s
  own definition — "failed *structural* validation" — does not cover, and using it would be exactly the
  code-overloading `error-codes.md`'s "Adding a code" section forbids); a genuinely new top-level wire error
  code — rejected as contradicting RFC-ACDP-0014 §10's "No new wire error code" bullet outright, which this
  rule's own placement in §4 (not §10) does not exempt it from, since that bullet is a whole-RFC statement
  about the wire surface, not scoped to the section it happens to sit in.
- **Blast radius if wrong:** A registry-table row and a schema-enum-adjacent (but not enum-member) string
  literal. Reversible: renaming or removing the reason token touches one table row, one fixture's
  `details.reason` values (two scenarios, O and P), and the RFC-0014 §4 paragraph that names it.
- **Status:** CONFIRMED (2026-09-21) — see `DECISIONS.md`

## Finalization (Phases 5+6+7) — RFC-ACDP-0014 §7's "not itself a key-revocation" broadened to include the §10 interim form, as an unmarked Final clarification

- **Plan:** open-issues-2026-09 (local planning doc; `plans/` is gitignored and not part of the published tree)
- **Assumed:** The finalization-pass cross-phase verifier (fresh Opus, over the cumulative Phases 5+6+7
  diff) found a genuine ambiguity Phase 5's own per-phase verifier could not have seen, because it only had
  Phase 5's diff: §7's consumer-side disarm rule ("a superseding context that is not itself a
  `key-revocation`... MUST be disregarded") used a literal-string definition of "key-revocation" that
  predates Phase 7's §4 amendment, which explicitly broadens the same comparison to include the §10 interim
  `acdp:key-revocation` form. Left unfixed, a consumer implementing §7 by literal string match would treat
  an interim-typed **widening** successor as a disarming non-revocation and fall back to the superseded
  (later, less protective) boundary — a genuine fail-open, not merely inconsistent prose.
- **Chose:** Mirrored §4's broadening into §7's clause ("for this comparison, 'a revocation' means
  `key-revocation` **or** the §10 interim `acdp:key-revocation`"), and added `rev-002` scenario H pinning
  the divergent-verdict case, following the same publish-time-between-two-boundaries methodology E/F/G
  already established. **First-round mistake, caught by round-2 re-verification and corrected:** the initial
  fix marked this change *(0.5.0)* and gated scenario H at `acdp_version >= 0.5.0`, treating it as a new
  Draft-line obligation parallel to §4/§10's genuinely new registry rejections. A round-2 fresh-Opus verifier
  flagged this as inconsistent with RFC-ACDP-0014 §10's own pre-existing (Final, unmarked, binding since
  0.3.0's promotion) sentence: "0.3.0 consumers MUST treat `acdp:key-revocation` as equivalent to
  `key-revocation` when it satisfies §4–§5." That sentence already required full equivalence for every
  consumer-side purpose, including §7's fold — so the disarm-clause fix is a **Final-line precision fix**
  clarifying an obligation that already existed, not a new one. Corrected: removed the *(0.5.0)* marker and
  every version-gate reference from §7's clause, `rev-002`'s description/tags/scenario-H text, and every
  wiring artifact (§1, VERSIONING.md, README.md, profiles.md) that had inherited the wrong framing; scenario
  H is now wired as an unconditional 0.3.0 obligation, exactly like A-G.
- **Why this is decidable, not a Fable-routed one-way door:** it is a narrow clarification of what an
  existing, unambiguous Final sentence (§10's equivalence rule) already required, in the same category as
  other Final-line precision fixes already in `CHANGELOG.md` (e.g. the `embedded.content_hash`
  disambiguation sweep) — not a new wire obligation, and not itself a version-gated Draft amendment. The
  disarm rule's outcome for every non-interim case (scenarios A-G) is byte-for-byte unchanged.
- **Alternatives:** Leave §7 unmarked and narrow, relying on §10's blanket equivalence sentence to rescue a
  careful reader without spelling out the disarm-clause case — rejected for the reason above (a normative
  clause should not depend on a reader independently cross-applying a sentence from elsewhere). Gate the fix
  at `>=0.5.0` as a new Draft-line amendment (the first-round choice) — rejected on round-2 review as
  factually wrong: it would have left every 0.3.0/0.4.0 consumer non-conformant to an obligation §10 already
  imposed on it, with no fixture to catch it, for the entire time before 0.5.0 promotes.
- **Blast radius if wrong:** One RFC paragraph (§7) plus one new fixture scenario (`rev-002` H) and its
  lineage/receipt scaffolding, now unconditional rather than 0.5.0-gated. No schema or wire change either
  way. If the "already-Final" reading is itself wrong (i.e. §10's equivalence sentence was not intended to
  reach this far), the fix would need to become version-gated after all — a one-file, one-scenario reversal,
  not a wire change.
- **Status:** CONFIRMED (2026-09-21) — see `DECISIONS.md`

## Finalization (Phases 5+6+7) — new `rev-004` fixture for the retrieval-continuity half of §10's interim-form retirement

- **Plan:** open-issues-2026-09 (local planning doc; `plans/` is gitignored and not part of the published tree)
- **Assumed:** The same finalization-pass verifier found that RFC-ACDP-0014 §10's explicit statement that a
  ≥0.5.0 registry "continues serving [an existing interim-form body] unchanged" — required by the plan's own
  Phase 7 acceptance criterion 2 ("explicitly preserves retrieval and consumer-equivalence for existing
  ones") — had no conformance fixture pinning it: `rev-003` Q pins only the *publish-time* rejection of a
  *new* interim-form publish, leaving the retrieval-time half asserted in prose only.
- **Chose:** A new fixture, `rev-004-interim-form-retrieval-unaffected`, with three black-box scenarios
  (direct `GET`, search, lineage-walk) against a pre-existing interim-typed body on a ≥0.5.0 registry, all
  expecting unfiltered success — wired into `profiles.json`/`profiles.md` as a fourth `acdp-registry-core`
  conditional entry (`>=0.5.0`) alongside `rev-003`'s O–R entry, and into the README fixture index and §12's
  RFC-ACDP-0014 table.
- **Why a new file, not a `rev-003` extension (distinct from the O–R decision above):** `rev-003`'s own
  title and every existing scenario are publish-request-shaped (`POST /contexts`); this concern is about
  retrieval (`GET`), a different request shape and a different obligation axis (what the registry must NOT
  do, at a different endpoint, to something already on the record) — folding it into a file named
  "publish-rejects" would be a scope mismatch that a future reader would have to untangle. This does not
  reopen the earlier decision to keep O–R inside `rev-003` rather than splitting them into their own file:
  that decision was about scenarios sharing `rev-003`'s existing publish-request shape and obligation axis;
  this one is not.
- **Round-2 correction:** the first-round scenario B (search) asserted an unconditional `200`/success —
  round-2 fresh-Opus re-verification flagged that `GET /contexts/search` is a discovery-profile endpoint,
  and `acdp-registry-core`'s own `not_implemented_permitted_on` allowance lets a core-only registry answer
  it with `not_implemented` (501), which B's original wording would have wrongly failed. Fixed with a
  per-scenario `applies_when` field on B (mirroring `rev-003` O–R's own use of that field for a different
  kind of scenario-level conditionality) stating B binds only when `acdp-registry-discovery` is additionally
  advertised, and that a core-only registry's `501` trivially satisfies it. Scenarios A (direct GET) and C
  (lineage walk) are unaffected — both use core-only endpoints and remain unconditional at `>=0.5.0`.
- **Blast radius if wrong:** One new fixture file plus four wiring-point additions (`profiles.json`,
  `profiles.md`, README index + prose, RFC-ACDP-0014 §12 table row), plus one `applies_when` field on
  scenario B. No schema or wire change. Reversible: removing the fixture and its wiring entries cleanly
  un-pins the retrieval-continuity claim back to prose-only, with no effect on `rev-001`/`002`/`003`.
- **Status:** CONFIRMED (2026-09-21) — see `DECISIONS.md`
