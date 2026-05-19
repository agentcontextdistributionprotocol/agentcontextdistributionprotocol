# DataRef Type Registry

The `type` field on each entry in a context body's `data_refs[]` array describes the role of that data within the context. v0.1.0 defines a closed set of four values; the schema (`acdp-data-ref.schema.json`) enforces this with an `enum`. Custom or namespaced DataRef types are **not supported** in v0.1.0 — extensibility is reserved for a future ACDP version.

The validation rules every registry MUST apply to `data_refs[]` entries — including the `type` check — are in [RFC-ACDP-0002 §6.6 DataRef Validation Checklist](../rfcs/RFC-ACDP-0002-context-body.md#66-dataref-validation-checklist).

## v0.1.0 values

| Value | Status | Description | Spec |
|---|---|---|---|
| `primary_result` | Stable | The main output the context describes. The data a consumer is most likely to want first. Examples: a forecast model's prediction array; an analysis context's report file; an alert context's payload. | [RFC-ACDP-0002 §6](../rfcs/RFC-ACDP-0002-context-body.md#6-data-references) |
| `raw_data` | Stable | Source or input data the context was produced from. Useful for reproducibility and provenance walks. Examples: the input dataset to an analysis; the transaction stream feeding a fraud-alert; the time series feeding a forecast. | [RFC-ACDP-0002 §6](../rfcs/RFC-ACDP-0002-context-body.md#6-data-references) |
| `supporting_info` | Stable | Ancillary data the context references but that is neither the primary result nor a raw input. Examples: a methodology document; an external dataset cited as evidence; a glossary or schema document. | [RFC-ACDP-0002 §6](../rfcs/RFC-ACDP-0002-context-body.md#6-data-references) |
| `derived_data` | Stable | Data computed from the primary result that is itself part of the context's deliverable. Examples: aggregate statistics derived from `primary_result`; a visualization rendering of the result; intermediate artifacts kept alongside the main output. | [RFC-ACDP-0002 §6](../rfcs/RFC-ACDP-0002-context-body.md#6-data-references) |

## Choosing the right value

A common pattern is to attach one `primary_result` plus zero or more of the other types:

- `analysis` context: `primary_result` (the report) + `raw_data` (inputs) + maybe `supporting_info` (methodology).
- `prediction` context: `primary_result` (the forecast) + `raw_data` (training/input series) + `derived_data` (confidence intervals).
- `alert` context: `primary_result` (the alert payload) + `supporting_info` (the rule that fired).
- `data_snapshot` context: usually a single `primary_result` capturing the reading.

When in doubt: if a consumer would naturally fetch this first, it's `primary_result`. If it's the input the producer started from, `raw_data`. If it's secondary supporting material, `supporting_info`. If it was computed from `primary_result` as part of the same workflow, `derived_data`.

## Why no custom types in v0.1.0

`DataRef.type` is a discoverability primitive — registries index by it and consumers branch on it. Allowing custom values in v0.1.0 would fragment that index without giving registries any handle to compare or rank custom types.

A future ACDP version may introduce namespaced custom values (`<namespace>:<type>`) once the indexing semantics are specified. The schema's `enum` will be relaxed to a `pattern` at that point, gated on a new `acdp_version` value in the body.

## Adding a standard value

Standard values are added via the [RFC process](../governance/RFC-PROCESS.md). New values MUST:

- Have a use case that cannot be expressed by combining existing values.
- Be backed by at least two independent producer implementations before promotion to `Stable`.
- Bump the `acdp-data-ref.schema.json` `enum` and the `acdp_version` value associated with it.
