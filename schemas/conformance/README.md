# Conformance Test Fixtures

ACDP conformance fixtures are JSON files that describe a scenario, the input, and the expected behavior. Any compliant implementation MUST produce the specified outcome for each fixture.

---

## Structure

```
conformance/
├── README.md
├── pub-*.json      Publish-flow scenarios (RFC-ACDP-0003)
├── idem-*.json     Idempotency-Key scenarios (RFC-ACDP-0003 §6)
├── rate-*.json     Rate-limiting wire-shape scenarios (RFC-ACDP-0008 §4.3)
├── ret-*.json      Retrieval scenarios (RFC-ACDP-0004)
├── vis-*.json      Visibility-leak prevention scenarios (RFC-ACDP-0002, RFC-ACDP-0008)
├── can-*.json      Canonicalization / hashing test vectors (RFC-ACDP-0001, RFC-ACDP-0002 §6.7)
├── lin-*.json      Lineage-id derivation golden vectors (RFC-ACDP-0001 §5.6)
├── sig-*.json      Cryptographic golden vectors (signing & verification, RFC-ACDP-0001)
├── rcpt-*.json     Registry receipts — golden vector + verification failures (RFC-ACDP-0010, 0.2.0)
├── lhr-*.json      Lineage-head receipts — golden vector + verification failures (RFC-ACDP-0011, 0.3.0)
├── log-*.json      Registry transparency log — Merkle golden vectors + verification failures (RFC-ACDP-0012, 0.3.0)
├── lc-*.json       Lifecycle events & retraction scenarios (RFC-ACDP-0013, 0.3.0)
├── rev-*.json      Producer key revocation — golden vector + boundary semantics (RFC-ACDP-0014, 0.3.0)├── fp-*.json       Key-fingerprint encoding vectors (RFC-ACDP-0010 §6, 0.2.0)
├── rot-*.json      Historical producer-key verification with receipts (RFC-ACDP-0010 §10, 0.2.0)
├── dk-*.json       did:key resolution rejection scenarios (RFC-ACDP-0001 §5.11.1, 0.2.0)
├── fed-*.json      Cross-registry / SSRF protection scenarios (RFC-ACDP-0006 §7; fed-009 receipts, RFC-ACDP-0010 §11)
├── did-ssrf-*.json Producer DID resolution SSRF protection (RFC-ACDP-0008 §4.8)
├── err-*.json      Error envelope and HTTP status fixtures (RFC-ACDP-0007)
├── caps-*.json     Capabilities-document validation (RFC-ACDP-0007 §3.5)
├── status-*.json   Registry-state status pattern validation (RFC-ACDP-0004 §4.1)
├── schema-*.json   Schema openness + absent-vs-null wire convention (RFC-ACDP-0007 §3.3.1, RFC-ACDP-0005 §2.2.1)
├── cur-*.json      Pagination cursor expiry / validity (RFC-ACDP-0005 §2.5.4)
├── data-ref-*.json DataRef validation (RFC-ACDP-0002 §6.5, §6.6)
├── data-ref-ssrf-*.json DataRef location fetch SSRF protection (RFC-ACDP-0008 §4.9)
├── meta-*.json     Metadata limit cases (RFC-ACDP-0002 §3.3)
└── body-*.json     Body identity-field validation (RFC-ACDP-0002 §3)
```

---

## What the bundled conformance runner verifies

`scripts/conformance-runner.py` verifies **arithmetic and cryptographic** vectors only:

- `can-*.json` — JCS canonicalization, SHA-256 hashing, lineage_id derivation
- `lin-*.json` — lineage_id derivation golden vectors
- `sig-*.json` — Ed25519 / ECDSA-P256 sign/verify golden vectors, plus pure did:key identity derivation for `sig-003` (0.2.0)
- `rcpt-*.json` carrying a `registry_test_keypair` (i.e. `rcpt-001`) — full registry-receipt golden cycle: preimage, receipt hash, signature, producer key fingerprint (RFC-ACDP-0010 §5–§6)
- `lhr-*.json` carrying a `registry_test_keypair` (i.e. `lhr-001`) — full lineage-head-receipt golden cycle: preimage, receipt hash, signature, binding consistency (RFC-ACDP-0011 §5, §7)
- `log-*.json` carrying a `registry_test_keypair` (i.e. `log-001`, `log-003`) — full transparency-log golden cycle: JCS leaf encodings, `0x00`/`0x01` domain-separated leaf and node hashes, Merkle roots, signed checkpoints, inclusion-proof and consistency-proof generation and verification-algorithm folding (RFC-ACDP-0012 §4–§6, §9)
- `fp-*.json` — key-fingerprint encoding vectors (RFC-ACDP-0010 §6)

**It does not execute behavioral fixtures** (`pub-*`, `vis-*`, `ret-*`, `err-*`, `cur-*`, `did-ssrf-*`, `data-ref-ssrf-*`, `schema-*`, `dk-*`, `rot-*`, `rcpt-002`..`rcpt-004`, `lhr-002`..`lhr-004`, `log-002`/`log-004`, …). Those fixtures define request/response scenarios that require a running registry or consumer to execute. They are machine-readable specifications for implementers to validate against their implementation.

To claim full conformance a registry MUST:
1. Pass `python3 scripts/conformance-runner.py` (arithmetic/cryptographic)
2. Separately execute all behavioral fixture scenarios (`pub-*`, `vis-*`, `ret-*`, `err-*`, `schema-*`, `cur-*`, `did-ssrf-*`, `data-ref-ssrf-*`, `dk-*`, `rcpt-*`, `lhr-*`, `log-*`, `rot-*`, …) against a live registry instance
- `rev-*.json` carrying a `test_keypair` (i.e. `rev-001`) — key-revocation context golden cycle: same arithmetic as `sig-*`, plus the RFC-ACDP-0014 §4 shape and §5 not-self-signed checks
- `fp-*.json` — key-fingerprint encoding vectors (RFC-ACDP-0010 §6)

**It does not execute behavioral fixtures** (`pub-*`, `vis-*`, `ret-*`, `err-*`, `cur-*`, `did-ssrf-*`, `data-ref-ssrf-*`, `schema-*`, `dk-*`, `rot-*`, `lc-*`, `rcpt-002`..`rcpt-004`, `lhr-002`..`lhr-004`, `rev-002`, …). Those fixtures define request/response scenarios that require a running registry or consumer to execute. They are machine-readable specifications for implementers to validate against their implementation.

To claim full conformance a registry MUST:
1. Pass `python3 scripts/conformance-runner.py` (arithmetic/cryptographic)
2. Separately execute all behavioral fixture scenarios (`pub-*`, `vis-*`, `ret-*`, `err-*`, `schema-*`, `cur-*`, `did-ssrf-*`, `data-ref-ssrf-*`, `dk-*`, `rcpt-*`, `lhr-*`, `rot-*`, `lc-*`, `rev-*`, …) against a live registry instance
---

## Fixture Format

```json
{
  "id": "unique-fixture-id",
  "description": "Human-readable description of the scenario",
  "tags": ["happy-path | failure | security | edge-case"],
  "input": { ... },
  "expected": {
    "outcome": "success | failure",
    "error_code": "code (if failure)",
    "...": "scenario-specific fields"
  }
}
```

---

## Running Conformance Tests

Implementations MUST provide a conformance runner that:

1. Accepts a fixture directory path.
2. Executes each fixture against the implementation.
3. Reports pass/fail per fixture ID.

The runner interface is implementation-defined.

---

## Fixture Index

### Publish flow (RFC-ACDP-0003)

| ID | Description | Outcome |
|---|---|---|
| `pub-001` | Producer signature does not verify | failure: `invalid_signature` |
| `pub-002` | Recomputed `content_hash` ≠ submitted `content_hash` | failure: `hash_mismatch` |
| `pub-003` | Supersession target's `lineage_id` ≠ computed lineage of new context | failure: `superseded_target` (`details.reason: lineage_mismatch`) |
| `pub-004` | First-version publish illegally includes `lineage_id` | failure: `schema_violation` |
| `pub-005` | `visibility: restricted` with no `audience` | failure: `schema_violation` |
| `pub-006` | `signature.key_id` DID portion ≠ `body.agent_id` | failure: `key_not_authorized` |
| `pub-007` | Publish response shape — exactly five fields, no `content_hash` or other body fields echoed back (0.2.0: receipts-profile registries additionally return `registry_receipt`, and nothing else) | success: HTTP 201; response object pinned to `{ctx_id, lineage_id, version, created_at, status}` (+ `registry_receipt` under the receipts profile) |
| `pub-008` | `body.agent_id` is not `did:web` (v0.1.0 §5.4 mandate) | failure: `schema_violation` (preferred) or `key_not_authorized` |
| `pub-009` | `signature.key_id` DID is not `did:web` while `agent_id` is `did:web` | failure: `key_not_authorized` |
| `pub-010` | Non-`did:web` entry in `contributors[]` (attribution-only — registry MUST accept) | success |
| `pub-011` | Persist-only-after-signature-verify atomicity — body MUST NOT be persisted if signature verification fails, even when `content_hash` is correct | failure: `invalid_signature` + post-failure invariants |
| `pub-012` | PublishRequest with extra unknown top-level field — closed-schema rejection | failure: `schema_violation` |
| `pub-013` | PublishRequest containing producer-supplied registry-assigned `ctx_id` | failure: `schema_violation` |
| `pub-014` | PublishRequest containing producer-supplied registry-assigned `created_at` | failure: `schema_violation` |

### Idempotency (RFC-ACDP-0003 §6)

| ID | Description | Outcome |
|---|---|---|
| `idem-001` | First publish with `Idempotency-Key` on a registry that advertises `supports_idempotency_key: true` | success: HTTP 201, durable record |
| `idem-002` | Retry with same `(agent_id, key)` and same `content_hash` | success: HTTP 200 with original response (NOT 201, NOT re-validated) |
| `idem-003` | Reuse of `(agent_id, key)` with different `content_hash` | failure: `duplicate_publish` (HTTP 409) |
| `idem-004` | Same content under a NEW idempotency key — fresh publish, NEW `ctx_id` | success: HTTP 201 |
| `idem-005` | Registry not advertising `supports_idempotency_key` MUST ignore the header (treat as absent) | success: each request mints fresh `ctx_id` |
| `idem-006` | Concurrent publish with same `(agent_id, key)` and same hash — pinned tolerated/non-conformant outcomes | success: cardinality-1 mapping is normative, two outcomes tolerated |
| `idem-007` | *(0.3.0)* Capabilities document advertises `acdp_version` ≥ 0.3.0 with `supports_idempotency_key` absent or `false` — idempotency is REQUIRED for `acdp-registry-core` at 0.3.0 (RFC-ACDP-0003 §6.4; RFC-ACDP-0007 §3.5 item 10) | reject: `schema_violation` (capabilities validation; consumer MUST NOT proceed) |

These fixtures exercise the §6.2 contract and the §6.2.1 ordering/atomicity guidance. `idem-001..005` are REQUIRED for `acdp-registry-core` when the registry advertises `supports_idempotency_key: true`. `idem-006` is informative — the wire contract is "exactly one stored `ctx_id` per `(agent_id, key)` pair regardless of concurrency"; integration tests SHOULD verify with stress harnesses. *(0.3.0)* `idem-007` pins the RFC-ACDP-0003 §6.4 tightening: a registry advertising `acdp_version` ≥ 0.3.0 MUST advertise `supports_idempotency_key: true` (making `idem-001..005` unconditionally required for it) and MUST implement the §6.2.2 atomic storage contract and §6 TTL bounds. It is a capabilities-validation outcome like the `caps-*` family, but lives in the `idem-` family because the requirement it pins is RFC-ACDP-0003 §6 conformance — version-conditional, with implementation of §6 (not document repair) as the remediation; both families are behavioral, so the runner is unaffected.

### Rate limiting (RFC-ACDP-0008 §4.3)

| ID | Description | Outcome |
|---|---|---|
| `rate-001` | Wire shape of `rate_limited` response: HTTP 429, standard error envelope, `Retry-After` MUST be present (integer seconds or HTTP-date; a limiter without an exact refill horizon emits a conservative estimate — RFC-ACDP-0008 §4.3) | failure: `rate_limited` |

Rate-limit triggering depends on registry policy (window, bucket, threshold), so this fixture pins only the wire shape. Implementers MUST self-test the trigger by configuring a known per-agent rate per the recipe in `rate-001-rate-limited-response-shape.json`.

### Metadata limits (RFC-ACDP-0002 §3.3)

| ID | Description | Outcome |
|---|---|---|
| `meta-001` | Metadata nesting depth > 8 levels | failure: `schema_violation` |
| `meta-002` | JCS-canonicalized metadata > 65536 bytes | failure: `schema_violation` |
| `meta-003` | Metadata at exactly depth 8 (boundary) | success |

### DataRef validation (RFC-ACDP-0002 §6.6)

| ID | Description | Outcome |
|---|---|---|
| `data-ref-001` | Neither `location` nor `embedded` present | failure: `schema_violation` |
| `data-ref-002` | Both `location` and `embedded` present | failure: `schema_violation` |
| `data-ref-003` | URI location contains userinfo credentials | failure: `schema_violation` |
| `data-ref-004` | Structured location object missing `scheme` field | failure: `schema_violation` |
| `data-ref-005` | Embedded decoded size > 65536 bytes | failure: `embedded_too_large` |
| `data-ref-006` | `embedded.encoding` is `utf8` or `base64` but `content` is not a string | failure: `schema_violation` |
| `data-ref-007` | `embedded.content_hash` present but does not match decoded bytes | failure: `data_ref_hash_mismatch` |
| `data-ref-008` | External `data_ref.location` whose fetched bytes do not match `data_ref.content_hash` — consumer-side fetch-time check; the body signature and body `content_hash` stay valid | failure: `data_ref_hash_mismatch` (body still verified) |

### DataRef location SSRF (RFC-ACDP-0008 §4.9)

| ID | Description | Outcome |
|---|---|---|
| `data-ref-ssrf-001` | Consumer fetches a `data_refs[].location` whose `https://` host is a private/loopback/link-local/IMDS IP literal — MUST refuse before connecting | failure: fetch refused; DataRef unfetchable, body still valid |
| `data-ref-ssrf-002` | `data_refs[].location` hostname passes URL-syntax checks but resolves via DNS to a loopback/IMDS/private address — MUST refuse after DNS, with the IP pinned (no rebinding) | failure: fetch refused; DataRef unfetchable, body still valid |
| `data-ref-ssrf-003` | `data_refs[].location` fetch receives a cross-authority HTTP redirect — MUST refuse to follow | failure: fetch refused; DataRef unfetchable, body still valid |
| `data-ref-ssrf-004` | `data_refs[].location` host resolves to a DNS answer set mixing a public and a forbidden address — MUST reject the entire resolution (filter-and-proceed is non-conformant) | failure: fetch refused; DataRef unfetchable, body still valid |
| `data-ref-ssrf-005` | `data_refs[].location` fetch is redirected to the same host but a different port — MUST refuse (authority = scheme + host + effective port) | failure: fetch refused; DataRef unfetchable, body still valid |

A `data_refs[].location` URL is producer-controlled, so a consumer dereferencing it over HTTP(S) is making an attacker-influenced outbound request — the same SSRF vector as producer DID resolution (`did-ssrf-*`) and cross-registry resolution (`fed-*`), and it MUST be defended identically (RFC-ACDP-0008 §4.9). These are **consumer-side** fixtures: a registry does not fetch external `data_refs` and MUST NOT reject a publish on these grounds. A refused fetch does not invalidate the body — the producer signature and body `content_hash` remain valid; only the external reference is unreachable on the SSRF-safe path. `data-ref-ssrf-004` pins the mixed-answer rejection rule (RFC-ACDP-0006 §7.1) and `data-ref-ssrf-005` the same-authority redirect definition (RFC-ACDP-0006 §7.5). Required for `acdp-consumer`.

### Body identity fields (RFC-ACDP-0002 §3)

| ID | Description | Outcome |
|---|---|---|
| `body-001` | `body.origin_registry` is a bare DNS hostname matching the `ctx_id` authority | accept |
| `body-002` | `body.origin_registry` is a DID URI (`did:web:...`) instead of a hostname | reject: `schema_violation` |

### Retrieval (RFC-ACDP-0004)

| ID | Description | Outcome |
|---|---|---|
| `ret-001` | `ctx_id` does not exist | failure: `not_found` |
| `ret-002` | `GET /lineages/{id}/current` semantics: all-superseded → `not_found`; expired head → returned with `status: expired`; active head → returned | mixed (per-scenario) |

### Visibility (RFC-ACDP-0002, RFC-ACDP-0008)

| ID | Description | Outcome |
|---|---|---|
| `vis-001` | Restricted retrieval — authorized=200, unauthorized=404 indistinguishably from genuinely-missing; contributors NOT auto-authorized | mixed (per-scenario; unauthorized cases use `not_found`) |
| `vis-002` | Search excludes restricted contexts from BOTH `matches` AND `total_estimate`; anonymous requests handled per `anonymous_public_reads` capability | mixed (per-scenario) |
| `vis-003` | Search response wrapping key MUST be `matches` (not `results`); registry MUST emit, consumer MUST reject substitutes | mixed (per-scenario; both sides exercised) |
| `vis-004` | Private + audience: audience member CAN retrieve by known `ctx_id`; outsider/contributor cannot (RFC-ACDP-0008 §4.5) | mixed (per-scenario) |
| `vis-005` | Private + audience: audience member MUST NOT find context via search/`derived_from` filter; search visibility for `private` is strictly `agent_id`-only | mixed (per-scenario; counts AND `total_estimate` scoped) |
| `vis-006` | Public match SHOULD include `visibility: "public"` in `match_summary` (cache-classification signal) | success: optional disclosure permitted |
| `vis-007` | Restricted/private match served to unauthorized requester MUST omit the match entirely AND MUST NOT carry `visibility` metadata anywhere | mixed (per-scenario; existence-leak prevention) |
| `vis-008` | Lineage endpoints (`GET /lineages/{id}` and `/current`) apply per-context visibility: strangers see `[]` for a fully-restricted lineage, audience members see all versions, partial visibility leaves version gaps, private current head → `not_found` for non-producers | mixed (per-scenario; RFC-ACDP-0004 §5.4) |
| `vis-009` | `anonymous_public_reads` governs keyword search: anonymous search blocked (`not_authorized`) when `false`, public-only when `true`; authenticated requesters unaffected by the flag | mixed (per-scenario; RFC-ACDP-0005 §2.5.5) |

### Canonicalization & hashing (RFC-ACDP-0001)

| ID | Description | Outcome |
|---|---|---|
| `can-001` | Body canonicalization → SHA-256 → lineage derivation test vectors | success: byte-exact reproduction |
| `can-002` | Unicode (NFC) handling — title with é (U+00E9 precomposed) and em dash (U+2014) | success: byte-exact reproduction |
| `can-003` | Body with `metadata` object — verifies nested-key sorting | success: byte-exact reproduction |
| `can-004` | Body with embedded JSON data ref — verifies key sorting inside `data_refs[].embedded` | success: byte-exact reproduction |
| `can-005` | Empty-vs-absent field distinction (`tags: []` vs no `tags` key) | success: distinct hashes; absent-tags vector hash matches `can-001` vector 1 |
| `can-006` | Timestamp precision — nanosecond vs millisecond hash divergence (RFC-ACDP-0001 §5.3 producers MUST truncate) | success: byte-exact reproduction of both vectors |
| `can-007` | Registry-side `created_at` MUST use canonical millisecond precision (RFC-ACDP-0001 §5.3) — descriptive fixture (no JCS round-trip; verify by registry code review + integration regex match `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$`) | conformance verified by registry implementer; runner skips |
| `can-008` | Body with unknown producer-controlled field (`priority`) — consumer MUST include in hash recomputation (RFC-ACDP-0001 §5.7 raw-JSON rule) | success: byte-exact reproduction including the unknown field |
| `can-009` | Stored Body → ProducerContent — exclusion set is stripped BY NAME, regardless of typed-model knowledge | success: byte-exact reproduction matches the stored `content_hash` |
| `can-010` | Body whose `data_refs[]` entry carries an unknown producer-controlled field — DataRef is an open schema, the field MUST be retained in hash recomputation (RFC-ACDP-0002 §6.7) | success: byte-exact reproduction including the unknown DataRef field |
| `can-011` | RFC 8785 §3.2.2.3 numeric serialization (RFC-ACDP-0001 §5.2) — exponential-notation boundaries (≥ 1e21 → `e+`, ≤ 1e-7 → `e-`), the plain-decimal band, integer exactness through 2^53, negative-zero normalization, and IEEE 754 magnitude extremes | success: byte-exact reproduction of all six numeric vectors |
| `can-012` | Divergence-corpus vectors (0.2.0, RFC-ACDP-0001 §6 + Appendix A): `acdp_version` omitted vs explicit `"0.1.0"` vs explicit `"0.2.0"` (three distinct pinned preimages; 0.2.0 producers MUST emit the field), microsecond timestamp divergence + millisecond truncation, and null-vs-absent-vs-empty `metadata` | success: byte-exact reproduction of all seven vectors |

**Test DIDs.** The `can-*` canonicalization fixtures use `did:agent:test` as a deliberately short, fictitious DID method to keep canonical-form expected values readable. The precomputed `canonical_form` and `sha256_hex` values depend on the exact string. v0.1.0 wire deployments MUST use `did:web` (RFC-ACDP-0001 §5.4) — `did:agent:` is a test-only convention and is not a registered DID method.

All v0.1.0 fixtures listed above are authored. The `can-005` fixture's "absent tags" vector cross-checks with `can-001` vector 1 — they have bit-identical input and MUST produce the same hash. Additional fixtures (embedded-too-large, payload-too-large, race on supersession, etc.) are welcome via PR.

### Lineage identifier derivation (RFC-ACDP-0001 §5.6)

| ID | Description | Outcome |
|---|---|---|
| `lin-001` | Dedicated golden vectors for `lineage_id = "lin:sha256:" + lowercase_hex(SHA-256(utf8(first_version_ctx_id)))`. Three vectors over different `ctx_id` authorities. | success: byte-exact reproduction of each `lineage_id` |

`lin-001` is executed by `scripts/conformance-runner.py` with the same lineage-derivation check applied to `can-*` lineage vectors. Its vectors cross-check `can-001` (lineage vectors 1–3) and `sig-001` (`registry_assigned.lineage_id`); all three MUST agree.

### Cryptographic golden vectors (RFC-ACDP-0001)

| ID | Description | Outcome |
|---|---|---|
| `sig-001` | Real Ed25519 keypair (test seed of 32 zero bytes); produce content_hash, sign, verify, derive lineage. | success: byte-exact reproduction of canonical form, content_hash, signature, lineage_id |
| `sig-002` | Real ECDSA-P256 keypair (private scalar = 1); same producer content as `sig-001`; pinned RFC 6979 deterministic signature in IEEE 1363 r‖s wire form (NOT DER). | success: byte-exact verification of canonical form, content_hash, IEEE 1363 r‖s length (64 bytes), signature verification, lineage_id |
| `sig-003` | did:key golden vector (0.2.0): real Ed25519 keypair (test seed of 32 `0x42` bytes); derive `did:key:z…` identity (multicodec `0xed01` + base58-btc), pure resolution (RFC-ACDP-0001 §5.11.1), explicit `acdp_version: "0.2.0"` inside the signed bytes; produce content_hash, sign, verify, derive lineage. | success: byte-exact reproduction of did:key identity, canonical form, content_hash, signature, lineage_id |

The `sig-*` fixtures are checked by `scripts/conformance-runner.py` (CI). A failing `sig-001`, `sig-002`, or `sig-003` indicates an end-to-end pipeline defect: JCS, SHA-256, signing-input framing (full `sha256:` prefix), Ed25519/ECDSA, base64, IEEE 1363 r‖s framing for ECDSA (NOT DER), did:key identity derivation (`sig-003`), or lineage derivation.

### Registry receipts & key fingerprints (RFC-ACDP-0010, 0.2.0)

| ID | Description | Outcome |
|---|---|---|
| `rcpt-001` | Receipt golden vector: registry test keypair (seed of 32 `0x11` bytes), receipt preimage canonical bytes, receipt hash, Ed25519 signature, producer `key_fingerprint`. Executed by the runner — the `sig-001`-equivalent for the receipt layer. | success: byte-exact reproduction end-to-end |
| `rcpt-002` | `created_at` tampered after minting → recomputed preimage diverges → receipt signature MUST fail to verify (body verdict independent) | failure: `invalid_receipt` category |
| `rcpt-003` | `receipt.key_fingerprint` ≠ fingerprint of the resolved producer key (RFC-ACDP-0010 §8 step 5) | failure: `invalid_receipt` category |
| `rcpt-004` | `receipt.registry_did` does not bind to the serving authority (RFC-ACDP-0010 §8 step 2; same principle as `fed-006`) | failure: `invalid_receipt` category |
| `fp-001` | Key-fingerprint encoding vectors (RFC-ACDP-0010 §6): `sha256:` over the raw 32-byte Ed25519 key / 33-byte SEC1-compressed P-256 point — never SPKI, multibase, or JWK serializations. Executed by the runner. | success: byte-exact fingerprints |
| `rot-001` | Historical key verification (RFC-ACDP-0010 §10): K1 retired to verificationMethod-only, K2 current; valid receipt attesting K1's fingerprint → *historically authorized (receipt-attested)*; same retrieval without receipt → fails closed; K1 removed from verificationMethod entirely → fails closed regardless | mixed (per-scenario) |

`rcpt-001` and `fp-001` are executed arithmetically by `scripts/conformance-runner.py`; the runner also verifies `examples/retrieval/golden-context-with-receipt.json` end-to-end against the `rcpt-001` registry keypair. `rcpt-002`..`rcpt-004` and `rot-001` are behavioral. Required for `acdp-registry-receipts` and `acdp-consumer`.

### Lineage-head receipts (RFC-ACDP-0011, 0.3.0)

| ID | Description | Outcome |
|---|---|---|
| `lhr-001` | Head-receipt golden vector: same registry test keypair as `rcpt-001` (RFC-ACDP-0011 §5 reuses the RFC-ACDP-0010 receipt signing key and construction), head-receipt preimage canonical bytes over the sig-001 golden lineage (v1 head, `active`), receipt hash, Ed25519 signature, version-1 lineage-derivation cross-check. Executed by the runner — the `rcpt-001`-equivalent for the serve-time layer. | success: byte-exact reproduction end-to-end |
| `lhr-002` | `/current` serves a v2 head but the attached receipt attests v1 — RFC-ACDP-0011 §7 step 5 head binding MUST fail; the receipt's signature itself verifies (stale-head-serving detection is the point) | failure: `invalid_receipt` category |
| `lhr-003` | `receipt.registry_did` does not bind to the serving authority / `capabilities.registry_did` (RFC-ACDP-0011 §7 step 3; same principle as `rcpt-004` / `fed-006`) | failure: `invalid_receipt` category |
| `lhr-004` | Validly signed receipt whose `as_of` is in the future beyond the clock-skew allowance (RECOMMENDED 120 s) — a forged freshness claim (RFC-ACDP-0011 §7 step 6). Past-dated `as_of` is instead a consumer max-age freshness-policy matter (§6), reported distinctly. | failure: `invalid_receipt` category |

`lhr-001` is executed arithmetically by `scripts/conformance-runner.py`; `lhr-002`..`lhr-004` are behavioral. Required for `acdp-registry-head-receipts`; conditionally required for `acdp-consumer` implementations that rely on `lineage_head_receipt` members (a consumer ignoring the member under the RFC-ACDP-0001 §6 unknown-field rule is unaffected). No new wire error code: head-receipt failures reuse `invalid_receipt` (RFC-ACDP-0011 §9).

### Registry transparency log (RFC-ACDP-0012, 0.3.0)

| ID | Description | Outcome |
|---|---|---|
| `log-001` | Leaf-and-root golden vector: five leaves (leaf 0 = the `rcpt-001` receipt's publish event, binding rcpt-001's pinned receipt hash), JCS leaf encodings, §5.1 leaf hashes (`SHA-256(0x00 ‖ JCS(leaf))`), the tree-size-5 Merkle root (`0x01`-prefixed interior nodes, RFC 6962 §2.1), a checkpoint signed with the shared registry receipt test keypair, and the inclusion proof for leaf 0. Executed by the runner — the `sig-001`-equivalent for the log layer. | success: byte-exact reproduction end-to-end |
| `log-002` | The `log-001` inclusion proof with one tampered `inclusion_path` element — the §9.1 fold yields a root ≠ the checkpoint's `root_hash`; the checkpoint's own signature verifies (the failure is the tree arithmetic, not the cryptography) | failure: `invalid_log_proof` category |
| `log-003` | Consistency-proof golden vector: RFC 6962 §2.1.2 `PROOF(3, D[5])` between tree sizes 3 and 5 of the `log-001` tree, both checkpoints signed; §9.2 verification end-to-end — the history-rewrite detector. Executed by the runner. | success: byte-exact reproduction end-to-end |
| `log-004` | A checkpoint whose `root_hash` was altered after signing (original signature bytes kept) — JCS-recomputing the preimage yields a different checkpoint hash, so the signature MUST fail to verify (RFC-ACDP-0012 §9.3 step 2; the `rcpt-002` analogue one layer up) | failure: `invalid_log_proof` category |

`log-001` and `log-003` are executed arithmetically by `scripts/conformance-runner.py` (including negative self-checks that tampered paths and swapped roots are rejected by the verification algorithms); `log-002` and `log-004` are behavioral. Required for `acdp-registry-transparency-log`; conditionally required for `acdp-consumer` implementations that rely on `log_inclusion` members or the `/log/*` endpoints. New wire error code: proof/checkpoint failures surface as `invalid_log_proof`, deliberately distinct from `invalid_receipt` (RFC-ACDP-0012 §11).
### Lifecycle events & retraction (RFC-ACDP-0013, 0.3.0)

| ID | Description | Outcome |
|---|---|---|
| `lc-001` | End-to-end retraction flow: authenticated `POST /contexts/{ctx_id}/retract` with a producer-signed event → `status: retracted`, event appended (append-only); body remains retrievable byte-identical (mark-not-delete) and the body-only endpoint is untouched; excluded from default search, returned under `status=retracted`; double retract → `invalid_lifecycle_transition` (409); `/republish` reverses with both events retained | mixed (per-scenario) |
| `lc-002` | Lifecycle request attempting to supply/alter body content (a `body` member or body-field-named member) → `immutable_field` (400), distinct from `schema_violation`; actor ≠ `agent_id` → `not_authorized` (403, after visibility); unsigned producer event → rejected | failure (per-scenario codes) |
| `lc-003` | `/current` with retraction (RFC-ACDP-0013 §8.3): a retracted version is never a head; all-superseded-or-retracted lineage → `not_found`; recovery via supersession of the retracted head or republication; head receipts (where advertised) never name a retracted head | mixed (per-scenario) |

All `lc-*` fixtures are behavioral. Required for `acdp-registry-lifecycle`; `lc-001`/`lc-003` are conditionally required (consumer-observable aspects) for `acdp-consumer` implementations retrieving from lifecycle-advertising registries. The event vocabulary is the open registry `registries/lifecycle-event-types.md` (v1: `retracted`, `republished`); the event object schema (`acdp-lifecycle-event.schema.json`) is closed.

### Producer key revocation (RFC-ACDP-0014, 0.3.0)

| ID | Description | Outcome |
|---|---|---|
| `rev-001` | Key-revocation context golden vector: producer-signed `key-revocation` body revoking K1 (the `sig-001` key; fingerprint as in `fp-001`/`rot-001`), signed by current key K2 (the `sig-003` seed — `rot-001`'s K2). Canonical form, `content_hash`, Ed25519 signature over the ASCII `content_hash` string; §4 shape (public visibility, §6-encoded fingerprint, canonical-ms `compromised_since`); §5 not-self-signed rule. Executed by the runner. | success: byte-exact reproduction end-to-end |
| `rev-002` | Compromise-boundary semantics (RFC-ACDP-0014 §7), completing `rot-001`: receipt-attested publish time strictly before `compromised_since` → *historically authorized (pre-compromise, receipt-attested)*; at/after → fail closed despite a valid receipt; no receipt (publish time unverifiable) → fail closed under the strict profile; producer-signed vs registry-attested trust classes distinguishable | mixed (per-scenario) |

`rev-001` is executed arithmetically by `scripts/conformance-runner.py`; `rev-002` is behavioral. Both are required for 0.3.0 `acdp-consumer` implementations; `rev-001`'s registry-side rejections (shape → `schema_violation`; self-signed-by-revoked-key → `key_not_authorized`) bind to `acdp-registry-core` at `acdp_version` ≥ 0.3.0. No new wire error code and no profile: revocation rides existing surfaces (RFC-ACDP-0014 §10).
### did:key resolution (RFC-ACDP-0001 §5.4 / §5.11.1, 0.2.0)

| ID | Description | Outcome |
|---|---|---|
| `dk-001` | did:key with a multicodec prefix that is neither `0xed01` (varint of `ed25519-pub` code `0xed`) nor `0x8024` (varint of `p256-pub` code `0x1200`) — e.g. secp256k1 `0xe701` | failure: `key_resolution_failed` |
| `dk-002` | Malformed multibase: non-`z` prefix, characters outside the base58-btc alphabet, or payload too short | failure: `key_resolution_failed` |
| `dk-003` | Cryptographically valid did:key publish against a registry that does NOT advertise `"did:key"` in `supported_did_methods` | failure: `key_resolution_failed` (permanent — pinned code choice, RFC-ACDP-0007 §3.1) |
| `dk-004` | `signature.key_id` fragment ≠ the DID's method-specific identifier (`did:key:z<mb>#z<mb>` convention) | failure: `key_resolution_failed` |

did:key resolution is **pure** — no network, no DID document, no `assertionMethod` check (the DID *is* the key). The golden path is `sig-003`. `dk-001`/`dk-002`/`dk-004` are required for registries advertising `did:key` and for all 0.2.0 consumers; `dk-003` is required for 0.2.0 registries that do not advertise it.

### Cross-registry / SSRF (RFC-ACDP-0006)

| ID | Description | Outcome |
|---|---|---|
| `fed-001` | Cross-registry resolution attempted over plain HTTP — MUST refuse before connecting | failure: `cross_registry_resolution_failed` |
| `fed-002` | Authority resolves to RFC 1918 private IP (10/8, 172.16/12, 192.168/16) — MUST reject after DNS, before connect | failure: `cross_registry_resolution_failed` |
| `fed-003` | Authority resolves to loopback (127/8, ::1) — MUST reject before connect | failure: `cross_registry_resolution_failed` |
| `fed-004` | Authority resolves to link-local (169.254/16, fe80::/10) including IMDS 169.254.169.254 — MUST reject | failure: `cross_registry_resolution_failed` |
| `fed-005` | Cross-authority HTTP redirect from initial request — MUST reject after first redirect | failure: `cross_registry_resolution_failed` |
| `fed-006` | Capabilities document declares `registry_did` ≠ `did:web:<authority>` — MUST reject | failure: `cross_registry_resolution_failed` |
| `fed-007` | DNS answer set mixing a public and a forbidden address — MUST reject the entire resolution (filter-and-proceed is non-conformant) | failure: `cross_registry_resolution_failed` |
| `fed-008` | Redirect to the same host but a different port — MUST reject (same host ≠ same authority; authority = scheme + host + effective port) | failure: `cross_registry_resolution_failed` |
| `fed-009` | (0.2.0) Upstream registry advertises `acdp-registry-receipts` and serves a receipt — resolver MUST verify it per RFC-ACDP-0010 §8 against the REMOTE authority, preserve it verbatim on success, and surface failure (or a missing receipt from a profile-advertising upstream) as `invalid_receipt` | mixed (per-scenario; failures: `invalid_receipt`, HTTP 502) |
| `fed-010` | A `derived_from` walk truncated by a §4.1 traversal control (depth / total nodes / fanout / timeout) — a surfaced partial result MUST carry an explicit truncation marker (e.g. `complete: false`) and MUST NOT be presented as exhaustive; aborting with `cross_registry_resolution_failed` remains conformant | success: partial result with truncation flag |

These fixtures are required for `acdp-registry-federated` profile conformance (registries/profiles.md). The bundled conformance runner does not execute them; they describe black-box scenarios that registry integration tests MUST verify against a live deployment. `fed-007` pins the mixed-answer rejection rule (RFC-ACDP-0006 §7.1), `fed-008` the same-authority redirect definition (RFC-ACDP-0006 §7.5), and `fed-010` the partial-walk reporting rule (RFC-ACDP-0006 §4.1 — truncation is not completeness). `fed-009` is required when the resolver also advertises `acdp-registry-receipts` or resolves from receipts-advertising upstreams; `fed-010` is additionally required for `acdp-consumer` implementations that walk `derived_from`, whether or not they resolve cross-registry.

### Error envelope (RFC-ACDP-0007)

| ID | Description | Outcome |
|---|---|---|
| `err-001` | 500 Internal Error returns the standard envelope with `internal_error` code | failure: HTTP 500, envelope-conformant |

### Capabilities document (RFC-ACDP-0007 §3.5)

| ID | Description | Outcome |
|---|---|---|
| `caps-001` | Minimal valid capabilities document | accept |
| `caps-002` | `supported_signature_algorithms` lacks `"ed25519"` | reject: `schema_violation` |
| `caps-003` | `supported_did_methods` lacks `"did:web"` | reject: `schema_violation` |
| `caps-004` | `supports_idempotency_key: true` but `limits.idempotency_key_ttl_seconds` missing | reject: `schema_violation` |
| `caps-005` | `limits.max_embedded_bytes != 65536` | reject: `schema_violation` |
| `caps-006` | Unknown top-level field — consumer MUST tolerate (open schema) | accept |
| `caps-007` | *(0.3.0)* `limits.max_publish_per_minute` present and ≥ 1 — OPTIONAL advisory per-agent publish ceiling (RFC-ACDP-0007 §3.2, RFC-ACDP-0008 §4.3); reject variants pin zero / negative / non-integer values | accept (valid doc); reject variants: `schema_violation` |

### Registry-state `status` pattern (RFC-ACDP-0004 §4.1)

| ID | Description | Outcome |
|---|---|---|
| `status-001` | Unknown but pattern-conformant value (`"retracted"`) — consumer treats as `active` | accept |
| `status-002` | Uppercase value (`"ACTIVE"`) | reject: `schema_violation` |
| `status-003` | Value containing whitespace (`"in progress"`) | reject: `schema_violation` |
| `status-004` | Empty string | reject: `schema_violation` |

### Schema openness & wire convention (RFC-ACDP-0007 §3.3.1, RFC-ACDP-0005 §2.2.1)

| ID | Description | Outcome |
|---|---|---|
| `schema-001` | Search response with extra `results` field (closed schema) — companion to `vis-003` | reject: `schema_violation` |
| `schema-002` | Publish response echoing `content_hash` (closed schema) — companion to `pub-007` | reject: `schema_violation` |
| `schema-003` | DataRef `embedded` sub-object with extra field (closed sub-schema) | reject: `schema_violation` |
| `schema-004` | Capabilities document with extra top-level field — duplicate angle on `caps-006` | accept |
| `schema-005` | Search response with `next_cursor: null` — `next_cursor` is a non-nullable bare string; absent optional fields MUST be omitted, not nulled | reject: `schema_violation` |
| `schema-006` | `match_summary` with `summary: null` — non-nullable bare string | reject: `schema_violation` |
| `schema-007` | `match_summary` with `domain: null` — non-nullable bare string | reject: `schema_violation` |
| `schema-008` | Body `signature` object with an extra field (closed sub-schema) | reject: `schema_violation` |
| `schema-009` | Body `data_period` object with an extra field (closed sub-schema) | reject: `schema_violation` |
| `schema-010` | Capabilities `limits` sub-object with an extra field (closed sub-schema inside the open document) | reject: `schema_violation` |
| `schema-011` | `DataRef.format` is `null` — optional, non-nullable string; MUST be omitted, not nulled (RFC-ACDP-0002 §6.8) | reject: `schema_violation` |
| `schema-012` | `DataRef.location` is `null` — not nullable; mutual exclusivity with `embedded` does not make it nullable (RFC-ACDP-0002 §6.8) | reject: `schema_violation` |
| `schema-013` | Error envelope `error.details` is `null` — optional, non-nullable object; MUST be omitted, not nulled | reject: `schema_violation` |
| `schema-014` | Capabilities `limits.idempotency_key_ttl_seconds` is `null` — optional, non-nullable integer; MUST be omitted, not nulled | reject: `schema_violation` |

`schema-005`..`schema-007` pin the absent-vs-null wire convention (RFC-ACDP-0005 §2.2.1): an optional field whose schema types it as a bare string is NOT nullable on the wire; `null` is rejected, `supersedes` (typed `string | null`) is the contrasting legitimately-nullable field. `schema-008`..`schema-010` pin the closed nested schemas in the openness map. `schema-011`..`schema-014` extend the absent-vs-null convention to `DataRef` optional fields (`format`, `location` — RFC-ACDP-0002 §6.8), the error envelope (`error.details`), and the capabilities document (`limits.idempotency_key_ttl_seconds`): in every case an unset optional field MUST be omitted, and an explicit `null` is a `schema_violation`.

### Pagination cursors (RFC-ACDP-0005 §2.5.4)

| ID | Description | Outcome |
|---|---|---|
| `cur-001` | Search request replays a cursor that was validly issued but is now stale (validity window elapsed or result set mutated) | failure: `cursor_expired` (HTTP 400) |
| `cur-002` | Search request supplies a malformed / never-issued cursor the registry cannot parse | failure: `invalid_cursor` (HTTP 400) |

`cursor_expired` (was valid, now stale) and `invalid_cursor` (never parseable) are kept distinct so a client can tell "restart pagination" apart from "this cursor is corrupt or forged". Both are required for the `acdp-registry-discovery` profile.

### Producer DID resolution / SSRF (RFC-ACDP-0008 §4.8)

| ID | Description | Outcome |
|---|---|---|
| `did-ssrf-001` | Producer `did:web` authority resolves to a loopback address (`127.0.0.0/8`, `::1`, `0.0.0.0`) — MUST refuse before connecting | failure: `key_resolution_failed` (HTTP 400) |
| `did-ssrf-002` | Producer `did:web` authority resolves to the cloud-metadata / IMDS address (`169.254.169.254`) or other link-local target | failure: `key_resolution_failed` (HTTP 400) |
| `did-ssrf-003` | Producer `did:web` authority resolves to an RFC 1918 private-range address (`10/8`, `172.16/12`, `192.168/16`, `fc00::/7`) | failure: `key_resolution_failed` (HTTP 400) |
| `did-ssrf-004` | Producer `did:web` host resolves to a DNS answer set mixing a public and a forbidden address — MUST reject the entire resolution (filter-and-proceed is non-conformant) | failure: `key_resolution_failed` (HTTP 400) |
| `did-ssrf-005` | Producer DID-document fetch is redirected to the same host but a different port — MUST reject (authority = scheme + host + effective port) | failure: `key_resolution_failed` (HTTP 400) |

Producer DID resolution happens at publish-time signature verification (RFC-ACDP-0003 §2.1 step 6) and at consumer-side end-to-end verification (RFC-ACDP-0008 §4.4). It is the same SSRF vector as cross-registry resolution (`fed-*`) and MUST be defended identically — see RFC-ACDP-0008 §4.8. The refusal is permanent and producer-caused, so the code is `key_resolution_failed` (HTTP 400, not retryable), never `key_resolution_unreachable` (HTTP 502). `did-ssrf-004` pins the mixed-answer rejection rule (RFC-ACDP-0006 §7.1) and `did-ssrf-005` the same-authority redirect definition (RFC-ACDP-0006 §7.5). Required for `acdp-registry-core` and `acdp-consumer`.
