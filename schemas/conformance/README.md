# Conformance Test Fixtures

ACDP conformance fixtures are JSON files that describe a scenario, the input, and the expected behavior. Any compliant implementation MUST produce the specified outcome for each fixture.

---

## Structure

```
conformance/
├── README.md
├── pub-*.json    Publish-flow scenarios (RFC-ACDP-0003)
├── ret-*.json    Retrieval scenarios (RFC-ACDP-0004)
├── vis-*.json    Visibility-leak prevention scenarios (RFC-ACDP-0002, RFC-ACDP-0008)
├── can-*.json    Canonicalization / hashing test vectors (RFC-ACDP-0001)
├── sig-*.json    Cryptographic golden vectors (signing & verification, RFC-ACDP-0001)
└── err-*.json    Error envelope and HTTP status fixtures (RFC-ACDP-0007)
```

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

### Retrieval (RFC-ACDP-0004)

| ID | Description | Outcome |
|---|---|---|
| `ret-001` | `ctx_id` does not exist | failure: `not_found` |

### Visibility (RFC-ACDP-0002, RFC-ACDP-0008)

| ID | Description | Outcome |
|---|---|---|
| `vis-001` | Restricted retrieval — authorized=200, unauthorized=404 indistinguishably from genuinely-missing; contributors NOT auto-authorized | mixed (per-scenario; unauthorized cases use `not_found`) |
| `vis-002` | Search excludes restricted contexts from BOTH `matches` AND `total_estimate`; anonymous requests handled per `anonymous_public_reads` capability | mixed (per-scenario) |

### Canonicalization & hashing (RFC-ACDP-0001)

| ID | Description | Outcome |
|---|---|---|
| `can-001` | Body canonicalization → SHA-256 → lineage derivation test vectors | success: byte-exact reproduction |
| `can-002` | Unicode (NFC) handling — title with é (U+00E9 precomposed) and em dash (U+2014) | success: byte-exact reproduction |
| `can-003` | Body with `metadata` object — verifies nested-key sorting | success: byte-exact reproduction |
| `can-004` | Body with embedded JSON data ref — verifies key sorting inside `data_refs[].embedded` | success: byte-exact reproduction |
| `can-005` | Empty-vs-absent field distinction (`tags: []` vs no `tags` key) | success: distinct hashes; absent-tags vector hash matches `can-001` vector 1 |

**Test DIDs.** The `can-*` canonicalization fixtures use `did:agent:test` as a deliberately short, fictitious DID method to keep canonical-form expected values readable. The precomputed `canonical_form` and `sha256_hex` values depend on the exact string. v0.0.1 wire deployments MUST use `did:web` (RFC-ACDP-0001 §5.4) — `did:agent:` is a test-only convention and is not a registered DID method.

All v0.0.1 fixtures listed above are authored. The `can-005` fixture's "absent tags" vector cross-checks with `can-001` vector 1 — they have bit-identical input and MUST produce the same hash. Additional fixtures (embedded-too-large, payload-too-large, race on supersession, etc.) are welcome via PR.

### Cryptographic golden vectors (RFC-ACDP-0001)

| ID | Description | Outcome |
|---|---|---|
| `sig-001` | Real Ed25519 keypair (test seed of 32 zero bytes); produce content_hash, sign, verify, derive lineage. | success: byte-exact reproduction of canonical form, content_hash, signature, lineage_id |

The `sig-*` fixtures are checked by `scripts/conformance-runner.py` (CI). A failing `sig-001` indicates an end-to-end pipeline defect: JCS, SHA-256, signing-input framing (full `sha256:` prefix), Ed25519, base64, or lineage derivation.

### Error envelope (RFC-ACDP-0007)

| ID | Description | Outcome |
|---|---|---|
| `err-001` | 500 Internal Error returns the standard envelope with `internal_error` code | failure: HTTP 500, envelope-conformant |
