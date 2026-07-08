# ACDP Release Checklist

This checklist governs promoting an ACDP version line from `Release Candidate` to
`Final` and cutting the release tags. It complements [VERSIONING.md](VERSIONING.md)
(the versioning policy), [CONTRIBUTING.md](CONTRIBUTING.md) (how changes land), and
[governance/RFC-PROCESS.md](governance/RFC-PROCESS.md) (the per-RFC lifecycle).

A release is **not** a code change — it is a coordinated state transition across the
RFC prose, the schemas, the conformance manifest, and the changelog. Run the whole
checklist; a partial promotion (some RFCs `Final`, some still `Release Candidate`) is
a documentation bug.

---

## 1. Promotion gate (must hold before starting)

- [ ] The conformance suite under `schemas/conformance/` — arithmetic/cryptographic
      vectors **and** the behavioral fixtures — passes against **at least two
      interoperating implementations** (the `Final` gate in VERSIONING.md).
- [ ] No open issue is labelled `blocks-final` for the version line being promoted.
- [ ] Every RFC in the line is at `Release Candidate` (not `Draft`/`Review`) or
      `Reserved`. `Reserved` RFCs (e.g. RFC-ACDP-0009) are **not** promoted.

## 2. RFC prose

- [ ] Each RFC header `**Version:**` carries the bare semver string (no `-rcN`).
- [ ] Each RFC header `**Status:**` reads `Community Standards Track (Final)`.
- [ ] Each RFC §1 "Status of This Memo" states the document is `Final`.
- [ ] `rfcs/README.md` status column reads `Final` for every promoted RFC.
- [ ] No stray `Release Candidate` / `rcN` / `0.1.0-rc1` references remain in RFC
      prose. The string is permitted **only** where it is historically or
      structurally accurate: the dated `CHANGELOG.md` entry for the RC, the RC row
      of the `VERSIONING.md` status ladder, the generic lifecycle descriptions in
      `governance/RFC-PROCESS.md` / `governance/GOVERNANCE.md`, and the generic
      lifecycle-ladder mentions in `rfcs/RFC-ACDP-0001-core.md` §1 and
      `rfcs/README.md` (which describe the `Draft → … → Release Candidate N →
      Final` ladder, not the current version's status).

      The grep below surfaces *candidates for review*, not a clean-must-be-empty
      check — eyeball each hit and confirm it is one of the permitted lifecycle
      descriptions above and not a stale status line for the version being
      promoted. `CHANGELOG.md`, `VERSIONING.md`, and `governance/` are excluded
      from the scan because every occurrence there is permitted:

      ```sh
      grep -rn 'rc1\|Release Candidate\|0.1.0-rc' rfcs/ docs/ manifesto/ README.md
      ```

## 3. Schemas and conformance

- [ ] Schema `$id` namespace (`schemas.acdp.io/v<major>.<minor>.<patch>/`) matches the
      release version. The namespace never carries an `-rcN` suffix.
- [ ] `registries/profiles.json` and `registries/profiles.md` agree on every
      profile's required-fixture set (profiles.md is authoritative on divergence).
      The mechanical half of this — every listed fixture exists, every fixture is
      listed in both forms and in the conformance README index — is enforced by
      `make consistency`; review the *semantic* placement (right profile, right
      conditionality) by hand.
- [ ] `make validate` passes (JSON Schema meta-validation, example/fixture
      validation, the executable conformance runner, and the cross-artifact
      consistency gate).

## 4. Changelog

- [ ] `CHANGELOG.md` has a new dated entry for the `Final` release.
- [ ] The entry states wire-compatibility with the preceding RC.
- [ ] The prior `-rcN` entry is left intact as historical record.

## 5. Tag

Per VERSIONING.md "Release tags":

- [ ] Tag the canonical schemas: `schema-vX.Y.Z`.
- [ ] Tag each promoted RFC at `Final`: `rfc-acdp-NNNN-vX.Y.Z`.
- [ ] Push tags and open the release on the forge.

## 6. Post-release

- [ ] Open the next development line (new `Draft`/`Review` RFCs or an `-rcN`
      candidate) so `main` is never ambiguously "between releases".
- [ ] Announce the release and the conformance status of the interoperating
      implementations that cleared the promotion gate.

---

## Release history

| Version | Date | Notes |
|---|---|---|
| `0.1.0-rc1` | 2026-05-18 | First published version; Release Candidate 1. |
| `0.1.0` | 2026-05-19 | First `Final` release. Specification-hardening pass over `0.1.0-rc1`; wire-compatible. |
| `0.2.0` | 2026-07-05 | Trust & Hardening promoted from `Draft` to `Final` (no RC window; the Draft carried its own two-implementation promotion gate per VERSIONING.md). Wire-compatible with 0.1.0. |
| `0.3.0` | 2026-07-05 | 0.3.0 line promoted from `Draft` to `Final` in the same promotion (RFC-ACDP-0011–0014 + amendments). Wire-compatible with 0.1.0/0.2.0. |
