# Contributing to ACDP

Thank you for contributing to the Agent Context Distribution Protocol (ACDP).

ACDP is a coordination-agnostic context-publication standard. All changes MUST preserve the core invariants:

- Bodies are immutable once published.
- Every body is cryptographically signed by its producer.
- `lineage_id` is deterministically derived from the first version's `ctx_id` and is end-to-end verifiable.
- `content_hash` is a SHA-256 over the JCS-canonicalized body, with the registry-assigned exclusion set.
- Cross-registry references resolve via the `acdp://` URI scheme, and the producing agent's signature — not the serving registry — is the trust anchor.
- Registries do not retract; supersession is the only correction mechanism in v0.1.0.

## Local development

Run once to install dev dependencies:

```bash
make bootstrap
```

This installs `ajv-cli` (Node.js, for JSON Schema validation) and Python packages (`jcs`, `cryptography`) for the conformance runner.

Once bootstrapped:

```bash
make validate     # Run all validations (schema + JSON + conformance)
make help         # Show all targets
```

## Types of contributions

- Specification clarifications (non-normative)
- New RFCs or amendments to existing RFCs
- Schema updates (JSON Schema)
- Conformance fixtures
- Tooling and CI improvements
- Documentation

## Submitting changes

### Minor clarifications

Open a PR directly against the relevant document.

### Substantive (normative) changes

1. Open an issue using the [RFC proposal template](.github/ISSUE_TEMPLATE/rfc_proposal.yml).
2. Discuss motivation and compatibility.
3. Submit a PR updating the relevant RFC and any affected schemas/fixtures.

Breaking changes require:
- A version bump on the affected RFC.
- Migration notes in the PR description.
- An explicit compatibility statement.

## Registry additions

To add an entry to a registry under `registries/` (`auth-methods.md`, `context-types.md`, `data-ref-types.md`, `error-codes.md`, `locator-schemes.md`, `media-types.md`, `profiles.md`, `signature-algorithms.md`), submit a PR adding a row to the relevant table. Each entry MUST include a `Status` (`Proposed`, `Provisional`, `Stable`, `Deprecated`). New identifiers MUST NOT conflict with existing entries.

The profile registry is the one registry kept in two synchronized forms: `profiles.md` (human-readable, authoritative on divergence) and `profiles.json` (machine-readable conformance manifest). A change to one MUST be mirrored in the other.

## Adding a conformance fixture

Conformance fixtures under `schemas/conformance/` come in two kinds, dispatched by `id` prefix in `scripts/conformance-runner.py`:

- `can-*` / `lin-*` (canonicalization, hashing, lineage) and `sig-*` (Ed25519 / ECDSA-P256 golden vectors) are **executed arithmetically** — the runner reproduces the JCS / hash / signature and byte-compares against the pinned `expected`. Compute `canonical_form` and `sha256_hex` with the `jcs` library (RFC 8785); never hand-write them, because the runner byte-compares. Python stdlib `json.dumps` is non-conformant.
- All other families (`pub-`, `vis-`, `ret-`, `caps-`, `schema-`, `*-ssrf-`, `fed-`, …) are **behavioral scenarios** the runner does not execute; they describe a request → expected outcome that registry implementations verify.

Adding a fixture is a three-file change:

1. The fixture JSON under `schemas/conformance/` (its `id` prefix MUST match a handled family so the runner auto-discovers it).
2. An entry in the relevant profile(s) in **both** `registries/profiles.json` and `registries/profiles.md`.
3. A row in the `schemas/conformance/README.md` fixture index.

## Technical requirements

- `make validate` MUST pass — this is the gate CI enforces on every PR. It runs the three checks below.
- JSON examples MUST validate against the relevant JSON Schema (`make json-validate`).
- JSON Schemas MUST themselves be valid (`make json-schema-validate`).
- The executable conformance vectors MUST pass (`make conformance`).
- Backward compatibility MUST be addressed explicitly in the PR description.

## Versioning and releases

ACDP `0.1.0` is wire-frozen: existing bodies, signatures, and `content_hash` values MUST remain valid. Changes are almost always non-breaking clarifications, not wire changes. A genuine wire change requires an RFC version bump, migration notes, and an explicit compatibility statement.

- [VERSIONING.md](VERSIONING.md) — the layered versioning policy and the status ladder.
- [RELEASE.md](RELEASE.md) — the checklist for promoting a version line to `Final` and cutting tags.
- Record non-breaking spec changes in [CHANGELOG.md](CHANGELOG.md) under a `## v0.1.0 — Clarifications addendum (round N)` heading that opens by asserting that no body field, schema `$id`, JCS rule, content-hash, or signature semantic changed.

## Pull requests

- Use the [pull request template](.github/PULL_REQUEST_TEMPLATE.md) and complete its checklist.
- Write a clear, present-tense PR summary describing what changed and why.
- Keep a PR scoped to one logical change; split unrelated edits.

## Reporting security issues

Do **not** open a public issue for a flaw that weakens a protocol security guarantee (signature, hashing, visibility, or SSRF defenses — see [RFC-ACDP-0008](rfcs/RFC-ACDP-0008-security.md)). Report it privately via GitHub's "Report a vulnerability" advisory on this repository, as described in [governance/GOVERNANCE.md § Reporting Issues](governance/GOVERNANCE.md#reporting-issues).

## Style

- Use RFC 2119 keywords (MUST, SHOULD, MAY) consistently in normative text.
- Use present tense ("Registries MUST verify…", not "Registries should verify…").
- JSON examples MUST be valid against the corresponding schema.

## Normative RFCs

- **[RFC-ACDP-0001 Core](rfcs/RFC-ACDP-0001-core.md)**
- **[RFC-ACDP-0002 Context Body](rfcs/RFC-ACDP-0002-context-body.md)**
- **[RFC-ACDP-0003 Publish](rfcs/RFC-ACDP-0003-publish.md)**
- **[RFC-ACDP-0004 Retrieval](rfcs/RFC-ACDP-0004-retrieval.md)**
- **[RFC-ACDP-0005 Discovery](rfcs/RFC-ACDP-0005-discovery.md)**
- **[RFC-ACDP-0006 Cross-Registry](rfcs/RFC-ACDP-0006-cross-registry.md)**
- **[RFC-ACDP-0007 Capabilities](rfcs/RFC-ACDP-0007-capabilities.md)**
- **[RFC-ACDP-0008 Security](rfcs/RFC-ACDP-0008-security.md)**

## Reserved RFCs

- **[RFC-ACDP-0009 Extensions](rfcs/RFC-ACDP-0009-extensions.md)** *(reserved)*

## Community

All contributors must follow the [Code of Conduct](CODE_OF_CONDUCT.md).
