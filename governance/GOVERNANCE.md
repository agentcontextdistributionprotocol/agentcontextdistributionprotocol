# ACDP Governance

ACDP is maintained as an open protocol specification.

## Maintainers

Maintainers are responsible for:

- Reviewing and merging pull requests.
- Protecting protocol invariants (see [CONTRIBUTING.md](../CONTRIBUTING.md#contributing-to-acdp)).
- Managing releases (RFC final transitions, schema/proto tags).
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
- Error codes (`registries/error-codes.md`)
- Locator schemes (`registries/locator-schemes.md`)
- Media types (`registries/media-types.md`)
- Profiles (`registries/profiles.md`)
- Signature algorithms (`registries/signature-algorithms.md`)

Experimental identifiers SHOULD use reverse-domain notation (e.g. `com.example.feature`).

## Code of Conduct

All contributors are expected to follow the [Code of Conduct](../CODE_OF_CONDUCT.md).
