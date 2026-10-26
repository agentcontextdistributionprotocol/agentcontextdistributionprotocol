# Context Type Registry

The `type` field in a context body categorizes its role. Standard types are listed below. Implementations MAY define custom types using the `<namespace>:<type>` form.

## Standard types

| Type | Status | Description | Spec |
|---|---|---|---|
| `data_snapshot` | Stable | Point-in-time data, such as a market price reading or system metric. | [RFC-ACDP-0002 §5](../rfcs/RFC-ACDP-0002-context-body.md#5-context-types) |
| `analysis` | Stable | Analytical results, including summaries, experiments, performance reviews, and other analytical work. | [RFC-ACDP-0002 §5](../rfcs/RFC-ACDP-0002-context-body.md#5-context-types) |
| `prediction` | Stable | Forward-looking insights, such as forecasts or trend projections. | [RFC-ACDP-0002 §5](../rfcs/RFC-ACDP-0002-context-body.md#5-context-types) |
| `alert` | Stable | Time-sensitive notifications, such as fraud or anomaly alerts. | [RFC-ACDP-0002 §5](../rfcs/RFC-ACDP-0002-context-body.md#5-context-types) |
| `key-revocation` | Stable (0.3.0) | A producer's time-scoped declaration that a signing key is compromised: `metadata.revoked_key_fingerprint` (RFC-ACDP-0010 §6 encoding), `metadata.compromised_since` (canonical ms RFC 3339 UTC), optional `reason` / `revoked_key_id` / `revoked_key_controller`. MUST be `visibility: public`; MUST be signed by a current non-revoked key (or registry-attested — the weaker trust class of RFC-ACDP-0014 §6). The first standard type with a normatively constrained, publish-time-validated metadata shape (`acdp_version` ≥ 0.3.0). Interim form on pre-0.3.0 registries: `acdp:key-revocation` (RFC-ACDP-0014 §10) — *(0.5.0)* a registry advertising `acdp_version` ≥ 0.5.0 MUST reject a **new** publication under the interim form (`schema_violation`), though it continues serving bodies already published under it. | [RFC-ACDP-0014 §4, §10](../rfcs/RFC-ACDP-0014-key-revocation.md) |

## ACDP-namespaced types

Types in the `acdp:` namespace are defined by an ACDP RFC but use the custom-type grammar below, so the standard-type enum (and every validator pinned to it) is unchanged.

| Type | Status | Description | Spec |
|---|---|---|---|
| `acdp:mcp-tool-result` | Provisional (0.5.0) | One MCP `tools/call` observed by an MCP signing proxy, which is the producer. `metadata` is an `acdp-mcp-tool-result/1` record: salted hashes of the arguments, result and request id, the upstream server's identity, timing and flags; the result itself only when allowlisted for embedding. | [RFC-ACDP-0019 §4](../rfcs/RFC-ACDP-0019-mcp-tool-result-provenance.md) |
| `acdp:trust-list` | Provisional (0.5.0) | A registry trust list: `metadata` is an `acdp-trust-list/1` object (issuer-chosen `list_id`, strictly increasing `serial`, `issued_at`, `valid_from`/`valid_until`, and `entries` naming trusted registries with optional receipt-key pins, required profiles, scope and windows). The producer is the issuer; consumers verify it against configured issuer pins. | [RFC-ACDP-0020 §4](../rfcs/RFC-ACDP-0020-registry-trust-lists.md) |

## Custom-type format

Custom types use namespaced format:

```
<namespace>:<type>
```

- `<namespace>` MUST match `^[a-z][a-z0-9_]*$` and SHOULD be a domain or organization marker.
- `<type>` MUST match `^[a-z][a-z0-9_-]*$`.

Examples: `science:experiment-replication`, `finance:earnings-call-summary`, `com.example.fraud-alert`.

Custom types are not interpreted by core ACDP; consumers handling them MUST understand the namespace.

## Adding a standard type

Standard types are added via the [RFC process](../governance/RFC-PROCESS.md). New standard types MUST:

- Have a clear use case that can't be expressed as a custom type or by extending an existing one.
- Be implemented by at least two independent producers before promotion to `Stable`.
- Be uniformly enforceable by registry indexes (no producer-specific quirks).
