# RFC-ACDP-0007
# Agent Context Distribution Protocol (ACDP) — Capabilities & Errors

**Document:** RFC-ACDP-0007
**Version:** 0.3.0
**Status:** Community Standards Track (Final)

This RFC specifies the registry capability declaration document and the standard error envelope used by all ACDP endpoints.

---

## 1. Status of This Memo

This document is a Final ACDP specification (acdp/0.1.0, with Final amendments through acdp/0.3.0). It is stable for the released lines; subsequent breaking changes require a new RFC and a version bump per [VERSIONING.md](../VERSIONING.md).

Passages marked *(0.2.0)* are amendments from the acdp/0.2.0 Trust & Hardening program. Passages marked *(0.3.0)* are amendments from the acdp/0.3.0 program (mandatory Idempotency-Key support per RFC-ACDP-0003 §6.4, the OPTIONAL `limits.max_publish_per_minute` capabilities field, and the RFC-ACDP-0011/0012/0013 surfaces). Both lines are **Final** as of 2026-07-05, promoted after their conformance packs passed against two independent interoperating implementations (see [CHANGELOG.md](../CHANGELOG.md)); the markers record provenance, not status. Neither set changes any v0.1.0 body field, hash, or signature semantic; everything not so marked remains Final and wire-frozen for acdp/0.1.0.

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
| `supported_did_methods` | array of string | DID methods this registry can resolve. MUST be non-empty and MUST include `"did:web"` (RFC-ACDP-0001 §5.4 mandates `did:web` for v0.1.0 producers; RFC-ACDP-0001 §5.11 specifies the resolution algorithm). *(0.2.0)* MAY additionally include `"did:key"` (pure resolution per RFC-ACDP-0001 §5.11.1). A registry that does **not** advertise `"did:key"` MUST reject a `did:key` publish with `key_resolution_failed` (permanent, HTTP 400) — this code choice is pinned here and by fixture `dk-003`: the condition is producer-caused and not retryable against this registry, so `key_resolution_unreachable` (transient, 502) and `unsupported_algorithm` (the *algorithm* may well be supported) are both wrong. |
| `profiles` | array of string | Profile(s) this implementation claims conformance to. Any registry MUST declare at least `"acdp-registry-core"`. See RFC-ACDP-0001 §9. *(0.2.0)* The profile `"acdp-registry-receipts"` (RFC-ACDP-0010 §11) declares that the registry mints and serves registry receipts on every publish response and full retrieval — advertising it is a hard commitment: there is no degraded "receipts sometimes" mode and no `receipt_unavailable` error. Registries advertising it MUST also advertise `acdp_version` ≥ `0.2.0`. |
| `limits.max_payload_bytes` | integer | Maximum size of a publish request body in bytes. |
| `limits.max_embedded_bytes` | integer | Maximum decoded size of any embedded data reference. **Fixed at 65536 by the spec.** |

### 3.2 Optional fields

| Field | Type | Description |
|---|---|---|
| `read_authentication_methods` | array of string | Read-authentication methods supported by this registry. At least one MUST be declared if the registry serves any non-public contexts. Defined values: `http_signatures`, `mtls`, `oauth`. See RFC-ACDP-0008 §6.2. |
| `anonymous_public_reads` | boolean | Whether anonymous (unauthenticated) reads are permitted for public contexts. Default `false`. See RFC-ACDP-0008 §6.3. |
| `supports_idempotency_key` | boolean | Whether this registry honors the `Idempotency-Key` header on `POST /contexts`. Default `false`. See RFC-ACDP-0003 §6. *(0.3.0)* A registry advertising `acdp_version` ≥ 0.3.0 MUST support the header and MUST advertise this field as `true` — the field stays in the document for introspection even though its value is no longer free (RFC-ACDP-0003 §6.4; §3.5 item 10; fixture `idem-007`). |
| `limits.idempotency_key_ttl_seconds` | integer | How long this registry retains idempotency-key mappings, in seconds. MUST be present when `supports_idempotency_key` is true. Range 86400 (24h) to 604800 (7d). |
| `limits.max_publish_per_minute` | integer | *(0.3.0)* OPTIONAL. The nominal per-agent publish ceiling this registry enforces on `POST /contexts`, in requests per minute. Integer ≥ 1. Advisory: producers SHOULD use it to pace publishes below the limiter's threshold. Its presence does NOT change the RFC-ACDP-0008 §4.3 requirements — per-agent rate limiting is REQUIRED whether or not the ceiling is advertised, and 429 responses MUST still carry `Retry-After`. The `limits` sub-object is a closed schema (§3.3.1), so this field is a 0.3.0 schema addition: strict pre-0.3.0 validators of `limits` will reject documents carrying it (same compatibility posture as `registry_receipt` on the closed publish response — validators must track the additive schema edit). Fixture `caps-007`. |

### 3.3 Forward-compatible additions

The capabilities document is `additionalProperties: true` to support forward compatibility — future versions of ACDP will add capability flags here as new features become available. Consumers MUST tolerate unknown fields.

**Implementer note.** The `CapabilitiesDocument` model MUST be deserialized with unknown-field tolerance enabled. Concrete patterns:

- **Rust (serde):** add `#[serde(flatten)] pub extensions: serde_json::Map<String, serde_json::Value>` (or a typed `BTreeMap<String, Value>`) to capture unknown keys; do NOT annotate the struct with `#[serde(deny_unknown_fields)]`.
- **Python (pydantic v2):** set `model_config = ConfigDict(extra="allow")` on the capabilities model, OR keep the model loose and operate on `dict[str, Any]` for unknown keys.
- **Python (dataclasses or attrs):** keep an explicit catch-all field (e.g. `extensions: dict[str, Any] = field(default_factory=dict)`) and route unknown keys into it.
- **TypeScript:** no action needed by default — object types are open. Runtime decoders (zod, valibot) MUST use a passthrough or partial-strict mode (e.g. zod's `.passthrough()`); decoders configured to strip or fail unknown keys MUST NOT be used.
- **Go:** unmarshalling into `map[string]any` or a struct with an `Extensions json.RawMessage` field both work; do NOT use `json.UnmarshalDisallowUnknownFields`.

Libraries that throw, panic, or strip unknown fields will break silently the next time ACDP adds a capability flag — for example, when push subscriptions ship in a future version, registries will start advertising `supports_push_subscriptions: true`, and a strict-decoder consumer will fail to read the document at all. The same forward-compat policy applies to the `status` field on registry state (RFC-ACDP-0004 §4.1).

#### 3.3.1 Schema openness map (NORMATIVE)

ACDP uses a mix of CLOSED schemas (`additionalProperties: false`, used for tightly defined wire shapes where unknown fields signal a bug) and OPEN schemas (`additionalProperties: true`, used where forward compatibility matters). Consumers and registries MUST honor each schema's openness exactly as documented; treating a closed schema as open masks bugs, and treating an open schema as closed breaks forward compatibility.

| Schema | Openness | `additionalProperties` |
|---|---|---|
| `acdp-publish-request.schema.json` | **Closed** | `false` |
| `acdp-publish-response.schema.json` | **Closed** | `false` |
| `acdp-search-response.schema.json` | **Closed** | `false` |
| `acdp-error.schema.json` | **Closed** | `false` |
| `acdp-error.schema.json` (`error.details`) | **Open** | `true` |
| `acdp-data-ref.schema.json` (`DataRef` root object) | **Open** | `true` |
| `acdp-data-ref.schema.json` (`embedded` sub-object) | **Closed** | `false` |
| `acdp-data-ref.schema.json` (structured `location` object) | **Open** | `true` |
| `acdp-context-body.schema.json` (`Body` for retrieval) | **Open** | `true` |
| `acdp-capabilities.schema.json` (top level) | **Open** | `true` |
| `acdp-capabilities.schema.json` (`limits` sub-object) | **Closed** | `false` |
| `acdp-context.schema.json` (full retrieval envelope) | **Open** | `true` |
| `acdp-registry-state.schema.json` | **Open** | `true` |
| `match_summary` (in `acdp-common.schema.json`) | **Closed** | `false` |
| `signature` (in `acdp-common.schema.json`) | **Closed** | `false` |
| `data_period` (in `acdp-common.schema.json`) | **Closed** | `false` |
| `acdp-registry-receipt.schema.json` *(0.2.0)* | **Closed** | `false` |
| `acdp-lineage-head-receipt.schema.json` *(0.3.0)* | **Closed** | `false` |
| `acdp-log-leaf.schema.json` *(0.3.0)* | **Closed** | `false` |
| `acdp-log-checkpoint.schema.json` *(0.3.0)* | **Closed** | `false` |
| `acdp-log-inclusion.schema.json` *(0.3.0)* | **Closed** | `false` |
| `acdp-lifecycle-event.schema.json` *(0.3.0)* | **Closed** | `false` — the event *object* is closed (every member is signed where a signature is present, RFC-ACDP-0013 §4); the `event_type` *vocabulary* is open (`registries/lifecycle-event-types.md`) |
Conformant consumers MUST reject deserializing a closed-schema object that contains fields not defined in the schema (`schema_violation`). Conformant consumers MUST NOT reject deserializing an open-schema object that contains unknown fields. The fixtures pin specific instances of both rules:

- **Open (tolerate):** `caps-006`/`schema-004` (capabilities document top level), `can-008` (unknown field at the body root), `can-010` (unknown field inside a `data_refs[]` entry).
- **Closed (reject):** `pub-007`/`schema-002` (publish response — forbid extras like `content_hash`), `schema-001` (search response — forbid `results`), `schema-003` (DataRef `embedded` sub-object), `schema-008` (`signature` object), `schema-009` (`data_period` object), `schema-010` (capabilities `limits` sub-object).

The table above governs every shape across the schema set; the fixtures are representative, not exhaustive.

*(0.3.0)* Closed does not mean frozen: a closed schema can still gain a field through an additive schema edit in a minor version — the closure means only that fields *not in the schema* are rejected. The `limits` sub-object remains **Closed** (`additionalProperties: false`) and gains the OPTIONAL `max_publish_per_minute` field in 0.3.0 (§3.2), exactly as the closed publish response gained `registry_receipt` in 0.2.0. Validators MUST track the current schema text; a `limits` object carrying any field beyond `max_payload_bytes`, `max_embedded_bytes`, `idempotency_key_ttl_seconds`, and *(0.3.0)* `max_publish_per_minute` remains a `schema_violation` (fixture `schema-010`).

### 3.4 Example

```json
{
  "acdp_version": "0.1.0",
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

### 3.5 Consumer validation checklist (NORMATIVE)

After fetching `/.well-known/acdp.json`, consumers and cross-registry resolvers MUST validate the following before relying on the document. Schema validation alone is necessary but not sufficient — the items marked **(value)** below are not enforceable by the JSON Schema in all toolchains, so implementations MUST verify them in code.

1. `acdp_version` matches the semver pattern `^\d+\.\d+\.\d+$`.
2. `registry_did` is a valid DID. For v0.1.0 registries, `registry_did` MUST be `did:web:<authority>`, and `<authority>` MUST equal the hostname the capabilities document was fetched from. **(value, cross-field)**
3. `supported_signature_algorithms` MUST contain `"ed25519"`.
4. `supported_did_methods` MUST contain `"did:web"`.
5. `profiles` MUST contain `"acdp-registry-core"`.
6. `limits.max_embedded_bytes` MUST equal `65536`.
7. `limits.max_payload_bytes` MUST be `>= 1024`.
8. If `supports_idempotency_key` is `true`, `limits.idempotency_key_ttl_seconds` MUST be present and in the inclusive range `86400..604800` (24h to 7d).
9. If the registry serves any non-public contexts, `read_authentication_methods` MUST be non-empty (RFC-ACDP-0008 §6.2). **(value, cross-field)**
10. *(0.3.0)* If `acdp_version` ≥ `0.3.0`, `supports_idempotency_key` MUST be present and `true` (RFC-ACDP-0003 §6.4) — and check 8 therefore always applies. A 0.3.0-advertising registry without idempotency support is self-contradictory and NON-CONFORMANT. **(value, cross-field)** Fixture `idem-007`.
11. *(0.3.0)* If `limits.max_publish_per_minute` is present, it MUST be an integer ≥ 1 (schema-enforced: zero, negative, or non-integer values are a `schema_violation`). Fixture `caps-007`.

A consumer encountering a capabilities document that fails any of the checks above MUST NOT proceed with the operation that required fetching capabilities (publish, retrieval, cross-registry resolution). Implementations SHOULD surface the failing check to operators so the registry can be corrected. The conformance fixtures `caps-001..007` (`schemas/conformance/caps-001-valid-minimal.json` through `caps-007-max-publish-per-minute.json`) plus *(0.3.0)* `idem-007` pin representative positive and negative payloads for the checklist.

#### 3.5.1 Implementer note: validate capabilities at server construction time

The conditional and cross-field constraints above (`registry_did` must bind to the serving authority; `limits.max_embedded_bytes` is fixed at 65536; `limits.idempotency_key_ttl_seconds` is REQUIRED when `supports_idempotency_key = true` and is bounded to [86400, 604800]) are enforceable in code but not by JSON Schema in all toolchains. Registry implementers SHOULD validate the capabilities document they intend to serve **at server construction time, not at runtime per request**. A server that runs the §3.5 checklist once at startup cannot silently start serving with misconfigured limits, a mismatched `registry_did`, or a missing idempotency TTL. Recommended pattern (pseudocode, illustrative):

```
server = RegistryServer.try_new(store, caps, authority)
  # raises a typed configuration error at startup if any of the following hold:
  # - caps.registry_did != "did:web:" + authority
  # - "ed25519" not in caps.supported_signature_algorithms
  # - "did:web" not in caps.supported_did_methods
  # - "acdp-registry-core" not in caps.profiles
  # - caps.limits.max_embedded_bytes != 65536
  # - caps.limits.max_payload_bytes < 1024
  # - caps.supports_idempotency_key == true AND
  #     (caps.limits.idempotency_key_ttl_seconds is None
  #      or not 86400 <= caps.limits.idempotency_key_ttl_seconds <= 604800)
  # - caps.acdp_version >= 0.3.0 AND caps.supports_idempotency_key != true   (0.3.0)
  # - caps.limits.max_publish_per_minute is not None
  #     AND caps.limits.max_publish_per_minute < 1                           (0.3.0)
  # - caps serves any non-public visibility AND caps.read_authentication_methods is empty
```

Concrete idioms:

- **Rust:** a `RegistryServer::try_new(store, caps, authority) -> Result<Self, ConfigError>` constructor that enumerates the checks above and returns a typed error per failure. Library APIs SHOULD prefer this over an infallible `RegistryServer::new` followed by per-request validation.
- **Python:** raise `ValueError` (or a typed `RegistryConfigError`) from the registry application factory before binding the listening socket.
- **Go:** return a non-nil error from the `NewRegistryServer` constructor; callers `log.Fatal` rather than starting `http.ListenAndServe`.
- **TypeScript:** throw from the constructor or factory function before the framework starts listening.

The principle is uniform across languages: a misconfigured registry MUST refuse to start. Per-request validation is a defense-in-depth fallback for configuration that mutates at runtime (rare) and for capabilities documents fetched from external sources (consumer-side §3.5).

### 3.6 Caching

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

The full registry is maintained in [`registries/error-codes.md`](../registries/error-codes.md). The codes defined by v0.1.0:

| Code | HTTP | Meaning | Source |
|---|---|---|---|
| `invalid_signature` | 400 | Signature verification failed. | RFC-ACDP-0001 §5.8, RFC-ACDP-0003 §2.1 |
| `hash_mismatch` | 400 | The body's `content_hash` (over ProducerContent) does not match the canonicalized body. | RFC-ACDP-0001 §5.7, RFC-ACDP-0003 §2.1 |
| `data_ref_hash_mismatch` | 400 | A DataRef's bytes do not match the producer-declared `data_ref.content_hash`. Returned by a registry at publish time when an embedded `data_ref.content_hash` does not match the decoded `embedded.content` (RFC-ACDP-0002 §6.6 Check 8). Also the code a consumer SHOULD surface when it fetches an external `data_ref.location` and the retrieved bytes do not match `data_ref.content_hash` (RFC-ACDP-0002 §6.5). The body's own `content_hash` and signature are still valid — the integrity failure is at the data-reference level, not the body level. | RFC-ACDP-0002 §6.5, §6.6 |
| `schema_violation` | 400 | Request body or query failed structural validation. | RFC-ACDP-0003 §2.1 |
| `not_authorized` | 403 | Agent lacks permission for the operation. Returned for supersession by a different `agent_id`, and for unauthenticated reads on a registry that does not advertise `anonymous_public_reads`. | RFC-ACDP-0003 §3.1, RFC-ACDP-0008 §6.3 |
| `not_found` | 404 | Resource not found. (Also returned for visibility-restricted contexts to non-audience requesters; see RFC-ACDP-0008 §4.5.) | RFC-ACDP-0004 §7 |
| `superseded_target` | 400 / 409 | The `supersedes` target is invalid. `details.reason` provides specifics. HTTP 400 for static violations (`not_found`, `lineage_mismatch`, `cross_registry_supersession_unsupported`, `lineage_walk_failed`); HTTP 409 Conflict for race conditions (`already_superseded`, `version_mismatch`). | RFC-ACDP-0001 §5.6.1, RFC-ACDP-0003 §2.1 steps 9–10, §3.1 |
| `unsupported_algorithm` | 400 | Signature algorithm not in the registry's `supported_signature_algorithms`. | RFC-ACDP-0001 §5.10, RFC-ACDP-0003 §2.1 step 5 |
| `rate_limited` | 429 | Per-agent rate limit exceeded. | RFC-ACDP-0008 §4.3 |
| `payload_too_large` | 413 | Request body exceeds `limits.max_payload_bytes`. | RFC-ACDP-0003 §2.1 step 2 |
| `embedded_too_large` | 413 | An embedded data reference exceeds 64 KB. | RFC-ACDP-0002 §6.3, RFC-ACDP-0003 §2.1 step 3 |
| `key_resolution_failed` | 400 | The signing key referenced by `signature.key_id` could not be resolved due to a permanent condition: the DID document parsed successfully but does not contain the requested key fragment; the fragment is missing from `key_id`; or the producer DID resolves to a network target forbidden by SSRF policy (RFC-ACDP-0008 §4.8). Producer error; not retryable. | RFC-ACDP-0003 §2.1 step 6, RFC-ACDP-0008 §4.8 |
| `key_resolution_unreachable` | 502 | The signing key could not be resolved due to a transient condition (DNS failure, TLS error, HTTP non-2xx, network timeout fetching the DID document). Retryable with backoff. | RFC-ACDP-0003 §2.1 step 6 |
| `key_not_authorized` | 403 | The DID portion of `signature.key_id` does not equal `body.agent_id`, or the resolved verification method is not in the DID document's `assertionMethod` array. | RFC-ACDP-0003 §2.1 step 6 |
| `not_implemented` | 501 | Endpoint or capability not implemented by this registry. Returned with the standard error envelope. Emitted when the requested endpoint requires a profile this registry does not advertise (e.g., `GET /contexts/search` on a registry that does not declare `acdp-registry-discovery` in `profiles`). All `acdp-registry-core` endpoints are mandatory and MUST NOT return `not_implemented`. | RFC-ACDP-0001 §9.1, RFC-ACDP-0007 §4 |
| `cursor_expired` | 400 | A previously-issued pagination cursor is no longer valid. Client SHOULD restart pagination. | RFC-ACDP-0005 §2.5.4 |
| `invalid_cursor` | 400 | A pagination cursor is malformed or unrecognized. | RFC-ACDP-0005 §2.5.4 |
| `duplicate_publish` | 409 | An idempotent publish was retried with conflicting content (same `Idempotency-Key`, different `content_hash`). | RFC-ACDP-0003 §6.2 |
| `cross_registry_resolution_failed` | 502 | A cross-registry resolution failed (DNS resolution refused, response oversize, timeout, redirect-policy violation, or upstream registry unavailable). | RFC-ACDP-0006 §7 |
| `invalid_receipt` *(0.2.0)* | 502 | A registry receipt failed the RFC-ACDP-0010 §8 verification procedure (signature, registry/authority binding, context binding, content binding, key binding, or timestamp form). Emitted on the wire by a federated resolver (or any registry validating an upstream receipt on a caller's behalf) about a receipt obtained from an upstream registry — hence 502, the upstream is at fault. It is also the verification-failure **category** consumer SDKs MUST use in their own diagnostics when a locally verified receipt fails; in that consumer-side use it does not invalidate the body, whose producer signature is judged independently (RFC-ACDP-0010 §8). There is deliberately no `receipt_unavailable`: registries advertising `acdp-registry-receipts` MUST always mint (RFC-ACDP-0010 §7), so a missing receipt from such a registry is a registry fault, not an error category. | RFC-ACDP-0010 §8, §11 |
| `immutable_field` *(0.3.0)* | 400 | A lifecycle (or any future mutation) endpoint request attempted to supply or alter immutable body content — e.g. a `body` member or a body-field-named member on `POST /contexts/{ctx_id}/retract`. Bodies are immutable; lifecycle endpoints mutate registry state only. Activated by RFC-ACDP-0013 §6 from the reservation held since v0.1.0 (RFC-ACDP-0009 §2.1); distinct from `schema_violation` so producers learn the category error. Not retryable. | RFC-ACDP-0013 §6, §10 |
| `invalid_lifecycle_transition` *(0.3.0)* | 409 | The requested lifecycle transition conflicts with the context's current retraction state (retract of an already-retracted context; republish of a never-retracted one). A state conflict, like the 409 arm of `superseded_target`; retryable only after the state changes. | RFC-ACDP-0013 §6 step 4, §10 |
| `invalid_log_proof` *(0.3.0)* | 502 | A transparency-log artifact failed the RFC-ACDP-0012 §9 verification procedures: an inclusion proof whose folded audit path does not reproduce the checkpoint's `root_hash`, a consistency proof that fails between two tree sizes of the same `log_id`, or a checkpoint whose signature does not verify over the recomputed preimage. Deliberately **not** `invalid_receipt`: a proof failure indicts the log, not the receipt, and the verdicts are independent (RFC-ACDP-0012 §9.3). Emitted on the wire by a federated resolver (or any registry validating an upstream's proofs on a caller's behalf) — hence 502, the upstream is at fault; also the verification-failure category consumer SDKs use for locally failing proofs. Malformed proof requests are `schema_violation`; an unlogged or invisible `ctx_id` on `GET /log/proof` is `not_found`; there is deliberately no `log_unavailable` (RFC-ACDP-0012 §7). | RFC-ACDP-0012 §9, §11 |
| `internal_error` | 500 | The registry encountered an unexpected internal condition. The standard error envelope MUST be used; `error.message` MUST NOT leak stack traces or sensitive context. Retryable. | RFC-ACDP-0007 §4 |

> **Reserved codes (not in this table or the v0.1.0 wire enum):** `unsupported_embedding_model` is reserved for a future version's similarity endpoints (see RFC-ACDP-0009 §2.9). Implementations MUST NOT emit it. *(0.2.0)* `invalid_receipt` graduated from reserved space into the table above and the wire enum; implementations declaring `acdp_version` `0.1.0` MUST NOT emit it. *(0.3.0)* `immutable_field` — reserved for "a future version's mutation endpoints" since v0.1.0 — is activated by RFC-ACDP-0013 and likewise graduates, together with the new `invalid_lifecycle_transition`; and `invalid_log_proof` is added via the §5.1 process by RFC-ACDP-0012 (it was never in reserved space — RFC-ACDP-0009 §2.11 reserved field/endpoint/profile names only). Implementations declaring `acdp_version` < `0.3.0` MUST NOT emit any of the three.
**Distinguishing hash failures.** Three failure codes can arise from integrity checks; implementations MUST keep them distinct so consumers can react correctly:

- `hash_mismatch` — the body's ProducerContent hash, recomputed by the registry or consumer, does not match `body.content_hash`. The body's signed content cannot be verified; the **body is untrusted**.
- `data_ref_hash_mismatch` — a DataRef's fetched (external) or decoded (embedded) bytes do not match the producer-declared `data_ref.content_hash`. The **body itself is cryptographically valid**; only the referenced data has diverged from what the producer signed. Returning `hash_mismatch` here would wrongly imply the whole body failed verification; returning `invalid_signature` would wrongly imply a signature-verification failure.
- `invalid_signature` — `signature.value` does not verify against the resolved public key. The body's authorship cannot be established.

A registry emits `data_ref_hash_mismatch` only at publish time, for embedded data (`embedded.content_hash` mismatch — RFC-ACDP-0002 §6.6 Check 8). For external `data_refs[].location`, hash verification happens consumer-side after fetch (RFC-ACDP-0002 §6.5); a consumer SHOULD surface the mismatch with the same `data_ref_hash_mismatch` semantic in its own diagnostics, logs, or API surface.

### 5.1 Adding a code

New codes are added via the [RFC process](../governance/RFC-PROCESS.md). Codes MUST be lowercase snake_case. Codes MUST NOT collide with existing entries.

### 5.2 Information leakage

Registries MUST NOT reveal which specific policy check failed beyond the registered code. The `error.message` string is informational only and MUST NOT be used in automated decision-making by consumers.

For visibility-restricted contexts, registries MUST return `not_found` (HTTP 404) — they MUST NOT distinguish "not found" from "not authorized" externally. The internal label `visibility_denied` MAY be used in registry logs or metrics for auditing purposes but MUST NOT appear in wire responses.

### 5.3 SDK guidance — `data_ref_hash_mismatch` vs body hash mismatch

The error-code table and the "Distinguishing hash failures" note above are normative for the wire. This section is implementation guidance for SDK authors who expose a verification API to application code.

SDKs exposing verification APIs MUST distinguish `data_ref_hash_mismatch` from body-level hash and signature failures:

- Report `data_ref_hash_mismatch` when a DataRef's bytes — fetched from an external `data_ref.location` (RFC-ACDP-0002 §6.5) or decoded from `data_ref.embedded` (RFC-ACDP-0002 §6.6 Check 8) — do not match the producer-declared `data_ref.content_hash`.
- An SDK MUST NOT report this case as `invalid_signature`. `invalid_signature` implies the producer's key or signature failed; here the signature is intact.
- An SDK MUST NOT collapse this case into `hash_mismatch`. `hash_mismatch` implies the entire body's ProducerContent hash failed and the body is unverifiable; here the body is fully verifiable.

A `data_ref_hash_mismatch` indicates the body remains cryptographically valid: the producer signed the hash of the data they intended to reference, but the data at that location has since changed (external case) or was mis-encoded (embedded case). It is an integrity failure at the **data layer**, not the **body layer**. A verification result object SHOULD therefore carry the body-level verdict and the data-ref-level verdict as separate fields, so an application can decide — for example — to trust the body's metadata and `derived_from` lineage while treating one stale DataRef as unusable.

The `data-ref-007` fixture pins the embedded case (registry-side, publish time). The `data-ref-008` fixture pins the external case (consumer-side, fetch time): the body signature MUST still verify, and the SDK SHOULD surface `data_ref_hash_mismatch`, not `invalid_signature`.

---

## 6. Security Considerations

See [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md). Specific to capabilities and errors:

- The capabilities document MUST be served over TLS.
- Registries SHOULD include the same `registry_did` value across all responses to avoid identity confusion.
- Error messages MUST NOT echo unsanitized request content (defends against XSS in registry-served clients and injection into log pipelines).
- Rate-limit responses (`rate_limited`) MUST include a `Retry-After` header (integer seconds or HTTP-date); a limiter without an exact refill horizon emits a conservative estimate rather than omitting the header (RFC-ACDP-0008 §4.3).

---

## 7. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0003 Publish](RFC-ACDP-0003-publish.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0005 Discovery](RFC-ACDP-0005-discovery.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
- [RFC-ACDP-0010 Registry Receipts](RFC-ACDP-0010-registry-receipts.md) *(0.2.0)*
- [RFC-ACDP-0013 Lifecycle Events & Retraction](RFC-ACDP-0013-lifecycle-events.md) *(0.3.0)* — activates `immutable_field`; adds `invalid_lifecycle_transition`.
