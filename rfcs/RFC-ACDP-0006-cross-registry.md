# RFC-ACDP-0006
# Agent Context Description Protocol (ACDP) — Cross-Registry References

**Document:** RFC-ACDP-0006
**Version:** 0.1.0
**Status:** Community Standards Track (Final)

This RFC specifies how consumers resolve `acdp://` references that point to contexts on a different registry. It depends on RFC-ACDP-0001 (Core) and RFC-ACDP-0007 (Capabilities).

---

## 1. Status of This Memo

This document is a Final ACDP specification (acdp/0.1.0). It is stable for the 0.1.0 release; subsequent breaking changes require a new RFC and a version bump per [VERSIONING.md](../VERSIONING.md).

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

### 3.1 What registry DID authenticates

The registry's DID identifies the registry **endpoint**, not the content it serves. Verifying the registry DID confirms "this `https://<authority>/.well-known/acdp.json` is operated by `did:web:<authority>`" — i.e., that you are talking to who you think. It does NOT prove that the content the registry serves is authentic — that requires the producer signature on the body.

In short:

- **Registry DID:** "you are talking to the right server."
- **Producer signature (RFC-ACDP-0001 §5.8):** "this body is from the right producer."

Both are required to trust an ACDP context end-to-end. RFC-ACDP-0008 §9.1 details what the producer signature does and does not bind, including the v0.1.0 limitation that registry-assigned identifiers (`ctx_id`, `lineage_id`, `origin_registry`, `created_at`) are not cryptographically bound by the producer signature.

---

## 4. Resolution

When a consumer encounters an `acdp://other-registry.example/uuid` reference and wishes to retrieve it, resolution proceeds:

### 4.1 Steps

1. **Parse the URI.** Extract `<authority>` and the UUID. Reject URIs that do not match the syntax in RFC-ACDP-0001 §5.4.
2. **Resolve the registry.** Construct the registry's well-known URL: `https://<authority>/.well-known/acdp.json`. Fetch and parse. Verify `acdp_version`, `registry_did`, `supported_signature_algorithms`.
3. **Verify the registry's DID.** Resolve `registry_did` and verify the DID document's web binding matches `<authority>`. This is REQUIRED for `acdp-registry-federated` profile conformance (RFC-ACDP-0001 §9.1) and RECOMMENDED for any consumer doing cross-registry resolution. On mismatch, treat the resolution as failed. Operators of consumer deployments SHOULD additionally pin the `registry_did` they expect for each upstream they rely on (defense against an attacker who controls DNS for the authority but not the original registry's DID document).
4. **Issue retrieval.** `GET https://<authority>/contexts/{encoded_ctx_id}` per RFC-ACDP-0004 §2.
5. **Verify the body's signature.** Resolve the producing agent's signing key per RFC-ACDP-0001 §5.11, then verify `body.signature.value` against `body.content_hash`. v0.1.0 producers MUST use `did:web` (RFC-ACDP-0001 §5.4); consumers encountering other DID methods MAY surface this to higher layers as `key_resolution_failed`-equivalent if they cannot resolve them.
6. **Verify the content hash.** Recompute `content_hash` over the JCS-canonicalized body (with the exclusion set from RFC-ACDP-0001 §5.7) and confirm it matches.
7. **Walk further references.** For each entry in `body.derived_from`, repeat from step 1 if the consumer needs the predecessor. ACDP's content-addressing forbids cycles in honest data (a body cannot reference its own future `ctx_id`), but consumers SHOULD detect cycles defensively (track visited `ctx_id`s within a single walk) and abort with a logged error if one is observed — its presence indicates a tampered body or a registry serving forged data.

   Implementations MUST apply the following traversal controls to bound work on hostile or accidentally-deep DAGs. The schema permits `derived_from.maxItems = 1000`, so a naïve walk that follows only depth limits can still traverse millions of nodes in a wide graph; the per-axis controls below are NORMATIVE:

   | Control | Default (RECOMMENDED) | Behavior on overrun |
   |---|---|---|
   | **Max depth** | 10 | Stop traversal at the depth limit; surface partial results to higher layers along with a `cross_registry_resolution_failed` indication for the unwalked subtree. |
   | **Max total nodes** | 500 | Abort the entire walk with `cross_registry_resolution_failed` (HTTP 502 if surfaced via a registry endpoint; consumer-side: surface an equivalent typed error). |
   | **Max fanout per context** | 100 | Skip or refuse the offending context's `derived_from` array; prefer aborting (`cross_registry_resolution_failed`) over silently truncating, because partial fanout produces non-deterministic walk outputs that mislead downstream evidence assembly. |
   | **Total walk timeout** | 30 seconds | Abort with `cross_registry_resolution_failed`. The timeout is end-to-end across the walk (not per-fetch); per-fetch timeouts are governed separately by §7.4. |

   All four controls MUST be configurable. Operators in trusted environments MAY raise the defaults (e.g., for a knowledge-graph indexer with internal-only inputs); operators handling untrusted inputs SHOULD lower them. Implementations SHOULD cache resolved capabilities documents and DID documents per-authority within a single walk to avoid redundant network calls; this caching is intra-walk only and MUST NOT extend across walks unless governed by the §4.3 caching rules.

   Consumers MUST cap traversal depth at the configured limit even when the depth limit alone is sufficient to keep node count bounded; the per-axis controls are joined by AND, not OR. A walk MUST stop at the first limit it hits.

### 4.2 Trust model

The trust split is critical:

- **Registry trust extends only to availability.** The serving registry can be untrusted, compromised, or adversarial — the consumer MUST NOT rely on it for context authenticity.
- **The producing agent's signature is the trust anchor.** A context produced by a trusted agent remains trustworthy even if served by an untrusted registry, because the agent signature is checkable end-to-end against the agent's DID document.

A consumer that finds a `derived_from` reference to a context on a registry it does not recognize SHOULD nonetheless attempt resolution; the producing agent's signature is the deciding factor.

### 4.2.1 Capabilities caching

Consumers resolving cross-registry references SHOULD cache the fetched `/.well-known/acdp.json` capabilities document per authority. Caching reduces redundant network traffic, latency, and dependency on the upstream registry's availability. The cache TTL is governed by the following rules:

1. **Honor `Cache-Control: max-age=N` from the capabilities response.** If the HTTP response carries a `Cache-Control` header with a `max-age` directive, consumers SHOULD cache for `min(N, 3600)` seconds. The 3600-second upper bound is the absolute ceiling regardless of the value the registry signals — capabilities can change (e.g. when a registry adds or removes profiles, rotates `registry_did`, or updates `supported_signature_algorithms`) and a stale value beyond an hour creates a meaningful divergence window.
2. **Default TTL when no header is present.** If no `Cache-Control: max-age` directive is present (or the response does not carry a `Cache-Control` header at all), consumers SHOULD apply a default TTL of 300 seconds.
3. **Absolute ceiling.** Consumers MUST NOT apply a TTL longer than 3600 seconds without a fresh fetch, even if the response signals a longer max-age. Registries advertising `Cache-Control: max-age=86400` will be honored at most for one hour by conformant consumers.
4. **Re-fetch on validation failure.** Consumers that observe a `validate_capabilities` failure on a cached document (per RFC-ACDP-0007 §3.5 — schema violation, missing `registry_did`, etc.) SHOULD immediately bypass the cache and re-fetch before surfacing the error to higher layers. The most common cause of an in-cache `validate_capabilities` failure is a registry that updated its capabilities document mid-window.
5. **Stale-while-revalidate is OPTIONAL.** Consumers MAY serve a stale cached entry to the application path while asynchronously re-fetching, provided the staleness window does not exceed the ceiling in rule 3. This is a consumer-side optimization; registries cannot rely on it.

Registries SHOULD emit `Cache-Control: max-age=300` or higher on `/.well-known/acdp.json` responses. Registries with rapidly-changing capabilities (e.g. during a feature rollout) MAY emit shorter values; registries operating with a stable capability surface MAY emit values up to the consumer ceiling.

This caching guidance applies to the capabilities document only. DID document caching is governed separately by RFC-ACDP-0001 §5.11 ("Caching" paragraph). Body caching is governed by §4.3 below.

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
- **Cross-registry supersession** (publishing a v2 on a different registry from v1). **Forbidden** in v0.1.0 — registries MUST reject with `superseded_target` (`details.reason = "cross_registry_supersession_unsupported"`). See RFC-ACDP-0003 §3.1 step 2 and the reservation in RFC-ACDP-0009 §2.8.
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

**DNS-level protection is required.** URL host-syntax checks — verifying that the raw hostname string does not look like a private IP literal — are necessary but **insufficient**. A conformant implementation MUST also:

1. Resolve the hostname to one or more IP addresses.
2. Validate that EVERY resolved address is in an allowed range (no answer in the disallowed ranges above; an attacker MUST NOT be able to bypass the filter by mixing one public and one private answer in a single DNS response).
3. Connect only to the validated address(es), and not re-resolve at connect time (see §7.6).

Acceptable approaches:

- Install a custom DNS resolver in the HTTP client that **rejects the whole resolution** if any returned address is disallowed (e.g. a `reqwest` `dns_resolver` hook, a `SafeDnsResolver`, or a custom `Resolver` trait implementation). The resolver MUST fail — not return a filtered subset (see "Mixed-answer rejection" below).
- Resolve before constructing the HTTP client and pin the resolved IP via the HTTP client's `resolve()` / `connect_to()` API.

Unacceptable approach (NOT conformant):

- Call a URL-syntax SSRF check on the reference string, then use a standard HTTP client that resolves DNS normally at connect time. This is vulnerable to DNS rebinding and split-horizon DNS — a hostname can pass a string check yet resolve to a private address. The IP-range filter and the connection MUST consume the **same** DNS resolution.

**Mixed-answer rejection (NORMATIVE).** If DNS resolution for a hostname returns multiple IP addresses and **any** of them is in a forbidden range (loopback, private, link-local, multicast, IMDS, unspecified, documentation-range where disallowed by local policy), the implementation MUST reject the **entire** resolution for that hostname.

Implementations MUST NOT silently filter out the forbidden addresses and connect to the remaining safe addresses. Partial filtering defeats the SSRF defense: an attacker controlling both a public IP and a private target can return both addresses, causing a filter-based implementation to proceed to the private target on a retry, a connection-pool reconnect, or a TOCTOU second resolution. The IP-range filter is all-or-nothing per hostname.

**Non-conformant behavior (explicitly disallowed):**

```
resolve("attacker.example")  → ["203.0.113.10", "10.0.0.1"]
filter to safe:              → ["203.0.113.10"]
connect to:                  → 203.0.113.10  ← WRONG: should reject entirely
```

**Required behavior:**

```
resolve("attacker.example")  → ["203.0.113.10", "10.0.0.1"]
validate all:                → 10.0.0.1 is forbidden → reject resolution
result:                      → error, no connection made
```

The `fed-007` conformance fixture pins mixed-answer rejection for cross-registry resolution; `did-ssrf-004` and `data-ref-ssrf-004` pin it for producer DID resolution and DataRef location fetches respectively.

This requirement — including mixed-answer rejection — applies identically to producer DID resolution (RFC-ACDP-0008 §4.8) and DataRef location fetches (RFC-ACDP-0008 §4.9).

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

**Same-authority definition (NORMATIVE).** For the purpose of redirect enforcement in this specification, two URLs share the same authority if and only if all three of the following match:

1. **Scheme** — both use `https://` (HTTP is not permitted regardless — §7.2).
2. **Host** — the hostname or IP literal is identical (case-insensitive per [RFC 3986]).
3. **Effective port** — the port after applying the scheme default (443 for `https`, 80 for `http`) is identical. An explicit `:443` on an `https://` URL is the same effective port as the implicit default; `:8443` is not.

Examples:

| From | To | Authority match? |
|---|---|---|
| `https://a.example/x` | `https://a.example/y` | ✅ Yes |
| `https://a.example/x` | `https://a.example:443/y` | ✅ Yes (same effective port) |
| `https://a.example/x` | `https://a.example:8443/y` | ❌ No (different port) |
| `https://a.example/x` | `http://a.example/y` | ❌ No (scheme change) |
| `https://a.example/x` | `https://b.example/y` | ❌ No (different host) |

A host-only comparison is **non-conformant**: it would follow a redirect to a different port on the same host, crossing a service boundary the attacker may not control on the original port. Implementations MUST compare the full (scheme, host, effective port) triple.

This definition applies identically to all three producer-controlled outbound fetch contexts: cross-registry resolution (§7.5), producer DID resolution (RFC-ACDP-0008 §4.8), and DataRef location fetches (RFC-ACDP-0008 §4.9). The `fed-008` conformance fixture pins same-host-different-port redirect rejection for cross-registry resolution; `did-ssrf-005` and `data-ref-ssrf-005` pin it for the other two contexts.

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
- [RFC 3986] Berners-Lee, T., Fielding, R., and L. Masinter, "Uniform Resource Identifier (URI): Generic Syntax".
