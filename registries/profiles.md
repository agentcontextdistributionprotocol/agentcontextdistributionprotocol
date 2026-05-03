# Implementation Profiles Registry

ACDP implementation profile identifiers used in `capabilities.profiles`. Identifiers are lowercase ASCII matching `^acdp-[a-z][a-z0-9-]*$`.

The schema vocabulary is open. Profiles are normatively defined in [RFC-ACDP-0001 §9.1](../rfcs/RFC-ACDP-0001-core.md#91-implementation-profiles).

## Registered values

| Identifier | Status | Reference | Prerequisite |
|---|---|---|---|
| `acdp-registry-core` | Mandatory for any registry | RFC-ACDP-0001 §9.1 | — |
| `acdp-registry-discovery` | Optional | RFC-ACDP-0001 §9.1 | `acdp-registry-core` |
| `acdp-registry-federated` | Optional | RFC-ACDP-0001 §9.1 | `acdp-registry-core` |
| `acdp-consumer` | For consumer deployments | RFC-ACDP-0001 §9.1 | — |

## Adding a profile

Open a PR adding a row above and amending RFC-ACDP-0001 §9.1 with the profile's MUST list. Profiles MUST:

- Be a strict superset of any prerequisite.
- Carry conformance fixtures sufficient to validate the additional MUSTs.
- Have a stable name; renames are forbidden.

Reserved future identifiers: `acdp-registry-receipts` (RFC-ACDP-0009 §2.7), `acdp-registry-push` (RFC-ACDP-0009 §2.4), `acdp-registry-walks` (RFC-ACDP-0009 §2.5).
