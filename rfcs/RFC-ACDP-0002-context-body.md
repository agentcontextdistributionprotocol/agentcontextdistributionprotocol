# RFC-ACDP-0002
# Agent Context Description Protocol (ACDP) — Context Body

**Document:** RFC-ACDP-0002
**Version:** 0.0.1-draft
**Status:** Community Standards Track (Draft)

This RFC specifies the immutable, signed body of an ACDP context. It depends on RFC-ACDP-0001 Core (identifiers, JCS, content hash, signature).

---

## 1. Status of This Memo

Draft. Backward-incompatible changes remain possible until Final.

---

## 2. The Two-Part Structure

A context consists of two parts (terminology defined in RFC-ACDP-0001 §2):

- The **Body**: an immutable JSON object containing the content of the context. The Body wraps ProducerContent (the producer-signed portion) plus the registry-assigned identity fields and the signature. Defined in this document.
- The **RegistryState**: a JSON object maintained by a registry containing fields derived after publication. Defined in RFC-ACDP-0004 §3.

When a context is retrieved (RFC-ACDP-0004 §2), both parts are returned together as a JSON object with two top-level keys: `body` and `registry_state`.

This structural separation is preserved in v0.0.1 to enable forward compatibility: future versions will add lifecycle events, relationships, and attestations to RegistryState without changing the Body's structure or signing semantics.

---

## 3. Body Fields

The body is a JSON object. All body fields are set at publish time and MUST NOT change thereafter. Once published, the body is permanent.

The canonical schema is [`schemas/json/acdp-context-body.schema.json`](../schemas/json/acdp-context-body.schema.json).

### 3.1 Identity Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `ctx_id` | string | Yes | Globally-unique URI identifying this context version. Form: `acdp://<authority>/<uuid>`. **Assigned by the registry** at publish time. |
| `lineage_id` | string | Yes | Deterministically-derived identifier for the lineage. See RFC-ACDP-0001 §5.6. |
| `version` | integer | Yes | Monotonically-increasing version number within the lineage, starting at 1. |
| `supersedes` | string \| null | Yes | The `ctx_id` of the immediately previous version, or `null` for version 1. |
| `agent_id` | string | Yes | The DID of the single signing identity for this context. v0.0.1 producers MUST use `did:web` so that any conformant registry can resolve their keys (RFC-ACDP-0001 §5.4, §5.11). |
| `contributors` | array of string | Yes | DIDs of agents that contributed to but did not sign this context. MAY be empty. |
| `origin_registry` | string | Yes | DNS hostname of the registry that originally accepted this context. **Assigned by the registry**. |
| `created_at` | string | Yes | RFC 3339 timestamp of registry acceptance. **Assigned by the registry**. |

### 3.2 Integrity Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `content_hash` | string | Yes | SHA-256 hash of the canonicalized body. See RFC-ACDP-0001 §5.7. |
| `signature` | object | Yes | The producer's detached signature over `content_hash`. See RFC-ACDP-0001 §5.8. |

### 3.3 Description Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | Yes | Short human-readable title. Maximum 500 characters. |
| `description` | string | No | Longer human-readable description. Maximum 5000 characters. |
| `type` | string | Yes | Context type. See §5. |
| `domain` | string | No | Subject domain identifier. Free-form. |
| `tags` | array of string | No | Free-form tags for keyword discovery. |
| `summary` | string | No | Short producer-supplied summary for search results. Maximum 1000 characters. |
| `metadata` | object | No | Producer-specific structured payload. Shape SHOULD be bound by `schema_uri`. |

### 3.4 Content Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `data_refs` | array of object | Yes | References to the data this context describes. MAY be empty (`[]`) for self-contained contexts whose payload lives entirely in `metadata` and `summary`. See §6. |
| `schema_uri` | string | No | URI of a JSON Schema describing the shape of `metadata`. |

### 3.5 Lineage Field

| Field | Type | Required | Description |
|---|---|---|---|
| `derived_from` | array of string | Yes | `ctx_id`s of contexts whose content directly informed this one. MAY be empty. |

`derived_from` is the only graph field in v0.0.1. It captures *epistemic* lineage: contexts the producer actually consumed at publication time. Because it is part of the signed body, the lineage chain is end-to-end verifiable: a consumer following `derived_from` references can verify each context's signature independently.

Future versions of ACDP will add post-publication relationships (third-party `builds_on` claims). v0.0.1 supports lineage-based discovery via the `derived_from` search filter (RFC-ACDP-0005 §2) but does not support post-publication relationship creation.

### 3.6 Discovery Aid Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `embedding` | array of number | No | Vector representation for similarity discovery. |
| `embedding_model` | string | Conditional | REQUIRED if `embedding` is present. Form: `<model_name>@<version>`. |
| `data_period` | object | No | Object with `start` and `end` RFC 3339 timestamps describing the time window the data covers. |
| `expires_at` | string | No | RFC 3339 timestamp after which the context's conclusions should not be relied upon. |

### 3.7 Visibility Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `visibility` | string | Yes | One of `public`, `restricted`, `private`. |
| `audience` | array of string | Conditional | REQUIRED if `visibility` is `restricted`. Array of DIDs. |

---

## 4. Identity, Versioning, and Lineage

### 4.1 ctx_id

A context's `ctx_id` MUST conform to the form `acdp://<authority>/<uuid>` where `<authority>` is the DNS hostname of the origin registry and `<uuid>` is a UUID v4 [RFC 4122]. The registry MUST assign `ctx_id` at publish time; producers MUST NOT supply a `ctx_id` in publish requests.

### 4.2 lineage_id

A context's `lineage_id` MUST be derived deterministically per RFC-ACDP-0001 §5.6.

### 4.3 version

A context's `version` MUST be 1 if `supersedes` is `null`, and MUST be `previous.version + 1` otherwise.

### 4.4 supersedes

When publishing a context with `supersedes` set, the registry MUST verify per RFC-ACDP-0003 §3:

1. The superseded context exists and is accessible.
2. The publishing agent's `agent_id` matches the superseded context's `agent_id`, OR the publishing agent presents a valid delegation chain from the superseded context's `agent_id` (delegation is out of scope for v0.0.1; only direct match is required).
3. The new context's computed `lineage_id` matches the superseded context's `lineage_id`.

The registry MUST reject the publication if any of these checks fail.

---

## 5. Context Types

The `type` field categorizes a context's role. The following values are defined by this specification:

| Value | Description |
|---|---|
| `data_snapshot` | Point-in-time data, such as a market price reading or system metric. |
| `analysis` | Analytical results, including summaries, experiments, performance reviews, and other analytical work. |
| `prediction` | Forward-looking insights, such as forecasts or trend projections. |
| `alert` | Time-sensitive notifications, such as fraud or anomaly alerts. |

Implementations MAY define custom types using a namespaced format: `<namespace>:<type>` (e.g., `science:experiment-replication`). Custom types are not interpreted by core ACDP; consumers handling them MUST understand the namespace. The standard registry of types is in [`registries/context-types.md`](../registries/context-types.md).

---

## 6. Data References

Each entry in `data_refs` is a JSON object describing one piece of data that the context refers to. Each entry MUST contain exactly one of `location` or `embedded`. The canonical schema is [`schemas/json/acdp-data-ref.schema.json`](../schemas/json/acdp-data-ref.schema.json).

### 6.1 Common Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | string | Yes | One of `primary_result`, `raw_data`, `supporting_info`, `derived_data`. |
| `description` | string | No | Human-readable description. |
| `size_bytes` | integer | No | Size of the referenced data in bytes. |
| `format` | string | No | Format identifier (e.g., `json`, `csv`, `parquet`, `binary`). |
| `schema_version` | string | No | Producer-specific schema version for this data. |
| `content_hash` | string | No | SHA-256 hash of the referenced data, allowing consumers to verify integrity at fetch time. |

### 6.2 Location Forms

When `location` is present, it MUST be either:

(a) A URI string conforming to a registered URI scheme. Common schemes: `https`, `http`, `s3`, `postgres`, `mongodb`, `kafka`, `file`. Example:

```json
"location": "postgres://analytics_db/sentiment_analysis?id=12345"
```

(b) A structured locator object with a required `scheme` field of dotted-namespace format and producer-defined additional fields. Example:

```json
"location": {
  "scheme": "kafka.offset",
  "broker": "kafka.example.com:9092",
  "topic": "events",
  "partition": 3,
  "offset": 1024
}
```

ACDP does not maintain an exhaustive registry of structured locator schemes; commonly used schemes are tracked in [`registries/locator-schemes.md`](../registries/locator-schemes.md). Producers using novel schemes SHOULD prefix the scheme with their organization or domain.

### 6.3 Embedded Form

When `embedded` is present, it is a JSON object:

| Field | Type | Required | Description |
|---|---|---|---|
| `encoding` | string | Yes | One of `json`, `utf8`, `base64`. |
| `content` | varies | Yes | The embedded content. For `json`, a JSON value. For `utf8` or `base64`, a string. |

The decoded size of `embedded.content` MUST NOT exceed 65536 bytes (64 KB). Registries MUST reject contexts containing embedded data exceeding this limit with `embedded_too_large` (RFC-ACDP-0007).

When `content_hash` is present on an embedded data reference, it is computed over the decoded bytes:
- For `encoding: "base64"`: over the bytes after base64 decoding.
- For `encoding: "utf8"`: over the bytes of the UTF-8 encoding.
- For `encoding: "json"`: over the bytes of the JCS-canonicalized form.

---

## 7. Visibility

The `visibility` field controls who may discover a context.

| Value | Effective audience | `audience` field |
|---|---|---|
| `public` | Any requester (subject to registry policy on anonymous access — RFC-ACDP-0008 §6.3). | MUST be absent or empty. |
| `restricted` | `agent_id` plus all DIDs listed in `audience`. | MUST be present and non-empty. |
| `private` | `agent_id` only, plus any DIDs explicitly listed in `audience` (if present). **Contributors are NOT auto-authorized.** | MAY be present to grant additional access. |

Retrieval by a requester who is not in the effective audience for a `restricted` or `private` context MUST return `not_found` (HTTP 404) to avoid leaking existence — see RFC-ACDP-0008 §4.5.

`contributors` is for **attribution**, not authorization. Crediting a contributor on a private context does not implicitly grant that contributor read access. To grant read access, list the DID explicitly in `audience`.

ACDP does not enforce access control on data referenced by `data_refs`. The visibility field affects metadata discoverability through the registry; the underlying data store enforces its own access control.

### 7.1 Visibility is permanent for a given body

Bodies are immutable, and `audience` is a producer-signed field of the body. The audience encoded in a body is therefore frozen forever. To revoke a DID's access to a context, the producer MUST publish a successor (via supersession) with a smaller audience; the predecessor remains accessible to its original audience until expiration or future retraction (RFC-ACDP-0009 §2.1). Retrieval-time `Cache-Control: private, no-store` (RFC-ACDP-0004 §6.2) is conservative against potential future visibility-model changes; it does not change the per-body audience semantics.

---

## 8. Embedded vs Referenced Data

The 64 KB embedded-data limit is intentional: it is large enough to carry a meaningful inline payload (a small JSON document, a short alert), but small enough that the registry can index and serve it without becoming a content-distribution network.

Producers SHOULD use `embedded` when:
- The data fits in 64 KB and is fully described by a structured object.
- Avoiding a fetch round-trip is valuable (e.g. alerts).
- The data is sensitive and benefits from being signed inline.

Producers SHOULD use `location` when:
- The data is large.
- The data is mutable (the `content_hash` on the data_ref pins a specific revision).
- The data lives in an existing system the consumer already has access to.

---

## 9. Forward Compatibility

Consumers parsing context bodies MUST tolerate unknown fields. Future versions will add fields to the body (only as additions; existing fields are stable) and to registry state (lifecycle events, relationships, attestations).

Implementations MUST NOT reject contexts solely because they contain unknown fields, with one exception: registries MUST reject **publish requests** containing fields not defined in the version they implement, to prevent producers from depending on registry-specific extensions.

---

## 10. Security Considerations

See [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md). Key points relevant to the body:

- The body is signed end-to-end. Tampering is detected by recomputing `content_hash`.
- `derived_from` is part of the signed body and cannot be backfilled.
- `embedding` can leak content; restricted/private contexts SHOULD omit it unless the registry's similarity index respects visibility.
- `data_refs.location` MUST NOT contain credentials.

---

## 11. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0003 Publish](RFC-ACDP-0003-publish.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
- [DID-CORE] W3C, "Decentralized Identifiers (DIDs) v1.0".
- [RFC 4122] Leach, P., Mealling, M., and R. Salz, "A Universally Unique IDentifier (UUID) URN Namespace".
