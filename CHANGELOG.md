# Changelog

## v0.0.1 (Draft) — current

The first published version of ACDP. **Coordination-agnostic substrate from the start.** No retraction, no post-publication relationships, no push subscriptions in this version — those are deferred (see RFC-ACDP-0009 Extensions, reserved).

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
