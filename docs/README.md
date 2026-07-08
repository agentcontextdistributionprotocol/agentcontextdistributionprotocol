# ACDP Documentation

Everything in this directory is **non-normative** — the authoritative documents are the RFCs in [`rfcs/`](../rfcs/) (run `make docs` at the repo root for the canonical reading order). These documents explain, position, and guide.

## Start here

| Document | Read it when you want |
|---|---|
| [overview.md](overview.md) | The one-page picture: the problem, the publish/discover/verify shape, what each RFC adds. |
| [why-acdp.md](why-acdp.md) | The motivation: why databases, APIs, tokens, and ledgers don't solve agent-to-agent knowledge handoff. |
| [acdp-vs-the-field.md](acdp-vs-the-field.md) | Positioning against MCP, A2A, C2PA, AT Protocol, and DIDComm. |

## Building

| Document | Read it when you want |
|---|---|
| [architecture.md](architecture.md) | The implementer's map: roles, flows, the 0.2.0–0.4.0 trust arc, where state lives. |
| [integration-guide.md](integration-guide.md) | Working producer/consumer code: hash, sign, publish, verify, walk lineage, verify trust artifacts. |
| [discovery.md](discovery.md) | How agents first find a registry (bootstrap patterns; deliberately out of protocol scope). |
| [version-matrix.md](version-matrix.md) | Which spec version each known implementation tracks. |

## Boundaries and security

| Document | Read it when you want |
|---|---|
| [threat-model.md](threat-model.md) | Quick-reference threat table and attack scenarios (full model: RFC-ACDP-0008). |
| [non-goals.md](non-goals.md) | What ACDP deliberately does not do, and why each exclusion holds. |
| [data-protection.md](data-protection.md) | Permanence vs. erasure rights (GDPR and similar): carry personal data by reference, not by value. |
