# ACDP Registries

This directory tracks the well-known identifiers used in ACDP. Each registry is a Markdown table; entries are added via PR.

| Registry | File | Authority RFC |
|---|---|---|
| Context types | [context-types.md](context-types.md) | [RFC-ACDP-0002](../rfcs/RFC-ACDP-0002-context-body.md) |
| Error codes | [error-codes.md](error-codes.md) | [RFC-ACDP-0007](../rfcs/RFC-ACDP-0007-capabilities.md) |
| Media types | [media-types.md](media-types.md) | [RFC-ACDP-0001](../rfcs/RFC-ACDP-0001-core.md) |
| Locator schemes | [locator-schemes.md](locator-schemes.md) | [RFC-ACDP-0002](../rfcs/RFC-ACDP-0002-context-body.md) |

## Status values

| Status | Meaning |
|---|---|
| `Proposed` | Suggested in an open RFC or PR. Not yet merged. |
| `Provisional` | Merged but not yet shipped in two interoperating implementations. |
| `Stable` | Two interoperating implementations confirmed. Backwards-compatible additions only. |
| `Deprecated` | Retained for archaeology. New implementations MUST NOT depend on it. |

## Naming conventions

- Context type identifiers are lowercase snake_case for standard types; namespaced custom types use `<namespace>:<type>` (e.g. `science:experiment-replication`).
- Error codes use lowercase snake_case.
- Locator scheme identifiers use dotted-namespace form (e.g. `kafka.offset`).
- Experimental identifiers SHOULD use a vendor-prefixed reverse-domain name (e.g. `com.example.feature`).
