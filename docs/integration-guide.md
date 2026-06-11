# Integration Guide

How to integrate ACDP into a producer or consumer agent. This document is non-normative — the authoritative documents are the RFCs in [`rfcs/`](../rfcs/).

---

## What you need

- A DID for your agent (`did:web:agent.example`, `did:key:...`, etc.) and a published DID document with at least one verification key.
- An ed25519 signing key whose public component is in the DID document.
- A target registry's URL (discovered out-of-band per [discovery.md](discovery.md)).
- A JCS implementation in your language (see RFC-ACDP-0001 §5.2).

---

## Producer flow

### Step 1: Build the body

Construct the producer-supplied portion of the body — everything except the registry-assigned fields (`ctx_id`, `lineage_id`, `origin_registry`, `created_at`). For first versions, set `version: 1` and `supersedes: null`.

Set `acdp_version: "0.1.0"` explicitly. RFC-ACDP-0001 §6 RECOMMENDS that producers — and SDK builders, by default — emit `acdp_version` in every body: it is producer-signed and part of `content_hash`, and it removes any ambiguity about which exclusion set and algorithm vocabulary a verifier should apply. An absent field is interpreted as `"0.1.0"`, but absent and explicit `"0.1.0"` are distinct byte sequences and therefore distinct `content_hash` preimages — pick one and sign exactly what you emit.

```python
body = {
    "acdp_version": "0.1.0",
    "version": 1,
    "supersedes": None,
    "agent_id": "did:web:agent.example",
    "contributors": [],
    "title": "BTC Price Snapshot",
    "type": "data_snapshot",
    "domain": "financial_markets",
    "data_refs": [
        {
            "type": "primary_result",
            "location": "postgres://prices_db/snapshots?timestamp=2026-04-16T10:15:00Z",
            "description": "OHLCV data for BTC-USD",
        }
    ],
    "derived_from": [],
    "tags": ["bitcoin", "price"],
    "visibility": "public",
    "summary": "BTC: $43,250.67 (+2.3%), Volume: 15,423 BTC",
}
```

### Step 2: Compute content_hash

Canonicalize the body using JCS (RFC 8785), compute SHA-256, and prepend the `sha256:` algorithm prefix.

```python
import hashlib, jcs

# Body must NOT yet contain content_hash, signature, or any registry-assigned fields.
canonical = jcs.canonicalize(body)
hash_hex = hashlib.sha256(canonical).hexdigest()
content_hash = f"sha256:{hash_hex}"
body["content_hash"] = content_hash
```

The exclusion set (RFC-ACDP-0001 §5.7) is `content_hash`, `signature`, `ctx_id`, `lineage_id`, `origin_registry`, `created_at`. At this stage, the body contains none of these (you haven't set `content_hash` or `signature` yet, and the registry-assigned fields don't exist on the producer side), so the exclusion is implicit.

> **Python implementer note.** `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)` is JCS-conformant for most input shapes but fails on negative zero (preserves `-0.0` instead of emitting `0`). Use the `jcs` package on PyPI to be safe. See RFC-ACDP-0001 §5.2.

### Step 3: Sign

Sign the bytes of the **full `content_hash` string** — that is, the ASCII bytes of `sha256:` followed by the 64 hex chars. Producers MUST NOT sign the raw 32-byte digest, and MUST NOT sign the hex-only substring without the `sha256:` prefix.

```python
import base64

# private_key is an ed25519 private key (cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PrivateKey)
sig_bytes = private_key.sign(content_hash.encode("ascii"))

body["signature"] = {
    "algorithm": "ed25519",
    "key_id": "did:web:agents.example.com:my-agent#key-1",
    "value": base64.b64encode(sig_bytes).decode("ascii")
}
```

The `key_id` MUST be a DID URL whose DID portion equals `body.agent_id` — the registry will verify this binding (RFC-ACDP-0003 §2.1 step 6) and reject mismatches with `key_not_authorized`.

### Step 4: Publish

```python
import httpx

resp = httpx.post(
    "https://registry.example.com/contexts",
    json=body,
    headers={"Content-Type": "application/acdp+json"},
)
resp.raise_for_status()
result = resp.json()
# result has: ctx_id, lineage_id, version, created_at, status
```

---

## Consumer flow

### Step 1: Retrieve

```python
ctx_id = "acdp://registry.example.com/550e8400-e29b-41d4-a716-446655440000"
encoded = ctx_id.replace("/", "%2F")  # or use a registry's path-style alternate
resp = httpx.get(f"https://registry.example.com/contexts/{encoded}")
resp.raise_for_status()
context = resp.json()  # {"body": {...}, "registry_state": {"status": "active"}}
body = context["body"]
state = context["registry_state"]
```

### Step 2: Recompute content_hash

```python
import hashlib, jcs

# Strip the full exclusion set per RFC-ACDP-0001 §5.7 — including content_hash itself.
EXCLUDE = {"content_hash", "signature", "ctx_id", "lineage_id", "origin_registry", "created_at"}
producer_content = {k: v for k, v in body.items() if k not in EXCLUDE}

canonical = jcs.canonicalize(producer_content)
recomputed_hex = hashlib.sha256(canonical).hexdigest()
recomputed = f"sha256:{recomputed_hex}"

assert recomputed == body["content_hash"], "content_hash mismatch — body has been tampered"
```

### Step 3: Verify signature

```python
import base64

# resolve_did_key returns the producer's Ed25519 public key for the DID URL in signature.key_id.
producer_pubkey = resolve_did_key(body["signature"]["key_id"])

# The signature was made over the bytes of the full content_hash string.
sig_bytes = base64.b64decode(body["signature"]["value"])
producer_pubkey.verify(sig_bytes, body["content_hash"].encode("ascii"))
```

If `verify` raises, the body is not authentically from `agent_id`.

> **SSRF — DID resolution.** `signature.key_id` is producer-controlled, so `resolve_did_key` dereferences a `did:web` host taken verbatim from the body. The resolver MUST apply SSRF protection (RFC-ACDP-0008 §4.8): resolve the host, refuse if any resolved IP is in a private/loopback/link-local/IMDS range, pin the resolved IP for the connection, HTTPS-only, and cap redirects to the same authority. A URL-string check alone is **not** sufficient — DNS rebinding defeats it (RFC-ACDP-0006 §7.1). A producer DID that resolves to a forbidden target is treated as unverifiable.

Steps 1–3 are the **`StrictV010`** verification profile (RFC-ACDP-0001 §9.2, §5.11): schema validation → `content_hash` recomputation → `did:web` resolution → signature verification → embedded `data_ref.content_hash` checks, returning on the first failure. It is the only verification mode valid for an `acdp-consumer` conformance claim. SDKs MAY expose `Diagnostic` (records every stage) or `UnsafeForTests` (skips steps) modes, but neither may be the default and neither is conformant.

### Step 4: Use the context

At this point the body is verifiably authentic. Inspect `data_refs`, fetch any `location` references, check `data_period` against the use case, check `state["status"]` and `body.get("expires_at")` for currency.

> **SSRF — DataRef fetches.** `data_refs[].location` is producer-controlled. When a `location` is an `https://` URL and you dereference it, you are making an outbound request to a host the producer chose — apply the SSRF protections of RFC-ACDP-0008 §4.9 (HTTPS-only, DNS-level IP-range filtering on every resolved address, IP pinning against rebinding, same-authority redirect cap capped at 3 follows). A refused fetch does not invalidate the body — the producer signature and `content_hash` stay valid; only the external reference is unreachable on the SSRF-safe path. Non-HTTP schemes (`s3://`, `postgres://`, …) are dereferenced by their own clients under your deployment's egress policy. Access to the referenced data is governed by that system's own ACLs, not by ACDP `visibility` (RFC-ACDP-0002 §6.4).

---

## Walking lineage

```python
def walk_derived_from(body, depth=10):
    if depth == 0 or not body.get("derived_from"):
        return
    for ref_ctx_id in body["derived_from"]:
        # Parse acdp://<authority>/<uuid>
        authority = ref_ctx_id.split("//", 1)[1].split("/", 1)[0]
        # Fetch capabilities (ensure registry is reachable + advertises ACDP)
        caps = httpx.get(f"https://{authority}/.well-known/acdp.json").json()
        assert caps["acdp_version"], "not an ACDP registry"
        # Retrieve, verify, recurse
        encoded = ref_ctx_id.replace("/", "%2F")
        ref = httpx.get(f"https://{authority}/contexts/{encoded}").json()
        verify_body(ref["body"])  # Steps 2 & 3 above
        walk_derived_from(ref["body"], depth - 1)
```

The `depth` parameter is a defense against deep chains. Real `derived_from` chains are typically shallow (1–3 levels); set `depth` accordingly. A production walk also bounds total nodes, fanout, and wall-clock time per RFC-ACDP-0006 §4.1.

> **Cross-registry resolution is public-only in v0.1.0.** The walk above sends no caller credentials to the remote registry — ACDP v0.1.0 defines no bearer-token forwarding or token exchange across registries (RFC-ACDP-0006 §4.4). A `restricted`/`private` predecessor on another registry therefore returns `not_found` (HTTP 404), indistinguishable from a genuinely missing one. Handle a 404 in the walk as "unresolvable predecessor, proceed without it" — not as proof the context never existed. If you actually need a non-public context held on another registry, authenticate to *that* registry directly, out of band, using a read-authentication method from its `/.well-known/acdp.json`. Producers should likewise assume any `acdp://` reference to a non-public context is opaque to third-party consumers.

> **SSRF — cross-registry resolution.** The `authority` in the loop above comes from a producer-signed `acdp://` reference, so every `httpx.get` is an outbound request to a host an upstream producer chose. Cross-registry resolution MUST apply the SSRF protections of RFC-ACDP-0006 §7 — the same posture as DID resolution and DataRef fetches: HTTPS-only, DNS-level IP-range filtering on every resolved address, IP pinning, response-size caps (64 KB for capabilities/DID documents, 1 MB for context retrievals), bounded timeouts, and a same-authority redirect cap. The minimal example above omits these for brevity; a production resolver MUST NOT.

---

## Discovery

Polling lineage:

```python
# What has been built on my context?
my_ctx = "acdp://registry.example.com/my-published-analysis"
last_seen = "2026-04-16T12:00:00.000Z"

resp = httpx.get(
    "https://registry.example.com/contexts/search",
    params={"derived_from": my_ctx, "created_after": last_seen},
)
matches = resp.json()["matches"]
# Each match has ctx_id, agent_id, title, summary, etc. — fetch each one for the full body.
```

**Paginating correctly.** `next_cursor` is the *only* signal for "there are more results" — loop until it is absent, not until you see an empty page. Because the registry applies visibility scoping and other per-requester filters *after* reading a storage page, a page MAY come back with an empty `matches[]` and a non-empty `next_cursor` (the storage page held only rows you can't see); the next page may still carry visible results. Stopping on the first empty `matches[]` would silently truncate the result set (RFC-ACDP-0005 §2.3).

```python
def search_all(url, params):
    cursor = None
    while True:
        page = httpx.get(url, params={**params, **({"cursor": cursor} if cursor else {})}).json()
        yield from page["matches"]          # may be empty for this page
        cursor = page.get("next_cursor")
        if cursor is None:                  # absent next_cursor — and only that — ends the loop
            break
```

Semantic similarity is reserved for a future ACDP version (RFC-ACDP-0009 §2.9); v0.1.0 implementations expose keyword search only.

---

## Common errors

| Error code | Cause | Fix |
|---|---|---|
| `invalid_signature` | Signature didn't verify | Confirm you signed the bytes of the full `sha256:<hex>` string (not raw digest, not hex without prefix). Check `key_id` resolution and algorithm. |
| `hash_mismatch` | Body `content_hash` ≠ recomputed | JCS implementation differs. Run `schemas/conformance/can-001-jcs-vector.json`. Common cause: stdlib `json.dumps` not normalizing `-0.0`; use the `jcs` PyPI package. |
| `data_ref_hash_mismatch` | An embedded `data_ref.content_hash` ≠ the decoded `embedded.content` | Recompute the data-ref digest per the encoding (RFC-ACDP-0002 §6.3): `base64` → decoded bytes, `utf8` → UTF-8 bytes, `json` → JCS canonical bytes. DataRef-level failure — distinct from `hash_mismatch` (body-level) and `invalid_signature`. |
| `superseded_target` | Supersession constraints failed | Check `details.reason` — common values: `not_found`, `lineage_mismatch`, `version_mismatch`, `already_superseded`. |
| `unsupported_algorithm` | You used a non-ed25519 algorithm | Either use ed25519 or check the registry's `supported_signature_algorithms`. |
| `embedded_too_large` | Embedded data > 64 KB | Switch to `location` form. |

---

## See also

- [Architecture overview](architecture.md)
- [RFC-ACDP-0001 Core](../rfcs/RFC-ACDP-0001-core.md)
- [RFC-ACDP-0003 Publish](../rfcs/RFC-ACDP-0003-publish.md)
- [Examples](../examples/)
