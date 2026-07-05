# Error Code Registry

ACDP error codes returned in error envelopes (`error.code`). The envelope shape and HTTP status mapping are defined in [RFC-ACDP-0007 §4–5](../rfcs/RFC-ACDP-0007-capabilities.md).

## v0.1.0 codes (plus 0.2.0 / 0.3.0 additions, marked)

| Code | Status | HTTP | Meaning | Source |
|---|---|---|---|---|
| `invalid_signature` | Stable | 400 | Signature verification failed. | [RFC-ACDP-0001 §5.8](../rfcs/RFC-ACDP-0001-core.md#58-signature), [RFC-ACDP-0003 §2.1](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `hash_mismatch` | Stable | 400 | The body's `content_hash` (over ProducerContent) does not match the canonicalized body. | [RFC-ACDP-0001 §5.7](../rfcs/RFC-ACDP-0001-core.md#57-content-hash) |
| `data_ref_hash_mismatch` | Stable | 400 | A DataRef's bytes do not match the producer-declared `data_ref.content_hash`. Emitted by a registry at publish time for an embedded `content_hash` mismatch (RFC-ACDP-0002 §6.6 Check 8); also the semantic a consumer surfaces for an external-DataRef fetch mismatch (RFC-ACDP-0002 §6.5). Distinct from `hash_mismatch` (body-level) and `invalid_signature` — the body stays cryptographically valid; only the referenced data diverged. | [RFC-ACDP-0002 §6.5–§6.6](../rfcs/RFC-ACDP-0002-context-body.md#6-data-references), [RFC-ACDP-0007 §5](../rfcs/RFC-ACDP-0007-capabilities.md#5-error-code-registry) |
| `schema_violation` | Stable | 400 | Request body or query failed structural validation. | [RFC-ACDP-0003 §2.1](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `not_authorized` | Stable | 403 | Agent lacks permission for the operation. Call sites: supersession by a different `agent_id` (RFC-ACDP-0003 §3.1 step 3); unauthenticated read on a registry that does not advertise `anonymous_public_reads` (RFC-ACDP-0008 §6.3). | [RFC-ACDP-0003 §3.1](../rfcs/RFC-ACDP-0003-publish.md#31-supersession-constraints), [RFC-ACDP-0008 §6.3](../rfcs/RFC-ACDP-0008-security.md#63-anonymous-reads) |
| `not_found` | Stable | 404 | Resource not found. | [RFC-ACDP-0004 §7](../rfcs/RFC-ACDP-0004-retrieval.md#7-errors) |
| `superseded_target` | Stable | 400 / 409 | The `supersedes` target is invalid (any reason — `details.reason` provides specifics). HTTP 400 for static violations; HTTP 409 Conflict for race conditions (`already_superseded`, `version_mismatch`). | [RFC-ACDP-0001 §5.6.1](../rfcs/RFC-ACDP-0001-core.md#561-lineage-walk-failure), [RFC-ACDP-0003 §2.1 steps 9–10](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing), [§3.1](../rfcs/RFC-ACDP-0003-publish.md#31-supersession-constraints) |
| `unsupported_algorithm` | Stable | 400 | Signature algorithm not in the registry's `supported_signature_algorithms`. | [RFC-ACDP-0001 §5.10](../rfcs/RFC-ACDP-0001-core.md#510-signature-algorithms), [RFC-ACDP-0003 §2.1 step 5](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `rate_limited` | Stable | 429 | Per-agent rate limit exceeded. | [RFC-ACDP-0008 §4.3](../rfcs/RFC-ACDP-0008-security.md#43-rate-limiting) |
| `payload_too_large` | Stable | 413 | Request body exceeds `limits.max_payload_bytes`. | [RFC-ACDP-0003 §2.1 step 2](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `embedded_too_large` | Stable | 413 | An embedded data reference exceeds 64 KB. | [RFC-ACDP-0002 §6.3](../rfcs/RFC-ACDP-0002-context-body.md#63-embedded-form), [RFC-ACDP-0003 §2.1 step 3](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `key_resolution_failed` | Stable | 400 | Permanent DID resolution failure: DID document parsed successfully but does not contain the requested key fragment; fragment is missing from `key_id`; or the producer DID resolves to a network target forbidden by SSRF policy (RFC-ACDP-0008 §4.8). Producer error; not retryable. | [RFC-ACDP-0003 §2.1 step 6](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing), [RFC-ACDP-0008 §4.8](../rfcs/RFC-ACDP-0008-security.md#48-producer-did-resolution-ssrf-protection) |
| `key_resolution_unreachable` | Stable | 502 | Transient DID resolution failure: DNS, TLS, HTTP non-2xx, or timeout while fetching the DID document. Retryable with backoff. | [RFC-ACDP-0001 §5.11](../rfcs/RFC-ACDP-0001-core.md#511-key-resolution), [RFC-ACDP-0003 §2.1 step 6](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `key_not_authorized` | Stable | 403 | The DID portion of `signature.key_id` (everything before `#`) does not equal `body.agent_id`, or the resolved verification method is not in the DID document's `assertionMethod`. | [RFC-ACDP-0003 §2.1 step 6](../rfcs/RFC-ACDP-0003-publish.md#21-registry-processing) |
| `not_implemented` | Stable | 501 | The requested endpoint requires a profile this registry does not advertise (e.g., `GET /contexts/search` without `acdp-registry-discovery`). All `acdp-registry-core` endpoints are mandatory and MUST NOT return this code. | [RFC-ACDP-0001 §9.1](../rfcs/RFC-ACDP-0001-core.md#91-implementation-profiles), [RFC-ACDP-0007 §4](../rfcs/RFC-ACDP-0007-capabilities.md#4-error-envelope) |
| `cursor_expired` | Stable | 400 | A previously-issued pagination cursor is no longer valid. Client SHOULD restart pagination. | [RFC-ACDP-0005 §2.5.4](../rfcs/RFC-ACDP-0005-discovery.md#254-cursor-stability) |
| `invalid_cursor` | Stable | 400 | A pagination cursor is malformed or unrecognized. | [RFC-ACDP-0005 §2.5.4](../rfcs/RFC-ACDP-0005-discovery.md#254-cursor-stability) |
| `duplicate_publish` | Stable | 409 | An idempotent publish was retried with conflicting content (same `Idempotency-Key`, different `content_hash`). | [RFC-ACDP-0003 §6.2](../rfcs/RFC-ACDP-0003-publish.md#62-registry-behavior) |
| `cross_registry_resolution_failed` | Stable | 502 | A cross-registry resolution failed (DNS resolution refused by IP-range filter, response oversize, timeout, redirect-policy violation, or upstream registry unavailable). See RFC-ACDP-0006 §7. | [RFC-ACDP-0006 §7](../rfcs/RFC-ACDP-0006-cross-registry.md#7-server-side-request-forgery-ssrf-protections) |
| `internal_error` | Stable | 500 | Unexpected registry error. The standard envelope MUST be used; `error.message` MUST NOT leak stack traces or sensitive context. Retryable. | [RFC-ACDP-0007 §4](../rfcs/RFC-ACDP-0007-capabilities.md#4-error-envelope) |
| `immutable_field` *(0.3.0)* | Proposed | 400 | A lifecycle (or any future mutation) endpoint request attempted to supply or alter immutable body content (e.g. a `body` member or a body-field-named member on `POST /contexts/{ctx_id}/retract`). Bodies are immutable; lifecycle endpoints mutate registry state only. **Activated from the reserved-codes table below** (reserved since v0.1.0 per RFC-ACDP-0009 §2.1); distinct from `schema_violation` so producers learn the category error. MUST NOT be emitted by implementations declaring `acdp_version` < `0.3.0`. Not retryable. Fixture `lc-002`. | [RFC-ACDP-0013 §6, §10](../rfcs/RFC-ACDP-0013-lifecycle-events.md) |
| `invalid_lifecycle_transition` *(0.3.0)* | Proposed | 409 | The requested lifecycle transition conflicts with the context's current retraction state: `retract` of an already-retracted context, or `republish` of one not retracted (RFC-ACDP-0013 §6 step 4 — strict `retracted`/`republished` alternation). A state conflict, like the 409 arm of `superseded_target`; retryable only after the state changes. MUST NOT be emitted by implementations declaring `acdp_version` < `0.3.0`. Fixture `lc-001` scenario C. | [RFC-ACDP-0013 §6, §10](../rfcs/RFC-ACDP-0013-lifecycle-events.md) |
| `invalid_receipt` *(0.2.0)* | Proposed | 502 | A registry receipt failed the RFC-ACDP-0010 §8 verification procedure. On the wire it is emitted by a federated resolver (or any registry validating an upstream receipt on a caller's behalf) — the upstream registry is at fault, hence 502. It is also the verification-failure category consumer SDKs use in their own diagnostics for a locally failing receipt; in that use the accompanying body's verdict is independent (the producer signature may still verify). There is deliberately no `receipt_unavailable`: registries advertising `acdp-registry-receipts` MUST always mint (RFC-ACDP-0010 §7). MUST NOT be emitted by implementations declaring `acdp_version` `0.1.0`. *(0.3.0)* Also the failure category for lineage-head receipts failing the RFC-ACDP-0011 §7 procedure — RFC-ACDP-0011 deliberately introduces **no new wire code** (its §9); `as_of` staleness within the past is consumer freshness policy, not a wire error. | [RFC-ACDP-0010 §8, §11](../rfcs/RFC-ACDP-0010-registry-receipts.md), [RFC-ACDP-0011 §7, §9](../rfcs/RFC-ACDP-0011-lineage-head-receipts.md) |

> Note: `visibility_denied` is an internal-only signal (logging/metrics). Visibility denial is always reported externally as `not_found` per RFC-ACDP-0008 §4.5. The wire-visible enum in `acdp-error.schema.json` does NOT include `visibility_denied`.

## Reserved future codes

These codes are NOT in the v0.1.0 wire schema enum. They are reserved for future ACDP versions and MUST NOT appear in v0.1.0 wire responses.

| Code | Reserved for | Reference |
|---|---|---|
| `unsupported_embedding_model` | A future version's similarity endpoints. ACDP v0.1.0 has no similarity surface. | [RFC-ACDP-0009 §2.9](../rfcs/RFC-ACDP-0009-extensions.md#29-semantic-similarity-and-embeddings) |

*(0.3.0)* `immutable_field` — reserved here since v0.1.0 for "a future version's mutation endpoints (retraction, attestation updates)" — was **activated** by RFC-ACDP-0013 and moved to the main table above, exactly as `invalid_receipt` graduated in 0.2.0.

## `superseded_target` reason codes

When returning `superseded_target`, registries SHOULD include `details.reason` to disambiguate. Defined values:

| `details.reason` | Meaning |
|---|---|
| `not_found` | The `supersedes` target does not exist. |
| `lineage_mismatch` | The new context's computed `lineage_id` ≠ the superseded context's `lineage_id`. |
| `version_mismatch` | The new context's `version` ≠ `previous.version + 1`. |
| `already_superseded` | Another context already supersedes the target. |
| `cross_registry_supersession_unsupported` | Registry does not support cross-registry supersession. |
| `lineage_walk_failed` | The registry could not retrieve an intermediate context while walking back through `supersedes` to compute `lineage_id`. See [RFC-ACDP-0001 §5.6.1](../rfcs/RFC-ACDP-0001-core.md#561-lineage-walk-failure). |

## Adding a code

Open a PR adding a row to the table above. Codes MUST:

- Be lowercase snake_case.
- Not collide with existing entries.
- Be implementable by both registries and consumers (registries emit; consumers handle).
- Carry a single semantic — no overloading. If an existing code already covers the case, reuse it with `details`.

Information leakage rule: `error.message` is informational only and MUST NOT be used in automated decisions. Registries MUST NOT distinguish "not found" from "not authorized" externally for visibility-restricted contexts.
