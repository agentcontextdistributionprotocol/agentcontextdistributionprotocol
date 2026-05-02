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

`Draft → Review → Final Comment Period → Final` (or `Rejected`).

Status MUST be reflected in the RFC document header. See [RFC-PROCESS.md](RFC-PROCESS.md).

## Registry Authority

The project maintains four registries under [`registries/`](../registries/):

- Context types (`registries/context-types.md`)
- Error codes (`registries/error-codes.md`)
- Media types (`registries/media-types.md`)
- Locator schemes (`registries/locator-schemes.md`)

Experimental identifiers SHOULD use reverse-domain notation (e.g. `com.example.feature`).

## Code of Conduct

All contributors are expected to follow the [Code of Conduct](../CODE_OF_CONDUCT.md).
