# RFC-ACDP-0007
# Agent Context Description Protocol (ACDP) — Capabilities & Errors

**Document:** RFC-ACDP-0007
**Version:** 0.0.1-draft
**Status:** Community Standards Track (Draft)

This RFC specifies the registry capability declaration document and the standard error envelope used by all ACDP endpoints.

---

## 1. Status of This Memo

Draft. Backward-incompatible changes remain possible until Final.

---

## 2. Motivation

Two pieces of information must be discoverable about every registry:

1. **What does it support?** — Which signature algorithms, embedding models, and limits.
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
| `limits.max_payload_bytes` | integer | Maximum size of a publish request body in bytes. |
| `limits.max_embedded_bytes` | integer | Maximum decoded size of any embedded data reference. **Fixed at 65536 by the spec.** |

### 3.2 Optional fields

| Field | Type | Description |
|---|---|---|
| `supported_embedding_models` | array of string | Embedding model identifiers indexed by this registry. Empty if registry does not index embeddings (similarity endpoints return 501 Not Implemented). |
| `read_authentication_methods` | array of string | Read-authentication methods supported by this registry. At least one MUST be declared if the registry serves any non-public contexts. Defined values: `http_signatures`, `mtls`, `oauth`. See RFC-ACDP-0008 §6.2. |
| `anonymous_public_reads` | boolean | Whether anonymous (unauthenticated) reads are permitted for public contexts. Default `false`. See RFC-ACDP-0008 §6.3. |

### 3.3 Forward-compatible additions

The capabilities document is `additionalProperties: true` to support forward compatibility — future versions of ACDP will add capability flags here as new features become available. Consumers MUST tolerate unknown fields.

### 3.4 Example

```json
{
  "acdp_version": "0.0.1",
  "registry_did": "did:web:registry.example.com",
  "supported_signature_algorithms": ["ed25519"],
  "supported_embedding_models": [
    "text-embedding-3-large@2026-02"
  ],
  "limits": {
    "max_payload_bytes": 1048576,
    "max_embedded_bytes": 65536
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

`Content-Type` MUST be `application/acdp+json`. The HTTP status code is per the table in §5.

---

## 5. Error Code Registry

The full registry is maintained in [`registries/error-codes.md`](../registries/error-codes.md). The codes defined by v0.0.1:

| Code | HTTP | Meaning | Source |
|---|---|---|---|
| `invalid_signature` | 400 | Signature verification failed. | RFC-ACDP-0001 §5.8, RFC-ACDP-0003 §2.1 |
| `hash_mismatch` | 400 | `content_hash` does not match the canonicalized body. | RFC-ACDP-0001 §5.7, RFC-ACDP-0003 §2.1 |
| `schema_violation` | 400 | Request body or query failed structural validation. | RFC-ACDP-0003 §2.1 |
| `not_authorized` | 403 | Agent lacks permission for the operation. | RFC-ACDP-0003 §3.1 |
| `not_found` | 404 | Resource not found. | RFC-ACDP-0004 §7 |
| `visibility_denied` | 404 | Resource exists but is not visible to the requester (returned as 404 to avoid leaking existence). | RFC-ACDP-0002 §7, RFC-ACDP-0004 §2.3 |
| `superseded_target` | 400 | The `supersedes` target is invalid (any reason — `details.reason` provides specifics). | RFC-ACDP-0003 §3.1 |
| `unsupported_algorithm` | 400 | Signature algorithm not supported by the registry. | RFC-ACDP-0003 §2.1 |
| `unsupported_embedding_model` | 400 | Embedding model not indexed by the registry. | RFC-ACDP-0003 §2.1, RFC-ACDP-0005 §3.1 |
| `rate_limited` | 429 | Per-agent rate limit exceeded. | RFC-ACDP-0008 §4 |
| `payload_too_large` | 413 | Request body exceeds registry limits. | RFC-ACDP-0003 §2.1 |
| `embedded_too_large` | 413 | An embedded data reference exceeds 64 KB. | RFC-ACDP-0002 §6.3 |
| `immutable_field` | 400 | Attempted mutation of an immutable field. | RFC-ACDP-0002 §3 |

### 5.1 Adding a code

New codes are added via the [RFC process](../governance/RFC-PROCESS.md). Codes MUST be lowercase snake_case. Codes MUST NOT collide with existing entries.

### 5.2 Information leakage

Registries MUST NOT reveal which specific policy check failed beyond the registered code. The `error.message` string is informational only and MUST NOT be used in automated decision-making by consumers.

For visibility-restricted contexts, registries MUST return `not_found` with HTTP 404 (the `visibility_denied` semantic) — they MUST NOT distinguish "not found" from "not authorized" externally.

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
