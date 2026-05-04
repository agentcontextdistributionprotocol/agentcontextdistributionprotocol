# ACDP RFC Index

This directory contains the normative RFCs that define the Agent Context Description Protocol (ACDP). ACDP is a coordination-agnostic substrate for **publishing, discovering, and verifying** units of agent-produced content; v0.0.1 is the first published version.

| RFC | Title | Status |
|---|---|---|
| [RFC-ACDP-0001](RFC-ACDP-0001-core.md) | Core — identifiers, JCS, hashing, signatures | Release Candidate 1 |
| [RFC-ACDP-0002](RFC-ACDP-0002-context-body.md) | Context Body | Release Candidate 1 |
| [RFC-ACDP-0003](RFC-ACDP-0003-publish.md) | Publish & Supersession | Release Candidate 1 |
| [RFC-ACDP-0004](RFC-ACDP-0004-retrieval.md) | Retrieval & Lineage | Release Candidate 1 |
| [RFC-ACDP-0005](RFC-ACDP-0005-discovery.md) | Discovery (keyword + similarity) | Release Candidate 1 |
| [RFC-ACDP-0006](RFC-ACDP-0006-cross-registry.md) | Cross-Registry References | Release Candidate 1 |
| [RFC-ACDP-0007](RFC-ACDP-0007-capabilities.md) | Capabilities & Errors | Release Candidate 1 |
| [RFC-ACDP-0008](RFC-ACDP-0008-security.md) | Security & Threat Model | Release Candidate 1 |
| [RFC-ACDP-0009](RFC-ACDP-0009-extensions.md) | Extensions (lifecycle, attestations, walks) | Reserved |

## Reading order

The numbering matches dependency order. Read top-to-bottom:

1. **[RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)** — identifiers, JCS canonicalization, content hashing, signatures, time format.
2. **[RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md)** — the immutable signed body; context types; data references; visibility.
3. **[RFC-ACDP-0003 Publish](RFC-ACDP-0003-publish.md)** — `POST /contexts`, supersession constraints, registry-assigned fields.
4. **[RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)** — `GET /contexts/{ctx_id}` and lineage queries.
5. **[RFC-ACDP-0005 Discovery](RFC-ACDP-0005-discovery.md)** — keyword and similarity search.
6. **[RFC-ACDP-0006 Cross-Registry](RFC-ACDP-0006-cross-registry.md)** — `acdp://` URI scheme and resolution flow.
7. **[RFC-ACDP-0007 Capabilities](RFC-ACDP-0007-capabilities.md)** — `/.well-known/acdp.json` and the error envelope.
8. **[RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)** — threat model and required defenses.

Reserved (no normative text, numbering pinned for future work):

- **[RFC-ACDP-0009 Extensions](RFC-ACDP-0009-extensions.md)** — retraction/lifecycle events, post-publication relationships, attestations, push subscriptions, server-side traversal.

## RFC lifecycle

`Draft → Review → Final Comment Period → Release Candidate N → Final` (or `Rejected`). `Reserved` is a sidebar state for placeholder RFCs (e.g. RFC-ACDP-0009). See [governance/RFC-PROCESS.md](../governance/RFC-PROCESS.md) and [VERSIONING.md](../VERSIONING.md).
