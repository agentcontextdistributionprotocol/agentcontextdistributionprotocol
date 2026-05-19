# Initial Registry Discovery

This document is **non-normative**. ACDP does not define how a producer agent first learns the URL of a registry to publish to, nor how a consumer first learns the hostname of a registry to query. The protocol begins at the well-known URL (RFC-ACDP-0007 §3); everything before that is operational.

This document lists the patterns we have seen work, and a single recommendation: **whatever you choose, the producer signature is the trust root, not the registry hostname.** Initial discovery may be untrusted; cryptographic verification starts at the moment a body is fetched.

---

## What "discovery" means here

Two distinct questions are often conflated:

1. **Bootstrap discovery** — how does an agent learn that "Registry X" exists at `https://x.example.com`?
2. **Authentication of retrieved bodies** — how does the agent know the body it just received is authentic?

**ACDP only answers (2)** — through the producer's signature, the content hash, and the registry's published DID. (1) is left to deployment. The patterns below are how implementations have addressed (1).

---

## Pattern 1: Out-of-band configuration (RECOMMENDED for v0.1.0)

The simplest, most secure pattern for closed deployments.

```yaml
registries:
  primary:
    url: https://registry.agents.example.com
    expected_did: did:web:registry.agents.example.com
  partner_a:
    url: https://acdp.partner-a.example.com
    expected_did: did:web:acdp.partner-a.example.com
```

**Trust posture.** An operator-curated allowlist. The `expected_did` field lets the consumer reject a registry that has been served from the right hostname but with a different DID (compromised host).

**When to use.** Small ecosystems, regulated environments, anything where registries are explicitly partnered.

**Trade-offs.** Doesn't scale; every new registry requires configuration on every consumer.

---

## Pattern 2: DNS SRV record

The standard internet-protocol pattern. An organization publishes:

```
_acdp._tcp.example.com.   3600   IN   SRV   10 5 443 registry.example.com.
```

Consumers fetch `https://registry.example.com/.well-known/acdp.json` to confirm the registry's identity.

**Trust posture.** DNS resolution itself is not authenticated unless DNSSEC is in use. **Producer signatures are the actual trust anchors** — DNS just gets you to a hostname. An attacker who can spoof DNS still cannot forge a valid producer signature.

**When to use.** Public registry ecosystems where organizations publish their own registries; cross-organization interop.

**Trade-offs.** Requires DNS access. SRV records have spotty client-library support. Scales linearly.

---

## Pattern 3: Registry catalog

A directory service maintained by the ecosystem (or by an organization for its own registries). A consumer queries the catalog for "registries serving domain X" and gets back a list of `(did, url)` pairs.

**Trust posture.** The catalog is **not part of the trust path**. A consumer treats every catalog entry as untrusted until it has fetched and verified the corresponding `/.well-known/acdp.json`. A compromised catalog can introduce or hide registries but cannot impersonate one.

**When to use.** Larger ecosystems, domain-based routing, marketplaces.

**Trade-offs.** The catalog itself is operational complexity. It needs its own auth and consistency story.

---

## Pattern 4: Embedded references

Once an organization's first ACDP context appears in a downstream agent's evidence chain, the registry hostname is implicitly discovered: it is the authority component of the `acdp://` URI in `derived_from`.

**Trust posture.** Same as Pattern 2 — DNS gets the consumer to a hostname; producer signature is the trust anchor.

**When to use.** Late-stage networks where contexts are already flowing — discovery is emergent.

**Trade-offs.** Doesn't help bootstrap; depends on the network already existing.

---

## What does not change across patterns

In all four patterns, the moment a consumer has a candidate registry URL, the ACDP normative flow takes over (RFC-ACDP-0006 §4):

1. Fetch `/.well-known/acdp.json` over HTTPS (validate the TLS certificate).
2. Verify `acdp_version` is supported.
3. Cross-check `registry_did` against any pinned/expected value.
4. Issue retrievals; verify each body's signature against the producer's DID document.

If any of these fail, the candidate is rejected — regardless of how it was discovered. **Cryptographic verification is the trust boundary.**

---

## A recommendation

Pick **one** discovery pattern per deployment and stick with it. Mixing patterns inside a single ecosystem leads to inconsistent operational posture (some consumers have DID pinning, others don't; some go through DNSSEC, others don't). Consistency at the deployment layer makes incident response tractable.

For new deployments without an existing directory, start with Pattern 1 (out-of-band configuration). Move to Pattern 2 or 3 only when the operational cost of Pattern 1 exceeds the implementation cost of the alternative.

---

## See also

- [RFC-ACDP-0006 Cross-Registry References](../rfcs/RFC-ACDP-0006-cross-registry.md) — what discovery hands you off to.
- [RFC-ACDP-0007 Capabilities](../rfcs/RFC-ACDP-0007-capabilities.md) — the capabilities document and its caching.
- [RFC-ACDP-0008 Security](../rfcs/RFC-ACDP-0008-security.md) §3 (Threats addressed) and §6.2 (DNS spoof scenarios).
