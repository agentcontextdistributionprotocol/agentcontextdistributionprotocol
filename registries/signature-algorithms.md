# Signature Algorithms Registry

ACDP signature algorithm identifiers used in `signature.algorithm` and `capabilities.supported_signature_algorithms`. Identifiers are lowercase ASCII matching `^[a-z][a-z0-9-]*$`.

The schema vocabulary is open (no JSON Schema enum). Runtime gating is via the registry's `supported_signature_algorithms` capability. Producers using an unregistered algorithm SHOULD register it via the [RFC process](../governance/RFC-PROCESS.md) before relying on cross-registry interoperability.

## Registered values

| Identifier | Status | Reference | Notes |
|---|---|---|---|
| `ed25519` | Mandatory | [RFC 8032](https://datatracker.ietf.org/doc/html/rfc8032) | EdDSA over Curve25519. MUST be supported by every conformant registry per RFC-ACDP-0001 §5.10. Signature length: 64 bytes (88 base64 chars with padding). Golden vector: `schemas/conformance/sig-001-ed25519-golden.json`. |
| `ecdsa-p256` | Optional | [FIPS 186-4](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-4.pdf) | ECDSA over NIST P-256. Signature is the IEEE 1363 (r‖s) form, 64 bytes. Golden vector: `schemas/conformance/sig-002-ecdsa-p256-golden.json`. |

## `ecdsa-p256` wire form (NORMATIVE)

ECDSA-P256 signatures MUST use the **IEEE 1363 (r‖s)** wire form: the 32-byte big-endian unsigned `r` value concatenated with the 32-byte big-endian unsigned `s` value, totalling 64 raw bytes. Base64-encoded with padding the value is exactly 88 characters. **DER-encoded signatures (the default output of many libraries, including OpenSSL `i2d_ECDSA_SIG` and Go `ecdsa.SignASN1`) are NON-CONFORMANT** and registries MUST reject them as `invalid_signature`. Implementations MUST convert DER → r‖s before transmission and r‖s → DER before passing to verifiers that demand DER input.

ECDSA-P256 is non-deterministic by default. Implementers SHOULD use **RFC 6979 deterministic ECDSA** (with SHA-256 as the hash) so that test vectors and signatures are reproducible across implementations. Random-k ECDSA is permitted at runtime but precludes byte-exact reproduction of golden vectors.

## `ecdsa-p256` key material (NORMATIVE)

For `ecdsa-p256`, the producer's DID document verification method MUST publish the public key as a JWK with:

- `kty`: `EC`
- `crv`: `P-256`
- `x`: base64url-encoded big-endian 32-byte unsigned integer (the affine x coordinate)
- `y`: base64url-encoded big-endian 32-byte unsigned integer (the affine y coordinate)

Both `x` and `y` MUST be exactly 32 bytes after base64url decoding (left-pad with zero bytes if the natural integer encoding is shorter). The compressed-point form (`y` omitted) and the SEC1 single-string form are NOT accepted in v0.0.1; producers MUST publish the uncompressed `(x, y)` pair.

Verifiers reconstruct the SEC1 uncompressed point as `0x04 || x || y` (65 bytes total). Compressed SEC1 (`0x02 || x` or `0x03 || x`) MUST NOT appear in DID documents but verifiers that accept it for compatibility MUST decompress before use.

## Adding an algorithm

Open a PR adding a row to the table above. Algorithms MUST:

- Be lowercase ASCII matching `^[a-z][a-z0-9-]*$`.
- Identify a single deterministic primitive (no algorithm-suite confusion).
- Have a public, stable specification (IETF RFC, NIST publication, or equivalent).
- Define the wire form of the signature value bytes (so base64 encoding is unambiguous).
- Have at least one independent implementation.

Reserved future identifiers: `ed448`, `ml-dsa-44`, `ml-dsa-65`, `ml-dsa-87` (post-quantum, pending NIST FIPS 204 stabilization).
