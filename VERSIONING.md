# ACDP Versioning Policy

ACDP uses a layered versioning model so that the wire format, the canonical schemas, and the published RFCs can evolve at different rates without surprising implementers.

`acdp/0.1.0` is the **first published version**. There is no earlier published version to migrate from. (The `0.0.1` identifier was used only by internal pre-release drafts and never reached a Release Candidate or Final status; internal drafts under the `CXTM`/`CTXM` working title are likewise not considered published versions.)

The `0.1.0` line is published as **`Final`** (`acdp/0.1.0`): RFCs 0001–0008 carry the `Final` status; RFC-ACDP-0009 remains `Reserved`. The line passed through a `Release Candidate` window (`acdp/0.1.0-rc1`) before this promotion; the status ladder below records both states.

The `0.2.0` line (**Trust & Hardening**) is published as **`Final`** (promoted from Draft on 2026-07-05): RFC-ACDP-0010 (Registry Receipts) is Final at version `0.2.0`, and the amendments marked *(0.2.0)* in-prose in RFCs 0001/0003/0004/0007/0008 are Final. The 0.1.0 surface of every amended RFC remains wire-frozen — no 0.2.0 change touches any v0.1.0 body field, JCS rule, content-hash, or signature semantic. 0.2.0 is a backward-compatible minor (new optional `registry_receipt` retrieval/publish-response member, second signing identity, `did:key` producers, explicit-`acdp_version` producer rule); per the namespace rule below the canonical schemas stay in the `v0.1.0` namespace with additive edits. The promotion gate was met per the same discipline as 0.1.0: the 0.2.0 conformance pack (`rcpt-*`, `fp-001`, `rot-001`, `sig-003`, `dk-*`, `can-012`, `fed-009`) passes against two independent interoperating implementations (see [CHANGELOG.md](CHANGELOG.md)).

The `0.3.0` line is published as **`Final`** (promoted from Draft on 2026-07-05): RFC-ACDP-0011 (Lineage-Head Receipts), RFC-ACDP-0012 (Registry Transparency Log), RFC-ACDP-0013 (Lifecycle Events & Retraction), and RFC-ACDP-0014 (Producer Key-Revocation Signal) are Final at version `0.3.0`, and the amendments marked *(0.3.0)* in-prose in RFCs 0001/0002/0003/0004/0005/0007/0008 are Final. It also comprises one **conformance tightening** — `Idempotency-Key` support (RFC-ACDP-0003 §6, including the §6.2.2 atomic storage contract and the §6 TTL bounds) is REQUIRED for `acdp-registry-core` when the registry advertises `acdp_version` ≥ 0.3.0; registries advertising 0.1.0/0.2.0 are unchanged — and one **backward-compatible addition** to capabilities, the OPTIONAL `limits.max_publish_per_minute` field (RFC-ACDP-0007 §3.2). None of it is a wire change for existing surfaces: no body field, JCS rule, content-hash, signature semantic, header syntax, or existing parse surface is touched, and per the namespace rule below the canonical schemas stay in the `v0.1.0` namespace with additive edits. Migration: a 0.2.0-conformant registry upgrades by implementing RFC-ACDP-0003 §6 *before* advertising `acdp_version` ≥ 0.3.0; until then it keeps advertising `0.2.0` and remains fully conformant. The promotion gate was met: the 0.3.0 conformance fixtures (`lhr-*`, `log-*`, `lc-*`, `rev-*`, `caps-007`, `idem-007`) pass against two independent interoperating implementations (see [CHANGELOG.md](CHANGELOG.md)).

## Layers

| Layer | Identifier | Example | Compat rules |
|---|---|---|---|
| Protocol version | `acdp_version` field on the capabilities document | `0.1.0` | Bare `<major>.<minor>.<patch>` (no `-rcN` suffix — the `acdp_version` wire field carries only released semver). Major mismatch ⇒ consumer SHOULD treat as a higher unknown version and degrade gracefully. |
| Body version | `body.acdp_version` (optional); absent ⇒ `0.1.0` | `0.1.0` | Body fields are stable; future versions add fields only. |
| Registry-state extensibility | Open object | n/a | Future versions add fields (lifecycle, relationships, attestations). Consumers MUST tolerate unknown fields. |
| RFC version | RFC document `Version:` header | `0.1.0` | Final RFCs carry the bare semver string (e.g. `0.1.0`); Draft-stage documents (new RFCs or Final RFCs carrying Draft amendments for an in-progress line) use `-draft` (e.g. `0.2.0-draft`); pre-final candidates use `-rcN` during the Release Candidate window (e.g. `0.1.0-rc1`); reserved-numbering RFCs without normative text use `-reserved` (e.g. `0.2.0-reserved` for RFC-ACDP-0009). |
| Schema namespace | `$id` URL path segment | `v0.1.0` | The canonical JSON Schemas live under `schemas.acdp.io/v<major>.<minor>.<patch>/`. The namespace carries the target release version (no `-rcN`); a breaking change opens a new namespace. |

## Change classes

- **Editorial / clarification** — patch-level RFC bump. No schema or wire change.
- **Backward-compatible addition** — minor RFC bump. New optional body fields, new registry-state fields, new error codes, new context types. Unknown fields MUST be ignored on consumers.
- **Breaking change** — major RFC bump and a new schema namespace. Migration notes required.

While the protocol is in the `0.x` series, the `0.x` semver convention applies: the **minor** component absorbs both additive and (rarely, with migration notes) breaking changes, and the spec does not yet offer the long-term stability guarantee that a `1.0.0` release would. Backward-compatible additions advance the minor component (`0.1.0` → `0.2.0`); pre-`1.0.0` breaking changes also advance the minor component and MUST ship migration notes and a new schema namespace.

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

The end-to-end checklist for promoting a version line to `Final` and cutting these tags is in [RELEASE.md](RELEASE.md).

## Status ladder

| Status | Meaning |
|---|---|
| `Draft` | Open for substantive change. |
| `Review` | Under shepherded review. No structural changes during the FCP window. |
| `Final Comment Period` | Last call. Editorial fixes only. |
| `Release Candidate N` | A specific candidate (`rc1`, `rc2`, …) intended for implementation testing. Backward-incompatible changes remain possible until `Final`; only editorial fixes are expected during the RC window. ACDP `0.1.0` RFCs 0001–0008 passed through `Release Candidate 1` (`acdp/0.1.0-rc1`) before promotion. |
| `Final` | Stable for the release. Breaking changes require a new RFC and a minor (pre-`1.0.0`) or major version bump. An RFC is promoted to `Final` once the conformance suite (`schemas/conformance/`, including the behavioral fixtures) passes against at least two interoperating implementations. ACDP `0.1.0` RFCs 0001–0008 are at `Final`; the `0.2.0` line (RFC-ACDP-0010 and the *(0.2.0)* amendments) and the `0.3.0` line (RFC-ACDP-0011–0014 and the *(0.3.0)* amendments) were promoted to `Final` on 2026-07-05. |
| `Reserved` | Numbering pinned, no normative text yet (e.g. RFC-ACDP-0009). Implementations MUST NOT depend on its identifiers until promoted out of `Reserved`. |
| `Deprecated` | Superseded by another RFC; retained for archaeology. |
