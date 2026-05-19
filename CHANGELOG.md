# Changelog

All notable changes to ACDP are recorded here. ACDP follows the versioning policy in [VERSIONING.md](VERSIONING.md).

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
