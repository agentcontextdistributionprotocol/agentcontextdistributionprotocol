# RFC-ACDP-0007
# Agent Context Description Protocol (ACDP) — Capabilities & Errors

**Document:** RFC-ACDP-0007
**Version:** 0.0.1
**Status:** Community Standards Track (Draft)

This RFC specifies the registry capability declaration document and the standard error envelope used by all ACDP endpoints.

---

## 1. Status of This Memo

This document is a Draft. Backward-incompatible changes remain possible until Final.

---

## 2. Motivation

Two pieces of information must be discoverable about every registry:

1. **What does it support?** — Which signature algorithms, profiles, and limits.
2. **How does it report failures?** — A consistent error envelope and code registry, so consumers can react programmatically.

Both must be discoverable without prior bilateral configuration. The well-known capabilities document and the standard error envelope serve those needs respectively.

---

## 3. Capabilities Document

```
GET /.well-known/acdp.json
```

Returns the registry's capability declaration. Conforms to [`schemas/json/acdp-capabilities.schema.json`](../schemas/json/acdp-capabilities.schema.json).

### 3.1 Required fields

| Field | Type | Description |
|---|---|---|
| `acdp_version` | string | The ACDP specification version this registry implements. Form: `<major>.<minor>.<patch>`. |
| `registry_did` | string | The registry's own DID, typically `did:web:<hostname>`. |
| `supported_signature_algorithms` | array of string | Signature algorithms accepted on publish. MUST contain at least `"ed25519"`. |
| `supported_did_methods` | array of string | DID methods this registry can resolve. MUST be non-empty and MUST include `"did:web"` (RFC-ACDP-0001 §5.4 mandates `did:web` for v0.0.1 producers; RFC-ACDP-0001 §5.11 specifies the resolution algorithm). |
| `profiles` | array of string | Profile(s) this implementation claims conformance to. Any registry MUST declare at least `"acdp-registry-core"`. See RFC-ACDP-0001 §9. |
| `limits.max_payload_bytes` | integer | Maximum size of a publish request body in bytes. |
| `limits.max_embedded_bytes` | integer | Maximum decoded size of any embedded data reference. **Fixed at 65536 by the spec.** |

### 3.2 Optional fields

| Field | Type | Description |
|---|---|---|
| `read_authentication_methods` | array of string | Read-authentication methods supported by this registry. At least one MUST be declared if the registry serves any non-public contexts. Defined values: `http_signatures`, `mtls`, `oauth`. See RFC-ACDP-0008 §6.2. |
| `anonymous_public_reads` | boolean | Whether anonymous (unauthenticated) reads are permitted for public contexts. Default `false`. See RFC-ACDP-0008 §6.3. |
| `supports_idempotency_key` | boolean | Whether this registry honors the `Idempotency-Key` header on `POST /contexts`. Default `false`. See RFC-ACDP-0003 §6. |
| `limits.idempotency_key_ttl_seconds` | integer | How long this registry retains idempotency-key mappings, in seconds. MUST be present when `supports_idempotency_key` is true. Range 86400 (24h) to 604800 (7d). |

### 3.3 Forward-compatible additions

The capabilities document is `additionalProperties: true` to support forward compatibility — future versions of ACDP will add capability flags here as new features become available. Consumers MUST tolerate unknown fields.

### 3.4 Example

```json
{
  "acdp_version": "0.0.1",
  "registry_did": "did:web:registry.example.com",
  "supported_signature_algorithms": ["ed25519"],
  "supported_did_methods": ["did:web"],
  "read_authentication_methods": ["http_signatures"],
  "anonymous_public_reads": true,
  "supports_idempotency_key": true,
  "profiles": ["acdp-registry-core", "acdp-registry-discovery"],
  "limits": {
    "max_payload_bytes": 1048576,
    "max_embedded_bytes": 65536,
    "idempotency_key_ttl_seconds": 86400
  }
}
```

### 3.5 Caching

The capabilities document is moderately stable. Registries SHOULD set:

```
Cache-Control: public, max-age=3600
```

Consumers MUST refresh the capabilities document at least daily, and MUST refresh on receipt of any error code that suggests version drift (e.g. `unsupported_algorithm` for an algorithm the consumer believed was supported).

---

## 4. Error Envelope

All error responses use the following structure, conforming to [`schemas/json/acdp-error.schema.json`](../schemas/json/acdp-error.schema.json):

```json
{
  "error": {
    "code": "...",
    "message": "Human-readable description",
    "details": {}
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `error.code` | string | Yes | A machine-readable error code from §5. |
| `error.message` | string | Yes | Human-readable description, suitable for logs. MUST NOT be used for automated decisions. |
| `error.details` | object | No | Optional structured details. Shape is error-code-specific. |

`Content-Type` MUST be `application/acdp+json`. The HTTP status code is per the table in §5. The error envelope MUST be returned for **every** failure response from an ACDP endpoint, including 4xx, 5xx, 501 Not Implemented, and 502 Bad Gateway responses. Registries MUST NOT return empty bodies, framework default error pages, or non-`application/acdp+json` content types on ACDP endpoints. The corresponding fixture is `err-001-internal-error.json` (illustrating a 500 envelope).

---

## 5. Error Code Registry

The full registry is maintained in [`registries/error-codes.md`](../registries/error-codes.md). The codes defined by v0.0.1:

| Code | HTTP | Meaning | Source |
|---|---|---|---|
| `invalid_signature` | 400 | Signature verification failed. | RFC-ACDP-0001 §5.8, RFC-ACDP-0003 §2.1 |
| `hash_mismatch` | 400 | `content_hash` does not match the canonicalized body. | RFC-ACDP-0001 §5.7, RFC-ACDP-0003 §2.1 |
| `schema_violation` | 400 | Request body or query failed structural validation. | RFC-ACDP-0003 §2.1 |
| `not_authorized` | 403 | Agent lacks permission for the operation. Returned for supersession by a different `agent_id`, and for unauthenticated reads on a registry that does not advertise `anonymous_public_reads`. | RFC-ACDP-0003 §3.1, RFC-ACDP-0008 §6.3 |
| `not_found` | 404 | Resource not found. (Also returned for visibility-restricted contexts to non-audience requesters; see RFC-ACDP-0008 §4.5.) | RFC-ACDP-0004 §7 |
| `superseded_target` | 400 / 409 | The `supersedes` target is invalid. `details.reason` provides specifics. HTTP 400 for static violations (`not_found`, `lineage_mismatch`, `cross_registry_supersession_unsupported`); HTTP 409 Conflict for race conditions (`already_superseded`, `version_mismatch`). | RFC-ACDP-0003 §2.1 step 9, §3.1 |
| `unsupported_algorithm` | 400 | Signature algorithm not in the registry's `supported_signature_algorithms`. | RFC-ACDP-0001 §5.10, RFC-ACDP-0003 §2.1 step 5 |
| `rate_limited` | 429 | Per-agent rate limit exceeded. | RFC-ACDP-0008 §4.3 |
| `payload_too_large` | 413 | Request body exceeds `limits.max_payload_bytes`. | RFC-ACDP-0003 §2.1 step 2 |
| `embedded_too_large` | 413 | An embedded data reference exceeds 64 KB. | RFC-ACDP-0002 §6.3, RFC-ACDP-0003 §2.1 step 3 |
| `key_resolution_failed` | 400 | The signing key referenced by `signature.key_id` could not be resolved due to a permanent condition (DID document parsed successfully but does not contain the requested key fragment, or fragment is missing from `key_id`). Producer error; not retryable. | RFC-ACDP-0003 §2.1 step 6 |
| `key_resolution_unreachable` | 502 | The signing key could not be resolved due to a transient condition (DNS failure, TLS error, HTTP non-2xx, network timeout fetching the DID document). Retryable with backoff. | RFC-ACDP-0003 §2.1 step 6 |
| `key_not_authorized` | 403 | The DID portion of `signature.key_id` does not equal `body.agent_id`, or the resolved verification method is not in the DID document's `assertionMethod` array. | RFC-ACDP-0003 §2.1 step 6 |
| `not_implemented` | 501 | Endpoint or capability not implemented by this registry. Returned with the standard error envelope. Emitted when the requested endpoint requires a profile this registry does not advertise (e.g., `GET /contexts/search` on a registry that does not declare `acdp-registry-discovery` in `profiles`). All `acdp-registry-core` endpoints are mandatory and MUST NOT return `not_implemented`. | RFC-ACDP-0001 §9.1, RFC-ACDP-0007 §4 |
| `cursor_expired` | 400 | A previously-issued pagination cursor is no longer valid. Client SHOULD restart pagination. | RFC-ACDP-0005 §2.5.4 |
| `invalid_cursor` | 400 | A pagination cursor is malformed or unrecognized. | RFC-ACDP-0005 §2.5.4 |
| `duplicate_publish` | 409 | An idempotent publish was retried with conflicting content (same `Idempotency-Key`, different `content_hash`). | RFC-ACDP-0003 §6.2 |
| `cross_registry_resolution_failed` | 502 | A cross-registry resolution failed (DNS resolution refused, response oversize, timeout, redirect-policy violation, or upstream registry unavailable). | RFC-ACDP-0006 §7 |
| `internal_error` | 500 | The registry encountered an unexpected internal condition. The standard error envelope MUST be used; `error.message` MUST NOT leak stack traces or sensitive context. Retryable. | RFC-ACDP-0007 §4 |

> **Reserved codes (not in this table or the v0.0.1 wire enum):** `immutable_field` is reserved for v0.1+ mutation endpoints (retraction, attestation updates — see RFC-ACDP-0009 §2.1). `unsupported_embedding_model` is reserved for v0.1+ similarity endpoints (see RFC-ACDP-0009 §2.9). Implementations MUST NOT emit either in v0.0.1 responses.

### 5.1 Adding a code

New codes are added via the [RFC process](../governance/RFC-PROCESS.md). Codes MUST be lowercase snake_case. Codes MUST NOT collide with existing entries.

### 5.2 Information leakage

Registries MUST NOT reveal which specific policy check failed beyond the registered code. The `error.message` string is informational only and MUST NOT be used in automated decision-making by consumers.

For visibility-restricted contexts, registries MUST return `not_found` (HTTP 404) — they MUST NOT distinguish "not found" from "not authorized" externally. The internal label `visibility_denied` MAY be used in registry logs or metrics for auditing purposes but MUST NOT appear in wire responses.

---

## 6. Security Considerations

See [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md). Specific to capabilities and errors:

- The capabilities document MUST be served over TLS.
- Registries SHOULD include the same `registry_did` value across all responses to avoid identity confusion.
- Error messages MUST NOT echo unsanitized request content (defends against XSS in registry-served clients and injection into log pipelines).
- Rate-limit responses (`rate_limited`) SHOULD include `Retry-After` headers when bounded.

---

## 7. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0003 Publish](RFC-ACDP-0003-publish.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0005 Discovery](RFC-ACDP-0005-discovery.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
