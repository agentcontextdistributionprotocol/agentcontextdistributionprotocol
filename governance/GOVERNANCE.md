# ACDP Governance

ACDP is maintained as an open protocol specification.

## Maintainers

ACDP maintainers — referred to as the **core team** in the [RFC process](RFC-PROCESS.md) — are the accounts with merge access to this repository. They can be reached via the issue tracker. Maintainers are responsible for:

- Reviewing and merging pull requests.
- Protecting protocol invariants (see [CONTRIBUTING.md](../CONTRIBUTING.md#contributing-to-acdp)).
- Shepherding RFCs and voting on their acceptance ([RFC-PROCESS.md](RFC-PROCESS.md)).
- Managing releases — RFC `Final` transitions and the coordinated version tag across RFCs, schemas, registries, and examples.
- Maintaining registry consistency (`registries/`).

## Decision Process

| Class | Decision rule |
|---|---|
| Clarifications | Maintainer approval. |
| Backward-compatible additions | Maintainer consensus. |
| Breaking changes | Formal [RFC process](RFC-PROCESS.md) + version bump on the affected RFC. |
| Registry additions | Maintainer approval; identifiers MUST NOT collide. |

## RFC Lifecycle

`Draft → Review → Final Comment Period → Release Candidate N → Final` (or `Rejected`). `Reserved` is a sidebar state for placeholder RFCs (e.g. RFC-ACDP-0009).

Status MUST be reflected in the RFC document header and SHOULD match the ladder in [VERSIONING.md](../VERSIONING.md). See [RFC-PROCESS.md](RFC-PROCESS.md).

## Registry Authority

The project maintains the following registries under [`registries/`](../registries/):

- Auth methods (`registries/auth-methods.md`)
- Context types (`registries/context-types.md`)
- Data-ref types (`registries/data-ref-types.md`)
- Error codes (`registries/error-codes.md`)
- Locator schemes (`registries/locator-schemes.md`)
- Media types (`registries/media-types.md`)
- Profiles (`registries/profiles.md`, with the machine-readable manifest `registries/profiles.json`)
- Signature algorithms (`registries/signature-algorithms.md`)

Experimental identifiers SHOULD use reverse-domain notation (e.g. `com.example.feature`).

## Reporting Issues

- **Spec bugs, ambiguities, and feature ideas** — open an issue using the templates in [`.github/ISSUE_TEMPLATE/`](../.github/ISSUE_TEMPLATE), or propose a normative change via the [RFC process](RFC-PROCESS.md).
- **Security-sensitive findings** — if you believe you have found a flaw that weakens a protocol security guarantee (signature, hashing, visibility, or SSRF defenses — see [RFC-ACDP-0008](../rfcs/RFC-ACDP-0008-security.md)), do **not** open a public issue. Report it privately via GitHub's "Report a vulnerability" (private security advisory) on this repository so it can be triaged before disclosure.

## Code of Conduct

All contributors are expected to follow the [Code of Conduct](../CODE_OF_CONDUCT.md).
