# ACDP RFC Process

ACDP evolves through RFCs (Request for Comments). This document describes the process for proposing, reviewing, and accepting changes.

---

## RFC Lifecycle

```
Idea → Draft → Review → Final Comment Period → Release Candidate N → Final | Rejected
```

`Reserved` is a sidebar state for RFCs whose number is pinned with no normative text yet (e.g. RFC-ACDP-0009). The status names below MUST match the ladder in [VERSIONING.md](../VERSIONING.md).

### Stages

**Draft**
- Author opens a PR adding or modifying a file in `rfcs/RFC-ACDP-XXXX-title.md`.
- New RFCs are numbered sequentially.
- Anyone may comment.

**Review**
- RFC is discussed for a minimum of 14 days.
- Core team triages and assigns a shepherd.
- Shepherd is responsible for driving the RFC to resolution.

**Final Comment Period (FCP)**
- Announced with a 7-day window.
- No new substantive changes during FCP.
- Core team votes.

**Release Candidate N**
- A specific candidate (`rc1`, `rc2`, …) intended for implementation testing.
- The RFC `Version:` header carries the `-rcN` suffix (e.g. `0.1.0-rc1`).
- Backward-incompatible changes remain possible until `Final`; editorial fixes are expected.
- Implementations MAY ship against an RC, but MUST be prepared for breaking changes before `Final`.

**Final**
- RFC is merged at its bare semver version (no `-rcN` suffix).
- Corresponding spec changes (schemas, registries, examples) are shipped together.
- Subsequent breaking changes require a new RFC and a version bump.

**Reserved** *(sidebar state)*
- RFC number is pinned but contains no normative text.
- `Version:` header carries the `-reserved` suffix (e.g. `0.1.0-reserved`).
- Implementations MUST NOT depend on identifiers reserved here until promoted out of `Reserved`.

**Rejected**
- PR is closed with explanation.
- Rejected RFCs remain in the repository for reference.

---

## RFC Template

```markdown
# RFC-ACDP-XXXX: Title

- **Status:** Draft
- **Authors:** @handle
- **Created:** YYYY-MM-DD
- **Spec sections affected:** rfcs/RFC-ACDP-NNNN-*.md, schemas/json/*.schema.json

## Summary

One paragraph description.

## Motivation

Why is this needed? What problem does it solve?

## Design

Detailed proposal. Include JSON Schema changes, registry additions (error codes, context types, …), conformance-fixture impact, and security implications.

## Alternatives considered

What else was considered and why was it rejected?

## Backward compatibility

How does this affect existing implementations? Producer flow? Consumer flow? Registry storage?

## Open questions

Unresolved issues that need discussion before acceptance.
```

---

## What Requires an RFC

- Any normative change to an existing RFC.
- New body fields or registry-state fields.
- Changes to canonicalization or hashing rules.
- New context types (standard).
- New error codes.
- Changes to security guarantees.
- New endpoints.
- New protocol versions.

What does NOT require an RFC:

- Fixing typos or clarifying non-normative text.
- Adding conformance fixtures.
- Adding examples.
- Updating `docs/`.
- Adding entries to any open-vocabulary registry under `registries/` (registry-additive change with maintainer approval).

---

## Core Team

The core team is responsible for shepherding RFCs and voting on acceptance. It is the project's set of maintainers — the accounts with merge access to this repository, as described in [GOVERNANCE.md § Maintainers](GOVERNANCE.md#maintainers). Contact the core team via the issue tracker.
