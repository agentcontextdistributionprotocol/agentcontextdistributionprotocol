# Version Matrix

This document is non-normative. It maps specification versions to the reference implementations and the conformance profiles each one claims, so an evaluator can tell at a glance which artifact implements which version of the protocol and where that claim is verified. The authoritative versioning policy is [VERSIONING.md](../VERSIONING.md); dated release notes are in [CHANGELOG.md](../CHANGELOG.md).

## The matrix

| Spec version | Status / where it lives | [`acdp-rs`](https://github.com/agentcontextdistributionprotocol/acdp-rs) (SDK) | [`acdp-registry-rs`](https://github.com/agentcontextdistributionprotocol/acdp-registry-rs) (registry) | Profiles defined |
|---|---|---|---|---|
| **v0.1.0** | **Final**, on `main` of this repo (wire-frozen; clarification addenda recorded in [CHANGELOG.md](../CHANGELOG.md)) | `0.1.x` | `0.1.x` (core surface) | `acdp-registry-core`, `acdp-registry-discovery`, `acdp-registry-federated`, `acdp-consumer` ([registries/profiles.md](../registries/profiles.md)) |
| **v0.2.0 Trust & Hardening** | **Draft**, merged on `main` (2026-07-04) — RFC-ACDP-0010 (registry receipts) plus RFC-ACDP-0001 amendments (`did:key` producers, hash-divergence corpus, explicit `acdp_version`) | `0.2.x` / `0.3.x` | `0.1.x` with a `[receipt]` signing key configured | v0.1.0 profiles + `acdp-registry-receipts` |

## Reading the rows

**Spec v0.1.0 (Final).** The contents of this repository's `main` branch: RFCs 0001–0008 at status Final, RFC-ACDP-0009 reserved, the JSON Schemas under `schemas/json/`, and the conformance fixtures under `schemas/conformance/`. v0.1.0 is wire-frozen — clarification rounds add prose and fixtures, never wire changes.

**Spec v0.2.0 (Draft).** Merged on `main` (2026-07-04); the amendments retain **Draft** status until the conformance pack passes against two independent implementations, at which point the line is promoted to Final per RELEASE.md. It is a backward-compatible minor version: every v0.1.0 body, signature, and `content_hash` remains valid. Headline additions: RFC-ACDP-0010 registry receipts (registry-signed binding of `ctx_id` / `lineage_id` / `origin_registry` / `created_at` / `content_hash` / producer-key fingerprint, closing the RFC-ACDP-0008 §9.1 registry-honesty gap for receipt-bearing responses), `did:key` producers, the hash-divergence corpus (`can-012`), and the `acdp-registry-receipts` profile. One parse-surface caveat: the previously closed publish response gains the OPTIONAL `registry_receipt` member.

**`acdp-rs` (reference SDK — producer, consumer, verification core).**

- `0.1.x` implements spec v0.1.0: the `acdp-consumer` profile (client, `WebResolver`, `CrossRegistryResolver`, strict verification) plus the producer and server-side validation building blocks.
- `0.2.x` implements the spec v0.2.0 draft: receipt minting/verification (RFC-ACDP-0010), `did:key` resolution, divergence diagnostics, and the explicit-`acdp_version` builder default.
- `0.3.x` is the same v0.2.0-draft protocol surface refactored into a fine-grained Cargo workspace; no wire-visible change.

*Where conformance is verified:* the SDK's own conformance suite (`tests/conformance.rs`) executes the spec's golden vectors and fixtures directly — point `ACDP_SPEC_DIR` at a checkout of this repository (the matching branch for 0.2.x/0.3.x) and run `cargo test --test conformance`. Note the suite skips silently when `ACDP_SPEC_DIR` is absent, so a green run only proves conformance when the spec checkout is wired in.

**`acdp-registry-rs` (reference registry).** Implements spec v0.1.0 as a running service: it advertises the `acdp-registry-core` and `acdp-registry-discovery` profiles by default, and — with a `[receipt]` signing key configured — the v0.2.0-draft `acdp-registry-receipts` profile (signed, atomically-persisted publish receipts, self-hosted `did:web` document, `did:key` producers). Cross-registry retrieval of foreign `ctx_id`s is available as a feature, but the registry does not currently claim the `acdp-registry-federated` profile.

*Where conformance is verified:* the registry's own harness (`crates/acdp-registry-server/tests/conformance.rs`) executes the behavioral fixture families (`pub-*`, `vis-*`, `ret-*`, `idem-*`, …) against a live in-process registry — the half of the suite that `scripts/conformance-runner.py` in this repo deliberately does not execute (it runs only the arithmetic/cryptographic `can-*` / `lin-*` / `sig-*` vectors; see [schemas/conformance/README.md](../schemas/conformance/README.md)).

## Rules of thumb

- Pinning a library? `acdp = "0.1"` gives you frozen v0.1.0 semantics; `0.2`/`0.3` track the v0.2.0 draft and may still move until that line goes Final.
- Talking to a registry? Read its `/.well-known/acdp.json`: `acdp_version` and `profiles` are the authoritative statement of what it implements — not this table.
- Writing a new implementation? Target v0.1.0 (Final); adopt the 0.2.0 Draft surface (receipts, `did:key`) only if you need it, and expect Draft-status churn until the two-implementation gate passes.
