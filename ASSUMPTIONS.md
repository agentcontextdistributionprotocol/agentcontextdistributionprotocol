# Assumptions

Decisions taken during implementation where something was ambiguous but a clearly-best option
existed. Each is `UNCONFIRMED` until reconciled (`/reconcile`). Entries are tagged with the plan
they belong to, so a reconcile pass can scope itself to one feature.

---

## Phase 1 — `invalid_witness_cosignature` treated as a 0.4.0 erratum

- **Plan:** `plans/open-issues-2026-09.md`
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

- **Plan:** `plans/open-issues-2026-09.md`
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
