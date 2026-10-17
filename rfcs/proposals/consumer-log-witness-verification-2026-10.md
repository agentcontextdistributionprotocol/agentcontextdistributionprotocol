# Proposal: Consumer Verification Preconditions for Log Proofs and Witness Quorums

**Target path:** `rfcs/proposals/consumer-log-witness-verification-2026-10.md`
**Status:** Pre-Draft proposal. It targets the **acdp/0.5.0 Draft line**. If accepted, each change below lands as an in-prose ***(0.5.0)*** amendment to the RFC it names.
**Amends:** RFC-ACDP-0012 §9.1/§9.3, RFC-ACDP-0015 §8.
**Spec pin:** `agentcontextdistributionprotocol` origin/HEAD `f4a19a1` (2026-10-08). **Evidence:** `acdp-rs` 0.15.0 implementation, draft acdp-rs#386.
**Companion:** split out of the consumer revocation proposal (`rfcs/proposals/consumer-revocation-and-verification-2026-10.md`, PR #77). These two items surfaced in the same `acdp-rs` 0.15.0 implementation pass, but they amend different RFCs and have different reviewers.

> **Process note.** As with the companion proposal, `rfcs/proposals/` is a review vehicle, not a stage defined by `governance/RFC-PROCESS.md`. If maintainers prefer, fold each section into its target RFC as a *(0.5.0)* passage and drop this file.

---

## Summary

Both items make explicit an outcome that today's normative text implies but never states. Neither adds a new check, wire field or error code.

1. **L1. An inclusion proof needs a verified receipt.** RFC-ACDP-0012 §9.1 step 1 rebuilds the leaf from a receipt verified per RFC-ACDP-0010 §8. Without one, the proof cannot be checked. The spec should say this is a *cannot-verify* result, distinct from a failing proof, and never "logged".
2. **L2. A witness quorum needs a verified checkpoint.** RFC-ACDP-0015 §8 counts cosignatures only for "a checkpoint it has itself verified". The spec should say that a consumer with a witness policy verifies the checkpoint whether or not it otherwise checks the log, and that it never reports a quorum over an unverified checkpoint.

## L1. Inclusion proofs without a verifiable receipt *(0.5.0)*

### Problem

**RFC-ACDP-0012 §9.1 step 1** requires the leaf to be rebuilt from *verified* material, including "the receipt hash recomputed from the receipt that was verified per RFC-ACDP-0010 §8", and forbids substituting an echoed `leaf`. It does not say what a consumer reports when the receipt is absent or fails. Implementations are left to choose among three readings:

- **Skip.** Treat the proof as not applicable and say nothing. A report that omits the log verdict looks the same as one from a registry that does not log.
- **`invalid_log_proof`.** This blames the log for what is really a receipt problem, which collides with §9.3's verdict-independence rule.
- **Trust the echo.** Fall back to the served `leaf`, which step 1 forbids.

`acdp-rs` 0.15.0 rebuilds the leaf only from verified material, and reports the proof as uncheckable when no verified receipt exists.

The registry-binding half of the `acdp-rs` observation is **already normative**. §9.3 step 3 binds the `log_id` registry DID to both the serving authority and `capabilities.registry_did`. This proposal only cross-references it.

### Proposed normative text

Append to **RFC-ACDP-0012 §9.1**, after step 6:

> *(0.5.0)* **Precondition: a verified receipt (NORMATIVE).** Step 1 cannot be performed without a receipt that verified per RFC-ACDP-0010 §8. Where the receipt is absent, or failed verification, the consumer MUST report the log verdict as **cannot-verify**. It MUST NOT report the context as logged, MUST NOT substitute an echoed `leaf`, and MUST NOT surface the result as `invalid_log_proof`, which indicts the log. The receipt failure is reported in its own verdict (RFC-ACDP-0010 §8; §9.3 independence). A cannot-verify log verdict is not evidence of a log violation (§3), because the consumer holds no valid receipt to demand inclusion against.

### Conformance vectors to add

**`log-005-proof-without-verified-receipt`** (behavioral, consumer): the `log-001` inclusion proof and checkpoint are served with the matching body.

- **A.** `registry_receipt` is absent. The log verdict is cannot-verify, not logged and not `invalid_log_proof`.
- **B.** The receipt is present but fails RFC-ACDP-0010 §8, for example the `rcpt-002` tampering. The result is the same as A, and the receipt verdict is reported separately as `invalid_receipt`.
- **C.** The served `leaf` member matches the true leaf, but no receipt is served. The result is still cannot-verify: the echo is never trusted.

## L2. Witness quorum over an unverified checkpoint *(0.5.0)*

### Problem

**RFC-ACDP-0015 §8** opens with "a checkpoint it has itself verified (RFC-ACDP-0012 §9.3)". That is a precondition, but it is stated only as a scope phrase. A consumer can leave log-proof checking off (nothing obliges a consumer to verify inclusion or consistency proofs) while keeping a witness quorum policy. It can then count cosignatures that match an *unverified* checkpoint's `(log_id, tree_size, root_hash)` and report it as N-witnessed. That checkpoint might not be the registry's at all: step 4's binding only compares cosignature fields with checkpoint fields, and an unverified checkpoint can carry any values.

`acdp-rs` 0.15.0 verifies the checkpoint itself whenever a witness policy is set, even when log checking is otherwise off, and reports a quorum over an unverified checkpoint as an error.

### Proposed normative text

Append to **RFC-ACDP-0015 §8**, after the N-witnessed paragraph:

> *(0.5.0)* **Precondition: a verified checkpoint (NORMATIVE).** A consumer that applies a witness quorum policy (§8.1) MUST verify the checkpoint per RFC-ACDP-0012 §9.3 before counting cosignatures, whether or not it otherwise verifies inclusion or consistency proofs. If the checkpoint fails or is not verified, the consumer MUST NOT report it as N-witnessed for any N, and it MUST report the witness verdict as failed. This is a checkpoint failure reported through RFC-ACDP-0012's `invalid_log_proof` semantic, not an `invalid_witness_cosignature` for each cosignature, because the cosignatures themselves may be genuine.

### Conformance vectors to add

Extend **`wit-003-quorum-verification`** behaviorally:

- **Scenario X.** The consumer's quorum is 1, and log-proof checking is disabled. The checkpoint's `root_hash` was altered after signing (the `log-004` tampering), and a cosignature over the altered triple verifies. Expected: the checkpoint is verified anyway and fails, the result is not 1-witnessed, and the failure is reported via `invalid_log_proof`.

## Compatibility

- **No wire, schema, body, hash, signature, receipt or checkpoint change.** No new error code. Both items state the outcome of preconditions that the RFCs already impose.
- **Tightenings, scoped to 0.5.0.** L1 forbids "skip silently", "blame the log" and "trust the echo". L2 forbids counting a quorum over an unverified checkpoint. Both are marked *(0.5.0)* and bind only consumers claiming the 0.5.0 `acdp-consumer` profile, following the companion proposal's precedent.
- **Registries:** no new obligation.
- **Fixtures:** `log-005` and the `wit-003` extension are the usual three-file change: fixture JSON, the `acdp-consumer` rows in `registries/profiles.json` and `profiles.md`, and the `schemas/conformance/README.md` index.

## Open questions

- L1: should cannot-verify have a reserved report token alongside the companion proposal's `key_revocation: unknown`, such as `log_inclusion: cannot_verify`? Or is the name left to SDKs?
