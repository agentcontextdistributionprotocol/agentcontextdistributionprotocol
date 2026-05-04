# ACDP Examples

Most files in this directory are illustrative — signatures and content hashes use placeholder values that pass schema validation but are not cryptographically verifiable. The single exception is [`retrieval/golden-context.json`](retrieval/golden-context.json), which carries a REAL Ed25519 signature over a known-good `content_hash` (using the public-domain test keypair from [`schemas/conformance/sig-001-ed25519-golden.json`](../schemas/conformance/sig-001-ed25519-golden.json)). Implementations MUST be able to verify it end-to-end; the conformance runner does so automatically.

## Layout

```
examples/
├── capabilities/           /.well-known/acdp.json documents (RFC-ACDP-0007)
├── error/                  Error envelope examples (RFC-ACDP-0007 §4)
├── idempotency/            Idempotency-Key cycles (RFC-ACDP-0003 §6) — tutorial
├── lineage/                derived_from chain walks (RFC-ACDP-0002 §3.5) — tutorial
├── mixed-data-refs/        Contexts demonstrating all three data_refs forms
├── publish/                Publish requests (POST /contexts body — RFC-ACDP-0003)
├── retrieval/              Full retrieval responses (RFC-ACDP-0004)
│                           — golden-context.json carries a real Ed25519 signature
├── search/                 Keyword search responses (RFC-ACDP-0005)
├── supersession/           v2 superseding v1 (RFC-ACDP-0003 §3)
└── visibility/             restricted / private body examples (RFC-ACDP-0002 §7)
```

Tutorial directories (`idempotency/`, `lineage/`) hold narrative documents that illustrate multi-step flows; they are syntax-checked but not validated against a wire schema. All other directories validate against the schema listed below.

## Validation

These examples are validated by `scripts/validate-json.sh` against:

- `schemas/json/acdp-publish-request.schema.json` — `publish/`
- `schemas/json/acdp-context.schema.json` — `retrieval/`, `supersession/`, `mixed-data-refs/`, `visibility/`
- `schemas/json/acdp-search-response.schema.json` — `search/keyword-search-response.json`
- `schemas/json/acdp-capabilities.schema.json` — `capabilities/`
- `schemas/json/acdp-error.schema.json` — `error/`
- syntax-check only — `idempotency/`, `lineage/` (tutorial documents)

Run `make json-validate` to validate the full set.

## Conformance fixtures

For pass/fail behavioral fixtures (invalid signature, hash mismatch, supersession-target validation, JCS test vectors) see [`schemas/conformance/`](../schemas/conformance/).
