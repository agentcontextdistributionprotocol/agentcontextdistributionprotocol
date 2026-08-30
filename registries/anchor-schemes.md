# Anchor Scheme Registry

ACDP `anchors[].scheme` (RFC-ACDP-0016, 0.5.0) names the external system an anchor's `content_hash` is meaningful within. This registry tracks known scheme identifiers. ACDP core never resolves an anchor or defines what a scheme's `content_hash` means — that is entirely the concern of the system that owns the scheme (RFC-ACDP-0016 §6–7) — so an entry here is a **pointer for scheme-aware verifiers**, not a normative dependency: ACDP's own schema, fixtures, and conformance gate for RFC-ACDP-0016 do not require any row in this table to exist, be complete, or be stable.

| Scheme | Status | `content_hash` construction | Description |
|---|---|---|---|
| `macp.commitment` | Provisional | Defined by the Multi-Agent Coordination Protocol (MACP), independently of ACDP. | Carries a MACP canonical commitment hash. Anchoring bodies claim a link to a MACP commitment artifact; resolving or verifying that link is a MACP-aware verifier's concern, not core ACDP's. |
| `seam.decision` | Provisional | Defined by the Seam decision-record system, independently of ACDP. | Carries a Seam sealed-decision-record audit digest. Anchoring bodies claim a link to a Seam decision artifact; resolving or verifying that link is a Seam-aware verifier's concern, not core ACDP's. |

## Adding a scheme

Open a PR adding a row to the table above. Schemes MUST:

- Use dotted-namespace form, matching the RFC-ACDP-0002 §6.2 structured-locator scheme grammar (`^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)+$`).
- Document, in this file, only what a scheme-aware verifier needs to know informally — what kind of artifact the scheme's `content_hash` identifies. ACDP does not require or maintain a citation into the owning system's own specification; that system is free to version, rename, or restructure its own documents without touching this registry.
- Not collide with an existing scheme.

New schemes are added at status `Provisional`. A registrant does not need ACDP maintainer involvement beyond the PR itself — any party may register a scheme it owns.

## Promotion from Provisional to Stable

A `Provisional` scheme MAY be promoted to `Stable` via PR when the scheme has shipped in at least two independent scheme-aware verifier implementations and at least one ACDP body carrying an anchor of that scheme has been published to a public, live registry. Promotion is a registry-policy change only; it does not alter the on-wire `anchors` schema.

## Example

```json
"anchors": [
  {
    "scheme": "macp.commitment",
    "content_hash": "sha256:2f9c2b3a1e6d4f7c8b0a5e3d1c9f6b2a4e7d0c3b6a9f2e5d8c1b4a7e0d3c6b9a"
  }
]
```
