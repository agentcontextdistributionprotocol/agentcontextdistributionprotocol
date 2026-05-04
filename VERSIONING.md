# ACDP Versioning Policy

ACDP uses a layered versioning model so that the wire format, the canonical schemas, and the published RFCs can evolve at different rates without surprising implementers.

`acdp/0.0.1` is the **first published version**. There is no earlier published version to migrate from. (Internal drafts under the `CXTM`/`CTXM` working title are not considered published versions.)

## Layers

| Layer | Identifier | Example | Compat rules |
|---|---|---|---|
| Protocol version | `acdp_version` field on the capabilities document | `0.0.1` | Major mismatch ⇒ consumer SHOULD treat as a higher unknown version and degrade gracefully. |
| Body version | Implicit via the protocol version on the registry that accepted it | n/a | Body fields are stable; future versions add fields only. |
| Registry-state extensibility | Open object | n/a | Future versions add fields (lifecycle, relationships, attestations). Consumers MUST tolerate unknown fields. |
| RFC version | RFC document `Version:` header | `0.0.1` | Stable RFCs carry the bare semver string. Pre-final candidates use `-rcN` during the Release Candidate window; reserved-numbering RFCs without normative text use `-reserved` (e.g. `0.0.1-reserved` for RFC-ACDP-0009). |

## Change classes

- **Editorial / clarification** — patch-level RFC bump. No schema or wire change.
- **Backward-compatible addition** — minor RFC bump. New optional body fields, new registry-state fields, new error codes, new context types. Unknown fields MUST be ignored on consumers.
- **Breaking change** — major RFC bump and a new schema namespace. Migration notes required.

## Forward / backward compatibility

- Unknown JSON fields MUST be ignored by consumers (body and registry-state).
- Registries MUST reject **publish** requests containing fields not defined in the version they implement, to prevent producers from depending on registry-specific extensions.
- Consumers receiving a capabilities document with an unknown `acdp_version` SHOULD treat it as a higher version and degrade gracefully.
- New context types are registered in [`registries/context-types.md`](registries/context-types.md) and start at status `Proposed`. They graduate to `Stable` once two independent implementations interoperate.

## Release tags

Schema artifacts are tagged independently of the spec:

- `schema-vX.Y.Z` — tag on the canonical JSON Schemas in `schemas/json/`.
- `rfc-acdp-NNNN-vX.Y.Z` — tag on individual RFC documents when they hit Final status.

Downstream consumers pin to a specific tag and upgrade on their own schedule.

## Status ladder

| Status | Meaning |
|---|---|
| `Draft` | Open for substantive change. |
| `Review` | Under shepherded review. No structural changes during the FCP window. |
| `Final Comment Period` | Last call. Editorial fixes only. |
| `Release Candidate N` | A specific candidate (`rc1`, `rc2`, …) intended for implementation testing. Backward-incompatible changes remain possible until `Final`. ACDP v0.0.1 RFCs 0001–0008 are at `Draft`. |
| `Final` | Stable. Breaking changes require a new RFC. |
| `Reserved` | Numbering pinned, no normative text yet (e.g. RFC-ACDP-0009). Implementations MUST NOT depend on its identifiers until promoted out of `Reserved`. |
| `Deprecated` | Superseded by another RFC; retained for archaeology. |
