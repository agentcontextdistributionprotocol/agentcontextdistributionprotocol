# Agent Context Description Protocol (ACDP)

**Version:** 0.1.0
**Status:** Community Standards Track (Final)
**Wire format:** JSON over HTTP
**Required JSON canonicalization:** [JCS — RFC 8785](https://datatracker.ietf.org/doc/html/rfc8785)

ACDP is a protocol for autonomous AI agents to **publish, discover, and verify** units of contextual information ("contexts") across distributed systems and organizational boundaries. ACDP defines a wire format, a data model, and a small set of HTTP-based operations that let heterogeneous agents find and build upon each other's work without a coordination protocol or shared trust authority.

ACDP introduces one strict invariant:

> **Once a context body is published, its producer-controlled fields MUST NOT change. The producer-controlled portion of every body MUST be cryptographically signed by its producer, and every lineage MUST be end-to-end verifiable.**

The "producer-controlled portion" — the **ProducerContent** — comprises the fields the producer authors and signs (everything except `ctx_id`, `lineage_id`, `origin_registry`, and `created_at`, which are registry-assigned at publish time). The **Body** is the immutable stored object that wraps ProducerContent plus the registry-assigned identity fields and the signature. See [RFC-ACDP-0001 §2](rfcs/RFC-ACDP-0001-core.md) for the formal Body / ProducerContent / RegistryState definitions, §5.7 for the exact exclusion set, and §5.9 for what the producer signature does and does not bind.

There is no central authority. Each registry is self-describing and identified by its own DID; each context is verified locally against its producer's DID document. ACDP is **coordination-agnostic** — it does not specify session, voting, consensus, marketplace, or reputation semantics.

This is the **first published version** of ACDP, released as **`Final`** (`acdp/0.1.0`). v0.1.0 defines the minimal substrate; lifecycle events, post-publication relationships, attestations, push subscriptions, and server-side traversal are deferred to future versions.

---

## What ACDP looks like

```
Producer Agent                                Consumer Agent
   │                                                │
   │  POST /contexts                                │
   │  (signed body)                                 │
   ├───────────────▶ Registry                       │
   │  ◀── ctx_id, lineage_id, status ───            │
   │                                                │
   │                          GET /contexts/{ctx_id}│
   │                          ◀────────────────────┤
   │                          (body + registry_state)│
   │                                                │
   │      verify producer signature locally,        │
   │      walk derived_from chain to other          │
   │      registries (cross-registry references)    │
```

---

## What this repository contains

This repository is structured like a publishable protocol standard. The normative core is small and stable; implementers get enough architectural and operational guidance to build real registries and clients.

```text
agentcontextdescriptionprotocol/
  manifesto/
    manifesto.md

  rfcs/
    RFC-ACDP-0001-core.md            # Data model, JCS, hashing, signatures
    RFC-ACDP-0002-context-body.md    # The body schema, types, data refs
    RFC-ACDP-0003-publish.md         # Publication and supersession
    RFC-ACDP-0004-retrieval.md       # Retrieval and lineage queries
    RFC-ACDP-0005-discovery.md       # Keyword search
    RFC-ACDP-0006-cross-registry.md  # acdp:// cross-registry reference resolution
    RFC-ACDP-0007-capabilities.md    # /.well-known/acdp.json + errors
    RFC-ACDP-0008-security.md        # Threat model and required defenses
    RFC-ACDP-0009-extensions.md      # Reserved — retraction, attestations…

  docs/
    overview.md
    architecture.md
    discovery.md
    integration-guide.md
    threat-model.md
    why-acdp.md
    non-goals.md

  registries/
    README.md
    auth-methods.md
    context-types.md
    data-ref-types.md
    error-codes.md
    locator-schemes.md
    media-types.md
    profiles.md                      # Profile registry (human-readable)
    profiles.json                    # Profile + conformance manifest (machine-readable)
    signature-algorithms.md

  schemas/
    json/                            # Canonical JSON Schemas
      acdp-capabilities.schema.json
      acdp-common.schema.json
      acdp-context-body.schema.json
      acdp-context.schema.json
      acdp-data-ref.schema.json
      acdp-error.schema.json
      acdp-index.schema.json
      acdp-publish-request.schema.json
      acdp-publish-response.schema.json
      acdp-registry-state.schema.json
      acdp-search-response.schema.json
    conformance/                     # Pass/fail behavioral fixtures + golden vectors
      README.md                      #   — fixture index + family map
      can-*.json  lin-*.json         # JCS canonicalization, hashing, lineage-id vectors
      sig-*.json                     # Ed25519 / ECDSA-P256 cryptographic golden vectors
      pub-*.json  idem-*.json        # Publish-flow and Idempotency-Key scenarios
      ret-*.json  vis-*.json         # Retrieval and visibility-scoping scenarios
      data-ref-*.json                # DataRef validation
      did-ssrf-*.json  data-ref-ssrf-*.json  fed-*.json   # SSRF protections
      caps-*.json  schema-*.json     # Capabilities + schema-openness validation
      body-*.json  meta-*.json  status-*.json  cur-*.json  err-*.json  rate-*.json

  examples/
    README.md
    capabilities/                    # /.well-known/acdp.json (RFC-ACDP-0007)
    error/                           # Error envelope examples
    idempotency/                     # Idempotency-Key cycles (RFC-ACDP-0003 §6)
    key-resolution/                  # DID document examples (RFC-ACDP-0001 §5.11)
    lineage/                         # derived_from chain walk (tutorial)
    mixed-data-refs/                 # All three data_refs forms in one body
    publish/                         # POST /contexts requests (RFC-ACDP-0003)
    retrieval/                       # Full retrieval responses (RFC-ACDP-0004)
                                     #   — golden-context.json carries a real Ed25519 signature
    search/                          # Keyword search responses (RFC-ACDP-0005)
    supersession/                    # v2 superseding v1 (RFC-ACDP-0003 §3)
    visibility/                      # restricted / private body examples

  governance/
    GOVERNANCE.md
    RFC-PROCESS.md

  scripts/        # Validation scripts
  .github/        # CI, issue templates, PR template

  Makefile
  CHANGELOG.md  CONTRIBUTING.md  CODE_OF_CONDUCT.md
  LICENSE       VERSIONING.md     README.md
```

---

## Reading order

If you are new to ACDP, read in this order:

1. **[manifesto/manifesto.md](manifesto/manifesto.md)** — why a context substrate is needed.
2. **[docs/overview.md](docs/overview.md)** — one-page architecture overview.
3. **[RFC-ACDP-0001 Core](rfcs/RFC-ACDP-0001-core.md)** — identifiers, JCS, hashing, signatures.
4. **[RFC-ACDP-0002 Context Body](rfcs/RFC-ACDP-0002-context-body.md)** — the immutable body schema.
5. **[RFC-ACDP-0003 Publish](rfcs/RFC-ACDP-0003-publish.md)** — POST `/contexts` and supersession.
6. **[RFC-ACDP-0004 Retrieval](rfcs/RFC-ACDP-0004-retrieval.md)** — GET `/contexts/{ctx_id}` and lineage queries.
7. **[RFC-ACDP-0005 Discovery](rfcs/RFC-ACDP-0005-discovery.md)** — keyword search.
8. **[RFC-ACDP-0006 Cross-Registry](rfcs/RFC-ACDP-0006-cross-registry.md)** — `acdp://` resolution.
9. **[RFC-ACDP-0007 Capabilities](rfcs/RFC-ACDP-0007-capabilities.md)** — `/.well-known/acdp.json` and error envelopes.
10. **[RFC-ACDP-0008 Security](rfcs/RFC-ACDP-0008-security.md)** — threat model.
11. **[docs/architecture.md](docs/architecture.md)** and **[docs/integration-guide.md](docs/integration-guide.md)** — operational guidance.

---

## Conformance profiles

| Profile | Required RFCs | Description |
|---|---|---|
| `acdp-registry-core` *(default)* | 0001–0004, 0007, 0008 | Every conformant registry. Implements canonicalization, body schema, publish, retrieval, capabilities, error envelope. |
| `acdp-registry-discovery` | + 0005 | Adds keyword search. |
| `acdp-registry-federated` | + 0006 | Resolves cross-registry `acdp://` references end-to-end. |
| `acdp-consumer` | 0001, 0002, 0004 (read), 0006, 0008 | A consumer that retrieves, verifies, and visibility-checks contexts. |

There is no producer-only profile: producers MUST be able to verify any context they publish, and that requires the same cryptographic core as a registry.

---

## Standards posture

- **RFC-ACDP-0001 Core** — identifiers (`acdp://`, `lin:`), JCS canonicalization, hashing, signatures, time format.
- **RFC-ACDP-0002 Context Body** — immutable signed body, context types, data references, visibility.
- **RFC-ACDP-0003 Publish** — `POST /contexts`, supersession constraints, registry-assigned fields.
- **RFC-ACDP-0004 Retrieval** — `GET /contexts/{ctx_id}`, body-only retrieval, lineage queries.
- **RFC-ACDP-0005 Discovery** — keyword search semantics, cursor pagination. Search ranking within results is registry-defined; ACDP does not normatively specify a ranking algorithm.
- **RFC-ACDP-0006 Cross-Registry** — `acdp://` URI scheme, resolution flow, federation non-goals.
- **RFC-ACDP-0007 Capabilities** — `/.well-known/acdp.json`, error envelope, error code registry.
- **RFC-ACDP-0008 Security** — threat model and required defenses for v0.1.0.
- **RFC-ACDP-0009 Extensions** *(reserved)* — retraction/lifecycle events, attestations, push subscriptions, walks.

---

## Compatibility model

- **Protocol version** is `0.1.0`. A registry advertises it as `acdp_version` in its capabilities document; a producer optionally carries it per-body as the producer-signed `body.acdp_version`. An absent `body.acdp_version` is interpreted as `0.1.0` (RFC-ACDP-0001 §6).
- **Registry capabilities** advertise per-registry options — supported signature algorithms, supported DID methods, read-authentication methods, profiles, and limits (RFC-ACDP-0007 §3).

Major mismatches are not compatible. Minor versions are expected to be backward compatible. Unknown fields MUST be ignored on body and registry-state. See [VERSIONING.md](VERSIONING.md).

ACDP v0.1.0 is **JSON-only**. Binary transport bindings are out of scope for this version.

---

## Repository highlights

- **Canonical JSON Schemas** under `schemas/json/` — the source of truth for the wire format.
- **Conformance fixtures** under `schemas/conformance/`, validated in CI.
- **Registries** under `registries/` evolve without destabilizing the core.
- **Examples** under `examples/` are validated against the canonical schemas.
- **GitHub Actions CI** validates JSON Schemas, examples, and fixtures on every PR.

---

## Development

```bash
make bootstrap        # Install dev deps: ajv-cli + Python (one-time)
make validate         # JSON Schemas + examples + conformance runner
make help             # Show all targets
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [RFC process](governance/RFC-PROCESS.md).

---

## License

Apache License 2.0. See [LICENSE](LICENSE).
