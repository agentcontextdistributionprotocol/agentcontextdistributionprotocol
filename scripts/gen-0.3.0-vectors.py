#!/usr/bin/env python3
"""One-shot generator for the ACDP 0.3.0 golden-vector values (RFC-ACDP-0011).

Computes the canonical form, SHA-256 digest, and Ed25519 signature for the
lineage-head-receipt conformance fixtures (lhr-001..004), using the same
libraries the conformance runner uses (jcs + cryptography) and the same
registry test keypair as rcpt-001 (RFC-ACDP-0011 §5 reuses the RFC-ACDP-0010
receipt signing key and construction verbatim). Values are printed as JSON
for transcription into the fixtures — never hand-write them.

Follows the approach of scripts/gen-0.2.0-vectors.py.
"""

import json
import hashlib
import base64

import jcs
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canon(obj):
    return jcs.canonicalize(obj)


def ed25519_from_seed(seed_hex: str):
    priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex))
    pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return priv, pub


def signed_vector(priv, unsigned: dict) -> dict:
    canonical = canon(unsigned)
    receipt_hash = "sha256:" + sha256_hex(canonical)
    sig = priv.sign(receipt_hash.encode("ascii"))
    return {
        "canonical_form": canonical.decode("utf-8"),
        "receipt_hash": receipt_hash,
        "signature_value_hex": sig.hex(),
        "signature_value_base64": base64.b64encode(sig).decode(),
    }


out = {}

# ── Registry receipt key (TEST ONLY, seed = 32 bytes of 0x11 — same as rcpt-001;
#    RFC-ACDP-0011 §5/§9 requires the head receipt to use the SAME signing key
#    and DID plumbing as RFC-ACDP-0010 receipts) ────────────────────────────────
reg_priv, reg_pub = ed25519_from_seed("11" * 32)
assert reg_pub.hex() == "d04ab232742bb4ab3a1368bd4615e4e6d0224ab71a016baf8520a332c9778737"
out["registry_receipt_key"] = {
    "private_seed_hex": "11" * 32,
    "public_key_hex": reg_pub.hex(),
    "public_key_base64": base64.b64encode(reg_pub).decode(),
}

# ── lhr-001: lineage-head receipt over the sig-001 golden lineage ─────────────
# The sig-001 golden context is version 1 and the only version of its lineage,
# so it is the head; head_status is "active".
lhr_unsigned = {
    "receipt_version": "acdp-lhr/1",
    "registry_did": "did:web:registry.example.com",
    "lineage_id": "lin:sha256:c7fef01c000f8edaa9cb46122ceb5d7bca38328f002fb0f40e362e3b289bbb2a",
    "head_ctx_id": "acdp://registry.example.com/12345678-1234-4321-8123-123456781234",
    "head_version": 1,
    "head_status": "active",
    "as_of": "2026-07-04T09:00:00.000Z",
}
out["lhr_001"] = signed_vector(reg_priv, lhr_unsigned)

# Sanity: the lineage derivation still holds for a version-1 head.
derived = "lin:sha256:" + sha256_hex(lhr_unsigned["head_ctx_id"].encode("utf-8"))
assert derived == lhr_unsigned["lineage_id"]

# ── lhr-002: the same receipt is later replayed against a lineage whose head
#    has moved to v2. The receipt itself is the valid lhr-001 receipt; the
#    fixture pins the served-response mismatch. Nothing new to sign — but pin
#    the v2 head the serving response carries so the fixture is concrete. ─────
out["lhr_002_served_head"] = {
    "head_ctx_id": "acdp://registry.example.com/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "head_version": 2,
    "head_status": "active",
}

# ── lhr-004: validly signed receipt whose as_of is far in the future — the
#    signature MUST verify (the failure is the as_of check, not the crypto). ──
lhr_future = dict(lhr_unsigned, as_of="2036-01-01T00:00:00.000Z")
out["lhr_004_future_as_of"] = dict(signed_vector(reg_priv, lhr_future), as_of=lhr_future["as_of"])

print(json.dumps(out, indent=2, ensure_ascii=False))
