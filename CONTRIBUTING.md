# Contributing to ACDP

Thank you for contributing to the Agent Context Description Protocol (ACDP).

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

To add an entry to a registry under `registries/` (`auth-methods.md`, `context-types.md`, `error-codes.md`, `locator-schemes.md`, `media-types.md`, `profiles.md`, `signature-algorithms.md`), submit a PR adding a row to the relevant table. Each entry MUST include a `Status` (`Proposed`, `Provisional`, `Stable`, `Deprecated`). New identifiers MUST NOT conflict with existing entries.

## Technical requirements

- JSON examples MUST validate against the relevant JSON Schema (`make json-validate`).
- JSON Schemas MUST themselves be valid (`make json-schema-validate`).
- Backward compatibility MUST be addressed explicitly in the PR description.

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
