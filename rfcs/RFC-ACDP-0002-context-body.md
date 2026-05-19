# RFC-ACDP-0002
# Agent Context Description Protocol (ACDP) — Context Body

**Document:** RFC-ACDP-0002
**Version:** 0.1.0
**Status:** Community Standards Track (Final)

This RFC specifies the immutable, signed body of an ACDP context. It depends on RFC-ACDP-0001 Core (identifiers, JCS, content hash, signature).

---

## 1. Status of This Memo

This document is a Final ACDP specification (acdp/0.1.0). It is stable for the 0.1.0 release; subsequent breaking changes require a new RFC and a version bump per [VERSIONING.md](../VERSIONING.md).

---

## 2. The Two-Part Structure

A context consists of two parts (terminology defined in RFC-ACDP-0001 §2):

- The **Body**: an immutable JSON object containing the content of the context. The Body wraps ProducerContent (the producer-signed portion) plus the registry-assigned identity fields and the signature. Defined in this document.
- The **RegistryState**: a JSON object maintained by a registry containing fields derived after publication. Defined in RFC-ACDP-0004 §3.

When a context is retrieved (RFC-ACDP-0004 §2), both parts are returned together as a JSON object with two top-level keys: `body` and `registry_state`.

This structural separation is preserved in v0.1.0 to enable forward compatibility: future versions will add lifecycle events, relationships, and attestations to RegistryState without changing the Body's structure or signing semantics.

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
| `agent_id` | string | Yes | The DID of the single signing identity for this context. v0.1.0 producers MUST use `did:web` so that any conformant registry can resolve their keys (RFC-ACDP-0001 §5.4, §5.11). |
| `contributors` | array of string | Yes | DIDs of agents that contributed to but did not sign this context. MAY be empty. |
| `origin_registry` | string | Yes | DNS hostname of the registry that originally accepted this context. **Assigned by the registry**. See the clarification below. |
| `created_at` | string | Yes | RFC 3339 timestamp of registry acceptance. **Assigned by the registry**. |

**`origin_registry` is a DNS hostname, NOT a DID URI (NORMATIVE).** The `origin_registry` field carries the plain DNS hostname of the registry authority (e.g. `registry.example.com`), matching the authority component of `ctx_id` (`acdp://registry.example.com/<uuid>`). The DID form of the registry's identity appears only in `capabilities.registry_did` (`did:web:registry.example.com`, RFC-ACDP-0007 §3.1). The two are distinct encodings of the same registry and MUST NOT be interchanged on the wire. Storing `did:web:registry.example.com` in `origin_registry` is a conformance violation: the field's schema type is a DNS hostname (`acdp-common.schema.json#/$defs/hostname` — LDH labels, no colons), not a DID. A registry MUST assign `origin_registry` as a bare hostname; a consumer validating a retrieved body MUST reject a DID-shaped `origin_registry` as `schema_violation`.

| Field | Location | Format | Example |
|---|---|---|---|
| `origin_registry` | `Body` | DNS hostname | `registry.example.com` |
| `registry_did` | `CapabilitiesDocument` | DID URI | `did:web:registry.example.com` |
| `ctx_id` authority | `CtxId` | DNS hostname (in `acdp://` URI) | `acdp://registry.example.com/<uuid>` |

The `body-001`/`body-002` conformance fixtures pin the accept/reject behavior.

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
| `summary` | string | No | Short producer-supplied summary for display in search results and previews. RECOMMENDED ≤ 200 characters; hard limit 1000 characters. See note below. |
| `metadata` | object | No | Producer-specific structured payload. Shape SHOULD be bound by `schema_uri`. |

`summary` is **producer-controlled**: it is part of ProducerContent (RFC-ACDP-0001 §2, §5.7) and is included in `content_hash`. Distinguishing `summary` from `description`:

- `description` is the long-form prose (max 5000 characters) — the human-readable explanation of the context.
- `summary` is a short display string (recommended ≤ 200 characters; hard cap 1000) for search result rows, link previews, and notification cards.

If `summary` is absent, registries MAY generate a display string from `description` for **search indexing or response rendering only**; this generated value MUST NOT be persisted into the body and MUST NOT alter `content_hash`. Once a body is signed, no field — including a registry-derived display summary — may modify it.

`metadata` is bounded structurally. Registries MUST enforce the following runtime limits on every publish request:

- **Maximum 100 top-level properties.** Schema-enforced (`maxProperties: 100` in `acdp-publish-request.schema.json`). Violations fail at RFC-ACDP-0003 §2.1 step 1.
- **Maximum nesting depth: 8 levels.** Top-level keys are level 1; the object values they point to count as level 2; arrays nested inside count as the next level; and so on. The depth of any path through `metadata` MUST be ≤ 8. Registries MUST reject deeper structures with `schema_violation` (HTTP 400). This check is runtime-only — JSON Schema 2020-12 cannot express it natively.
- **Maximum JCS-canonicalized byte size: 65536 bytes (64 KB).** `len(JCS(metadata)) > 65536` MUST fail with `schema_violation` (HTTP 400). The cap is on the JCS canonical form (the same bytes that feed `content_hash`), not the raw on-the-wire bytes; payload-level escaping or whitespace differences are irrelevant.

Producers requiring richer or larger structured metadata SHOULD use `data_refs` instead. The runtime checks above are conformance-tested by the `meta-*` fixtures under [`schemas/conformance/`](../schemas/conformance/).

### 3.4 Content Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `data_refs` | array of object | Yes | References to the data this context describes. MAY be empty (`[]`) for self-contained contexts whose payload lives entirely in `metadata` and `summary`. See §6. |
| `schema_uri` | string | No | URI of a JSON Schema describing the shape of `metadata`. |

### 3.5 Lineage Field

| Field | Type | Required | Description |
|---|---|---|---|
| `derived_from` | array of string | Yes | `ctx_id`s of contexts whose content directly informed this one. MAY be empty. |

`derived_from` is the only graph field in v0.1.0. It captures *epistemic* lineage: contexts the producer actually consumed at publication time. Because it is part of the signed body, the lineage chain is end-to-end verifiable: a consumer following `derived_from` references can verify each context's signature independently.

Future versions of ACDP will add post-publication relationships (third-party `builds_on` claims). v0.1.0 supports lineage-based discovery via the `derived_from` search filter (RFC-ACDP-0005 §2) but does not support post-publication relationship creation.

`derived_from` is REQUIRED on the wire even when empty (`derived_from: []`). This is for JCS canonicalization stability: an absent field and an empty array produce different canonical bytes (and therefore different `content_hash` values), so requiring the field uniformly removes ambiguity across implementations and ACDP versions. Producers with no upstream contexts MUST send `derived_from: []`.

### 3.6 Discovery Aid Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `data_period` | object | No | Object with `start` and `end` RFC 3339 timestamps describing the time window the data covers. |
| `expires_at` | string | No | RFC 3339 timestamp after which the context's conclusions should not be relied upon. |

### 3.7 Visibility Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `visibility` | string | Yes | One of `public`, `restricted`, `private`. |
| `audience` | array of string | Conditional | REQUIRED if `visibility` is `restricted`. Array of DIDs. |

### 3.8 Compatibility Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `acdp_version` | string | No | The ACDP body protocol version this body conforms to. Form: `<major>.<minor>.<patch>`. Producer-supplied and producer-signed (part of ProducerContent — RFC-ACDP-0001 §2, §5.7). An absent field MUST be treated as `"0.1.0"`, the inaugural release. Producers SHOULD set the field explicitly so verifiers can unambiguously apply the correct exclusion set and algorithm vocabulary for the body's declared version, especially as future versions evolve them. See RFC-ACDP-0001 §6. |

---

## 4. Identity, Versioning, and Lineage

### 4.1 ctx_id

A context's `ctx_id` MUST conform to the form `acdp://<authority>/<uuid>` where `<authority>` is the DNS hostname of the origin registry and `<uuid>` is a UUID v4 [RFC 9562]. The registry MUST assign `ctx_id` at publish time; producers MUST NOT supply a `ctx_id` in publish requests.

### 4.2 lineage_id

A context's `lineage_id` MUST be derived deterministically per RFC-ACDP-0001 §5.6.

### 4.3 version

A context's `version` MUST be 1 if `supersedes` is `null`, and MUST be `previous.version + 1` otherwise.

### 4.4 supersedes

When publishing a context with `supersedes` set, the registry MUST verify per RFC-ACDP-0003 §3:

1. The superseded context exists and is accessible.
2. The publishing agent's `agent_id` matches the superseded context's `agent_id`, OR the publishing agent presents a valid delegation chain from the superseded context's `agent_id` (delegation is out of scope for v0.1.0; only direct match is required).
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
| `type` | string | Yes | One of `primary_result`, `raw_data`, `supporting_info`, `derived_data`. The full registry, including selection guidance, is in [`registries/data-ref-types.md`](../registries/data-ref-types.md). v0.1.0 defines a **closed set**: custom or namespaced `DataRef.type` values are NOT supported (the schema's `enum` enforces this). Extensibility is reserved for a future ACDP version. |
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

A registry that finds a mismatch between `embedded.content_hash` and the decoded bytes MUST reject the publish with `data_ref_hash_mismatch` (HTTP 400), NOT `hash_mismatch`. `hash_mismatch` is reserved for a failure of the body-level `content_hash` over ProducerContent; an embedded-data digest mismatch is a DataRef-level integrity failure. See RFC-ACDP-0007 §5 ("Distinguishing hash failures").

### 6.4 Visibility scope

ACDP `visibility` (§7) protects access to the **registry record**: the body and any indexes the registry maintains. It does **NOT** control access to external data referenced by `data_refs[].location`.

If `data_refs` points to an external URL (e.g. `https://`, `s3://`, `postgres://`), access to that URL is governed by the external system's ACLs — NOT by ACDP. A producer publishing `visibility: private` while referencing a public S3 object has effectively published the data publicly; only the registry metadata is private.

Producers requiring true end-to-end visibility on data MUST ensure the referenced storage system enforces equivalent access controls. ACDP does not enforce or verify this.

For embedded `data_refs` (where `content` is in the body itself), visibility applies fully because the content is part of the registry record.

### 6.5 Transport security for data_refs

For `data_refs[].location` values that are URIs (URL form per §6.2):

- Producers SHOULD use `https://` (or another transport-encrypted scheme like `s3://` with TLS) rather than `http://`. Plaintext transport leaves the data integrity-vulnerable to network adversaries; ACDP's `content_hash` covers the body, NOT the data referenced from the body.
- For `http://` locations, producers SHOULD include a `data_refs[].content_hash` (the SHA-256 of the actual referenced data) so consumers can verify integrity even when transport doesn't.
- Producers in trusted-network deployments MAY use `http://` without `content_hash`; this is a deployment-policy decision but reduces the verifiable-trust budget.

Consumers fetching `data_refs[].location` MUST treat the result as untrusted until verified. If `data_refs[].content_hash` is present, consumers MUST verify the fetched bytes match before treating the data as authentic. A consumer that detects a mismatch SHOULD surface it with the `data_ref_hash_mismatch` semantic (RFC-ACDP-0007 §5) — distinct from `invalid_signature` and `hash_mismatch`, because the body's own signature and `content_hash` may still be valid; only the externally-referenced data has diverged from what the producer signed. If `content_hash` is absent and the location is `http://`, consumers SHOULD treat the data as untrusted indefinitely.

### 6.6 DataRef Validation Checklist

Several `DataRef` constraints cannot be expressed in JSON Schema 2020-12 and have historically been missed by reference implementations. Registries MUST execute the following ordered checks for each entry in `data_refs[]`:

| # | Check | Failure code |
|---|---|---|
| 1 | `type` is present and equals one of the registered values (`primary_result`, `raw_data`, `supporting_info`, `derived_data` — see [`registries/data-ref-types.md`](../registries/data-ref-types.md)). | `schema_violation` |
| 2 | Exactly one of `location` or `embedded` is present (not both, not neither). | `schema_violation` |
| 3 | If `location` is a URI string: it has a non-empty scheme matching `^[a-z][a-z0-9+.-]*:`, total length ≤ 4096 characters. | `schema_violation` |
| 4 | If `location` is a URI string: it MUST NOT contain credentials in the userinfo component (no `user:password@authority` form). Producers MUST NOT embed secrets in URIs; secrets in `data_refs[].location` are persisted in the signed body forever. | `schema_violation` |
| 5 | If `location` is a structured object: `scheme` is present and matches the dotted-namespace pattern `^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)+$`. | `schema_violation` |
| 6 | If `embedded` is present: the decoded byte length of `embedded.content` is ≤ 65536. Decoding rules: `base64` → decode as RFC 4648 base64 then count bytes; `utf8` → encode the string as UTF-8 then count bytes; `json` → emit JCS canonical form then count bytes. | `embedded_too_large` |
| 7 | If `embedded.encoding` is `utf8` or `base64`: `embedded.content` MUST be a JSON string (not an object, array, number, etc.). For `embedded.encoding: "json"`, `embedded.content` MAY be any JSON value. | `schema_violation` |
| 8 | If `embedded.content_hash` is present: the registry MUST verify it against the decoded bytes per §6.3 (base64 → decoded bytes; utf8 → UTF-8 bytes; json → JCS-canonicalized bytes). Mismatch is a publish-time failure. | `data_ref_hash_mismatch` |

Checks 1, 3, 5, and 7 are also expressible as JSON Schema constraints in `acdp-data-ref.schema.json` and produce schema-validation failures at step 1 of the publish pipeline (RFC-ACDP-0003 §2.1). Check 2 is expressed via `oneOf` in the schema. Checks 4, 6, and 8 are runtime-only and execute after schema validation; they fail with the codes shown above.

The corresponding negative-case conformance fixtures are listed in [`schemas/conformance/README.md`](../schemas/conformance/README.md) under "DataRef validation". Registries claiming `acdp-registry-core` conformance MUST pass all of them.

### 6.7 DataRef Schema Openness

`DataRef` is an **open schema**: root-level `DataRef` fields not defined in this RFC are treated as producer-controlled and are included in the `content_hash` preimage. This is a deliberate, normative decision and mirrors the forward-compatibility rule already in force for the body itself (RFC-ACDP-0001 §5.7).

The reasoning: each `DataRef` lives inside `body.data_refs[]`, which is part of ProducerContent (the §5.7 hash preimage). Any unknown field a producer adds to a `DataRef` therefore affects `content_hash` and is covered by the producer signature. Future ACDP minor versions MAY add producer-signed `DataRef` fields without a major-version break.

- Consumers and registries MUST preserve unknown `DataRef` fields when recomputing `content_hash`. A consumer that deserializes `data_refs[]` into a typed struct without an unknown-field catch-all will drop the producer's field, recompute a different hash, and raise a false `hash_mismatch` against a newer producer's body — the same silent-break hazard RFC-ACDP-0001 §5.7 forbids at the body level.
- Implementations using typed models MUST use an extension map or equivalent (e.g. `#[serde(flatten)] extensions` in Rust serde, `ConfigDict(extra="allow")` in pydantic v2, an open index signature in TypeScript, `map[string]json.RawMessage` in Go) so that no producer-signed `DataRef` field is silently lost.

The openness applies to the `DataRef` **root object only**. The nested `embedded` sub-object is a CLOSED schema (`additionalProperties: false`): it is a tightly-scoped wire shape (`encoding`, `content`, optional `content_hash`) where an unknown field signals a bug, not a forward-compatible extension. The structured `location` object is likewise open (producer-defined locator fields). The complete openness map is in RFC-ACDP-0007 §3.3.1; the canonical schema declares this explicitly via `additionalProperties: true` on the `DataRef` root and `additionalProperties: false` on `embedded`.

The `can-010` conformance fixture pins the positive case: a `DataRef` carrying an unknown producer field MUST be retained, byte-for-byte, in the `content_hash` recomputation. The `schema-003` fixture pins the closed-`embedded` negative case.

---

## 7. Visibility

The `visibility` field controls who may retrieve and discover a context.

| Value | Effective audience | `audience` field |
|---|---|---|
| `public` | Any requester (subject to registry policy on anonymous access — RFC-ACDP-0008 §6.3). | MUST be absent or empty. |
| `restricted` | `agent_id` plus all DIDs listed in `audience`. | MUST be present and non-empty. |
| `private` | `agent_id` only, plus any DIDs explicitly listed in `audience` (if present). **Contributors are NOT auto-authorized.** | MAY be present to grant additional access. |

**`public` MUST NOT carry an `audience`.** A `public` context with a non-empty `audience` field is a `schema_violation` (HTTP 400). This is enforced by the publish-request schema (`acdp-publish-request.schema.json`) via an `if/then` clause and MUST be rejected at RFC-ACDP-0003 §2.1 step 1. Including `audience` on a `public` context is a category error: `public` already grants every authorized requester access; an `audience` listing would imply a narrowing the protocol does not honor.

**For `private`, `audience` is OPTIONAL.** If present, it MUST be a non-empty array of DIDs. Listing a DID in `audience` on a `private` context grants that DID **retrieval** access but **NOT search** visibility — `private` contexts are invisible to discovery for everyone except the producing agent. To make a context discoverable to a defined cohort, use `restricted` (which grants both retrieval and search visibility to the listed DIDs).

Retrieval by a requester who is not in the effective audience for a `restricted` or `private` context MUST return `not_found` (HTTP 404) to avoid leaking existence — see RFC-ACDP-0008 §4.5.

`contributors` is for **attribution**, not authorization. Crediting a contributor on a private context does not implicitly grant that contributor read access. To grant read access, list the DID explicitly in `audience`.

### Visibility matrix

The complete combination of visibility level, requester role, retrieval, and search behavior:

| Visibility | Anonymous read | Authenticated read (non-audience) | Audience read | Producer (`agent_id`) read | Appears in search for requester |
|---|---|---|---|---|---|
| `public` | Allowed only if `anonymous_public_reads: true` (RFC-ACDP-0008 §6.3); otherwise `not_authorized` (HTTP 403) | Allowed | Allowed (audience MUST be absent — see above) | Allowed | Yes |
| `restricted` | `not_found` (HTTP 404) | `not_found` (HTTP 404) | Allowed (HTTP 200) | Allowed (HTTP 200) | Yes for the producer and for DIDs listed in `audience`; otherwise No |
| `private` | `not_found` (HTTP 404) | `not_found` (HTTP 404) | Allowed (HTTP 200) iff DID is in `audience` | Allowed (HTTP 200) | **Producer only** — never appears in search results for any other DID, even DIDs listed in `audience` |

Notes on the matrix:
- HTTP 404 `not_found` is mandated for both "really doesn't exist" and "exists but you can't see it" to prevent existence leakage (RFC-ACDP-0008 §4.5). The internal label `visibility_denied` MAY appear in registry logs but MUST NOT appear on the wire.
- Search visibility is strictly equal to or narrower than retrieval visibility: anything you can find in search you can retrieve, but not vice versa (specifically for `private` + `audience`, where audience members can retrieve but cannot find via search).
- For `restricted`, registries MUST exclude non-audience contexts from `total_estimate` (RFC-ACDP-0005 §3) to avoid leaking counts.

ACDP does not enforce access control on data referenced by `data_refs`. The visibility field affects metadata discoverability through the registry; the underlying data store enforces its own access control.

> **Visibility scope reminder.** Visibility protects the registry record (body and indexes). External data targets in `data_refs` are governed by their own ACLs (see §6.4).

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
- `data_refs.location` MUST NOT contain credentials.

---

## 11. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0003 Publish](RFC-ACDP-0003-publish.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
- [DID-CORE] W3C, "Decentralized Identifiers (DIDs) v1.0".
- [RFC 9562] Davis, K., Peabody, B., and P. Leach, "Universally Unique IDentifiers (UUIDs)", RFC 9562, May 2024. Obsoletes RFC 4122.
