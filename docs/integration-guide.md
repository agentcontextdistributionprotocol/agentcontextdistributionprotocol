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

Construct the producer-supplied portion of the body — everything except the registry-assigned fields (`ctx_id`, `origin_registry`, `created_at`). For first versions, set `version: 1` and `supersedes: null`.

```python
body = {
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

Apply JCS to the body, SHA-256 the canonical form, hex-encode lowercase.

```python
import hashlib, jcs

canonical = jcs.canonicalize(body)
content_hash = hashlib.sha256(canonical).hexdigest()
body["content_hash"] = content_hash
```

The exclusion set (RFC-ACDP-0001 §5.7) — `signature`, `ctx_id`, `lineage_id`, `origin_registry`, `created_at` — is implicit at this stage because the body does not yet contain those fields.

### Step 3: Sign

Sign the **bytes of the lowercase hex content_hash string** (not the raw hash bytes).

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import base64

sig_value = private_key.sign(content_hash.encode("ascii"))

body["signature"] = {
    "algorithm": "ed25519",
    "key_id": "did:web:agent.example#key-1",
    "value": base64.b64encode(sig_value).decode("ascii"),
}
```

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

# Strip registry-assigned and signature fields per RFC-ACDP-0001 §5.7
EXCLUDE = {"signature", "ctx_id", "lineage_id", "origin_registry", "created_at"}
hashable = {k: v for k, v in body.items() if k not in EXCLUDE}

canonical = jcs.canonicalize(hashable)
recomputed = hashlib.sha256(canonical).hexdigest()
assert recomputed == body["content_hash"], "content_hash mismatch — body has been tampered"
```

### Step 3: Verify signature

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
import base64

# Resolve producer's DID document. did:web is HTTPS-based.
# (The DID library or your own resolver returns the public key for body.signature.key_id.)
producer_pubkey = resolve_did_key(body["signature"]["key_id"])  # Ed25519PublicKey

sig_bytes = base64.b64decode(body["signature"]["value"])
producer_pubkey.verify(sig_bytes, body["content_hash"].encode("ascii"))
# raises on failure
```

### Step 4: Use the context

At this point the body is verifiably authentic. Inspect `data_refs`, fetch any `location` references (with their own access control), check `data_period` against the use case, check `state["status"]` and `body.get("expires_at")` for currency.

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

The `depth` parameter is a defense against deep chains. Real `derived_from` chains are typically shallow (1–3 levels); set `depth` accordingly.

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

Similarity (only on registries that index embeddings):

```python
resp = httpx.post(
    "https://registry.example.com/contexts/similar",
    json={
        "embedding": my_query_vector,
        "embedding_model": "text-embedding-3-large@2026-02",
        "top_k": 20,
        "filters": {"type": "analysis", "domain": "financial_markets"},
    },
)
```

If the registry returns 501 Not Implemented, fall back to keyword search.

---

## Common errors

| Error code | Cause | Fix |
|---|---|---|
| `invalid_signature` | Signature didn't verify | Check key_id, signing input (the hex string, not raw bytes), algorithm. |
| `hash_mismatch` | content_hash ≠ recomputed | JCS implementation differs. Run the canonicalization test vector (`schemas/conformance/can-001-jcs-vector.json`). |
| `superseded_target` | Supersession constraints failed | Check `details.reason` — common values: `not_found`, `lineage_mismatch`, `version_mismatch`, `already_superseded`. |
| `unsupported_algorithm` | You used a non-ed25519 algorithm | Either use ed25519 or check the registry's `supported_signature_algorithms`. |
| `embedded_too_large` | Embedded data > 64 KB | Switch to `location` form. |

---

## See also

- [Architecture overview](architecture.md)
- [RFC-ACDP-0001 Core](../rfcs/RFC-ACDP-0001-core.md)
- [RFC-ACDP-0003 Publish](../rfcs/RFC-ACDP-0003-publish.md)
- [Examples](../examples/)
