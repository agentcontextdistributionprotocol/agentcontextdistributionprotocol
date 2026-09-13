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
- **Status:** UNCONFIRMED

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
- **Status:** UNCONFIRMED

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
- **Status:** UNCONFIRMED

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
- **Status:** UNCONFIRMED

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
- **Status:** UNCONFIRMED
