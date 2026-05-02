# ACDP RFC Process

ACDP evolves through RFCs (Request for Comments). This document describes the process for proposing, reviewing, and accepting changes.

---

## RFC Lifecycle

```
Idea → Draft → Review → Final Comment Period → Accepted | Rejected
```

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

**Accepted**
- RFC is merged.
- Corresponding spec changes (schemas, protos, registries, examples) are tracked in the RFC and shipped together.

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

Detailed proposal. Include schema changes, proto changes, error-code additions, security implications.

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
- Adding entries to `registries/locator-schemes.md` (registry-additive change with maintainer approval).

---

## Core Team

The core team is responsible for shepherding RFCs and voting on acceptance. Contact via the issue tracker; the current core team is listed in [GOVERNANCE.md](GOVERNANCE.md).
