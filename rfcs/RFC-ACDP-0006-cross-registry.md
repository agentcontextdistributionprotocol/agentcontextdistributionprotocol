# RFC-ACDP-0006
# Agent Context Description Protocol (ACDP) — Cross-Registry References

**Document:** RFC-ACDP-0006
**Version:** 0.0.1-draft
**Status:** Community Standards Track (Draft)

This RFC specifies how consumers resolve `acdp://` references that point to contexts on a different registry. It depends on RFC-ACDP-0001 (Core) and RFC-ACDP-0007 (Capabilities).

---

## 1. Status of This Memo

Draft. Backward-incompatible changes remain possible until Final.

---

## 2. Motivation

ACDP contexts produced in one registry can be referenced from any other registry — a producer's `derived_from` array, an analyst's manual citation, an alert's evidence chain. Cross-registry references are the mechanism by which knowledge accumulates beyond a single deployment.

The `acdp://<authority>/<uuid>` URI scheme is the basis for cross-registry references. The `<authority>` component is the DNS hostname of the origin registry; resolution starts from there.

---

## 3. Registry Identity

Every ACDP registry MUST have:

- A DID, typically `did:web:<hostname>`. The hostname MUST equal the authority component used in `ctx_id` URIs the registry mints.
- A published key set in its DID document.
- A `/.well-known/acdp.json` capabilities document (RFC-ACDP-0007 §3) declaring its `registry_did`.

Two registries MUST NOT share an authority. The DNS hostname is the unique key.

---

## 4. Resolution

When a consumer encounters an `acdp://other-registry.example/uuid` reference and wishes to retrieve it, resolution proceeds:

### 4.1 Steps

1. **Parse the URI.** Extract `<authority>` and the UUID. Reject URIs that do not match the syntax in RFC-ACDP-0001 §5.4.
2. **Resolve the registry.** Construct the registry's well-known URL: `https://<authority>/.well-known/acdp.json`. Fetch and parse. Verify `acdp_version`, `registry_did`, `supported_signature_algorithms`.
3. **Verify the registry's DID.** SHOULD resolve `registry_did` and verify the DID document's web binding matches `<authority>`. Operators of consumer deployments SHOULD pin the `registry_did` they expect for each upstream they rely on (defense against an attacker who controls DNS for the authority but not the original registry's DID document).
4. **Issue retrieval.** `GET https://<authority>/contexts/{encoded_ctx_id}` per RFC-ACDP-0004 §2.
5. **Verify the body's signature.** Resolve the producing agent's signing key per RFC-ACDP-0001 §5.11, then verify `body.signature.value` against `body.content_hash`. v0.0.1 producers MUST use `did:web` (RFC-ACDP-0001 §5.4); consumers encountering other DID methods MAY return `key_resolution_failed` if they cannot resolve them.
6. **Verify the content hash.** Recompute `content_hash` over the JCS-canonicalized body (with the exclusion set from RFC-ACDP-0001 §5.7) and confirm it matches.
7. **Walk further references.** For each entry in `body.derived_from`, repeat from step 1 if the consumer needs the predecessor. Consumers MUST cap traversal depth (RECOMMENDED: 10) to bound work on hostile or accidentally-deep chains. ACDP's content-addressing forbids cycles in honest data (a body cannot reference its own future `ctx_id`), but consumers SHOULD detect cycles defensively (track visited `ctx_id`s within a single walk) and abort with a logged error if one is observed — its presence indicates a tampered body or a registry serving forged data.

### 4.2 Trust model

The trust split is critical:

- **Registry trust extends only to availability.** The serving registry can be untrusted, compromised, or adversarial — the consumer MUST NOT rely on it for context authenticity.
- **The producing agent's signature is the trust anchor.** A context produced by a trusted agent remains trustworthy even if served by an untrusted registry, because the agent signature is checkable end-to-end against the agent's DID document.

A consumer that finds a `derived_from` reference to a context on a registry it does not recognize SHOULD nonetheless attempt resolution; the producing agent's signature is the deciding factor.

### 4.3 Caching

Bodies are immutable. Consumers MAY cache fetched bodies indefinitely, keyed by `ctx_id` and validated by `content_hash`. Registry state (status) is mutable; consumers MUST NOT cache `registry_state.status` beyond the freshness window appropriate to their use case.

---

## 5. Failure Modes

| Failure | Behavior |
|---|---|
| Authority does not resolve in DNS | Treat the reference as unresolvable. The consumer SHOULD log this and proceed without the predecessor. |
| `/.well-known/acdp.json` returns non-200 | Treat as unresolvable. |
| `acdp_version` is unknown | Apply forward-compatibility (RFC-ACDP-0001 §6) — proceed with the operations the consumer understands. |
| Retrieval returns 404 | The reference is unresolvable. The consumer MUST NOT infer that the context never existed; only that it is not currently retrievable. |
| Signature verification fails | The retrieved body is **untrustworthy**. The consumer MUST NOT use it as evidence regardless of which registry served it. |
| Hash mismatch | Same as signature failure — body is corrupt. |
| Visibility-restricted (404 `not_found` returned indistinguishably) | The reference is not accessible to the consumer. The serving registry returns `not_found`; consumers cannot distinguish from a genuinely missing context. |

---

## 6. Out of Scope

The following are not specified by ACDP and are intentional non-goals (RFC-ACDP-0009 may revisit them):

- **Federation peering** between registries.
- **Cross-registry query forwarding** (search/discovery across registries from a single endpoint).
- **Cross-registry caching protocols** beyond plain HTTP caching.
- **Cross-registry supersession** (publishing a v2 on a different registry from v1). **Forbidden** in v0.0.1 — registries MUST reject with `superseded_target` (`details.reason = "cross_registry_supersession_unsupported"`). See RFC-ACDP-0003 §3.1 step 2 and the reservation in RFC-ACDP-0009 §2.8.
- **Server-side traversal** (`/walk`). Reserved in RFC-ACDP-0009.

Registries MAY implement these as private optimizations — but they are not part of the protocol.

---

## 7. Server-Side Request Forgery (SSRF) Protections

When a registry performs server-side resolution of `acdp://` references on behalf of a consumer (for example, when validating `derived_from` chains during a publish, or proxying retrievals), the registry initiates HTTP requests to authority hosts derived from user-supplied data. This is an SSRF vector.

Registries performing server-side `acdp://` resolution MUST implement the following defenses:

### 7.1 IP-range filtering

Resolve hostnames before connection and refuse to connect if any resolved IP is in:

- RFC 1918 private ranges: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- Loopback: `127.0.0.0/8`, `::1`
- Link-local: `169.254.0.0/16`, `fe80::/10`
- Multicast: `224.0.0.0/4`, `ff00::/8`
- The cloud-metadata endpoint: `169.254.169.254` (Google, AWS, Azure all use this)
- Any locally-defined "private" range relevant to the deployment (e.g. internal corporate networks).

Registries MUST refuse the resolution and MAY return `cross_registry_resolution_failed` (HTTP 502) to the requesting consumer.

### 7.2 HTTPS-only

Cross-registry calls MUST use `https://`. Plain HTTP, file://, ftp://, and other schemes MUST be refused without attempting connection.

### 7.3 Response-size caps

- Individual context retrievals (`GET /contexts/{ctx_id}`): MUST cap at 1 MB.
- Capabilities documents (`/.well-known/acdp.json`) and DID documents: MUST cap at 64 KB.

Exceeding either cap MUST cause the registry to abort the response and discard partial data. The cap MUST be enforced before any parse attempt to prevent memory-exhaustion attacks.

### 7.4 Timeouts

- Connection timeout: MUST NOT exceed 5 seconds.
- Total request timeout (including TLS handshake and response read): MUST NOT exceed 30 seconds.

Hung connections beyond these limits MUST be aborted.

### 7.5 Redirect handling

- HTTPS redirects MUST be capped at 3 follows.
- All redirect targets MUST be on the **same authority** as the original request. Cross-authority redirects MUST be rejected.

This prevents an attacker who controls a cooperating server from redirecting the registry to internal endpoints after passing the initial IP filter.

### 7.6 DNS rebinding protection

Registries MUST pin the resolved IP for the connection lifetime: a single DNS resolution per request, with the resolved IP used for both the IP-range filter check and the connection. A second resolution between filter check and connection (TOCTOU) MUST NOT be performed.

---

## 8. Security Considerations

See [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md). Specific to cross-registry resolution:

- The serving registry is **not** a trust anchor. Consumers MUST verify the producing agent's signature on every retrieved context.
- DNS resolution itself is not authenticated unless DNSSEC is in use. **The producer's signature is the actual trust anchor.** An attacker who can spoof DNS or compromise the registry still cannot forge a valid producer signature without the producer's private key.
- Public agent DIDs (`did:web`) are subject to DNS and HTTPS hijacking; consumers SHOULD pin or cache producer keys when feasible.
- A consumer following an `acdp://` reference is making an outbound HTTP request to a hostname controlled by an external party. Consumers operating in restrictive environments SHOULD apply egress policy.

---

## 9. References

- [RFC-ACDP-0001 Core](RFC-ACDP-0001-core.md)
- [RFC-ACDP-0004 Retrieval](RFC-ACDP-0004-retrieval.md)
- [RFC-ACDP-0007 Capabilities & Errors](RFC-ACDP-0007-capabilities.md)
- [RFC-ACDP-0008 Security](RFC-ACDP-0008-security.md)
- [DID-CORE] W3C, "Decentralized Identifiers (DIDs) v1.0".
- [RFC 1035] Mockapetris, P., "Domain names — implementation and specification".
