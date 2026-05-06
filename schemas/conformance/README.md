# Conformance Test Fixtures

ACDP conformance fixtures are JSON files that describe a scenario, the input, and the expected behavior. Any compliant implementation MUST produce the specified outcome for each fixture.

---

## Structure

```
conformance/
├── README.md
├── pub-*.json     Publish-flow scenarios (RFC-ACDP-0003)
├── ret-*.json     Retrieval scenarios (RFC-ACDP-0004)
├── vis-*.json     Visibility-leak prevention scenarios (RFC-ACDP-0002, RFC-ACDP-0008)
├── can-*.json     Canonicalization / hashing test vectors (RFC-ACDP-0001)
├── sig-*.json     Cryptographic golden vectors (signing & verification, RFC-ACDP-0001)
├── fed-*.json     Cross-registry / SSRF protection scenarios (RFC-ACDP-0006)
├── err-*.json     Error envelope and HTTP status fixtures (RFC-ACDP-0007)
├── caps-*.json    Capabilities-document validation (RFC-ACDP-0007 §3.5)
├── status-*.json  Registry-state status pattern validation (RFC-ACDP-0004 §4.1)
├── schema-*.json  Schema openness (closed-vs-open) cases (RFC-ACDP-0007 §3.3.1)
├── data-ref-*.json DataRef validation (RFC-ACDP-0002 §6.6)
└── meta-*.json    Metadata limit cases (RFC-ACDP-0002 §3.3)
```

---

## What the bundled conformance runner verifies

`scripts/conformance-runner.py` verifies **arithmetic and cryptographic** vectors only:

- `can-*.json` — JCS canonicalization, SHA-256 hashing, lineage_id derivation
- `sig-*.json` — Ed25519 sign/verify golden vectors

**It does not execute behavioral fixtures** (`pub-*`, `vis-*`, `ret-*`, `err-*`). Those fixtures define request/response scenarios that require a running registry to execute. They are machine-readable specifications for registry implementers to validate against their implementation.

To claim full conformance a registry MUST:
1. Pass `python3 scripts/conformance-runner.py` (arithmetic/cryptographic)
2. Separately execute all `pub-*`, `vis-*`, `ret-*`, and `err-*` fixture scenarios against a live registry instance

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
| `pub-007` | Publish response shape — exactly five fields, no `content_hash` or other body fields echoed back | success: HTTP 201; response object pinned to `{ctx_id, lineage_id, version, created_at, status}` |
| `pub-008` | `body.agent_id` is not `did:web` (v0.0.1 §5.4 mandate) | failure: `schema_violation` (preferred) or `key_not_authorized` |
| `pub-009` | `signature.key_id` DID is not `did:web` while `agent_id` is `did:web` | failure: `key_not_authorized` |
| `pub-010` | Non-`did:web` entry in `contributors[]` (attribution-only — registry MUST accept) | success |

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
| `data-ref-007` | `embedded.content_hash` present but does not match decoded bytes | failure: `hash_mismatch` |

### Retrieval (RFC-ACDP-0004)

| ID | Description | Outcome |
|---|---|---|
| `ret-001` | `ctx_id` does not exist | failure: `not_found` |

### Visibility (RFC-ACDP-0002, RFC-ACDP-0008)

| ID | Description | Outcome |
|---|---|---|
| `vis-001` | Restricted retrieval — authorized=200, unauthorized=404 indistinguishably from genuinely-missing; contributors NOT auto-authorized | mixed (per-scenario; unauthorized cases use `not_found`) |
| `vis-002` | Search excludes restricted contexts from BOTH `matches` AND `total_estimate`; anonymous requests handled per `anonymous_public_reads` capability | mixed (per-scenario) |
| `vis-003` | Search response wrapping key MUST be `matches` (not `results`); registry MUST emit, consumer MUST reject substitutes | mixed (per-scenario; both sides exercised) |

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

**Test DIDs.** The `can-*` canonicalization fixtures use `did:agent:test` as a deliberately short, fictitious DID method to keep canonical-form expected values readable. The precomputed `canonical_form` and `sha256_hex` values depend on the exact string. v0.0.1 wire deployments MUST use `did:web` (RFC-ACDP-0001 §5.4) — `did:agent:` is a test-only convention and is not a registered DID method.

All v0.0.1 fixtures listed above are authored. The `can-005` fixture's "absent tags" vector cross-checks with `can-001` vector 1 — they have bit-identical input and MUST produce the same hash. Additional fixtures (embedded-too-large, payload-too-large, race on supersession, etc.) are welcome via PR.

### Cryptographic golden vectors (RFC-ACDP-0001)

| ID | Description | Outcome |
|---|---|---|
| `sig-001` | Real Ed25519 keypair (test seed of 32 zero bytes); produce content_hash, sign, verify, derive lineage. | success: byte-exact reproduction of canonical form, content_hash, signature, lineage_id |
| `sig-002` | Real ECDSA-P256 keypair (private scalar = 1); same producer content as `sig-001`; pinned RFC 6979 deterministic signature in IEEE 1363 r‖s wire form (NOT DER). | success: byte-exact verification of canonical form, content_hash, IEEE 1363 r‖s length (64 bytes), signature verification, lineage_id |

The `sig-*` fixtures are checked by `scripts/conformance-runner.py` (CI). A failing `sig-001` or `sig-002` indicates an end-to-end pipeline defect: JCS, SHA-256, signing-input framing (full `sha256:` prefix), Ed25519/ECDSA, base64, IEEE 1363 r‖s framing for ECDSA (NOT DER), or lineage derivation.

### Cross-registry / SSRF (RFC-ACDP-0006)

| ID | Description | Outcome |
|---|---|---|
| `fed-001` | Cross-registry resolution attempted over plain HTTP — MUST refuse before connecting | failure: `cross_registry_resolution_failed` |
| `fed-002` | Authority resolves to RFC 1918 private IP (10/8, 172.16/12, 192.168/16) — MUST reject after DNS, before connect | failure: `cross_registry_resolution_failed` |
| `fed-003` | Authority resolves to loopback (127/8, ::1) — MUST reject before connect | failure: `cross_registry_resolution_failed` |
| `fed-004` | Authority resolves to link-local (169.254/16, fe80::/10) including IMDS 169.254.169.254 — MUST reject | failure: `cross_registry_resolution_failed` |
| `fed-005` | Cross-authority HTTP redirect from initial request — MUST reject after first redirect | failure: `cross_registry_resolution_failed` |
| `fed-006` | Capabilities document declares `registry_did` ≠ `did:web:<authority>` — MUST reject | failure: `cross_registry_resolution_failed` |

These fixtures are required for `acdp-registry-federated` profile conformance (registries/profiles.md). The bundled conformance runner does not execute them; they describe black-box scenarios that registry integration tests MUST verify against a live deployment.

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

### Registry-state `status` pattern (RFC-ACDP-0004 §4.1)

| ID | Description | Outcome |
|---|---|---|
| `status-001` | Unknown but pattern-conformant value (`"retracted"`) — consumer treats as `active` | accept |
| `status-002` | Uppercase value (`"ACTIVE"`) | reject: `schema_violation` |
| `status-003` | Value containing whitespace (`"in progress"`) | reject: `schema_violation` |
| `status-004` | Empty string | reject: `schema_violation` |

### Schema openness (RFC-ACDP-0007 §3.3.1)

| ID | Description | Outcome |
|---|---|---|
| `schema-001` | Search response with extra `results` field (closed schema) — companion to `vis-003` | reject: `schema_violation` |
| `schema-002` | Publish response echoing `content_hash` (closed schema) — companion to `pub-007` | reject: `schema_violation` |
| `schema-003` | DataRef `embedded` sub-object with extra field (closed sub-schema) | reject: `schema_violation` |
| `schema-004` | Capabilities document with extra top-level field — duplicate angle on `caps-006` | accept |
