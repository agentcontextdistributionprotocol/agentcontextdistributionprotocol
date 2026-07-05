# Context Type Registry

The `type` field in a context body categorizes its role. Standard types are listed below. Implementations MAY define custom types using the `<namespace>:<type>` form.

## Standard types

| Type | Status | Description | Spec |
|---|---|---|---|
| `data_snapshot` | Stable | Point-in-time data, such as a market price reading or system metric. | [RFC-ACDP-0002 §5](../rfcs/RFC-ACDP-0002-context-body.md#5-context-types) |
| `analysis` | Stable | Analytical results, including summaries, experiments, performance reviews, and other analytical work. | [RFC-ACDP-0002 §5](../rfcs/RFC-ACDP-0002-context-body.md#5-context-types) |
| `prediction` | Stable | Forward-looking insights, such as forecasts or trend projections. | [RFC-ACDP-0002 §5](../rfcs/RFC-ACDP-0002-context-body.md#5-context-types) |
| `alert` | Stable | Time-sensitive notifications, such as fraud or anomaly alerts. | [RFC-ACDP-0002 §5](../rfcs/RFC-ACDP-0002-context-body.md#5-context-types) |
| `key-revocation` | Proposed (0.3.0, Final) | A producer's time-scoped declaration that a signing key is compromised: `metadata.revoked_key_fingerprint` (RFC-ACDP-0010 §6 encoding), `metadata.compromised_since` (canonical ms RFC 3339 UTC), optional `reason` / `revoked_key_id` / `revoked_key_controller`. MUST be `visibility: public`; MUST be signed by a current non-revoked key (or registry-attested — the weaker trust class of RFC-ACDP-0014 §6). The first standard type with a normatively constrained, publish-time-validated metadata shape (`acdp_version` ≥ 0.3.0). Interim form on pre-0.3.0 registries: `acdp:key-revocation` (RFC-ACDP-0014 §10). | [RFC-ACDP-0014 §4](../rfcs/RFC-ACDP-0014-key-revocation.md) |

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
