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

## Producer DID document for `ecdsa-p256` (NORMATIVE)

A producer signing with `ecdsa-p256` MUST publish a `did:web` DID document containing a `verificationMethod` whose key material follows the rules above, AND whose `id` is referenced by `assertionMethod`. The §"Key Resolution" algorithm in RFC-ACDP-0001 §5.11 will otherwise reject the signature as `key_not_authorized` (assertion-method check) or `key_resolution_failed` (verification-method lookup).

The minimal conformant document:

```json
{
  "@context": [
    "https://www.w3.org/ns/did/v1",
    "https://w3id.org/security/suites/jws-2020/v1"
  ],
  "id": "did:web:agents.example.com",
  "verificationMethod": [
    {
      "id": "did:web:agents.example.com#key-1",
      "type": "JsonWebKey2020",
      "controller": "did:web:agents.example.com",
      "publicKeyJwk": {
        "kty": "EC",
        "crv": "P-256",
        "x": "<base64url 32-byte x>",
        "y": "<base64url 32-byte y>"
      }
    }
  ],
  "assertionMethod": ["did:web:agents.example.com#key-1"]
}
```

Rules:

- `verificationMethod[].type` MUST be `"JsonWebKey2020"`. Implementations that emit `EcdsaSecp256r1VerificationKey2019` are NON-CONFORMANT for v0.0.1 (the cryptosuite differs in canonical-bytes binding; see RFC-ACDP-0001 §5.11 step 6).
- `verificationMethod[].controller` MUST equal the DID document's `id` (no delegation of controller in v0.0.1).
- `publicKeyJwk.kty` MUST be `"EC"`; `publicKeyJwk.crv` MUST be `"P-256"`.
- `publicKeyJwk.x` and `publicKeyJwk.y` MUST each decode (base64url, RFC 4648 §5 with no padding) to exactly 32 bytes. If a producer's KMS or library exposes a natural-length integer shorter than 32 bytes, the producer MUST left-pad with zero bytes before base64url-encoding. Truncation MUST NOT be applied.
- The compressed-point form is NOT accepted in v0.0.1 — `y` MUST be present.
- `signature.key_id` in a publish request MUST equal the `verificationMethod[].id` exactly, including the fragment (e.g. `did:web:agents.example.com#key-1`).
- The verification method's `id` MUST appear in the document's `assertionMethod` array (either as a full URL or as a relative `#<fragment>`). v0.0.1 rejects keys not authorized for assertion (§5.11 step 5) with `key_not_authorized`.

Producers rotating keys MUST publish the new `verificationMethod` entry and include it in `assertionMethod` BEFORE signing with the new key; otherwise the registry's first publish with the new `key_id` will be rejected as `key_not_authorized`. Producers SHOULD retain the prior verification method in the document for as long as consumers may verify prior signatures (ACDP bodies are immutable; signatures remain mathematically valid as long as the key material is resolvable).

A worked end-to-end example (publish request + signed body + corresponding DID document) is in `examples/publish/data-snapshot-publish-request-p256.json` and `examples/key-resolution/did-document-p256.json`. The example reuses the `sig-002-ecdsa-p256-golden.json` test keypair so consumers can verify the signature against a publicly-known public key; the keypair is TEST-ONLY (private scalar = 1) and MUST NOT be used in production.

## Adding an algorithm

Open a PR adding a row to the table above. Algorithms MUST:

- Be lowercase ASCII matching `^[a-z][a-z0-9-]*$`.
- Identify a single deterministic primitive (no algorithm-suite confusion).
- Have a public, stable specification (IETF RFC, NIST publication, or equivalent).
- Define the wire form of the signature value bytes (so base64 encoding is unambiguous).
- Have at least one independent implementation.

Reserved future identifiers: `ed448`, `ml-dsa-44`, `ml-dsa-65`, `ml-dsa-87` (post-quantum, pending NIST FIPS 204 stabilization).
