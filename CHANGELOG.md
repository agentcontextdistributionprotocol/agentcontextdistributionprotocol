# Changelog

## v0.0.1 — current

ACDP v0.0.1, final. Builds on rc1 with a closing pass on real bugs, citation accuracy, and terminology precision.

### Post-ship audit pass (Taudit-1..7)

A full re-audit of the v0.0.1 repository against the published RFCs found seven real inconsistencies that survived the earlier cleanup rounds. All checks remain green: `make validate` 30/30, conformance runner 14/14. No schema, no wire-shape, and no example/fixture changes — purely citation, governance, and tooling alignment.

- **Taudit-1:** RFC-0003 §2.1 step 12 — fixed dangling `RFC-ACDP-0008 §6.4` reference (§6 only has 6.1–6.3); the contributors-not-auto-authorized text lives in `§4.5`.
- **Taudit-2:** RFC-0005 §6 — `RFC-ACDP-0008 §3.5` pointed at a table row, not a normative subsection. Repointed to `§4.5` (the visibility-enforcement MUST that the citation is actually invoking).
- **Taudit-3:** RFC-0009 §2.7 — fixed dangling `RFC-ACDP-0008 §10.1` reference (§10 is References); the producer-signature-binding-gap discussion lives in `§9.1`.
- **Taudit-4:** governance/GOVERNANCE.md — RFC lifecycle now includes `Release Candidate N` between FCP and Final; Registry Authority section now lists all seven registries (was four; missing `auth-methods`, `profiles`, `signature-algorithms` added in earlier iterations).
- **Taudit-5:** governance/RFC-PROCESS.md — added `Release Candidate N` stage and `Reserved` sidebar state; renamed terminal stage `Accepted` → `Final` to match VERSIONING.md and GOVERNANCE.md; broadened "What does NOT require an RFC" registry-additive bullet from `locator-schemes.md` only to any `registries/` open-vocabulary registry.
- **Taudit-6:** CONTRIBUTING.md — Registry additions section now lists all seven registries (was four).
- **Taudit-7:** CI tooling alignment — `requirements-dev.txt` trimmed from `{jcs, cryptography, jsonschema, referencing}` to `{jcs, cryptography}` (the conformance runner only imports the latter two; `jsonschema`/`referencing` were never used). CI workflow now installs from `requirements-dev.txt` (was hardcoded `pip install jcs cryptography`) so CI and `make bootstrap` cannot drift apart. CONTRIBUTING.md `make bootstrap` description updated to match.
- **Taudit-8:** RFC-0002 §6 numbering — closed the gap between `### 6.3 Embedded Form` and `### 6.5 Visibility scope` by renumbering §6.5 → §6.4 and §6.6 → §6.5. Section §6 is now contiguous (6.1–6.5). Updated the one in-RFC backreference (`see §6.5` → `see §6.4`). No external references existed (the cross-RFC audit pass confirmed); CHANGELOG entries TB6 and Tfinal-B3 still cite the historical `§6.5`/`§6.6` numbers, but CHANGELOG is intentionally a frozen historical record.
- **Taudit-9:** registries/error-codes.md — fixed broken anchor in the `immutable_field` row link to RFC-0009. The actual heading is `### 2.1 Retraction & lifecycle events *(likely v0.1)*`; the GitHub-flavored anchor is `#21-retraction--lifecycle-events-likely-v01` (the `(likely v0.1)` suffix is part of the heading and so part of the anchor).
- **Taudit-10:** rfcs/README.md — RFC lifecycle prose said `Draft → Review → Final Comment Period → Accepted`, contradicting the ladder this audit pass aligned in governance/RFC-PROCESS.md (Taudit-5). Updated to `Draft → Review → Final Comment Period → Release Candidate N → Final` with `Reserved` mentioned as a sidebar state, matching VERSIONING.md and RFC-PROCESS.md.

**Deeper passes that came back clean:** internal §X.Y references within each RFC (38 references across 9 RFCs); JSON Schema $id/$ref integrity (13 schemas, 15 $defs in `acdp-common`, all $refs resolve, no orphan $defs, `acdp-index.schema.json` is an active schema-discovery document); numeric-constant agreement across RFC text + schemas + capabilities example + registries (15 constants — embedded data 64 KB, metadata maxProperties 100, depth 8, serialized 64 KB, max_top_k 100, max_embedding_dimensions 4096, idempotency TTL [86400, 604800], signature value length 88, clock skew ±60s, cursor ≥1h, content_hash/lineage_id/ctx_id formats — all match); manifesto matches v0.0.1 shipped scope (deferred features correctly attributed to RFC-0009).

False positives that did NOT need fixing (verified directly):

- The `acdp-publish-request.schema.json` rule `{"if": {version: 1}, "then": {"not": {"required": ["lineage_id"]}}}` was claimed to be too permissive. ajv confirms it correctly rejects `pub-004-first-version-with-lineage.json` at `#/allOf/4/then/not` — the `not required` pattern does forbid the field.
- `registries/locator-schemes.md` was flagged for missing `acdp://` and `lin:sha256:`. That registry is scoped to `data_refs[].location` schemes only (RFC-0002 §6.2); `acdp://` ctx_ids and `lin:sha256:` lineage_ids are identifiers, not data references.

### v0.0.1-rc1 → v0.0.1 (final pre-ship pass)

- **Tv1-1:** Fixed RFC-0001 §4 registry role summary — hash recomputation now shown before signature verification.
- **Tv1-2:** Aligned RFC-0002 through RFC-0008 Status lines to "Release Candidate 1".
- **Tv1-3:** Federated profile now depends on `acdp-registry-core`, not `acdp-registry-discovery`. Cross-registry resolution does not require keyword search.
- **Tv1-4:** Removed `immutable_field` from wire schema enum; remains reserved for v0.1+ endpoints in registries doc.
- **Tv1-5:** Updated UUID citations from RFC 4122 to RFC 9562.
- **Tv1-6:** Clarified similarity profile gating — consumers check `supported_embedding_models` in the capability document, not the profile name.
- **Tv1-7:** Fixed schema descriptions to distinguish Body from ProducerContent where the imprecision could mislead implementers.

### Iteration Final changes (rc1 → final)

- **Tfinal-A1:** Fixed validation order in docs/architecture.md to match RFC-0003 §2.1 (hash recompute now precedes signature verification).
- **Tfinal-A2:** Enforced `idempotency_key_ttl_seconds` requirement when `supports_idempotency_key: true`. Added schema conditional and updated example.
- **Tfinal-A3:** Aligned all normative RFCs (0001–0008) at 0.0.1-rc1; RFC-0009 stays 0.0.1-reserved.
- **Tfinal-A4:** Marked `immutable_field` as reserved for v0.1+ endpoints (no v0.0.1 endpoint produces it).
- **Tfinal-A5:** Required registry DID verification for `acdp-registry-federated` profile conformance (RFC-0001 §9.1, RFC-0006 §4 step 3).
- **Tfinal-B1:** Locked `signature` schema with `additionalProperties: false`. Future signature variants require an explicit schema bump.
- **Tfinal-B2:** Added metadata depth (max 8 levels) and serialized-size (max 64 KB) limits as runtime checks (RFC-0002 §3.3).
- **Tfinal-B3:** Recommended HTTPS for `data_refs.location`; required `content_hash` for `http://` references (RFC-0002 §6.6).
- **Tfinal-B4:** Dropped `; version=` from media-types registry; protocol version is carried in JSON only.
- **Tfinal-B5:** Documented "schema-valid ≠ publish-valid" implementer note in RFC-0003 §2.
- **Tfinal-C1:** Added real Ed25519 golden retrieval example (`examples/retrieval/golden-context.json`) verified end-to-end by the conformance runner.

### Final cleanup pass (rc1 stamp → 0.0.1 ship)

Two rounds of close-reading found real bugs and documentation drift between the RFCs, schemas, registries, and READMEs that survived earlier iterations. All checks remain green: `make validate` 30/30, conformance runner 14/14, cross-RFC §X.Y references all resolve.

**Round 1 — schema and citation fixes:**

- **Tcleanup-1:** Opened `additionalProperties: true` on `acdp-context-body.schema.json`. Consumers MUST tolerate unknown body fields per RFC-0001 §9 and RFC-0002 §9.3, but the closed schema would have rejected forward-compatible v0.1 bodies. `acdp-publish-request.schema.json` remains closed (publish stays strict).
- **Tcleanup-2:** Fixed wrong `$comment` in `acdp-common.schema.json` signature `$def`. The entire signature object is excluded from ProducerContent (RFC-0001 §5.7), not just `signature.value`.
- **Tcleanup-3:** Replaced `ctx://` typo with `acdp://` in the README file tree comment.
- **Tcleanup-4:** Updated `rfcs/README.md` index table from `Draft` to `Release Candidate 1` for RFCs 0001–0008.
- **Tcleanup-5:** Updated top-level README `Status:` line to `Community Standards Track (Release Candidate 1)`.
- **Tcleanup-6:** Removed duplicate similarity paragraph in RFC-0001 §9.1; the precise capability-document gating sentence (added in Tv1-6) remains as the single statement.
- **Tcleanup-7:** RFC-0001 §11.2 IANA media-type registration now says `Optional parameters: None`. The protocol version is carried in JSON (`acdp_version`), not in the Content-Type. Removes the contradiction with `registries/media-types.md` (set in Tfinal-B4).
- **Tcleanup-8:** Removed `immutable_field` row from RFC-0007 §5 error table — already removed from the wire schema enum in Tv1-4. Added an explicit "Reserved codes" note below the table noting it is reserved for v0.1+ retraction/attestation endpoints.
- **Tcleanup-9:** Marked `examples/lineage/multi-step-derivation.json` as a tutorial document with a `_note` field; documented the syntax-only exclusion in `scripts/validate-json.sh`.

**Round 2 — registry/RFC alignment and version stamps:**

- **T1:** Fixed `registries/profiles.md` — `acdp-registry-federated` prerequisite is `acdp-registry-core`, not `acdp-registry-discovery`. Aligns the registry with RFC-0001 §9.1 (corrected in Tv1-3).
- **T2:** Aligned the §1 "Status of This Memo" body text in every normative RFC (0001–0008) to "Release Candidate 1". Earlier alignment only updated frontmatter `Status:` lines.
- **T3:** Added `idempotency_key_ttl_seconds: 86400` to the RFC-0007 §3 inline capabilities example. The example previously set `supports_idempotency_key: true` without the required TTL.
- **T4:** Added a "What the bundled conformance runner verifies" section to `schemas/conformance/README.md`. Clarifies that `scripts/conformance-runner.py` checks arithmetic + cryptographic vectors only; behavioral fixtures (`pub-*`, `vis-*`, `ret-*`, `err-*`) require a live registry to execute.
- **T5:** Bumped RFC-0002 through RFC-0008 `Version:` stamps from `0.0.1-rc1` → `0.0.1`. RFC-0001 was already at `0.0.1`; RFC-0009 stays `0.0.1-reserved`. This supersedes Tfinal-A3 (which had set them to rc1 during the iteration).

**Round 3 — documentation drift:**

- **Tcleanup-10:** Aligned README file trees with actual directory contents. README.md, `registries/README.md`, and `examples/README.md` had stale snapshots — added the missing entries for `auth-methods.md`, `profiles.md`, `signature-algorithms.md`, `acdp-similarity-request.schema.json`, `idempotency/`, `lineage/`, `visibility/`, and replaced the partial conformance fixture list with a glob summary.
- **Tcleanup-11:** Added `Release Candidate N` and `Reserved` rows to the VERSIONING.md status ladder; updated the RFC `Version:` example from the obsolete `0.0.1-draft` to `0.0.1` with `-rcN`/`-reserved` suffix guidance.
- **Tcleanup-12:** This entry — recorded the cleanup pass in the changelog.

### Deferred to v0.0.2 (informed by implementer feedback)

- Field-level body cuts (`expires_at`, `data_period`, `summary`, `domain` consolidation).
- Similarity search reorganization (currently OPTIONAL within `acdp-registry-discovery`).

### Iteration RC1 changes (final pre-RC pass)

**Phase A — RC1 blockers**

- **TA1:** Fixed RFC-0004 §2.3 contributor authorization. `visibility: private` no longer mistakenly auto-authorizes contributors; the rule now matches RFC-0002 §7 and RFC-0008 §4.5 (only `agent_id` and explicitly-listed `audience` members are authorized).
- **TA2:** Tightened RFC-0001 §4 architecture summary to point at the §5.7 exclusion set explicitly (instead of just "registry-assigned fields", which elided `content_hash` and `signature`). §5.9 cryptographic-vs-registry-honesty distinction was already in place from iteration-3.
- **TA3:** (Already done in iteration-3.) Cache headers are visibility-aware: `public, immutable` for public bodies, `private, no-store` for restricted/private; never `Cache-Control: public` on a non-public body.
- **TA4:** Supersession races (`already_superseded`, `version_mismatch`) now return HTTP 409 Conflict — they are concurrent-state failures, not malformed input. Static supersession violations keep HTTP 400. RFC-0003 §5 publish-error table now enumerates each supersession reason with its specific HTTP status. RFC-0007 §5 `superseded_target` row updated to "400 / 409".
- **TA5:** (Already done in iteration-3.) Integration guide producer/consumer hash + signature flow uses `sha256:<hex>` form, signs ASCII bytes of the full prefixed string, and EXCLUDE set includes `content_hash`.
- **TA6:** Introduced **Body** / **ProducerContent** / **RegistryState** terminology in RFC-0001 §2. The Body is the immutable stored object; ProducerContent is the §5.7-stripped signature/hash preimage; RegistryState is the mutable registry-derived object. Light propagation in RFC-0001 §5.7/§5.9, RFC-0002 §2, RFC-0003 §2.2, README.
- **TA7:** (Already done in iteration-3 as Tship-C1.) Real Ed25519 golden cryptographic vector at `schemas/conformance/sig-001-ed25519-golden.json`.
- **TA8:** Added `make bootstrap` target chaining ajv-cli + Python conformance-runner deps. New `requirements-dev.txt` lists `jcs`, `cryptography`, `jsonschema`, `referencing`. CONTRIBUTING.md gains a "Local development" section; README.md "Development" leads with `make bootstrap`.
- **TA9:** Fixed RFC-0005 §2.1 vs §2.5.1 contradiction. The `q` parameter row no longer claims a 3-field search (title/description/summary) — it now points at §2.5.1 for the canonical 7-field list.

**Phase B — release polish**

- **TB1:** (Already done in iteration-3.) `ctx_id` schema constrained to lowercase authority + RFC 4122 v4 UUID via tightened pattern.
- **TB2:** (Already done in iteration-3.) Capabilities schema uses `contains` to enforce mandatory `ed25519`, `did:web`, `acdp-registry-core`.
- **TB3:** (Already done in iteration-3.) `audience` MUST be non-empty when `visibility: restricted`; enforced via `if/then` in publish-request and context-body schemas.
- **TB4:** (Already done in iteration-3 as Tship-B5.) `acdp-similarity-request.schema.json` exists and is referenced from RFC-0005 §3.2.
- **TB5:** (Already done in iteration-3 as Tship-C2.) Executable conformance runner at `scripts/conformance-runner.py`; wired into `make validate`.
- **TB6:** Added RFC-0002 §6.5 "Visibility scope" — ACDP `visibility` controls registry-record access, not external `data_refs[].location` ACLs. A producer publishing `visibility: private` while pointing at a public S3 URL has effectively published the data publicly; only metadata is private. §7 gains a callout pointing at §6.5.
- **TB7:** Enforced `embedded.encoding` / `embedded.content` type pairing in `acdp-data-ref.schema.json`. `utf8` and `base64` encodings now require `content` to be a string; `json` encoding is unconstrained.
- **TB8:** Bounded `metadata` with `maxProperties: 100` in both `acdp-context-body` and `acdp-publish-request` schemas. RFC-0002 §3.3 documents the structural cap and recommends `data_refs` for larger payloads.
- **TB9:** Aligned replay/idempotency wording across RFCs 0001/0003/0008. RFC-0001 §5.9 now explicitly distinguishes content-level idempotency (intrinsic) from publication-level idempotency (requires `Idempotency-Key`). RFC-0008 §3.7 row uses the same terminology.
- **TB10:** Clarified registry DID is **endpoint identity**, not content authenticity. Added RFC-0006 §3.1 contrasting registry DID ("you are talking to the right server") with producer signature ("this body is from the right producer").
- **TB11:** README and `docs/overview.md` discovery summaries now state that search ranking within results is registry-defined; ACDP does not normatively specify a ranking algorithm.
- **TB12:** Documented why `derived_from` is REQUIRED on the wire even when empty (`derived_from: []`). RFC-0002 §3.5 now explains: an absent field and an empty array produce different JCS canonical bytes (and therefore different `content_hash` values), so requiring the field uniformly removes ambiguity.
- **TB13:** This entry. Version bumped from 0.0.1-draft to 0.0.1-rc1.

---

## v0.0.1 (Draft) — historical

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
