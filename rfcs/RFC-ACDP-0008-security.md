# RFC-ACDP-0008
# Agent Context Description Protocol (ACDP) — Security & Threat Model

**Document:** RFC-ACDP-0008
**Version:** 0.1.0
**Status:** Community Standards Track (Final)

This RFC specifies the threat model for ACDP v0.1.0 and the defenses every implementation MUST provide. It depends on the entire core RFC stack (0001–0007).

---

## 1. Status of This Memo

This document is a Final ACDP specification (acdp/0.1.0). It is stable for the 0.1.0 release; subsequent breaking changes require a new RFC and a version bump per [VERSIONING.md](../VERSIONING.md).

---

## 2. Threat Surface

ACDP exists in an environment where:

- Producers and consumers are autonomous agents acting on behalf of organizations.
- Registries are distributed services, possibly operated by different parties.
- Cross-registry references mean a consumer may pull data from a registry it does not control.
- Networks are partially adversarial (DNS spoofing, MitM on non-TLS hops, hostile intermediaries).
- Identities are pluggable; both producer DIDs and registry DIDs are subject to standard PKI risks.

The threat surface is therefore: **the entire path from producer's signing key, through the registry, across the network, to the consumer's verification logic — plus the surrounding metadata operations (discovery, capabilities, errors).**

---

## 3. Threats Addressed in v0.1.0

| Threat | Mechanism |
|---|---|
| **3.1 Body tampering** | `content_hash` is recomputed on retrieval; signature is verified against the producer's DID document. Any modification to a non-excluded field changes the hash. |
| **3.2 Lineage forgery** | `lineage_id` is deterministically derived from the first version's `ctx_id`. The registry verifies producer-supplied `lineage_id` matches the derived value. The chain is part of the signed body. |
| **3.3 Producer impersonation** | The signing key is bound to a DID. Verifiers resolve the key from the producer's DID document (e.g. `did:web` over HTTPS, with TLS verification). |
| **3.4 Cross-registry impersonation** | `origin_registry` is a registry-assigned field, not producer-controlled. The serving registry's authority must match the URI authority. |
| **3.5 Existence-leak via 404 differentiation** | Visibility-restricted contexts return `not_found`/HTTP 404 indistinguishably from genuinely missing contexts. |
| **3.6 Replay of publish requests** | TLS prevents on-wire replay reordering. At the application level, replay creates a duplicate publication with a new `ctx_id` but identical `content_hash`. This is **content-level idempotent** but not **publication-level idempotent**: the registry assigns a new `ctx_id` unless the producer used `Idempotency-Key` (RFC-ACDP-0003 §6) for true publication-level deduplication. Producers SHOULD also deduplicate locally on `content_hash`. |
| **3.7 DoS by oversize bodies** | `limits.max_payload_bytes` and `embedded_too_large` (64 KB cap) enforce upper bounds. |
| **3.8 Spam / Sybil** | Per-agent rate limiting is REQUIRED (§4). |
| **3.9 Algorithm downgrade** | Signature algorithm is named in the body (`signature.algorithm`) and MUST be in the registry's `supported_signature_algorithms`. Verifiers MUST reject if `signature.algorithm` does not match the algorithm declared by the resolved verification method in the producer's DID document — this prevents downgrade attacks where an attacker substitutes a weaker algorithm than the producer's actual key supports. |
| **3.10 Race on supersession** | The registry serializes supersession events: a `superseded_target` error is returned for the loser of a race. |

---

## 4. Required Defenses

### 4.1 Cryptographic core

- Implementations MUST support `ed25519` ([RFC 8032]).
- Implementations MUST use a cryptographically secure RNG for UUIDs (`ctx_id` UUID component).
- Private keys MUST be stored in secure storage (HSM, key vault, OS keystore).
- Implementations MUST fail closed on signature verification errors — there is no `soft_fail` mode in v0.1.0.

### 4.2 Input validation

- All inputs MUST be validated against the JSON Schemas before processing.
- Implementations MUST reject any publish request that does not validate against `acdp-publish-request.schema.json`.
- Implementations MUST reject any request whose body exceeds `limits.max_payload_bytes`.
- Implementations MUST reject embedded data exceeding 64 KB decoded.

### 4.3 Rate limiting

- Registries MUST rate-limit `POST /contexts` per `agent_id` (the signing producer).
- Registries SHOULD rate-limit retrieval and search endpoints per requesting principal.
- Rate-limit responses MUST use `rate_limited` (HTTP 429) and SHOULD include a `Retry-After` header when bounded.

### 4.4 Signature verification

- Registries MUST verify producer signatures at publish time. Verification failures MUST result in rejection with `invalid_signature`.
- Consumers MUST verify producer signatures on every retrieved context they rely on. Trusting the registry alone is **not** sufficient.
- When a producer rotates keys, prior signatures remain mathematically valid (the same content + same key still verifies). Verifying that the *signing key was authorized at the time of publication* requires historical key validity, which most DID methods do not natively provide. Verifiers SHOULD verify against the producer's current DID document; verifiers requiring stronger historical guarantees MUST consult external mechanisms (see §9.3).

### 4.5 Visibility enforcement

- Registries MUST scope discovery and retrieval responses by the requesting agent's effective audience (see below). Effective audience is computed independently for **retrieval** and **search**; the two MAY differ for `visibility: private` (see below).
- For `visibility: restricted` and `private`, registries MUST return `not_found` (HTTP 404) to non-audience requesters on retrieval. The `visibility_denied` semantic is internal logging only.
- Registries MUST NOT include restricted contexts in `total_estimate` for non-audience requesters, and MUST NOT include private contexts in `total_estimate` for any requester other than the producer.

**Effective audience for `visibility: private`:**

- For **retrieval**: `agent_id` is always authorized; DIDs listed in `audience` (if present) are authorized.
- For **search/discovery**: only `agent_id` is authorized. DIDs listed in `audience` are NOT authorized for search — they can retrieve a `ctx_id` they already know, but they MUST NOT find the context via `GET /contexts/search` or any other discovery surface. Search visibility is strictly narrower than retrieval visibility for `private`.
- Contributors listed in `contributors` are **NOT** automatically authorized for either retrieval or search; `contributors` is for attribution only. Producers wishing to grant a contributor read access MUST list the contributor's DID in `audience` explicitly (still retrieval-only).
- Producers wanting both retrieval AND search access for a defined cohort MUST use `visibility: restricted` instead.

**Effective audience for `visibility: restricted`:**

- For both retrieval and search: `agent_id` is always authorized; all DIDs in `audience` are authorized.
- `audience` MUST be present and non-empty for `restricted` contexts.

**Effective audience for `visibility: public`:**

- Any authenticated requester is authorized for both retrieval and search.
- Anonymous requesters are authorized only if the registry advertises `anonymous_public_reads: true` (§6.3); otherwise registries MUST reject unauthenticated requests with `not_authorized` (HTTP 403).
- The `audience` field MUST be absent or empty (RFC-ACDP-0002 §7); the publish-request schema rejects `public` with non-empty `audience` as `schema_violation`.

The full visibility matrix (retrieval × search × visibility level × requester role) is in [RFC-ACDP-0002 §7](RFC-ACDP-0002-context-body.md#7-visibility).

### 4.6 Transport

- Production deployments MUST use TLS for all ACDP endpoints.
- Registries MUST set cache headers based on body visibility (RFC-ACDP-0004 §6). Public bodies MAY use `Cache-Control: public, max-age=31536000, immutable`; restricted and private bodies MUST use `Cache-Control: private, no-store` (or `private, max-age=<short>`). Registries MUST NOT serve `Cache-Control: public` on non-public bodies.
- Registries MUST NOT echo unsanitized request content in `error.message`.

### 4.7 Cross-registry

- Consumers resolving `acdp://` references MUST verify the producing agent's signature on every retrieved context. They MUST NOT trust the serving registry to vouch for context authenticity. Registry trust extends only to availability.
- DNS spoofing or registry compromise MUST NOT be sufficient to forge a context — the producer's signature is the trust anchor.
- When `acdp://` resolution is performed server-side (e.g., on a registry advertising the `acdp-registry-federated` profile), the resolving party MUST verify the upstream registry's DID per RFC-ACDP-0006 §4.1 step 3 (fetch `https://<authority>/.well-known/acdp.json`, extract `registry_did`, resolve the DID document, and confirm the DID's web binding matches `<authority>`). Mismatch MUST result in `cross_registry_resolution_failed`. Server-side resolution MUST also apply the SSRF protections of RFC-ACDP-0006 §7. Consumers performing client-side resolution SHOULD apply the same checks.

### 4.8 Producer DID resolution SSRF protection

RFC-ACDP-0006 §7 specifies SSRF defenses for cross-registry resolution. **Producer DID resolution is an equally attacker-controlled SSRF vector** and MUST be defended identically.

Both a registry (verifying a signature during `POST /contexts` — RFC-ACDP-0003 §2.1 step 6) and a consumer (verifying a retrieved context end-to-end — §4.4) dereference a producer-supplied `did:web` identifier into an HTTPS URL: `did:web:agents.example.com` → `https://agents.example.com/.well-known/did.json`, and `did:web:example.com:path:to:agent` → `https://example.com/path/to/agent/did.json`. The host component is taken verbatim from `body.agent_id` and `signature.key_id`, which are producer-controlled. A registry that runs signature verification on user-submitted publish requests can therefore be turned into an SSRF proxy if its DID resolver applies no IP-range restrictions.

Registries and consumers MUST apply the following defenses to producer `did:web` resolution, mirroring RFC-ACDP-0006 §7:

- The resolved URL MUST use the `https://` scheme. `http://` and any other scheme MUST be refused without connecting.
- The host MUST be resolved before connecting, and the connection MUST be refused if any resolved IP is:
  - **Loopback** — `127.0.0.0/8`, `::1` (and the unspecified address `0.0.0.0`, which many OSes route to localhost).
  - **RFC 1918 private** — `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, and IPv6 ULA `fc00::/7`.
  - **Link-local, including the cloud-metadata endpoint** — `169.254.0.0/16`, `fe80::/10`, and specifically `169.254.169.254` (AWS / GCP / Azure IMDS).
  - Any locally-defined private range relevant to the deployment.
- The resolved IP MUST be pinned for the connection lifetime (one DNS resolution per request, used for both the filter check and the connection — no TOCTOU re-resolution), redirects MUST stay on the same authority and be capped, response size MUST be capped (DID documents MUST cap at 64 KB per RFC-ACDP-0006 §7.3), and connection/total timeouts MUST be bounded per RFC-ACDP-0006 §7.4.

A registry that refuses a producer DID on these grounds MUST fail the publish with `key_resolution_failed` (HTTP 400): the refusal is a permanent, policy-driven, producer-caused condition and is **not** retryable, so `key_resolution_unreachable` (HTTP 502, retryable) MUST NOT be used. A consumer that refuses a producer DID on these grounds MUST treat the context as unverifiable and MUST NOT rely on it.

Test harnesses MAY allow `localhost`/loopback targets only when an explicit, non-default test-mode SSRF policy is configured. Producers using `did:web:localhost%3A8443:...`-style DIDs are valid only in test and development deployments and MUST NOT appear in production publications. The `did-ssrf-001`, `did-ssrf-002`, and `did-ssrf-003` conformance fixtures pin loopback, IMDS, and private-range refusal respectively.

### 4.9 DataRef location SSRF protection

§4.8 covers producer DID resolution and RFC-ACDP-0006 §7 covers cross-registry resolution. There is a **third attacker-controlled outbound fetch**: a consumer that dereferences a `data_refs[].location` URL to fetch and verify the referenced data (RFC-ACDP-0002 §6.5). `data_refs[].location` is producer-controlled — it is part of the signed body — and a consumer that fetches it on behalf of an application can be turned into an SSRF proxy exactly as a DID resolver can.

This section governs the case where a consumer dereferences a `data_refs[].location` value **over HTTP(S)** (the `https://`/`http://` URL form of RFC-ACDP-0002 §6.2). Non-HTTP location schemes (`s3://`, `postgres://`, `kafka://`, structured locators, …) are dereferenced by their own client libraries and are governed by those clients plus the deployment's egress policy; this section does not constrain them. A `data_refs[].location` carrying a private, loopback, or link-local IP is **not** itself a publish-time error — a producer may legitimately reference an internal `postgres://10.0.0.1/...` datastore — so registries MUST NOT reject such a publish. The defense lives entirely at the consumer's fetch step.

When a consumer fetches a `data_refs[].location` over HTTP(S), it MUST apply the same SSRF posture as producer DID resolution (§4.8) and cross-registry resolution (RFC-ACDP-0006 §7):

**URL-level checks (necessary but insufficient):**

- The fetched URL MUST use the `https://` scheme. A consumer MUST NOT silently fall back to `http://`; per RFC-ACDP-0002 §6.5 an `http://` location is fetched only as an explicit, integrity-checked deployment-policy decision and is outside the SSRF-safe path.
- If the host is an IP literal, it MUST NOT be in any private (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`), loopback (`127.0.0.0/8`, `::1`, `0.0.0.0`), link-local (`169.254.0.0/16`, `fe80::/10`, including the IMDS address `169.254.169.254`), or multicast (`224.0.0.0/4`, `ff00::/8`) range.

**DNS-level checks (required for full protection):**

- The host MUST be resolved before connecting and EVERY resolved IP address MUST be validated against the same disallowed ranges (RFC-ACDP-0006 §7.1).
- The resolved IP MUST be pinned for the connection lifetime — one DNS resolution per request, used for both the filter check and the connection (no TOCTOU re-resolution; RFC-ACDP-0006 §7.6). Acceptable implementation: install a `SafeDnsResolver` in the HTTP client that rejects disallowed addresses.

**Redirect policy:**

- Redirects MUST NOT cross to a different authority (host + port), and the total redirect count MUST be capped at 3 follows (same limit as cross-registry, RFC-ACDP-0006 §7.5).
- A same-authority redirect MUST NOT trigger a fresh DNS lookup — the pinned IP is reused.

**Response and timeout caps:**

- The connection and total-request timeouts MUST be bounded per RFC-ACDP-0006 §7.4. Consumers SHOULD cap the response size for a DataRef fetch at a deployment-appropriate limit and abort before parsing if exceeded.

**Insufficient approach (explicitly disallowed):**

- Calling a URL-syntax check (`check_url()` or equivalent) on the `location` string and then using an unconstrained HTTP client that resolves DNS normally at connect time. DNS rebinding and split-horizon DNS can still route such requests to internal services. See §4.8 and RFC-ACDP-0006 §7.6.

A consumer that refuses a `data_refs[].location` fetch on these grounds MUST treat that DataRef as unfetchable and unverifiable: it MUST NOT use the referenced data, and if a `data_refs[].content_hash` was present the DataRef MUST NOT be reported as verified. The refusal does **not** invalidate the body — the producer signature and body `content_hash` remain valid; only the external reference is unreachable on the SSRF-safe path (the same body-stays-valid principle as the consumer-side `data_ref_hash_mismatch` case, RFC-ACDP-0007 §5.3).

Implementations exposing a `DataRefFetcher` (or equivalent) abstraction MUST apply this policy in the default fetcher and SHOULD apply it to custom fetchers; where a caller supplies a custom fetcher that deviates, the SDK MUST document the deviation as outside the SSRF-safe path. The `data-ref-ssrf-001`, `data-ref-ssrf-002`, and `data-ref-ssrf-003` conformance fixtures pin IP-literal, DNS-rebinding, and cross-authority-redirect refusal respectively.

---

## 5. Known Gaps (Acknowledged)

| Gap | Reason | Mitigation in v0.1.0 |
|---|---|---|
| **No retraction** | Permanent publication is the v0.1.0 invariant. | Use supersession to publish corrections. RFC-ACDP-0009 reserves a formal lifecycle-events mechanism. |
| **No real-time key revocation push** | Out of scope for the substrate. | Pull-based; consumers consult DID documents. Producers can publish a "this key is compromised" context as a soft signal. |
| **No third-party attestations** | Out of scope for v0.1.0. | RFC-ACDP-0009 reserves `attestations` in registry state. |
| **No third-party `builds_on` claims** | Out of scope for v0.1.0. | `derived_from` is producer-only; downstream consumers can publish their own `derived_from` context. |
| **No push subscriptions** | Polling is the v0.1.0 model. | RFC-ACDP-0009 reserves push semantics. |
| **No federation peering** | Out of scope. | Cross-registry resolution via `acdp://` is the federation primitive. |
| **No multi-party / threshold signatures** | Out of scope. | Use `contributors` for joint authorship; the single signing identity is one of them. |
| **No quality scoring by registries** | Out of scope. | Consumers compute their own trust models from DID + signature evidence. |
| **No audit-grade time anchoring** | Out of scope. | `created_at` is registry clock; producers wishing strong time guarantees use external time-stamp services and embed those as `data_refs`. |

---

## 6. Request Authentication

ACDP defines two authentication contexts: writes (publish) and reads (retrieval, search).

### 6.1 Write authentication

The producer's signature on the request body authenticates the writer. The registry derives `effective_requester_did` for write operations from `body.agent_id`, after verifying the body signature per RFC-ACDP-0003 §2.1 steps 4–7.

Implementations MAY layer HTTP-level authentication (mTLS, bearer tokens) for additional protections such as rate limiting and abuse prevention, but the body signature is the protocol-level authoritative source.

### 6.2 Read authentication

Read operations have no body signature. Registries serving non-public contexts MUST establish the requester's DID via one of:

- **HTTP Message Signatures** [RFC 9421] using a key bound to the requester's DID document.
- **mTLS** with a client certificate bound to the requester's DID document.
- **OAuth 2.0 / OIDC** producing a token whose subject is bound to the requester's DID.

Registries MUST declare which read-authentication methods they support in `/.well-known/acdp.json` (capability field `read_authentication_methods`). The output of read authentication is `effective_requester_did`, used for visibility checks (§4.5), per-agent rate limiting (§4.3), and audit logging.

### 6.3 Anonymous reads

Registries MAY allow anonymous reads of `visibility: public` contexts. Anonymous requests have no `effective_requester_did`; registries MUST treat such requests as having empty audience membership and MUST NOT return any restricted or private context to an anonymous requester. A registry supporting anonymous public reads MUST declare `"anonymous_public_reads": true` in capabilities; otherwise unauthenticated requests MUST be rejected with `not_authorized` (HTTP 403).

---

## 7. Attack Scenarios

### 7.1 Hostile registry serves a tampered body

**Setup.** A consumer fetches `acdp://hostile.example/uuid`. The registry returns a modified body.

**Result.** The consumer recomputes `content_hash` over the JCS-canonicalized body and compares against `body.content_hash`. Mismatch ⇒ rejected. **Or**, the consumer verifies `body.signature` against the producer's resolved public key and gets a verification failure ⇒ rejected.

### 7.2 DNS spoof against a producer DID

**Setup.** An attacker spoofs DNS for `did:web:producer.example`. The consumer resolves what the attacker wants.

**Result.** TLS certificate validation at the producer's HTTPS endpoint catches the spoof unless the attacker has also obtained a valid TLS cert for the hostname. With DNSSEC + cert pinning, both are required to forge a context. Even with a forged DID document, the attacker must also produce a signature under the **real** producer's private key for any context the consumer is asking to verify — the existing signed contexts are tamper-evident.

### 7.3 Producer rotates keys; old context

**Setup.** Producer P signed `acdp://reg.example/<uuid>` with key K1 at `created_at=t1`. P later rotates to K2; K1 is removed from P's DID document at `t2`. A consumer at `t3 > t2` retrieves the context and tries to verify it.

**Result (v0.1.0, with the documented limitation in §9.3).** The consumer resolves P's *current* DID document and finds only K2. The K1 signature on the old context does not verify against K2. Without an external mechanism (DID-document snapshotting, transparency log, or registry receipt — none of which v0.1.0 specifies), the consumer **cannot** assert that K1 was authorized at `t1`.

Two acceptable v0.1.0 responses for the consumer:

- **Strict.** Reject the context. Old contexts whose signing keys have been rotated out are no longer locally verifiable.
- **Pragmatic.** Trust the producer's current DID document's claim about key rotation timeline (if any), or defer to an out-of-band attestation. The consumer accepts the residual risk that K1 was rotated *because* it was compromised, in which case signatures from K1 should not have been honored after `t2`.

A future ACDP version (RFC-ACDP-0009 §2.7 reserves registry receipts) will let the registry attest to *which producer key was current at the time of acceptance*, removing the historical-key dependency entirely. Until then, deployments where this matters SHOULD use external transparency logs as documented in §9.2.

### 7.4 Replay of a captured publish

**Setup.** An attacker captures a producer's `POST /contexts` request and replays it.

**Result.** Replay produces a duplicate publication. The body is content-addressed; the duplicate has identical `content_hash`. The registry assigns a new `ctx_id` (collision is statistically impossible). Idempotent at the content level. Producers wishing to suppress duplicate publication SHOULD deduplicate locally on `content_hash`.

### 7.5 Visibility-restricted lookup by unauthorized consumer

**Setup.** Consumer C requests `GET /contexts/{ctx_id}` for a context with `visibility: restricted` and `audience` not including C's DID.

**Result.** Registry returns `not_found` (HTTP 404). C cannot distinguish "doesn't exist" from "exists but you can't see it".

---

## 8. Security Considerations Summary

ACDP's security model rests on three pillars:

1. **Content addressing.** Bodies are JCS-canonicalized and SHA-256 hashed; any change is detectable.
2. **Producer signatures.** The trust anchor is the producer's DID document, not the registry. Registries are availability layers.
3. **Visibility scoping.** Registries enforce audience-based visibility on discovery and retrieval.

These three pillars are the minimum. Implementations MUST NOT relax any of them. Operators deploying ACDP in regulated environments SHOULD layer additional controls (egress policy, DID-document pinning, hardware-backed signing keys) on top of the protocol minimum.

---

## 9. Known Limitations

### 9.1 Producer signatures do not bind registry-assigned fields

ACDP v0.1.0 producer signatures cover producer-controlled fields. They do not cover registry-assigned identifiers (`ctx_id`, `lineage_id`, `origin_registry`, `created_at`). A consumer can verify content authorship by `agent_id` but **cannot** cryptographically verify which registry first accepted the content, what `ctx_id` the producer intended, or when publication occurred. These facts rely on registry honesty.

A malicious or compromised registry could republish a producer's signed content under a different `ctx_id` or `origin_registry` (the signature would still verify), or backdate `created_at`. A malicious registry **cannot** forge content from a producer, modify a body after publication, or forge a `derived_from` lineage.

### 9.2 Mitigations and future work

Deployments where this binding gap matters SHOULD use:

- External transparency logs anchoring `(ctx_id, content_hash, registry_did, timestamp)` tuples.
- Multi-registry replication with consumer-side comparison.

A future ACDP version will introduce **registry receipts**: registry-signed attestations binding `(ctx_id, lineage_id, origin_registry, created_at, content_hash)` to the registry's DID. The reservation is in [RFC-ACDP-0009 §2.7](RFC-ACDP-0009-extensions.md#27-registry-receipts).

### 9.3 Historical key validity

Verifying a context whose producer has rotated keys requires knowing which key was valid at `created_at`. Most DID methods do not expose reliable historical key validity. ACDP v0.1.0 SHOULD verify against the producer's current DID document; verifiers requiring historical accuracy MUST employ external mechanisms (DID-document snapshotting at publish time, transparency logs, archival proofs). A future ACDP version will define a normative DID-document snapshot mechanism.

---

## 10. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0002 Context Body](RFC-ACDP-0002-context-body.md)
- [RFC-ACDP-0003 Publish](RFC-ACDP-0003-publish.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0005 Discovery](RFC-ACDP-0005-discovery.md)
- [RFC-ACDP-0006 Cross-Registry References](RFC-ACDP-0006-cross-registry.md)
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md)
- [RFC-ACDP-0009 Extensions](RFC-ACDP-0009-extensions.md) — §2.7 reserves registry receipts.
- [docs/threat-model.md](../docs/threat-model.md) — non-normative summary.
- [DID-CORE] W3C, "Decentralized Identifiers (DIDs) v1.0".
- [RFC 8032] Josefsson, S. and I. Liusvaara, "Edwards-Curve Digital Signature Algorithm (EdDSA)".
