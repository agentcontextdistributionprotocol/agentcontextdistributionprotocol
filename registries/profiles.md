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
| **Conformance fixtures** | `can-001`..`can-009` (canonicalization, including registry-side timestamp emission per RFC-ACDP-0001 §5.3 and forward-compat hash verification per §5.7), `sig-001` (Ed25519 golden), `sig-002` (ECDSA-P256 golden, REQUIRED only if registry advertises `ecdsa-p256` in `supported_signature_algorithms`), `pub-001`..`pub-014` (publish flow, including DID method scope per RFC-ACDP-0001 §5.4, persist-only-after-signature-verify atomicity per RFC-ACDP-0003 §2.1 in `pub-011`, and closed-schema rejections per RFC-ACDP-0003 §2.1 step 1 in `pub-012..014`), `data-ref-001`..`data-ref-007` (DataRef validation), `meta-001`..`meta-003` (metadata limits), `ret-001` (retrieval), `vis-001` (restricted retrieval), `vis-004`, `vis-005` (private + audience search-vs-retrieval asymmetry per RFC-ACDP-0008 §4.5), `err-001` (error envelope), `caps-001`..`caps-006` (capabilities validation per RFC-ACDP-0007 §3.5), `status-001`..`status-004` (registry-state status pattern), `schema-002` and `schema-003` (closed-schema rejections; `schema-001` and `schema-004` are profile-scoped — see discovery and consumer rows), `rate-001` (rate-limit response shape; see note below). When `supports_idempotency_key: true` is advertised in capabilities, `idem-001`..`idem-005` are additionally REQUIRED (`idem-006` describes a tolerated race outcome — see fixture). |
| **`not_implemented` permitted on** | `GET /contexts/search` (registry MAY return 501 if `acdp-registry-discovery` is not advertised); cross-registry resolution endpoints are not part of v0.0.1 protocol surface and are NOT addressable by `not_implemented` |

**Rate-limit conformance note (`rate-001`).** The fixture pins the wire shape (HTTP 429, `application/acdp+json` body with `error.code = "rate_limited"`, optional `Retry-After`). It is informative for cross-impl wire compatibility, but black-box conformance testing cannot deterministically trigger a per-agent rate limit without registry-side cooperation. Implementers MUST self-test by configuring a known per-agent rate and verifying the response shape per the recipe in `schemas/conformance/rate-001-rate-limited-response-shape.json`.

### `acdp-registry-discovery`

Adds keyword search.

| | Required (in addition to `acdp-registry-core`) |
|---|---|
| **HTTP endpoints** | `GET /contexts/search` (RFC-ACDP-0005 §2) |
| **Conformance fixtures** | `vis-002` (search visibility scoping), `vis-003` (response field name `matches`), `vis-005` (private + audience search exclusion per RFC-ACDP-0008 §4.5 / RFC-ACDP-0005 §2.5.5), `vis-006` (visibility disclosure on public matches) and `vis-007` (visibility absence on unauthorized restricted matches) per RFC-ACDP-0005 §2.2, `schema-001` (closed search-response, no `results` synonym) |
| **`not_implemented` permitted on** | None — every endpoint listed above is mandatory once this profile is advertised |

### `acdp-registry-federated`

Adds cross-registry resolution.

| | Required (in addition to `acdp-registry-core`) |
|---|---|
| **HTTP endpoints** | None added — federation is not exposed as a new endpoint; the registry resolves `acdp://` references in `derived_from` chains transparently while serving existing endpoints (RFC-ACDP-0006 §4) |
| **Conformance fixtures** | `fed-001` (HTTPS-only refusal), `fed-002` (RFC 1918 private-IP refusal), `fed-003` (loopback refusal), `fed-004` (link-local + IMDS refusal), `fed-005` (cross-authority redirect refusal), `fed-006` (`registry_did` ↔ authority binding) — covering RFC-ACDP-0006 §7.1, §7.2, §7.5 and §4.1 step 3. Response-size caps (§7.3), timeouts (§7.4), and DNS-rebinding pinning (§7.6) are operational requirements that registry implementers MUST self-test; they are not exposed as standalone fixtures because the protocol surface alone does not allow a black-box assertion (an external observer cannot distinguish "the registry pinned the IP for the connection lifetime" from "the second DNS lookup happened to return the same IP"). |
| **`not_implemented` permitted on** | None |

### `acdp-consumer`

For consumer deployments (libraries, agents). Does not run a registry.

| | Required |
|---|---|
| **Behavioral requirements** | End-to-end signature verification (RFC-ACDP-0001 §5.11) on every retrieved context; `acdp://` cross-registry resolution per RFC-ACDP-0006 if followed (with SSRF protections of §7 if performed server-side); local visibility re-verification per RFC-ACDP-0008 §4.5; tolerance of unknown body / registry-state fields (RFC-ACDP-0001 §6, RFC-ACDP-0004 §4.1, RFC-ACDP-0007 §3.3) |
| **Conformance fixtures** | All `can-*` (including `can-008`, `can-009` for forward-compat hash verification), `sig-001`, `caps-001..006` (capabilities validation), `status-001..004` (registry-state status pattern tolerance), `schema-001..004` (schema openness), the consumer side of `vis-003`, `pub-007` and `schema-002` (publish-response shape), `pub-010` (non-`did:web` contributor tolerance), plus any cross-registry traversal vectors a consumer follows |

## Adding a profile

Open a PR adding a row above and amending RFC-ACDP-0001 §9.1 with the profile's MUST list. Profiles MUST:

- Be a strict superset of any prerequisite.
- Carry conformance fixtures sufficient to validate the additional MUSTs.
- Have a stable name; renames are forbidden.

Reserved future identifiers: `acdp-registry-receipts` (RFC-ACDP-0009 §2.7), `acdp-registry-push` (RFC-ACDP-0009 §2.4), `acdp-registry-walks` (RFC-ACDP-0009 §2.5).
