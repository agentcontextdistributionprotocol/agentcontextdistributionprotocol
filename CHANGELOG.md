# Changelog

## v0.0.1 (Draft) — current

The first published version of ACDP. **Coordination-agnostic substrate from the start.** No retraction, no post-publication relationships, no push subscriptions in this version — those are deferred (see RFC-ACDP-0009 Extensions, reserved).

### Iteration 1 changes (Phase 0–1, T3.4)

- **T0.1:** Removed binary-schema artifacts and tooling. ACDP v0.0.1 ships JSON-only; binary bindings deferred to a future version.
- **T1.1:** Reordered publish validation steps. Hash recomputation now precedes signature verification; step 6 explicitly resolves the signing key and verifies the DID portion of `signature.key_id` equals `body.agent_id`; step 12 makes private-visibility audience exclude contributors.
- **T1.2:** Made `content_hash` preimage explicit. `content_hash` itself is in the exclusion list ('a field cannot contain its own hash').
- **T1.3:** Standardized `content_hash` on `sha256:<hex>` form. Schema regex tightened from `^(sha256:)?[0-9a-f]{64}$` to `^sha256:[0-9a-f]{64}$`. Signature input is the bytes of the full prefixed string.
- **T1.4:** Clarified emit-vs-accept distinction for timestamps. MUST emit canonical millisecond form; MUST accept any RFC 3339; producer note about hash collisions on differing fractional precision.
- **T1.5:** Forbade `lineage_id` in first-version publish requests (MUST NOT). Schema enforces via allOf clause.
- **T1.6:** Added request authentication (RFC-ACDP-0008 §6) — write auth via body signature, read auth via HTTP Signatures / mTLS / OAuth, anonymous reads only with capability advertisement. Capabilities schema gains `read_authentication_methods` and `anonymous_public_reads`.
- **T1.7:** Fixed visibility audience semantics. Private authorizes `agent_id` only (NOT contributors); public requires `audience` absent or empty. Schema enforces.
- **T1.8:** Acknowledged producer-vs-registry binding gap (RFC-ACDP-0008 §9). Producer signatures don't bind `ctx_id` / `lineage_id` / `origin_registry` / `created_at`; weakened the historical-key-validity claim from MUST to SHOULD.
- **T3.4:** Reserved registry receipts in extensions RFC §2.7 for v0.1.

### Iteration 2 changes (Phase A–D)

- **B1 / TA1:** Fixed signature input contradiction. `RFC-ACDP-0003 §2.2 step 3` now signs the bytes of the full `sha256:<hex>` string per `RFC-ACDP-0001 §5.8`.
- **B2 / TA2:** Added missing error codes (`key_resolution_failed`, `key_not_authorized`, `not_implemented`); demoted `visibility_denied` to internal-only (removed from wire enum and registry table; explanatory note added).
- **B3 / TA3:** Fixed discovery RFC §4 contradiction on contributor authorization.
- **B4 / TA4:** Fixed security RFC §7.3 and `docs/threat-model.md` to match weakened §4.4 historical-key claim. Strict / pragmatic verification options documented.
- **S1 / TD1:** Renumbered §10 Known Limitations → §9, §11 References → §10. Section sequence is contiguous §1–§10.
- **B5:** Added Python `-0.0` implementer note to `can-001` JCS fixture.
- **TB1:** Added missing capability fields — `supported_did_methods` (required, MUST include `did:web`), `profiles` (required, ≥1, MUST include `acdp-registry-core` for any registry), `supports_idempotency_key` (optional), `limits.max_embedding_dimensions` (default 4096), `limits.max_top_k` (default 100).
- **TB2:** Defined keyword search semantics (RFC-ACDP-0005 §2.5) — required search fields, AND-of-terms tokenization, registry-defined ranking with `created_at` tiebreaker, opaque cursors with ≥1h validity. New error codes `cursor_expired` (400) and `invalid_cursor` (400).
- **TB3:** Constrained similarity vector inputs (RFC-ACDP-0005 §3.5) — finite IEEE 754 values only, dimension match against model, `top_k` bounds. Normalized 501 'Similarity not implemented' to use the standard error envelope with `not_implemented` code.
- **TB4:** Added Idempotency-Key support (RFC-ACDP-0003 §6). Same key + same `content_hash` → HTTP 200 with original ids. Same key + different `content_hash` → HTTP 409 `duplicate_publish` (new error code).
- **TB5:** Added SSRF protections to RFC-ACDP-0006 §7 — IP-range filtering, HTTPS-only, response/timeout caps, redirect cap on same authority, DNS-rebinding pin. New error code `cross_registry_resolution_failed` (502).
- **TB6:** Forbade cross-registry supersession in v0.0.1 (RFC-ACDP-0003 §3.1 step 2). Reserved for v0.1 in RFC-ACDP-0009 §2.8.
- **TC1:** Rewrote canonicalization fixtures `can-002` through `can-005` with distinguishing titles per fixture; user-provided hashes verified arithmetically.
- **TC2:** Restructured publish negative fixtures (`pub-004`, `pub-005`, `pub-006`) to standard `request: { method, path, content_type, body }` and `expected: { status, error_code }` shape.
- **TC3:** Restructured visibility fixtures (`vis-001`, `vis-002`) to the same shape; paths use percent-encoded `ctx_id`s. Added Python `-0.0` implementer note to `RFC-ACDP-0001 §5.2` (complementing B5).
- **TD3:** Percent-encoded `ctx_id` in `Location` header example (`acdp%3A%2F%2F<authority>%2F<uuid>`); paragraph requiring percent-encoded form on emit and accepting either form on retrieval.
- **TD4:** Split DID schema. `did` is plain (no fragment / query / path); `did_url` is the permissive form. `signature.key_id` now `$ref`s `did_url`.
- **TD5:** Made implementation profiles normative in `RFC-ACDP-0001 §9.1` — `acdp-registry-core`, `acdp-registry-discovery`, `acdp-registry-federated`, `acdp-consumer` each with their MUST list.

### Iteration 3 changes (release-readiness)

- **Tship-A1:** Rewrote RFC-0001 §5.9. Cross-registry impersonation is now correctly framed as registry-honesty protection, not cryptographic protection. Producer signatures bind producer-controlled content; registry-assigned fields rely on registry honesty in v0.0.1.
- **Tship-A2:** Cache headers are now visibility-aware. Public bodies use `Cache-Control: public, max-age=…, immutable`; restricted/private bodies MUST use `Cache-Control: private, no-store`. Closes a privacy leak via shared HTTP caches.
- **Tship-A3:** Aligned RFC-0007 §5 error code registry with the schema (added 7 missing codes; removed `visibility_denied` as a wire code). Wire enum and registry doc now agree exactly.
- **Tship-A4:** Rewrote integration-guide hash and signature flow. Producers now compute `sha256:<hex>` (not bare hex), sign the full prefixed string, and the consumer EXCLUDE set includes `content_hash`.
- **Tship-B1:** Tightened `ctx_id` schema to lowercase authority + RFC 4122 v4 UUID. Updated all fixtures to v4-conforming UUIDs and recomputed lineage_id values.
- **Tship-B2:** Added `contains` constraints to capabilities schema for `supported_signature_algorithms`, `supported_did_methods`, `profiles` (mandatory `ed25519`, `did:web`, `acdp-registry-core`).
- **Tship-B3:** Enforced non-empty `audience` for `visibility: restricted` in publish-request and context-body schemas.
- **Tship-B4:** Clarified the "signed body" invariant. The producer signature covers the producer-controlled portion of the body, not the registry-assigned fields. Light-touch wording change in RFC-0001, README, and overview.
- **Tship-B5:** Added `acdp-similarity-request.schema.json` for POST `/contexts/similar` request bodies; referenced from RFC-0005 §3.2.
- **Tship-C1:** Added `sig-001-ed25519-golden.json` — real Ed25519 keypair, real canonical bytes, real content_hash, real signature, full producer + verifier round-trip.
- **Tship-C2:** Added `scripts/conformance-runner.py` and wired into CI. Conformance vectors are now executed, not just structurally validated.
- **Tship-D1:** This entry.

### Iteration 4 changes (post-audit hardening)

Iteration 4 addresses the audit findings from "what remains" review of iteration-3. Five focus areas: forward-compat (open closed enums to keep RFC-0001 §6 promise), interoperability (specify did:web resolution), spec-completeness gaps (idempotency TTL, cursor scoping, error-envelope coverage), wire-payload examples (visibility/lineage/idempotency), and miscellaneous tightening.

#### Forward-compatibility (Phase F)

- **Tship-F1:** Opened closed enums to patterns: `signature.algorithm`, `capabilities.supported_signature_algorithms`, `capabilities.profiles`, `capabilities.read_authentication_methods`. Added named open-vocabulary registries: `registries/signature-algorithms.md`, `registries/auth-methods.md`, `registries/profiles.md`. The `contains` constraints (mandatory `ed25519`, `did:web`, `acdp-registry-core`) remain enforced.
- **Tship-F2:** Opened `status` enum to a string pattern; documented that v0.0.1 consumers MUST tolerate unknown status values and SHOULD treat them as `active` (forward-compat path for v0.1 `retracted`).
- **Tship-F3:** Set `additionalProperties: true` on `acdp-context.schema.json` (top-level) and `signature` def. Lets v0.1 add `registry_receipt` (RFC-0009 §2.7) and signature proof chains without a v0.0.1 schema bump.
- **Tship-F4:** Renamed `lin:<hex>` to `lin:sha256:<hex>` for hash-algorithm namespacing. Updated all fixtures, examples, and the conformance runner. Future ACDP versions can adopt `lin:sha3-256:`, `lin:blake3:`, etc., without colliding with v0.0.1 lineage_ids.
- **Tship-F5:** Added optional producer-signed `body.acdp_version` field (defaults to `0.0.1` when absent). v0.0.1 fixtures continue to validate without changes; v0.1+ producers can self-identify so verifiers apply the right exclusion set.

#### DID resolution and signature integrity (Phase G)

- **Tship-G1:** Specified the `did:web` resolution algorithm in RFC-0001 §5.11 — URL construction, fragment matching against `verificationMethod`, `assertionMethod` authorization check, key-encoding extraction (`publicKeyMultibase`/`publicKeyJwk`), caching guidance. Closes the largest interop gap: two implementations now resolve keys the same way.
- **Tship-G2:** Constrained v0.0.1 producers to `did:web` (matches the registry-side `did:web` mandate). Other DID methods may be supported by individual registries but interop is only guaranteed via `did:web`.
- **Tship-G3:** Tightened `signature.value` length to exactly 88 base64 chars for `ed25519` and `ecdsa-p256` (their 64-byte signatures). Normalized all fixture placeholder signatures to 88 chars.

#### Spec-completeness gaps (Phase H)

- **Tship-H1:** RFC-0004 §4 — reworded "consumer can independently verify status" to "status is registry-attested" (consumers cannot verify the registry's own supersession index without trusting the registry). Added §4.1 forward-compat for unknown status values.
- **Tship-H2:** Bounded idempotency-key TTL to [24h, 168h] and added required `limits.idempotency_key_ttl_seconds` capability advertisement when `supports_idempotency_key: true`. Cursor rule: registries MUST re-scope to the current requester on every page (replay by another principal MUST get that principal's visibility).
- **Tship-H3:** Added `internal_error` (HTTP 500) and `key_resolution_unreachable` (HTTP 502) error codes. Split `key_resolution_failed` into permanent (400, missing key) vs transient (502, network/DNS/TLS) for correct retry semantics. RFC-0007 §4 now says envelope MUST be returned on every failure response, including 5xx.
- **Tship-H4:** RFC-0002 §7.1 — visibility is permanent for a given body (`audience` is signed and immutable; revocation requires a successor). RFC-0001 §5.3 — clock-skew tolerance ±60s for consumer-side `expired` checks. (B12 done in H3.)
- **Tship-H5:** B6/B7/B8/B9/B10/B15/B17/B18/B19/B20/B21/B22 — embedding-model deprecation via `previously_supported_embedding_models`; supersession-race wording cleanup; empty `data_refs` documented; publish step 6 reordering note; `derived_from` depth + cycle-detection guidance; `total_estimate` determinism guard against side-channel inference; `did` regex comment; `data_refs[].location` URI-string requires a scheme; body-only retrieval errors clarified; lineage scoping clarified given v0.0.1 supersession constraints; embedding-on-restricted SHOULD reaffirmed; `match_summary.lineage_id` elevated to required.

#### Examples and fixture corrections (Phase I)

- **Tship-I:** Fixed pub-001 and pub-003 to use arithmetically derived hashes/lineage_ids (audit C12, C13). Added `examples/visibility/{restricted,private}-body.json`, `examples/lineage/multi-step-derivation.json`, `examples/idempotency/idempotency-key-cycle.json`, `schemas/conformance/err-001-internal-error.json`. Documented `details` shape per error code in `acdp-error.schema.json`. Updated `schemas/conformance/README.md` to list `sig-*` and `err-*` fixture families.

#### Cleanup polish (Phase J)

- **Tship-J:** RFC-0001 §3 merged duplicate RFC-0007 reference. RFC-0004 §6.4 ETag literal example. RFC-0008 §3.10 algorithm-downgrade now correctly inverts the dependency (algorithm in body MUST match algorithm of resolved key). RFC-0006 §3 strengthens `registry_did` resolution to SHOULD. Tag regex tightened. `data_period` runtime check note added. `did:agent:` test convention documented in conformance README.

### Included

- **Core** — identifiers, JCS canonicalization, content hashing, signatures, time format (RFC-ACDP-0001).
- **Context Body** — immutable signed body, context types, data references, visibility (RFC-ACDP-0002).
- **Publish** — `POST /contexts`, supersession constraints, registry-assigned fields (RFC-ACDP-0003).
- **Retrieval** — `GET /contexts/{ctx_id}`, body-only retrieval, lineage queries (RFC-ACDP-0004).
- **Discovery** — keyword search with cursor pagination; similarity OPTIONAL (RFC-ACDP-0005).
- **Cross-registry** — `acdp://` URI scheme and resolution flow (RFC-ACDP-0006).
- **Capabilities** — `/.well-known/acdp.json`, error envelope, error code registry (RFC-ACDP-0007).
- **Security** — A2A threat model and required defenses for v0.0.1 (RFC-ACDP-0008).
- **JSON Schemas** for context, body, registry-state, data-ref, publish-request/response, search-response, similarity-response, capabilities, error.
- **Conformance fixtures** for invalid-signature, hash-mismatch, superseded-target-mismatch, not-found, and JCS canonicalization vectors.

### Reserved (numbering pinned, no normative text)

- RFC-ACDP-0009 Extensions — retraction/lifecycle events, post-publication relationships, attestations, push subscriptions, server-side traversal.

### Explicitly out of scope in v0.0.1

- Retraction (any form).
- Post-publication `builds_on` relationships from third parties.
- Attestations (`reproduced` / `disputes`).
- Push subscriptions (poll-based discovery only).
- Server-side traversal (`/walk` endpoint reserved).
- Federation peering, cross-registry query forwarding, cross-registry caching.
- Encrypted bodies (use `data_refs` splitting).
- Hard deletion of any kind.
- Multi-party / threshold signatures (use `contributors`).
- Quality scoring or reputation algorithms by registries.
