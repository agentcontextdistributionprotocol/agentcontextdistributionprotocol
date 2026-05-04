# Context Type Registry

The `type` field in a context body categorizes its role. Standard types are listed below. Implementations MAY define custom types using the `<namespace>:<type>` form.

## Standard types

| Type | Status | Description | Spec |
|---|---|---|---|
| `data_snapshot` | Stable | Point-in-time data, such as a market price reading or system metric. | [RFC-ACDP-0002 §5](../rfcs/RFC-ACDP-0002-context-body.md#5-context-types) |
| `analysis` | Stable | Analytical results, including summaries, experiments, performance reviews, and other analytical work. | [RFC-ACDP-0002 §5](../rfcs/RFC-ACDP-0002-context-body.md#5-context-types) |
| `prediction` | Stable | Forward-looking insights, such as forecasts or trend projections. | [RFC-ACDP-0002 §5](../rfcs/RFC-ACDP-0002-context-body.md#5-context-types) |
| `alert` | Stable | Time-sensitive notifications, such as fraud or anomaly alerts. | [RFC-ACDP-0002 §5](../rfcs/RFC-ACDP-0002-context-body.md#5-context-types) |

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
