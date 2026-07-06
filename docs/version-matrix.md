# Version Matrix

This document is non-normative. It maps specification versions to the reference implementations and the conformance profiles each one claims, so an evaluator can tell at a glance which artifact implements which version of the protocol and where that claim is verified. The authoritative versioning policy is [VERSIONING.md](../VERSIONING.md); dated release notes are in [CHANGELOG.md](../CHANGELOG.md).

## The matrix

| Spec version | Status / where it lives | [`acdp-rs`](https://github.com/agentcontextdistributionprotocol/acdp-rs) (SDK) | [`acdp-registry-rs`](https://github.com/agentcontextdistributionprotocol/acdp-registry-rs) (registry) | Profiles defined |
|---|---|---|---|---|
| **v0.1.0** | **Final**, on `main` of this repo (wire-frozen; clarification addenda recorded in [CHANGELOG.md](../CHANGELOG.md)) | `0.1.x` | `0.1.x` (core surface) | `acdp-registry-core`, `acdp-registry-discovery`, `acdp-registry-federated`, `acdp-consumer` ([registries/profiles.md](../registries/profiles.md)) |
| **v0.2.0 Trust & Hardening** | **Final** (promoted 2026-07-05) — RFC-ACDP-0010 (registry receipts) plus RFC-ACDP-0001 amendments (`did:key` producers, hash-divergence corpus, explicit `acdp_version`) | `0.2.x` and later | `0.1.x` with a `[receipt]` signing key configured | v0.1.0 profiles + `acdp-registry-receipts` |
| **v0.3.0** | **Final** (promoted 2026-07-05) — RFC-ACDP-0011 (lineage-head receipts), RFC-ACDP-0012 (transparency log), RFC-ACDP-0013 (lifecycle events & retraction), RFC-ACDP-0014 (key-revocation signal), mandatory `Idempotency-Key`, `limits.max_publish_per_minute` | `0.5.x` (crates.io `acdp 0.5.3`) | current `main` (serves all three 0.3.0 profiles) | v0.2.0 profiles + `acdp-registry-head-receipts`, `acdp-registry-transparency-log`, `acdp-registry-lifecycle` |
| **v0.4.0 Witness Cosigning** | **Draft** (opened 2026-07-05) — RFC-ACDP-0015 (transparency-log witness cosigning), promoting the RFC-ACDP-0009 §2.12 reservation | `0.5.3+` (crates.io `acdp 0.5.3`; bindings 0.7.0) | current `main` aggregates witness cosignatures (`witness_signatures` on checkpoints) | v0.3.0 profiles + `acdp-log-witness` (a witness node, not a registry) |

## Reading the rows

**Spec v0.1.0 (Final).** The contents of this repository's `main` branch: RFCs 0001–0008 at status Final, RFC-ACDP-0009 reserved, the JSON Schemas under `schemas/json/`, and the conformance fixtures under `schemas/conformance/`. v0.1.0 is wire-frozen — clarification rounds add prose and fixtures, never wire changes.

**Spec v0.2.0 (Final).** Merged on `main` as Draft (2026-07-04) and promoted to **Final** on 2026-07-05 per RELEASE.md, the conformance pack having passed against two independent interoperating implementations (`acdp-rs` and `acdp-verifier-py` — see CHANGELOG.md). It is a backward-compatible minor version: every v0.1.0 body, signature, and `content_hash` remains valid. Headline additions: RFC-ACDP-0010 registry receipts (registry-signed binding of `ctx_id` / `lineage_id` / `origin_registry` / `created_at` / `content_hash` / producer-key fingerprint, closing the RFC-ACDP-0008 §9.1 registry-honesty gap for receipt-bearing responses), `did:key` producers, the hash-divergence corpus (`can-012`), and the `acdp-registry-receipts` profile. One parse-surface caveat: the previously closed publish response gains the OPTIONAL `registry_receipt` member.

**`acdp-rs` (reference SDK — producer, consumer, verification core).**

- `0.1.x` implements spec v0.1.0: the `acdp-consumer` profile (client, `WebResolver`, `CrossRegistryResolver`, strict verification) plus the producer and server-side validation building blocks.
- `0.2.x` implements the spec v0.2.0 surface (then Draft): receipt minting/verification (RFC-ACDP-0010), `did:key` resolution, divergence diagnostics, and the explicit-`acdp_version` builder default.
- `0.3.x` is the same v0.2.0 protocol surface refactored into a fine-grained Cargo workspace; no wire-visible change.
- `0.5.x` (crates.io `acdp 0.5.3`, current) implements the spec v0.2.0 + v0.3.0 Final surface plus the v0.4.0 RFC-ACDP-0015 witness-cosigning types: require-mode conformance passes the executed `rcpt`/`lhr`/`log`/`rev`/`wit` bindings. The language bindings (`acdp-py`, `acdp-node`) are published at **0.7.0** with the witness `build`/`verify`/`quorum` surface.

*Where conformance is verified:* the SDK's own conformance suite (`tests/conformance.rs`) executes the spec's golden vectors and fixtures directly — point `ACDP_SPEC_DIR` at a checkout of this repository (the matching branch for 0.2.x/0.3.x) and run `cargo test --test conformance`. Note the suite skips silently when `ACDP_SPEC_DIR` is absent, so a green run only proves conformance when the spec checkout is wired in.

**`acdp-registry-rs` (reference registry).** Implements the spec as a running service: it advertises the `acdp-registry-core` and `acdp-registry-discovery` profiles by default, and — with a `[receipt]` signing key configured — the v0.2.0 `acdp-registry-receipts` profile (signed, atomically-persisted publish receipts, self-hosted `did:web` document, `did:key` producers). Current `main` serves all three v0.3.0 profiles (`acdp-registry-head-receipts`, `acdp-registry-transparency-log`, `acdp-registry-lifecycle`) end-to-end. It also aggregates RFC-ACDP-0015 witness cosignatures, serving verified ones as the `witness_signatures` member on transparency-log checkpoints (0.4.0, Draft). Cross-registry retrieval of foreign `ctx_id`s is available as a feature, but the registry does not currently claim the `acdp-registry-federated` profile.

*Where conformance is verified:* the registry's own harness (`crates/acdp-registry-server/tests/conformance.rs`) executes the behavioral fixture families (`pub-*`, `vis-*`, `ret-*`, `idem-*`, …) against a live in-process registry — the half of the suite that `scripts/conformance-runner.py` in this repo deliberately does not execute (it runs only the arithmetic/cryptographic `can-*` / `lin-*` / `sig-*` vectors; see [schemas/conformance/README.md](../schemas/conformance/README.md)).

## Rules of thumb

- Pinning a library? `acdp = "0.1"` gives you frozen v0.1.0 semantics; `0.2`/`0.3` carry the v0.2.0 surface; `0.5.3` carries the v0.2.0 + v0.3.0 Final surface plus the v0.4.0 witness-cosigning types (bindings at `0.7.0`).
- Talking to a registry? Read its `/.well-known/acdp.json`: `acdp_version` and `profiles` are the authoritative statement of what it implements — not this table.
- Writing a new implementation? Target v0.3.0 (Final; v0.1.0/v0.2.0 remain Final and wire-frozen); the optional 0.2.0/0.3.0 surfaces (receipts, `did:key`, head receipts, transparency log, lifecycle) are profile-gated — adopt them as you need them.
