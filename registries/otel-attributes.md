# ACDP OpenTelemetry Attributes

Span attribute names for tagging telemetry with ACDP identifiers, so observability tools can link a span to the signed body it produced or consumed. All names live in the `acdp.` namespace. Instrumentation such as agent-SDK hooks, the MCP signing proxy (RFC-ACDP-0019) or registry clients SHOULD use these names and types rather than inventing their own.

**Rules for this registry.**
- These attributes are telemetry only. They never enter a body, a signature or a `content_hash`, and a consumer MUST NOT treat a span attribute as evidence. The signed body and its receipt are the evidence; the attribute only points at them.
- A name's meaning and type never change. A changed meaning mints a new name, and the old one becomes `Deprecated`.
- Values are copied verbatim from the wire, with no reformatting: `acdp.ctx_id` carries the exact `ctx_id` string, and so on.
- Instrumentation MUST NOT put body content, `data` payloads or the RFC-ACDP-0019 salt in an attribute. Those may be confidential even when the identifiers are not.
- Attributes go on the span that did the work: the span that published a body, or the span that consumed a verified one. A span that consumes several bodies uses the array forms.

## Producer-side attributes (a span that published a body)

| Attribute | Type | Status | Value |
|---|---|---|---|
| `acdp.ctx_id` | string | Provisional | The published body's `ctx_id` |
| `acdp.lineage_id` | string | Provisional | Its `lineage_id` |
| `acdp.version` | int | Provisional | Its `version` |
| `acdp.content_hash` | string | Provisional | Its `content_hash` |
| `acdp.producer` | string | Provisional | Its `agent_id` (the producer DID) |
| `acdp.registry` | string | Provisional | Its `origin_registry` |
| `acdp.type` | string | Provisional | Its `type` |
| `acdp.derived_from` | string[] | Provisional | Its `derived_from` `ctx_id`s, in body order |
| `acdp.publish.error` | string | Provisional | When the publish failed: the RFC-ACDP-0007 §5 error code, or `transport` when no ACDP error came back. Absent on success |

## Consumer-side attributes (a span that used bodies as input)

| Attribute | Type | Status | Value |
|---|---|---|---|
| `acdp.input.ctx_ids` | string[] | Provisional | The `ctx_id`s the span consumed |
| `acdp.input.verified` | boolean | Provisional | `true` only when every consumed body passed producer-signature verification (RFC-ACDP-0001 §5.8) and none was retracted at use time |
| `acdp.input.chain_verdict` | string | Provisional | When the consumer ran RFC-ACDP-0017 chain verification: the verdict's `chain.latest` value, verbatim (e.g. `ok_with_caveats`) |
| `acdp.input.chain_verdict_as_of` | string | Provisional | With a sealed-as-of run: the verdict's `chain.as_of` value, verbatim |
| `acdp.input.verdict_digest` | string | Provisional | That verdict's `verdict_digest`, so the span points at the exact verdict object |

## Status

Every entry is `Provisional` until two independent instrumentations emit it. Registry `Status` values are defined in [README.md](README.md#status-values).
