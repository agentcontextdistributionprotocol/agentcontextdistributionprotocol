# ACDP Registries

This directory tracks the well-known identifiers used in ACDP. Each registry is a Markdown table; entries are added via PR.

| Registry | File | Authority RFC |
|---|---|---|
| Authentication methods | [auth-methods.md](auth-methods.md) | [RFC-ACDP-0007](../rfcs/RFC-ACDP-0007-capabilities.md), [RFC-ACDP-0008](../rfcs/RFC-ACDP-0008-security.md) |
| Context types | [context-types.md](context-types.md) | [RFC-ACDP-0002 §5](../rfcs/RFC-ACDP-0002-context-body.md) |
| DataRef types | [data-ref-types.md](data-ref-types.md) | [RFC-ACDP-0002 §6](../rfcs/RFC-ACDP-0002-context-body.md) |
| Error codes | [error-codes.md](error-codes.md) | [RFC-ACDP-0007](../rfcs/RFC-ACDP-0007-capabilities.md) |
| Implementation profiles | [profiles.md](profiles.md) | [RFC-ACDP-0001 §9.1](../rfcs/RFC-ACDP-0001-core.md) |
| Lifecycle event types | [lifecycle-event-types.md](lifecycle-event-types.md) | [RFC-ACDP-0013 §4, §7.3](../rfcs/RFC-ACDP-0013-lifecycle-events.md) |
| Locator schemes | [locator-schemes.md](locator-schemes.md) | [RFC-ACDP-0002](../rfcs/RFC-ACDP-0002-context-body.md) |
| Media types | [media-types.md](media-types.md) | [RFC-ACDP-0001](../rfcs/RFC-ACDP-0001-core.md) |
| Signature algorithms | [signature-algorithms.md](signature-algorithms.md) | [RFC-ACDP-0001 §5.10](../rfcs/RFC-ACDP-0001-core.md) |

## Status values

| Status | Meaning |
|---|---|
| `Proposed` | Suggested in an open RFC or PR. Not yet merged. |
| `Provisional` | Merged but not yet shipped in two interoperating implementations. |
| `Stable` | Two interoperating implementations confirmed. Backwards-compatible additions only. |
| `Deprecated` | Retained for archaeology. New implementations MUST NOT depend on it. |

## Naming conventions

- Context type identifiers are lowercase for standard types — snake_case historically, with hyphens permitted since 0.3.0 (`key-revocation`, matching the custom-type `<type>` grammar `^[a-z][a-z0-9_-]*$`); namespaced custom types use `<namespace>:<type>` (e.g. `science:experiment-replication`).
- Lifecycle event types are lowercase snake_case matching `^[a-z][a-z0-9_]*$`.
- Error codes use lowercase snake_case.
- Locator scheme identifiers use dotted-namespace form (e.g. `kafka.offset`).
- Experimental identifiers SHOULD use a vendor-prefixed reverse-domain name (e.g. `com.example.feature`).
