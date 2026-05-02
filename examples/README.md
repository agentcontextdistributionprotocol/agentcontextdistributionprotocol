# ACDP Examples

These are illustrative JSON artifacts for the ACDP wire format. They are **not** real cryptographic material — signatures and content hashes use placeholder values that pass schema validation but are not verifiable.

## Layout

```
examples/
├── publish/                Publish requests (POST /contexts body — RFC-ACDP-0003)
├── retrieval/              Full retrieval responses (RFC-ACDP-0004)
├── supersession/           v2 superseding v1 (RFC-ACDP-0003 §3)
├── search/                 Keyword and similarity responses (RFC-ACDP-0005)
├── capabilities/           /.well-known/acdp.json documents (RFC-ACDP-0007)
├── error/                  Error envelope examples (RFC-ACDP-0007 §4)
└── mixed-data-refs/        Contexts demonstrating all three data_refs forms
```

## Validation

These examples are validated by `scripts/validate-json.sh` against:

- `schemas/json/acdp-publish-request.schema.json` — `publish/` directory
- `schemas/json/acdp-context.schema.json` — `retrieval/`, `supersession/`, `mixed-data-refs/` directories
- `schemas/json/acdp-search-response.schema.json` — `search/keyword-search-response.json`
- `schemas/json/acdp-similarity-response.schema.json` — `search/similarity-response.json`
- `schemas/json/acdp-capabilities.schema.json` — `capabilities/` directory
- `schemas/json/acdp-error.schema.json` — `error/` directory

Run `make json-validate` to validate the full set.

## Conformance fixtures

For pass/fail behavioral fixtures (invalid signature, hash mismatch, supersession-target validation, JCS test vectors) see [`schemas/conformance/`](../schemas/conformance/).
