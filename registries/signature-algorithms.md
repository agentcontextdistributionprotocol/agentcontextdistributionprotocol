# Signature Algorithms Registry

ACDP signature algorithm identifiers used in `signature.algorithm` and `capabilities.supported_signature_algorithms`. Identifiers are lowercase ASCII matching `^[a-z][a-z0-9-]*$`.

The schema vocabulary is open (no JSON Schema enum). Runtime gating is via the registry's `supported_signature_algorithms` capability. Producers using an unregistered algorithm SHOULD register it via the [RFC process](../governance/RFC-PROCESS.md) before relying on cross-registry interoperability.

## Registered values

| Identifier | Status | Reference | Notes |
|---|---|---|---|
| `ed25519` | Mandatory | [RFC 8032](https://datatracker.ietf.org/doc/html/rfc8032) | EdDSA over Curve25519. MUST be supported by every conformant registry per RFC-ACDP-0001 §5.10. Signature length: 64 bytes (88 base64 chars with padding). |
| `ecdsa-p256` | Optional | [FIPS 186-4](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-4.pdf) | ECDSA over NIST P-256. Signature is the IEEE 1363 (r‖s) form, 64 bytes. |

## Adding an algorithm

Open a PR adding a row to the table above. Algorithms MUST:

- Be lowercase ASCII matching `^[a-z][a-z0-9-]*$`.
- Identify a single deterministic primitive (no algorithm-suite confusion).
- Have a public, stable specification (IETF RFC, NIST publication, or equivalent).
- Define the wire form of the signature value bytes (so base64 encoding is unambiguous).
- Have at least one independent implementation.

Reserved future identifiers: `ed448`, `ml-dsa-44`, `ml-dsa-65`, `ml-dsa-87` (post-quantum, pending NIST FIPS 204 stabilization).
