# RFC-ACDP-0021
# Agent Context Distribution Protocol (ACDP) — Keyless Signing

**Document:** RFC-ACDP-0021
**Version:** 0.5.0-draft.4
**Status:** Community Standards Track (Draft)

This RFC specifies **keyless signing**: a producer that runs as a workload (a CI job, a container, a serverless function) signs bodies with a short-lived key it generates on the spot, instead of a long-lived key listed in its DID document. The workload proves who it is with a token it already has (an OIDC ID token or a SPIFFE JWT-SVID). A registry checks that token, checks that the producer's `did:web` document authorizes that workload identity, and publishes a signed, logged **key attestation** binding the ephemeral key to the producer DID for a few minutes. Bodies signed with the key point at the attestation. Consumers verify the attestation, place the signature inside its window with the registry receipt, and report one of the three existing key statuses. It depends on RFC-ACDP-0001 (Core), RFC-ACDP-0003 (Publish), RFC-ACDP-0010 (Registry Receipts), RFC-ACDP-0012 (Transparency Log), RFC-ACDP-0013 (Lifecycle Events), RFC-ACDP-0014 (Key Revocation), RFC-ACDP-0017 (Chain Verification) and RFC-ACDP-0020 (Registry Trust Lists), and reuses the identity descriptor of RFC-AITP-0002.

---

## 1. Status of This Memo

This document is a **Draft** ACDP specification on the `acdp/0.5.0` line. It is open for substantive change until it is promoted, and nothing in it is frozen. Per [VERSIONING.md](../VERSIONING.md), promotion to **Final** requires the conformance fixtures this document defines (`kl-001`..`kl-009`) to pass against two independent interoperating implementations.

Both profiles it defines, `acdp-registry-keyless` and `acdp-consumer-keyless` (§13), are OPTIONAL. Registries and consumers that implement neither are unaffected, and they refuse keyless bodies by the ordinary key-resolution rules they already follow (§12).

Nothing in this document invalidates any existing body, signature, `content_hash`, receipt, log leaf, checkpoint, cosignature or verdict. The `signature` object, the RFC-ACDP-0001 §5.7 exclusion set and the RFC-ACDP-0010 §6 fingerprint encoding are unchanged. It adds no wire error code, no key-authorization state, no revocation trust class, no RFC-ACDP-0017 stage value and no evidence-bundle member. The one amendment to Final text, to RFC-ACDP-0003 §3.1 step 3, is *(0.5.0)*-marked and applies only to keyless-signed bodies (§7). It adds one OPTIONAL RFC-ACDP-0017 `pinned` member, `keyless_attesters` (§10); `pinned` is a caller option, not a bundle member, and existing `chain-*` known answers are unchanged.

**Revision 0.5.0-draft.4 (2026-10-30)** keeps attestations verifiable across a rotation of the attester's signing key. §8.1 step 1 now applies the RFC-ACDP-0010 §10 historical arm to the attestation's own signature (`kl-005` M, N). No `kl-001` value changes.

**Revision 0.5.0-draft.3 (2026-10-30)** answers six follow-up findings from acdp-verifier-py. It defines the edge between an unavailable and an invalid revocation signer (§9.3), the `key_revocation` stage shape for an unevaluable keyless revocation (§10, `kl-008` F), the chain stages for a misplaced `key_attestation` (§10), and receipted registry events (§9.2). Chain attesters now come from `pinned` only (§10, §11). No `kl-001` value changes.

**Revision 0.5.0-draft.2 (2026-10-30)** applies the rulings on the second implementation's findings (acdp-verifier-py): unevaluable revocations are `unknown` (§8.1), retraction follows the RFC-ACDP-0013 fold (§9.2), the chain rules of §10 are spelled out, `pinned.keyless_attesters` (§10), the trust-list inputs (§11), the P-256 proof form (§5.1, `kl-001` vector 6), method-level refusal (§4.2), the `key_attestation` presence rules for consumers (§6.2), keyless-signed revocations (§9.3), and **keyless keys no longer sign lifecycle events** (§6.3).

---

## 2. Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described in BCP 14 ([RFC 2119], [RFC 8174]) when, and only when, they appear in all capitals.

| Term | Definition |
|---|---|
| **Controller** | The producer's `did:web` DID. It is the `agent_id` of every keyless-signed body. Keyless signing introduces no new DID method. |
| **Workload identity** | An `(type, issuer, subject)` triple naming a workload: an OIDC issuer and `sub`, or a SPIFFE ID. Its JSON shape is the RFC-AITP-0002 identity hint (§4). |
| **Token** | The credential that proves a workload identity: an OIDC ID token or a SPIFFE JWT-SVID. It is the `proof` of an RFC-AITP-0002 identity descriptor. |
| **Ephemeral key** | A key pair the workload generates for one job and discards. It is never listed in the controller's DID document. |
| **Attesting registry** | The registry that verified the token and minted the attestation. |
| **Key attestation** | A public body of type `acdp:key-attestation` whose `metadata` is an `acdp-key-attestation/1` object (§5.3), published by the attesting registry under its own DID. |
| **Attestation window** | `[not_before, not_after)` of a key attestation: the half-open interval in which signatures with the attested key count. |
| **Keyless key id** | A `signature.key_id` whose fragment begins `acdp-kl-` (§6.1). |
| **Keyless-signed body** | A body whose `signature.key_id` is a keyless key id. |
| **Org-wide identity** | A workload identity the controller's DID document marks `org_wide: true`. Its keys may supersede any of the controller's lineages (§7). |

All timestamps are canonical millisecond RFC 3339 UTC (RFC-ACDP-0001 §5.3), so they compare as strings.

---

## 3. Motivation and Design Choices

Every ACDP producer today holds a long-lived private key whose public half sits in its DID document. For a CI pipeline or an autoscaled agent fleet that means a secret to provision into every runner, rotate, and revoke when a runner leaks it. The workloads already hold a short-lived, audience-bound credential from their platform: GitHub Actions, GitLab, Google Cloud, AWS and Kubernetes issue OIDC tokens, and SPIFFE issues JWT-SVIDs. Keyless signing lets that credential stand in for the long-lived key.

Four choices shape the design.

1. **The registry is the attester.** Sigstore's Fulcio solves the same problem with a separate certificate authority. ACDP already has a signing, logging party on every publish path: the registry. Making it the attester gives the attestation a receipt and a transparency-log leaf for free (RFC-ACDP-0010, RFC-ACDP-0012), and lets RFC-ACDP-0020 trust lists say which registries' attestations a consumer accepts. A Fulcio binding is reserved for later (RFC-ACDP-0009 §2.13).
2. **The DID document stays the root of authority.** The controller decides which workload identities may sign for it by listing them in its `did:web` document (§4). A registry can attest a key only for a listed identity. Removing the identity stops new attestations (§9).
3. **The signature object does not change.** The keyless data lives in a new OPTIONAL, producer-signed body field, `key_attestation` (§6.2), inside the `content_hash`. The `signature` object stays closed with the same three members, the exclusion set is unchanged, and the attested key's fingerprint uses the RFC-ACDP-0010 §6 encoding, so receipts and log leaves carry it unchanged.
4. **No new states.** A keyless key ends in one of the three key statuses consumers already report, or fails closed (§8.2). Revocations keep their two trust classes (§9). Error responses reuse existing codes with new `details.reason` tokens (§13.3). Implementations that know nothing of this document fail closed on keyless bodies, because the keyless key id never resolves against a DID document (§12).

Non-goals: X.509-SVIDs and certificate chains; attesting `did:key` controllers (a `did:key` already needs no DID document); delegation between controllers; and any change to how long-lived keys work.

---

## 4. Authorized Workload Identities in the DID Document

### 4.1 The `AcdpKeylessSigning` service (NORMATIVE)

A controller authorizes workload identities by adding exactly one `service` entry to its `did:web` document:

```json
{
  "id": "did:web:agents.example.com:ci#acdp-keyless",
  "type": "AcdpKeylessSigning",
  "serviceEndpoint": {
    "identities": [
      { "type": "oidc", "issuer": "https://token.actions.githubusercontent.com",
        "subject": "repo:example/pipeline:ref:refs/heads/main" },
      { "type": "spiffe", "subject": "spiffe://prod.example.com/ns/agents/sa/publisher",
        "org_wide": true }
    ]
  }
}
```

`examples/key-resolution/did-document-keyless.json` is a complete document.

- `serviceEndpoint` is a JSON object with one member, `identities`: an array of identity entries.
- An identity entry is an RFC-AITP-0002 identity hint (`type`, `issuer` for `oidc` only, `subject`) plus an OPTIONAL boolean `org_wide`, default `false`. `type` is `oidc` or `spiffe`; entries of any other type MUST be ignored.
- If the document has no `AcdpKeylessSigning` service, or has more than one, no identity is authorized.
- An identity is **listed** when an entry has the same `type`, the same `issuer` (for `oidc`) and the same `subject`, each compared byte for byte. No normalization, case folding or wildcard is applied. A controller that wants a branch pattern lists each branch.

The service lives in the controller's document, which RFC-ACDP-0001 §5.11 already fetches with its SSRF defenses (RFC-ACDP-0008 §4.8). No new fetch target is introduced.

### 4.2 The reserved `acdp-kl-` fragment (NORMATIVE)

The fragment prefix `acdp-kl-` is reserved for keyless key ids (§6.1). A DID document MUST NOT contain a `verificationMethod` whose `id` fragment begins `acdp-kl-`. Registries and consumers MUST refuse to resolve such a method. The refusal is at method level: the method is never usable for any signature, while the rest of the document (its other methods and services, including `AcdpKeylessSigning`) still resolves. A registry returns `key_resolution_failed` on a publish whose key id names such a method, and a consumer fails closed for any signature that names it (`kl-007` B). Without this rule a controller (or an attacker who can edit its document) could pre-list a keyless key id and have old verifiers accept bodies that keyless-aware verifiers would refuse.

---

## 5. Key Attestation

### 5.1 The request: `POST /key-attestations` (NORMATIVE)

A workload requests an attestation with `POST /key-attestations`, `Content-Type: application/json`, and an `acdp-key-attestation-request/1` body (`schemas/json/acdp-key-attestation-request.schema.json`; example in `examples/key-attestation-request/`):

| Member | Meaning |
|---|---|
| `request_version` | `"acdp-key-attestation-request/1"`. |
| `controller` | The controller's `did:web` DID. A `did:key` is a `schema_violation`. |
| `identity` | An RFC-AITP-0002 identity descriptor with the token as `proof`: `{type: "oidc", issuer, subject, proof}`, or `{type: "spiffe", subject, svid_type: "jwt-svid", proof}`. X509-SVIDs are not accepted. |
| `algorithm` | `ed25519` or `ecdsa-p256` (`registries/signature-algorithms.md`). |
| `public_key_jwk` | The ephemeral public key as a JWK with exactly the RFC 7638 required members (`{crv, kty, x}` for Ed25519, `{crv, kty, x, y}` for P-256), the form RFC-AITP-0002 §2.2.1 uses. |
| `pop` | Proof of possession: a base64 signature by the ephemeral key, under `algorithm`, over the JCS bytes of the preimage below. |
| `requested_ttl_seconds` | OPTIONAL, 1 to 3600. Default 600. |

The proof-of-possession preimage is the JSON object

```json
{ "pop_version": "acdp-key-attestation-pop/1",
  "controller": "<controller>", "registry_did": "<attesting registry DID>",
  "token_hash": "sha256:<hex SHA-256 of the token's ASCII bytes>",
  "key_fingerprint": "sha256:<RFC-ACDP-0010 §6 fingerprint of the ephemeral key>" }
```

canonicalized with JCS (RFC 8785). The `pop` encoding follows RFC-ACDP-0001 §5.10 for the algorithm: for `ed25519` the 64-byte RFC 8032 signature; for `ecdsa-p256` the 64-byte `r||s` form (IEEE P1363) over SHA-256. A DER-encoded ECDSA signature MUST be rejected (`pop_invalid`). `kl-001` vector 6 pins the P-256 form. The proof is REQUIRED even when the token carries a `cnf` claim. Most workload issuers cannot put the workload's key in the token, and the proof binds the key to this token, this controller and this registry in every case.

The request is a write. It authenticates by its token, not by an RFC-ACDP-0008 HTTP signature, so registries MUST accept it without one. Registries SHOULD rate-limit it per `(issuer, subject)` and per source address.

### 5.2 Processing (NORMATIVE)

A registry advertising `acdp-registry-keyless` processes the request in this order and stops at the first failure. Every refusal uses an existing wire error code (RFC-ACDP-0007 §5) with the `details.reason` shown; §13.3 explains why no code was added.

1. **Schema.** Validate against `acdp-key-attestation-request/1`. Failure: `schema_violation` (400).
2. **Issuer acceptance.** For `oidc`, `identity.issuer` MUST appear in `keyless.accepted_oidc_issuers` (§13.1). For `spiffe`, the trust domain of `identity.subject` MUST appear in `keyless.accepted_spiffe_trust_domains`. Failure: `key_not_authorized` (403), `issuer_not_accepted`. This check precedes any fetch of issuer keys.
3. **Token.** Verify the token per RFC-AITP-0002 §2.3 (OIDC) or §6 (SPIFFE JWT-SVID): signature under the issuer's published keys, `exp` in the future, `iat` and `nbf` (when present) not in the future beyond 60 seconds of skew, `iss` equal to `identity.issuer` (or the SPIFFE trust domain's issuer) and `sub` equal to `identity.subject`, byte for byte. Failure: `key_not_authorized`, `token_invalid`. If the issuer's published keys cannot be fetched (a network failure, a timeout or a 5xx response), the failure is transient: `key_resolution_unreachable` (502), `issuer_unreachable`, and the client may retry.
   - **Audience.** The token's `aud` (a string, or an array) MUST contain the registry's own `registry_did`, byte for byte. A hostname, URL or another registry's DID does not count. Failure: `key_not_authorized`, `audience_mismatch`. This stops a token minted for one registry from being replayed at another.
   - **Confirmation.** If the token carries `cnf.jkt`, it MUST equal the RFC 7638 thumbprint of `public_key_jwk` (base64url SHA-256 of its JCS bytes). Failure: `key_not_authorized`, `confirmation_mismatch`.
   - **Single use.** The registry MUST refuse a `token_hash` it has already attested while that token is unexpired. Failure: `key_not_authorized`, `token_replayed`.
4. **Proof of possession.** Verify `pop` under `public_key_jwk`. Failure: `invalid_signature` (400), `pop_invalid`.
5. **Algorithm.** `algorithm` MUST be one the registry supports and MUST match the JWK's key type. Failure: `unsupported_algorithm` (400).
6. **Authorization.** Resolve `controller` per RFC-ACDP-0001 §5.11 (permanent failure: `key_resolution_failed`; transient: `key_resolution_unreachable`) and check that `identity` is listed (§4.1). If it is not listed in a cached document, the registry MUST re-fetch once bypassing its cache before refusing. Failure: `key_not_authorized`, `identity_not_authorized`.
7. **Mint.** Set `not_before` to the registry's current time and `not_after` to `not_before` plus the lesser of `requested_ttl_seconds` (default 600), `keyless.max_attestation_ttl_seconds` and the token's remaining lifetime, never more than 3600 seconds. `org_wide` is copied from the matching DID-document entry.
8. **Publish.** Publish the attestation as an ordinary body under the registry's own DID (§5.3), through the registry's normal publish path with its receipt and transparency-log leaf committed atomically (RFC-ACDP-0010, RFC-ACDP-0012). Respond `201 Created` with the attestation's full retrieval representation (RFC-ACDP-0004), including `registry_receipt`.

The registry MUST NOT publish, log or retain the token beyond what single-use enforcement needs; `token_hash` is its only trace in the attestation.

### 5.3 The attestation body (NORMATIVE)

A key attestation is a body with:

- `type` = `acdp:key-attestation` (`registries/context-types.md`), `visibility` = `public`, `version` = 1, `supersedes` = null, empty `data_refs` and `derived_from`;
- `agent_id` = the attesting registry's DID, which MUST be `did:web:` plus the authority of its own `ctx_id`, and a `signature` by a key in that DID document's `assertionMethod` (the registry signs it as a producer, with the same key it uses for receipts or another);
- `schema_uri` = `https://schemas.acdp.io/v0.1.0/acdp-key-attestation.schema.json` and `acdp_version` ≥ `0.5.0`;
- `metadata` = an `acdp-key-attestation/1` object (`schemas/json/acdp-key-attestation.schema.json`):

| Member | Meaning |
|---|---|
| `attestation_version` | `"acdp-key-attestation/1"`. |
| `controller` | The controller DID. |
| `identity` | The verified workload identity, as an RFC-AITP-0002 identity hint (no `proof`). |
| `org_wide` | Copied from the DID-document entry. |
| `key_id` | The keyless key id, `<controller>#acdp-kl-<hex>` (§6.1). |
| `algorithm` | The attested key's algorithm. |
| `public_key_jwk` | The attested key, in RFC 7638 canonical member form. |
| `key_fingerprint` | Its RFC-ACDP-0010 §6 fingerprint: over the raw 32-byte Ed25519 key, or the 33-byte SEC1-compressed P-256 point. |
| `not_before`, `not_after` | The attestation window. `not_before` < `not_after`, at most 3600 seconds apart. |
| `token_hash` | `sha256:` + hex SHA-256 of the token's ASCII bytes. |

A verifier checks the runtime rules the schema cannot express: `key_fingerprint` is the fingerprint of `public_key_jwk`, `key_id` is derived from it per §6.1, and the window bound holds. A body that fails any rule in this section is **attestation invalid**. An attestation's bytes are immutable. It is withdrawn by retraction and restored only by republication, both by the attesting registry (§9.2).

`kl-001` vector 1 is a golden attestation with its canonical form, `content_hash` and registry signature.

### 5.4 Listing: `GET /key-attestations` (NORMATIVE)

`GET /key-attestations?controller=<did>` returns every attestation the registry minted for the controller, newest first: `{items: [{ctx_id, content_hash, metadata}], next_cursor}`, paginated like RFC-ACDP-0005 search. Optional `issuer` and `subject` parameters narrow it to one identity. The endpoint is public, like the attestations. It lets a controller find every key attested for a leaked identity, so it can revoke them (§9.3).

Registries not advertising `acdp-registry-keyless` answer both endpoints with `not_implemented` (501).

---

## 6. Keyless-Signed Bodies

### 6.1 The keyless key id (NORMATIVE)

A keyless key id is `<controller>#acdp-kl-<h>`, where `<h>` is the 64 lowercase hex characters of the attested key's RFC-ACDP-0010 §6 fingerprint (the fingerprint without its `sha256:` prefix). It satisfies the existing `signature.key_id` pattern and the RFC-ACDP-0001 §5.11 rule that the DID part equals `agent_id`.

### 6.2 The `key_attestation` field (NORMATIVE)

A keyless-signed body carries a producer-signed field naming its attestation:

```json
"key_attestation": {
  "ctx_id": "acdp://registry.example.com/7a1c0f3e-5b2d-4c8e-9f10-2b3c4d5e6f70",
  "content_hash": "sha256:fbed72af712224f7d9d6e05a896d3a364c6c709247548a3de059198473399672"
}
```

- `key_attestation` MUST be present when the `signature.key_id` fragment begins `acdp-kl-`, and MUST be absent otherwise. A registry refuses a body that breaks either rule (`kl-003` C, I).
- `ctx_id` names the attestation and `content_hash` pins its bytes.
- The field is ProducerContent: it is inside the `content_hash` preimage under RFC-ACDP-0001 §5.7, so the ephemeral key signs it and nobody can re-point a body at another attestation. The exclusion set is unchanged.
- `agent_id` MUST equal the attestation's `controller`, and `signature.key_id` and `signature.algorithm` MUST equal its `key_id` and `algorithm`.
- A consumer claiming `acdp-consumer-keyless` enforces both presence rules too: a keyless key id with no `key_attestation` fails at §8.1 step 1 (`attestation_invalid`), and a `key_attestation` on a body whose key id is not a keyless key id fails closed with `attestation_mismatch` (§12).

Signing is unchanged: the ephemeral key signs the ASCII bytes of the `content_hash` (RFC-ACDP-0001 §5.8). `kl-001` vector 2 is a golden keyless-signed body.

The field is schema-valid in `acdp-context-body` and `acdp-publish-request`. A registry advertising `acdp_version` < `0.5.0` MUST reject a publish carrying it with `schema_violation` (`kl-007` C), as for `anchors` (RFC-ACDP-0016).

### 6.3 Publish path (NORMATIVE)

When a registry advertising `acdp-registry-keyless` receives a publish whose `signature.key_id` is a keyless key id, it replaces RFC-ACDP-0003 §2.1 step 6's key resolution (and only that) with these checks, in order:

1. `key_attestation` is present. Failure: `key_resolution_failed` (400), `attestation_missing`.
2. The `ctx_id` names a body on this registry. An attestation from another registry is not accepted on publish, because the receipt that places the signature must come from the attester (§8.1). Failure: `key_resolution_failed`, `attestation_foreign`.
3. The attestation exists, its stored `content_hash` equals `key_attestation.content_hash`, and it is a valid attestation (§5.3). Failure: `key_resolution_failed`, `attestation_not_found` or `attestation_mismatch`.
4. `agent_id`, `key_id` and `algorithm` match the attestation (§6.2). Failure: `key_not_authorized` (403), `attestation_mismatch`.
5. The attestation is not retracted. Failure: `key_not_authorized`, `attestation_withdrawn`.
6. The `created_at` the registry will assign lies in `[not_before, not_after)`. Failure: `key_not_authorized`, `outside_attestation_window`.
7. The registry SHOULD re-check that the identity is still listed in the controller's document, with its normal caching. Failure: `key_not_authorized`, `identity_not_authorized`.
8. Signature verification (step 7 of RFC-ACDP-0003 §2.1) uses `public_key_jwk`. Failure: `invalid_signature`.

The receipt's and log leaf's `key_fingerprint` is the attested `key_fingerprint`, which is the RFC-ACDP-0010 §6 fingerprint of the signing key, as for any body.

**Lifecycle events (NORMATIVE).** In this version a keyless key MUST NOT sign an RFC-ACDP-0013 lifecycle event. The event format has no member that carries an attestation, so no consumer could verify such an event. A producer-actor event MUST be signed by a key in the controller's DID document. A registry advertising `acdp-registry-keyless` refuses an event whose signing key id is a keyless key id with `key_resolution_failed` (400), `details.reason` = `keyless_event_unsupported` (`kl-004` F); a registry without the profile refuses it at key resolution anyway. Carrying an attestation on events is reserved in RFC-ACDP-0009 §2.14.

A registry not advertising `acdp-registry-keyless` runs RFC-ACDP-0001 §5.11 unchanged. The DID document has no `acdp-kl-` method, so step 4 fails and the publish is refused with `key_resolution_failed` (`kl-003` J).

---

## 7. Supersession (NORMATIVE)

*(0.5.0)* This section amends RFC-ACDP-0003 §3.1 step 3 for keyless-signed bodies. Step 3 still requires the successor's `agent_id` to equal the predecessor's. A registry advertising `acdp-registry-keyless` then also applies this rule, where "keyless" describes how a body is signed:

| Successor signed by | Allowed when |
|---|---|
| A key in the controller's DID document | always (unchanged) |
| A keyless key whose attestation has `org_wide: true` | always |
| A keyless key, not org-wide | the predecessor is keyless-signed **and** its attestation's `identity` is identical (same `type`, `issuer`, `subject`) |

Otherwise the publish is refused with `not_authorized` (403) and `details.reason` = `keyless_identity_mismatch`. The predecessor's `org_wide` does not matter: an org-wide predecessor does not let a narrower identity supersede it (`kl-001` vector 5, case S8). A non-org-wide keyless key cannot supersede a body signed with a DID-document key.

The rule follows from what the controller authorized. A controller that lists `repo:example/pipeline:ref:refs/heads/main` has authorized that workflow to publish, not to rewrite lineages another workflow owns. Without the rule any listed identity could supersede, and so mark as `superseded`, every lineage of the controller.

Lifecycle events cannot be keyless-signed in this version (§6.3), so this rule governs supersession only. A registry not advertising the profile never sees a keyless successor, because it refuses the publish at key resolution (§6.3).

`kl-001` vector 5 is the decision table and `kl-004` the registry scenarios.

---

## 8. Consumer Verification

### 8.1 Procedure (NORMATIVE)

A consumer claiming `acdp-consumer-keyless` that meets a keyless key id runs this procedure in place of RFC-ACDP-0001 §5.11 for that signature. It MUST NOT resolve a keyless key id by any other path. Inputs are the body, its `registry_receipt`, the attestation (fetched from `key_attestation.ctx_id`, or from an evidence bundle, §10) with its receipt, applicable revocations (§9), and the controller's current DID document.

The checks run in a fixed order, and the first failure decides:

1. **Attestation valid.** The body carries `key_attestation` (§6.2). The attestation's bytes hash to `key_attestation.content_hash`, its signature verifies under its `agent_id` per RFC-ACDP-0001 §5.11, its receipt verifies, and it meets §5.3. Failure: `attestation_invalid`.
   - **Attester key rotation.** An attestation always carries a receipt, so the RFC-ACDP-0010 §10 historical arm applies to its signature, as a MUST. When the attestation's receipt verifies and its `key_fingerprint` is the fingerprint of a key in the attesting registry's current `verificationMethod`, the attestation signature verifies against that key even if the key has left `assertionMethod`. Step 1 then passes. The retired key does not lower the status of the keyless body; that status still comes from steps 8 and 9. The receipt's own key follows RFC-ACDP-0010 §9.
   - **Compromise.** A key removed from `verificationMethod` entirely is the registry's compromise signal, and an attestation signed by it fails: `attestation_invalid`. A registry that rotates after compromise re-issues live attestations under the successor key; it cannot re-issue past ones, so bodies resting on them become unverifiable.
   - A registry rotating for any other reason MUST keep the retired key in `verificationMethod`, as RFC-ACDP-0010 §9 already requires of receipt keys (`kl-005` M, N).
2. **Attester accepted.** The attesting registry is one the consumer accepts (§11). Failure: `untrusted_attester`.
3. **Bindings.** `agent_id`, `signature.key_id` and `signature.algorithm` match the attestation. Failure: `attestation_mismatch`.
4. **Placement.** The body's `registry_receipt` verifies (RFC-ACDP-0010 §8), was issued by the attesting registry, and its `key_fingerprint` equals the attested one. Failure: `unplaceable`.
5. **Window.** The receipt's `created_at` lies in `[not_before, not_after)`. Failure: `outside_attestation_window`.
6. **Signature.** The signature verifies under `public_key_jwk`. Failure: `invalid_signature`.
7. **Withdrawn.** The attestation is not retracted (§9.2). Failure: `attestation_withdrawn`.
8. **Revocations.** If any RFC-ACDP-0014 revocation applies to the attested fingerprint (§9.3), let T be the earliest `compromised_since`. If the receipt's `created_at` ≥ T, fail: `revoked`. Otherwise the status is **historically authorized (pre-compromise)**, and no current DID document is needed. Only a verified revocation that applies counts here. A candidate revocation that targets the fingerprint but cannot be evaluated (§9.3) does not change the status: it makes the revocation result `unknown`, by RFC-ACDP-0014 §7 precedence (unknown overrides not-revoked and pre-compromise; a refusal still wins).
9. **Identity now.** Fetch the controller's current document. If the identity is listed, **currently authorized**. If it is not, **historically authorized**. If the document cannot be fetched, fail transiently: `controller_unreachable`.

The receipt is the only timestamp that places a keyless signature: the receipt's `created_at` is the time the attester saw it. A consumer MUST NOT place it by the body's own fields or by its own clock.

### 8.2 Mapping onto the existing key statuses (NORMATIVE)

A keyless key adds no key-authorization state. The outcome of §8.1 maps onto the three statuses RFC-ACDP-0010 §10 and RFC-ACDP-0014 §7 define, or onto failing closed:

| §8.1 outcome | Key status | Meaning for the keyless key |
|---|---|---|
| step 9, identity listed | **currently authorized** | The attestation is valid, the receipt placed the signature in its window, and the controller still authorizes the identity. |
| step 9, identity not listed | **historically authorized (receipt-attested)** | As above, but the controller has since removed the identity (§9.1). The removal does not reach back: the signature was authorized when the attester received it. |
| step 8, receipt before T | **historically authorized (pre-compromise, receipt-attested)** | A revocation names the attested fingerprint, and the receipt places the signature before `compromised_since`. |
| any failure in steps 1–8 | **fail closed** | The body MUST NOT be relied on. The reason token says why. |
| step 9, `controller_unreachable` | **fail closed** (transient) | Retry later. |

A consumer reports a keyless key's status as exactly one of these, together with its revocation result. When that result is `unknown` (§8.1 step 8), the consumer reports the status from steps 1–9 with `key_revocation: unknown`, never as not-revoked, and a consumer whose policy fails closed on an unknown revocation result refuses the body, as RFC-ACDP-0014 §7 requires for any key. An implementation that models key status as a closed enumeration needs no new member. `kl-001` vector 4 is the 21-case table and `kl-005` the scenarios.

---

## 9. Revocation

### 9.1 Identity-level revocation

The controller stops a workload identity from signing by removing it from its `AcdpKeylessSigning` service. Registries then refuse new attestations for it (§5.2 step 6) and SHOULD refuse publishes with live attestations for it (§6.3 step 7). Bodies already signed stay verifiable as historically authorized (§8.2). Removing an identity says nothing about past compromise. For that the controller revokes keys (§9.3).

### 9.2 Withdrawal by the registry (NORMATIVE)

An attesting registry withdraws an attestation by retracting it with a registry-actor RFC-ACDP-0013 `retracted` event, for example after learning that a token was stolen or the issuer misbehaved. A consumer MUST treat a retracted attestation as a **registry-attested** revocation (RFC-ACDP-0014 §7) of the attested fingerprint with `compromised_since` = `not_before`. Every body signed with that key then fails closed (`attestation_withdrawn`, §8.1 step 7). The registry is the only party that vouched for the key, so its withdrawal removes all support for it. No new revocation trust class is involved.

The attestation's retraction state is the RFC-ACDP-0013 fold of the lifecycle events on it, counting only the attesting registry's events. A registry-actor event counts when the attesting registry signed it, or when it was admitted on that registry's RFC-ACDP-0013 §10.3 event receipt, because the receipt is the registry's own signature over the event. An event by any other actor is disregarded for this purpose. A later registry-actor `republished` event restores the attestation, and from then on it no longer counts as a revocation. A verifier evaluating an as-of instant applies the fold as of that instant (RFC-ACDP-0017 §7.8).

### 9.3 Key revocation (NORMATIVE)

RFC-ACDP-0014 applies to keyless keys by fingerprint, unchanged. A `key-revocation` body names the attested `key_fingerprint` as `metadata.revoked_key_fingerprint`, with `compromised_since`; the revoked key's controller is the attestation's `controller`. Its trust class follows RFC-ACDP-0014 §7:

- **producer-signed** when it is signed by a key in the controller's DID document, or by a keyless key whose attestation is `org_wide`;
- **registry-attested** when a registry publishes it under RFC-ACDP-0014 §6, with `revoked_key_controller` = the controller.

A revocation signed by a non-org-wide keyless key does not speak for the controller. Consumers MUST NOT apply it, and MAY report it as a hint (`kl-005` G). This stops a stolen workload credential from minting revocations that knock out the controller's other keys.

**Evaluating a keyless-signed revocation (NORMATIVE).** A consumer evaluates the revocation's signer with §8.1 steps 1–7, using the same attester acceptance as for bodies (§11). It does not run step 8, so there is no recursion into revocations of the signer's own key, and it does not run step 9, because both of its outcomes authorize the signer. The outcomes are:

| Signer evaluation | Effect on the revocation |
|---|---|
| Passes, attestation `org_wide` | Producer-signed; it applies (`kl-005` I). |
| Passes, not org-wide | Not applied; MAY be reported as a hint (`kl-005` J, as G). |
| Not evaluable: no RFC-ACDP-0021 support, attester not accepted (step 2), or attestation unavailable (see below) | The revocation lookup is `unknown` (§8.1 step 8, RFC-ACDP-0014 §7), never not-revoked (`kl-005` K). |
| Definitively invalid: step 1 fails on the attestation's hash, signature, receipt or §5.3 rules, or steps 3–6 fail, or step 7 (withdrawn) | Ignored, as is any RFC-ACDP-0014 revocation whose signature fails (`kl-005` L). |

**Unavailable versus invalid (NORMATIVE).** The test is whether the evidence could be obtained. The signer's attestation is **unavailable** when the consumer cannot obtain an item it needs to run step 1: the attestation named by `key_attestation.ctx_id`, its `registry_receipt`, or the attesting registry's DID document. A supplied attestation whose `ctx_id` is not the one named also counts as unavailable, because the named one was not supplied. Obtained evidence that fails a check is **invalid**. That covers bytes that do not hash to `key_attestation.content_hash`, a signature or receipt that is present but does not verify, and a broken §5.3 rule. An unavailable signer gives `unknown`, and an invalid one is ignored.

Revocation discovery (RFC-ACDP-0014 §8) runs by `agent_id`, exactly as for any `did:web` producer. Keyless signing adds no per-identity or per-key discovery path, so consumers that cache revocations by producer DID need no change. To revoke every key a leaked identity received, the controller lists them with `GET /key-attestations` (§5.4) and revokes each fingerprint whose window ends after the compromise (`kl-009` D).

---

## 10. Chain Verification (NORMATIVE)

In RFC-ACDP-0017 a keyless node is evaluated with the existing stage vocabularies, and the bundle format is unchanged. §8.1 is split across the stages as follows:

- **Evidence.** The attestation is an ordinary context. The bundle carries it, with its receipt, in `contexts`, as it carries revocation bodies. The controller's DID-document snapshots serve as for any `did:web` producer.
- **`key` stage** (RFC-ACDP-0017 §7.6). It runs §8.1 steps 1–5 and step 9 against the chosen snapshot. **currently authorized** gives `current`, and **historically authorized** gives `historical_receipt_attested`. The basis is `registry`, and `evidence_time` is the body receipt's `created_at`, because the attester's receipt placed the signature. This holds also when the attester was accepted through a trust list.
- **`signature` stage** (RFC-ACDP-0017 §7.4). It runs §8.1 step 6 with the attested `public_key_jwk`. A failure is `signature: invalid`, with the `key` stage as located, as for a pinned key that does not verify (RFC-ACDP-0017 §6.3).
- **`key_revocation` stage** (RFC-ACDP-0017 §7.9). §8.1 steps 7 and 8 are never reported by the `key` stage. **pre-compromise** and `revoked` come from this stage as for any key, and a retracted attestation is an admitted registry-actor retraction here (§9.2), so a withdrawn key gives `key_revocation: revoked` and `key: revoked` (`kl-008` D). When the only revocation evidence that keeps the stage from `not-revoked` or `pre-compromise` is an unevaluable keyless-signed revocation (§9.3), the stage is `{"value": "unknown", "revocation_ctx_id": …}`. `revocation_ctx_id` names that revocation, the lowest by UTF-8 bytes when there are several. The stage carries no `basis` and no `evidence_time`, since nothing was established. RFC-ACDP-0014 §7 precedence still holds: `revoked` and `unplaceable` win over it, and it wins over `pre-compromise` and `not-revoked` (`kl-008` F).
- **Missing evidence.** When the attestation is absent from the bundle, when it is not yet admitted at T (its receipt's `created_at` is after T), or when no controller snapshot is selectable at T, the `key` stage is `unresolvable` in the latest pass, and `unknown` with reason `no_evidence_at_as_of` in the as-of pass (the `signature` stage is then omitted, RFC-ACDP-0017 §7.4).
- **Other failures.** Any other failure of steps 1–5 on evidence that is present gives `key: unresolvable` and `signature: unresolvable` in both passes. So does a `key_attestation` that breaks the §6.2 presence rules: a keyless key id with none, or one on a body whose key id is not keyless.
- **Attester acceptance.** `verify_chain` takes the §11 accepted attesters only from *(0.5.0)* `pinned.keyless_attesters` (RFC-ACDP-0017 §6.3). The §11 trust-list path does not apply inside `verify_chain`: RFC-ACDP-0020's chain integration evaluates a finished verdict and feeds nothing back into the `key` stage. A caller that wants trust-list attesters evaluates the lists first and pins the resulting registry DIDs. `verify_chain` MUST NOT consult any source outside `pinned`, so `options_digest` captures which attesters a verdict relied on.
- **Lifecycle events.** An RFC-ACDP-0013 event whose signing key id is a keyless key id is not admitted: its signer is unresolvable (§6.3).
- A verifier without RFC-ACDP-0021 support reaches `key: unresolvable` and `signature: unresolvable` for the node, so the node is refused, never `ok` (`kl-008` E).

The verdict schema, the stage values and the `chain-*` known answers are unchanged. The evidence schema's `#/$defs/pinned` gains only the OPTIONAL `keyless_attesters` member, absent when empty, so no existing `options_digest` moves.

---

## 11. Which Attesters a Consumer Accepts (NORMATIVE)

An attestation is only as good as the registry that minted it, so a consumer MUST decide which registries it accepts as attesters. A registry is accepted when either:

- the consumer's local keyless configuration names its DID; or
- the consumer applies RFC-ACDP-0020 trust lists and the keyless-signed body evaluates `trusted` (RFC-ACDP-0020 §6.2) with the attesting registry as its receipting registry. §6.3 step 2 makes the attester and the receipting registry the same for every body accepted on publish.

**Trust-list inputs (NORMATIVE).** The trust-list evaluation runs at §8.1 step 2, before placement, with these RFC-ACDP-0020 §6.2 inputs: the evaluated body is the keyless-signed body; the receipting registry R is the attestation's issuing registry (its `agent_id`); and the registry key fingerprint is that of the key that signed the attestation's receipt, which step 1 verified. Step 4 then requires the body's own receipt to come from that same registry, so a body receipted elsewhere is `unplaceable`. The trust-list path applies to direct verification (§8.1) only. Chain verification accepts attesters solely from `pinned.keyless_attesters` (§10).

The default accepts none: a consumer with no keyless configuration and no trust list refuses every keyless-signed body (`untrusted_attester`, `kl-006` A). A trust-list outcome other than `trusted` also refuses it. RFC-ACDP-0020's schema, outcomes and report are unchanged.

---

## 12. Compatibility and Failing Closed (NORMATIVE)

Implementations that do not implement this document MUST fail closed on keyless-signed bodies, and they do so without any change:

- **Consumers.** RFC-ACDP-0001 §5.11 step 4 looks up the `acdp-kl-` fragment in the controller's `verificationMethod` and finds nothing, because §4.2 forbids it there. The result is `key_resolution_failed`, and the body is not accepted (`kl-007` A).
- **Registries before 0.5.0.** They reject a publish carrying `key_attestation` with `schema_violation` (`kl-007` C).
- **0.5.0 registries without the profile.** They refuse at key resolution as above (`kl-003` J), and answer `/key-attestations` with `not_implemented`.
- **RFC-ACDP-0017 verifiers without support.** The node is `key: unresolvable` and refused (§10).
- **Seam and similar consumers pinned to an earlier SDK.** No new key-status value, revocation trust class, stage value or bundle member reaches them. They see a key that does not resolve (`kl-007` D).

No implementation MAY accept a keyless-signed body by treating `key_attestation` as advisory or by skipping key resolution. A verifier that does not run §8 MUST treat the body as unverifiable.

A body that is not keyless-signed but carries `key_attestation` is invalid at publish (§6.2). A consumer claiming `acdp-consumer-keyless` fails closed on such a body with `attestation_mismatch` (§6.2). A consumer that implements neither profile has no rule for the field and verifies the signature by §5.11 as usual.

---

## 13. Capabilities, Profiles and Errors

### 13.1 Capabilities (NORMATIVE)

A registry advertising `acdp-registry-keyless` MUST include a top-level `keyless` member in its capabilities document (`schemas/json/acdp-capabilities.schema.json`, example `examples/capabilities/acdp-capabilities-keyless.json`), and MUST NOT include it otherwise:

| Member | Meaning |
|---|---|
| `accepted_oidc_issuers` | OIDC issuer URIs whose tokens it verifies, compared byte for byte with `iss`. |
| `accepted_spiffe_trust_domains` | SPIFFE trust domains whose JWT-SVIDs it verifies. |
| `max_attestation_ttl_seconds` | Longest window it mints, 60 to 3600. |

Producers read it to pick a registry, and to request a token whose `aud` is that registry's `registry_did`.

### 13.2 Profiles (NORMATIVE)

- **`acdp-registry-keyless`** *(OPTIONAL)*. Prerequisites `acdp-registry-receipts`, `acdp-registry-transparency-log` and `acdp-registry-lifecycle`, with `acdp_version` ≥ `0.5.0`. Serves `POST /key-attestations` and `GET /key-attestations` (§5), accepts keyless-signed publishes (§6.3), enforces §7, and advertises `keyless`. Fixtures: `kl-001`, `kl-002`, `kl-003`, `kl-004`, `kl-007`, `kl-009`.
- **`acdp-consumer-keyless`** *(OPTIONAL)*. Prerequisite `acdp-consumer`. Runs §8 for keyless key ids and no other resolution, applies §9 and §11, and evaluates keyless chain nodes per §10. Fixtures: `kl-001`, `kl-005`, `kl-006`, `kl-007`, `kl-008`, `kl-009`.

Both are listed in `registries/profiles.md` and RFC-ACDP-0001 §9.1.

### 13.3 Errors: no new wire code (NORMATIVE)

This document adds no wire error code. Every refusal reuses a code whose meaning already fits (`key_not_authorized`, `key_resolution_failed`, `invalid_signature`, `not_authorized`, `schema_violation`, `unsupported_algorithm`, `key_resolution_unreachable`, `not_implemented`) and says why in `details.reason`, with the tokens listed in `registries/error-codes.md` ("Keyless-signing reason tokens"). `error.details` is an open object whose shape is code-specific (RFC-ACDP-0007 §4), so clients already handle members they do not know.

The choice was checked against the reference SDK. acdp-rs maps wire codes it knows onto `AcdpError` variants and sends any other code to a catch-all `AcdpError::Registry(WireError)` variant (the enum is `#[non_exhaustive]`), so a new code would not have broken it. Existing codes were still preferred: an SDK or registry that matches on the code keeps working, a client that retries on `key_not_authorized` behaves sensibly, and the reason tokens can change while this document is Draft without touching the three-way-synced code enum.

The consumer-side reasons of §8.1 (`attestation_invalid`, `untrusted_attester`, `attestation_mismatch`, `unplaceable`, `outside_attestation_window`, `attestation_withdrawn`, `revoked`, `controller_unreachable`) are verification results, not wire errors. Consumers SHOULD report them with these names.

---

## 14. Conformance Fixtures

| Fixture | Covers |
|---|---|
| `kl-001` | Executed. Golden attestation, keyless-signed body and proof of possession, all recomputed with `jcs`; a verify-only ecdsa-p256 proof of possession (vector 6: the `r||s` form accepted, DER rejected); the §8.2 table (21 cases) and the §7 table (9 cases), replayed by reference evaluators in `scripts/conformance-runner.py`. |
| `kl-002` | §5: audience mismatch, issuer, identity not listed, `cnf`, replay, proof, `did:key` controller, X509-SVID. |
| `kl-003` | §6: inside and outside the window, missing, foreign, mismatched and withdrawn attestations, non-keyless registries. |
| `kl-004` | §7: refused cross-identity supersession, allowed same-identity and org-wide supersession; §6.3: keyless-signed lifecycle events refused. |
| `kl-005` | §8 and §9: the status mapping, the two trust classes, and the four outcomes for a keyless-signed revocation. |
| `kl-006` | §11: untrusted attester, local configuration, trust-list gating. |
| `kl-007` | §12: old verifiers fail closed; the reserved fragment. |
| `kl-008` | §10: keyless chain nodes. |
| `kl-009` | §9: identity removal, listing, revoking a leaked identity's keys. |

The `kl-001` keys are publicly known test seeds and MUST NOT be used outside tests.

---

## 15. Security Considerations

- **A compromised registry can attest any key** for any controller whose listed issuer it accepts. Every attestation it mints is a public, logged body, so the controller can watch its own attestations with `GET /key-attestations` and the log (RFC-ACDP-0012, witnessed per RFC-ACDP-0015), and consumers limit which registries they accept (§11). This is the same exposure Fulcio has to its CA, with the log as the check.
- **A compromised issuer** (or a stolen token) can obtain attestations for an identity it controls, within the controller's listing. The `aud` binding limits a token to one registry, single use limits it to one key, and the window limits that key to at most an hour. The controller removes the identity (§9.1) and revokes the leaked keys (§9.3); the registry may withdraw them (§9.2).
- **Token replay across registries** is stopped by `aud` = `registry_did`. A token minted for a hostname is refused, because a hostname is not an identity a registry signs as.
- **Key substitution** is stopped by the proof of possession over the token hash, and by `key_attestation` sitting inside the signed `content_hash`.
- **Backdating** is stopped by placing every signature with the attester's receipt (§8.1 step 5). A producer cannot claim a time inside an old window, and the receipt's time is itself logged.
- **Lineage hijack** by one workload against another's lineages is stopped by §7.
- **Revocation abuse** by a stolen workload credential is stopped by §9.3: only DID-document keys and org-wide keyless keys sign producer revocations.
- **Old-verifier acceptance** is prevented by the reserved fragment (§4.2, §12).
- **Privacy.** The attestation publishes the workload's issuer and subject, which can name a repository, branch or service account. Controllers that consider those private SHOULD NOT use keyless signing on a public registry. The token itself is never published.
- **Issuer key fetches** happen at the registry and target only issuers it lists in its capabilities; they MUST use the RFC-ACDP-0008 §4.8 outbound-fetch defenses.

---

## 16. References

- **[RFC 2119]**, **[RFC 8174]** — requirement keywords.
- **[RFC 7517]** JSON Web Key; **[RFC 7638]** JWK Thumbprint; **[RFC 7800]** Proof-of-Possession Key Semantics for JWTs (`cnf`); **[RFC 8785]** JSON Canonicalization Scheme.
- **[OIDC Core]** OpenID Connect Core 1.0 — ID tokens.
- **[SPIFFE]** SPIFFE ID and JWT-SVID specifications.
- **[RFC-AITP-0002]** Agent Identity & Trust Protocol — Identity: the identity descriptor (`type`, `issuer`, `subject`, `proof`), the identity hint, and the OIDC (§2.3) and SPIFFE (§6) verification rules this document reuses. Normative reference: `rfcs/RFC-AITP-0002-identity.md` in https://github.com/agentidentitytrustprotocol/agentidentitytrustprotocol at commit `c11a2c4`. A later AITP revision applies only once this document re-pins it.
- **[Sigstore]** Fulcio and Rekor — the design this document adapts, with the registry as attester and its log as Rekor.
- RFC-ACDP-0001, 0003, 0007, 0008, 0010, 0012, 0013, 0014, 0017, 0020 (this repository).

---

## Appendix A. Relation to Sigstore Fulcio (informative)

Fulcio issues a short-lived X.509 certificate binding an ephemeral key to an OIDC identity, and Rekor logs signatures. Here the registry plays both parts: the key attestation is the certificate, and the registry's transparency log is Rekor. The differences are that the authorization of an identity comes from the producer's DID document rather than from the identity alone, and that the signature is placed by the registry receipt rather than by a separate log entry. A binding that accepts Fulcio certificates in place of registry attestations is reserved in RFC-ACDP-0009 §2.13.
