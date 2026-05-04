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

## Conformance manifests

Each profile pins a concrete set of HTTP endpoints and conformance fixtures. The columns below are normative for v0.0.1 implementers — passing the listed fixtures is necessary (but not sufficient) for claiming conformance with the corresponding profile.

### `acdp-registry-core`

| | Required |
|---|---|
| **HTTP endpoints** | `POST /contexts` (RFC-ACDP-0003 §2), `GET /contexts/{ctx_id}` (RFC-ACDP-0004 §2.1), `GET /contexts/{ctx_id}/body` (RFC-ACDP-0004 §2.2), `GET /lineages/{lineage_id}` (RFC-ACDP-0004 §5.1), `GET /lineages/{lineage_id}/current` (RFC-ACDP-0004 §5.2), `GET /.well-known/acdp.json` (RFC-ACDP-0007 §3) |
| **Conformance fixtures** | `can-001`..`can-006` (canonicalization), `sig-001` (Ed25519 golden), `pub-001`..`pub-007` (publish flow), `data-ref-001`..`data-ref-007` (DataRef validation), `meta-001`..`meta-003` (metadata limits), `ret-001` (retrieval), `vis-001` (restricted retrieval), `err-001` (error envelope) |
| **`not_implemented` permitted on** | `GET /contexts/search` (registry MAY return 501 if `acdp-registry-discovery` is not advertised); cross-registry resolution endpoints are not part of v0.0.1 protocol surface and are NOT addressable by `not_implemented` |

### `acdp-registry-discovery`

Adds keyword search.

| | Required (in addition to `acdp-registry-core`) |
|---|---|
| **HTTP endpoints** | `GET /contexts/search` (RFC-ACDP-0005 §2) |
| **Conformance fixtures** | `vis-002` (search visibility scoping), `vis-003` (response field name `matches`) |
| **`not_implemented` permitted on** | None — every endpoint listed above is mandatory once this profile is advertised |

### `acdp-registry-federated`

Adds cross-registry resolution.

| | Required (in addition to `acdp-registry-core`) |
|---|---|
| **HTTP endpoints** | None added — federation is not exposed as a new endpoint; the registry resolves `acdp://` references in `derived_from` chains transparently while serving existing endpoints (RFC-ACDP-0006 §4) |
| **Conformance fixtures** | RFC-ACDP-0006 §7 SSRF protection cases (IP-range filter, HTTPS-only, redirect cap, response/timeout caps, DNS-rebinding pin); registry-DID verification per RFC-ACDP-0006 §4.1 step 3 |
| **`not_implemented` permitted on** | None |

### `acdp-consumer`

For consumer deployments (libraries, agents). Does not run a registry.

| | Required |
|---|---|
| **Behavioral requirements** | End-to-end signature verification (RFC-ACDP-0001 §5.11) on every retrieved context; `acdp://` cross-registry resolution per RFC-ACDP-0006 if followed (with SSRF protections of §7 if performed server-side); local visibility re-verification per RFC-ACDP-0008 §4.5; tolerance of unknown body / registry-state fields (RFC-ACDP-0001 §6, RFC-ACDP-0004 §4.1, RFC-ACDP-0007 §3.3) |
| **Conformance fixtures** | All `can-*`, `sig-001`, the consumer side of `vis-003`, plus any cross-registry traversal vectors a consumer follows |

## Adding a profile

Open a PR adding a row above and amending RFC-ACDP-0001 §9.1 with the profile's MUST list. Profiles MUST:

- Be a strict superset of any prerequisite.
- Carry conformance fixtures sufficient to validate the additional MUSTs.
- Have a stable name; renames are forbidden.

Reserved future identifiers: `acdp-registry-receipts` (RFC-ACDP-0009 §2.7), `acdp-registry-push` (RFC-ACDP-0009 §2.4), `acdp-registry-walks` (RFC-ACDP-0009 §2.5).
