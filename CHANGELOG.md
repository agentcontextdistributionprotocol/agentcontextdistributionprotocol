# Changelog

All notable changes to ACDP are recorded here. ACDP follows the versioning policy in [VERSIONING.md](VERSIONING.md).

## v0.1.0 — 2026-05-19

**ACDP is promoted from Release Candidate to `Final`.** RFCs 0001–0008 now carry the `Final` status; RFC-ACDP-0009 remains `Reserved`. `0.1.0` is the first published Final version of the protocol — the `0.0.1` identifier named internal pre-release drafts only and was never promoted. `0.1.0` is wire-compatible with `0.1.0-rc1`: this release is a specification-hardening pass, not a wire change. No body field, schema `$id`, JCS rule, content-hash semantic, or signature semantic changed.

### Specification hardening since `0.1.0-rc1`

- **DataRef schema openness made explicit (RFC-ACDP-0002 §6.7, `acdp-data-ref.schema.json`).** The `DataRef` root object is now an explicit open schema (`additionalProperties: true`): root-level `DataRef` fields are producer-controlled and included in the `content_hash` preimage, so consumers MUST preserve unknown `DataRef` fields when recomputing the hash. The nested `embedded` sub-object remains closed. New fixture `can-010` pins the hash recomputation; the openness map in RFC-ACDP-0007 §3.3.1 gains a `DataRef` root row.
- **Absent-vs-null wire convention (RFC-ACDP-0005 §2.2.1).** Optional fields MUST be omitted, never serialized as JSON `null`, unless the schema explicitly types them nullable (`supersedes` is the one explicitly-nullable example). New fixtures `schema-005`/`schema-006`/`schema-007` pin rejection of `next_cursor: null`, `summary: null`, `domain: null`.
- **Producer DID resolution SSRF protection (RFC-ACDP-0008 §4.8).** Registries and consumers MUST apply the RFC-ACDP-0006 §7 SSRF defenses to producer `did:web` resolution, not only to cross-registry resolution. New fixtures `did-ssrf-001`/`did-ssrf-002`/`did-ssrf-003` pin loopback, IMDS, and private-range refusal; the `key_resolution_failed` code is broadened to cover SSRF-policy refusal.
- **Closed nested-schema conformance (RFC-ACDP-0007 §3.3.1).** New fixtures `schema-008`/`schema-009`/`schema-010` pin rejection of unknown fields in the closed `signature`, `data_period`, and `capabilities.limits` sub-objects.
- **`data_ref_hash_mismatch` SDK guidance (RFC-ACDP-0007 §5.3).** New guidance for SDK authors on keeping `data_ref_hash_mismatch` distinct from `hash_mismatch` and `invalid_signature`. New fixture `data-ref-008` pins the consumer-side external-DataRef mismatch case (body stays cryptographically valid).
- **Cursor conformance fixtures (RFC-ACDP-0005 §2.5.4).** New fixtures `cur-001` (`cursor_expired`) and `cur-002` (`invalid_cursor`).
- **`lineage_id` derivation golden vector (RFC-ACDP-0001 §5.6).** New dedicated fixture `lin-001`; the conformance runner now executes `lin-*` fixtures alongside `can-*`.
- **`acdp_version` producer guidance (RFC-ACDP-0001 §6).** Producers SHOULD set `acdp_version` explicitly; consumers, verifiers, and registries MUST NOT inject a default `acdp_version` into a body before recomputing `content_hash`.
- **Conformance manifest refresh (`registries/profiles.json`, `registries/profiles.md`, `schemas/conformance/README.md`).** All 14 new fixtures are wired into the `acdp-registry-core`, `acdp-registry-discovery`, and `acdp-consumer` profiles and the fixture index.
- **Editorial.** RFC headers, the RFC index, `README.md`, and `VERSIONING.md` updated from `Release Candidate 1` to `Final`. A `RELEASE.md` promotion checklist was added.

## v0.1.0-rc1 — 2026-05-18

**First published version of the Agent Context Description Protocol (ACDP), entering the world as Release Candidate 1.** RFCs 0001–0008 are at status `Release Candidate 1`; RFC-ACDP-0009 remains `Reserved`. The `0.0.1` identifier used by earlier pre-release drafts was never promoted to a Release Candidate or Final status and is superseded by `0.1.0`. `0.1.0` is wire-compatible with those drafts — the body format, JCS canonicalization, content-hash, and signature semantics are unchanged.

ACDP defines the minimal substrate for autonomous agents to publish, discover, and verify units of contextual information across distributed systems. It is JSON-only, coordination-agnostic, and has no central authority.

### Release Candidate scope

`0.1.0-rc1` is intended for implementation testing. Backward-incompatible changes remain possible until `Final`; only editorial fixes are expected during the RC window. Per [VERSIONING.md](VERSIONING.md), `0.1.0` is promoted to `Final` once the conformance suite — including the behavioral fixtures under `schemas/conformance/` — passes against at least two interoperating implementations.

### Normative RFCs (Release Candidate 1)

- **RFC-ACDP-0001 — Core.** Identifiers (`acdp://`, `lin:sha256:`), JCS canonicalization (RFC 8785), content hashing (`sha256:<hex>`), Ed25519 signatures, time format, `did:web` resolution, the v0.1.0 strict verification profile, and the **Body / ProducerContent / RegistryState** terminology that the rest of the spec depends on.
- **RFC-ACDP-0002 — Context Body.** The immutable signed body schema: context types, `data_refs` (URL / inline / embedded), visibility (`public` / `restricted` / `private`), `derived_from`, metadata bounds. `origin_registry` is normatively a DNS hostname, not a DID URI.
- **RFC-ACDP-0003 — Publish & Supersession.** `POST /contexts`, registry-assigned fields (`ctx_id`, `lineage_id`, `origin_registry`, `created_at`), the ordered publish-validation algorithm, supersession constraints, and `Idempotency-Key` semantics.
- **RFC-ACDP-0004 — Retrieval & Lineage.** `GET /contexts/{ctx_id}`, body-only retrieval, lineage queries (including `/current` semantics and lineage-endpoint visibility), visibility-aware cache headers, registry-attested status.
- **RFC-ACDP-0005 — Discovery.** Keyword search across the seven required fields, opaque cursors with ≥1h validity, requester-scoped pagination, `anonymous_public_reads` scoping, and whole-result-set `total_estimate`. Ranking is registry-defined.
- **RFC-ACDP-0006 — Cross-Registry References.** `acdp://` URI scheme, resolution flow, registry-DID-vs-producer-signature distinction, SSRF defenses.
- **RFC-ACDP-0007 — Capabilities & Errors.** `/.well-known/acdp.json` capability declaration, the standard error envelope, and the error-code registry (including `data_ref_hash_mismatch`).
- **RFC-ACDP-0008 — Security & Threat Model.** A2A threat model, required defenses, visibility enforcement, key-rotation rules, replay prevention.

### Reserved (numbering pinned, no normative text)

- **RFC-ACDP-0009 — Extensions.** Reserves the field namespaces and feature areas planned for future versions: retraction / lifecycle events, post-publication relationships, attestations, push subscriptions, server-side traversal (`/walk`), semantic similarity, cross-registry supersession, registry receipts.

### Conformance and tooling

- **11 canonical JSON Schemas** under `schemas/json/` covering context, body, registry-state, data-ref, publish request/response, search response, capabilities, the error envelope, common types, and the index. Schemas are namespaced under `schemas.acdp.io/v0.1.0/`.
- **Conformance fixtures** under `schemas/conformance/`: JCS canonicalization vectors, cryptographic golden vectors, and behavioral scenarios (publish, retrieval, lineage, visibility, capabilities, error-envelope, DataRef, metadata, body identity-field, and idempotency cases).
- **Conformance runner** (`scripts/conformance-runner.py`) that executes the arithmetic and cryptographic vectors end-to-end. Behavioral fixtures (`pub-*`, `vis-*`, `ret-*`, `body-*`, `err-*`, …) require a live registry to execute.
- **Open-vocabulary registries** under `registries/`: `auth-methods`, `context-types`, `error-codes`, `locator-schemes`, `media-types`, `profiles`, `signature-algorithms`. Each entry carries a status (`Proposed` / `Provisional` / `Stable` / `Deprecated`).
- **GitHub Actions CI** that validates JSON Schemas, examples, and conformance vectors on every PR.
- **`make bootstrap` + `make validate`** for one-shot local setup and verification.

### Conformance profiles

- `acdp-registry-core` *(default)* — RFC-0001..0004, 0007, 0008. Every conformant registry.
- `acdp-registry-discovery` — adds RFC-0005 keyword search.
- `acdp-registry-federated` — adds RFC-0006 cross-registry resolution.
- `acdp-consumer` — RFC-0001 + RFC-0004 (read) + RFC-0006.

### Examples

Working examples under `examples/` for capabilities, error envelopes, idempotency cycles, lineage walks, mixed `data_refs`, publishing, retrieval (including a real Ed25519 round-trip in `retrieval/golden-context.json`), keyword-search responses, supersession (v2 superseding v1), and visibility (`restricted` / `private` bodies). Every example is validated against the canonical schemas in CI.

### Hardening incorporated since the pre-release drafts

`0.1.0-rc1` folds in several rounds of specification hardening over the pre-release drafts, including: explicit lineage-endpoint visibility rules; `GET /lineages/{id}/current` semantics for all-superseded and expired-head lineages; `anonymous_public_reads` scoping of keyword search; whole-result-set `total_estimate`; the `data_ref_hash_mismatch` error code distinguishing DataRef-level integrity failures from body-level ones; a normative `origin_registry`-is-a-hostname rule with schema enforcement; and the v0.1.0 strict verification profile with recommended verification-report stage names.

### Explicitly out of scope in v0.1.0

Retraction (any form), post-publication `builds_on` relationships from third parties, attestations (`reproduced` / `disputes`), push subscriptions, server-side traversal, federation peering, cross-registry query forwarding, encrypted bodies, hard deletion, multi-party / threshold signatures, semantic similarity, and registry quality / reputation algorithms. Most of these are reserved in RFC-ACDP-0009 for future versions.
