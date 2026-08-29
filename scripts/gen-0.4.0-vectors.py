#!/usr/bin/env python3
"""One-shot generator for the ACDP 0.4.0 golden-vector values (RFC-ACDP-0015).

Computes the canonical form, SHA-256 digest, and Ed25519 signature for the
transparency-log witness-cosignature conformance fixtures (wit-001, wit-003),
using the same libraries the conformance runner uses (jcs + cryptography) and a
DISTINCT witness test keypair (seed = 32 bytes of 0x33; a second witness uses
0x44 for the quorum vector). The cosignature signing construction is
RFC-ACDP-0010 §5 verbatim (JCS preimage minus 'signature' -> SHA-256 -> sign the
ASCII "sha256:<hex>" string), keyed by the WITNESS's own assertionMethod key
(RFC-ACDP-0015 §5). The thing cosigned is the log-001 golden checkpoint tuple, so
the vectors chain. Values are printed as JSON for transcription into the fixtures
— never hand-write them. Follows scripts/gen-0.3.0-vectors.py.
"""

import json
import hashlib
import base64

import jcs
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def ed25519_from_seed(seed_hex: str):
    priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex))
    pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return priv, pub


def signed_cosignature(priv, unsigned: dict) -> dict:
    canonical = jcs.canonicalize(unsigned)
    cosignature_hash = "sha256:" + sha256_hex(canonical)
    sig = priv.sign(cosignature_hash.encode("ascii"))
    return {
        "canonical_form": canonical.decode("utf-8"),
        "cosignature_hash": cosignature_hash,
        "signature_input": cosignature_hash,
        "signature_value_hex": sig.hex(),
        "signature_value_base64": base64.b64encode(sig).decode(),
    }


out = {}

# ── Witness A test key (TEST ONLY, seed = 32 bytes of 0x33) ───────────────────
wa_priv, wa_pub = ed25519_from_seed("33" * 32)
out["witness_a_key"] = {
    "private_seed_hex": "33" * 32,
    "public_key_hex": wa_pub.hex(),
    "public_key_base64": base64.b64encode(wa_pub).decode(),
}

# ── Witness B test key (TEST ONLY, seed = 32 bytes of 0x44 — quorum vector) ───
wb_priv, wb_pub = ed25519_from_seed("44" * 32)
out["witness_b_key"] = {
    "private_seed_hex": "44" * 32,
    "public_key_hex": wb_pub.hex(),
    "public_key_base64": base64.b64encode(wb_pub).decode(),
}

# The log-001 golden checkpoint tuple that is being cosigned (RFC-ACDP-0012 §6).
witnessed_checkpoint = {
    "log_id": "did:web:registry.example.com/log/1",
    "tree_size": 5,
    "root_hash": "sha256:0b5978172c671ca050b44790a749b18fc29d58a7a17495fbb4e0f86eb885f731",
    "timestamp": "2026-07-04T12:00:00.000Z",
}

# ── wit-001: witness A cosigns the log-001 checkpoint ─────────────────────────
cosig_a_unsigned = {
    "cosignature_version": "acdp-cosig/1",
    "witness_id": "did:web:witness.example.org",
    "witnessed_checkpoint": witnessed_checkpoint,
    "witnessed_at": "2026-07-04T12:00:05.000Z",
}
out["wit_001"] = signed_cosignature(wa_priv, cosig_a_unsigned)

# ── wit-003: a SECOND, distinct witness cosigns the SAME checkpoint tuple ──────
# Vector A is byte-identical to wit-001 (witness A); vector B is witness B.
cosig_b_unsigned = {
    "cosignature_version": "acdp-cosig/1",
    "witness_id": "did:web:witness-2.example.org",
    "witnessed_checkpoint": witnessed_checkpoint,
    "witnessed_at": "2026-07-04T12:03:00.000Z",
}
out["wit_003_witness_b"] = signed_cosignature(wb_priv, cosig_b_unsigned)

# ── wit-004 helper: the CORRECT signature for the cosignature body, so the
#    fixture's tampered signature (a re-used/wrong-key value) is demonstrably
#    NOT this value. The behavioral fixture pins a cosignature whose signature
#    was produced by the WRONG key (witness B's key over witness A's body). ────
out["wit_004_wrong_key_signature"] = signed_cosignature(wb_priv, cosig_a_unsigned)

print(json.dumps(out, indent=2, ensure_ascii=False))
