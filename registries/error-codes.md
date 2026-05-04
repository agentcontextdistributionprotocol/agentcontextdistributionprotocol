# Error Code Registry

ACDP error codes returned in error envelopes (`error.code`). The envelope shape and HTTP status mapping are defined in [RFC-ACDP-0007 §4–5](../rfcs/RFC-ACDP-0007-capabilities.md).

## v0.0.1 codes

| Code | Status | HTTP | Meaning | Source |
|---|---|---|---|---|
| `invalid_signature` | Stable | 400 | Signature verification failed. | [RFC-ACDP-0001 §5.8](../rfcs/RFC-ACDP-0001-core.md#58-signature), [RFC-ACDP-0003 §2.1](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `hash_mismatch` | Stable | 400 | `content_hash` does not match the canonicalized body. | [RFC-ACDP-0001 §5.7](../rfcs/RFC-ACDP-0001-core.md#57-content-hash) |
| `schema_violation` | Stable | 400 | Request body or query failed structural validation. | [RFC-ACDP-0003 §2.1](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `not_authorized` | Stable | 403 | Agent lacks permission for the operation. Call sites: supersession by a different `agent_id` (RFC-ACDP-0003 §3.1 step 3); unauthenticated read on a registry that does not advertise `anonymous_public_reads` (RFC-ACDP-0008 §6.3). | [RFC-ACDP-0003 §3.1](../rfcs/RFC-ACDP-0003-publish.md#31-supersession-constraints), [RFC-ACDP-0008 §6.3](../rfcs/RFC-ACDP-0008-security.md#63-anonymous-reads) |
| `not_found` | Stable | 404 | Resource not found. | [RFC-ACDP-0004 §7](../rfcs/RFC-ACDP-0004-retrieval.md#7-errors) |
| `superseded_target` | Stable | 400 / 409 | The `supersedes` target is invalid (any reason — `details.reason` provides specifics). HTTP 400 for static violations; HTTP 409 Conflict for race conditions (`already_superseded`, `version_mismatch`). | [RFC-ACDP-0003 §2.1 step 9](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing), [§3.1](../rfcs/RFC-ACDP-0003-publish.md#31-supersession-constraints) |
| `unsupported_algorithm` | Stable | 400 | Signature algorithm not in the registry's `supported_signature_algorithms`. | [RFC-ACDP-0001 §5.10](../rfcs/RFC-ACDP-0001-core.md#510-signature-algorithms), [RFC-ACDP-0003 §2.1 step 5](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `rate_limited` | Stable | 429 | Per-agent rate limit exceeded. | [RFC-ACDP-0008 §4.3](../rfcs/RFC-ACDP-0008-security.md#43-rate-limiting) |
| `payload_too_large` | Stable | 413 | Request body exceeds `limits.max_payload_bytes`. | [RFC-ACDP-0003 §2.1 step 2](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `embedded_too_large` | Stable | 413 | An embedded data reference exceeds 64 KB. | [RFC-ACDP-0002 §6.3](../rfcs/RFC-ACDP-0002-context-body.md#63-embedded-form), [RFC-ACDP-0003 §2.1 step 3](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `key_resolution_failed` | Stable | 400 | Permanent DID resolution failure: DID document parsed successfully but does not contain the requested key fragment, or fragment is missing. Producer error. | [RFC-ACDP-0003 §2.1 step 6](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `key_resolution_unreachable` | Stable | 502 | Transient DID resolution failure: DNS, TLS, HTTP non-2xx, or timeout while fetching the DID document. Retryable with backoff. | [RFC-ACDP-0001 §5.11](../rfcs/RFC-ACDP-0001-core.md#511-key-resolution), [RFC-ACDP-0003 §2.1 step 6](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `key_not_authorized` | Stable | 403 | The DID portion of `signature.key_id` (everything before `#`) does not equal `body.agent_id`, or the resolved verification method is not in the DID document's `assertionMethod`. | [RFC-ACDP-0003 §2.1 step 6](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `not_implemented` | Stable | 501 | The requested endpoint requires a profile this registry does not advertise (e.g., `GET /contexts/search` without `acdp-registry-discovery`). All `acdp-registry-core` endpoints are mandatory and MUST NOT return this code. | [RFC-ACDP-0001 §9.1](../rfcs/RFC-ACDP-0001-core.md#91-implementation-profiles), [RFC-ACDP-0007 §4](../rfcs/RFC-ACDP-0007-capabilities.md#4-error-envelope) |
| `cursor_expired` | Stable | 400 | A previously-issued pagination cursor is no longer valid. Client SHOULD restart pagination. | [RFC-ACDP-0005 §2.5.4](../rfcs/RFC-ACDP-0005-discovery.md#254-cursor-stability) |
| `invalid_cursor` | Stable | 400 | A pagination cursor is malformed or unrecognized. | [RFC-ACDP-0005 §2.5.4](../rfcs/RFC-ACDP-0005-discovery.md#254-cursor-stability) |
| `duplicate_publish` | Stable | 409 | An idempotent publish was retried with conflicting content (same `Idempotency-Key`, different `content_hash`). | [RFC-ACDP-0003 §6.2](../rfcs/RFC-ACDP-0003-publish.md#62-registry-behavior) |
| `cross_registry_resolution_failed` | Stable | 502 | A cross-registry resolution failed (DNS resolution refused by IP-range filter, response oversize, timeout, redirect-policy violation, or upstream registry unavailable). See RFC-ACDP-0006 §7. | [RFC-ACDP-0006 §7](../rfcs/RFC-ACDP-0006-cross-registry.md#7-server-side-request-forgery-ssrf-protections) |
| `internal_error` | Stable | 500 | Unexpected registry error. The standard envelope MUST be used; `error.message` MUST NOT leak stack traces or sensitive context. Retryable. | [RFC-ACDP-0007 §4](../rfcs/RFC-ACDP-0007-capabilities.md#4-error-envelope) |

> Note: `visibility_denied` is an internal-only signal (logging/metrics). Visibility denial is always reported externally as `not_found` per RFC-ACDP-0008 §4.5. The wire-visible enum in `acdp-error.schema.json` does NOT include `visibility_denied`.

## Reserved future codes

These codes are NOT in the v0.0.1 wire schema enum. They are reserved for future ACDP versions and MUST NOT appear in v0.0.1 wire responses.

| Code | Reserved for | Reference |
|---|---|---|
| `immutable_field` | v0.1+ mutation endpoints (retraction, attestation updates). No v0.0.1 endpoint mutates a body field. | [RFC-ACDP-0009 §2.1](../rfcs/RFC-ACDP-0009-extensions.md#21-retraction--lifecycle-events-likely-v01) |
| `unsupported_embedding_model` | v0.1+ similarity endpoints. ACDP v0.0.1 has no similarity surface. | [RFC-ACDP-0009 §2.9](../rfcs/RFC-ACDP-0009-extensions.md#29-semantic-similarity-and-embeddings-likely-v01) |

## `superseded_target` reason codes

When returning `superseded_target`, registries SHOULD include `details.reason` to disambiguate. Defined values:

| `details.reason` | Meaning |
|---|---|
| `not_found` | The `supersedes` target does not exist. |
| `lineage_mismatch` | The new context's computed `lineage_id` ≠ the superseded context's `lineage_id`. |
| `version_mismatch` | The new context's `version` ≠ `previous.version + 1`. |
| `already_superseded` | Another context already supersedes the target. |
| `cross_registry_supersession_unsupported` | Registry does not support cross-registry supersession. |

## Adding a code

Open a PR adding a row to the table above. Codes MUST:

- Be lowercase snake_case.
- Not collide with existing entries.
- Be implementable by both registries and consumers (registries emit; consumers handle).
- Carry a single semantic — no overloading. If an existing code already covers the case, reuse it with `details`.

Information leakage rule: `error.message` is informational only and MUST NOT be used in automated decisions. Registries MUST NOT distinguish "not found" from "not authorized" externally for visibility-restricted contexts.
