#!/usr/bin/env python3
"""One-shot generator for the ACDP 0.2.0 golden-vector values.

Computes every canonical form, SHA-256 digest, key fingerprint, signature,
and did:key identity needed by the new conformance fixtures, using the same
libraries the conformance runner uses (jcs + cryptography). Values are
printed as JSON for transcription into the fixtures — never hand-write them.
"""

import json
import hashlib
import base64

import jcs
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58encode(data: bytes) -> str:
    n = int.from_bytes(data, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = B58_ALPHABET[r] + out
    # leading zero bytes -> leading '1's
    pad = 0
    for b in data:
        if b == 0:
            pad += 1
        else:
            break
    return "1" * pad + out


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fingerprint(raw_key_bytes: bytes) -> str:
    return "sha256:" + sha256_hex(raw_key_bytes)


def canon(obj):
    return jcs.canonicalize(obj)


def content_hash(obj) -> str:
    return "sha256:" + sha256_hex(canon(obj))


def ed25519_from_seed(seed_hex: str):
    priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex))
    pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return priv, pub


out = {}

# ── sig-001 producer key (existing golden) ───────────────────────────────────
producer_priv, producer_pub = ed25519_from_seed("00" * 32)
assert producer_pub.hex() == "3b6a27bcceb6a42d62a3a8d02a6f0d73653215771de243a63ac048a18b59da29"
out["producer_key_fingerprint"] = fingerprint(producer_pub)

# ── P-256 sig-002 key (scalar = 1 → generator point), compressed SEC1 ───────
p256_priv = ec.derive_private_key(1, ec.SECP256R1())
p256_pub = p256_priv.public_key()
compressed = p256_pub.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.CompressedPoint,
)
nums = p256_pub.public_numbers()
out["p256"] = {
    "x_hex": format(nums.x, "064x"),
    "y_hex": format(nums.y, "064x"),
    "compressed_sec1_hex": compressed.hex(),
    "fingerprint": fingerprint(compressed),
}

# ── Registry receipt key (TEST ONLY, seed = 32 bytes of 0x11) ────────────────
reg_priv, reg_pub = ed25519_from_seed("11" * 32)
out["registry_receipt_key"] = {
    "private_seed_hex": "11" * 32,
    "public_key_hex": reg_pub.hex(),
    "public_key_base64": base64.b64encode(reg_pub).decode(),
    "fingerprint": fingerprint(reg_pub),
}

# ── rcpt-001: receipt over the sig-001 golden context ────────────────────────
receipt_unsigned = {
    "registry_did": "did:web:registry.example.com",
    "ctx_id": "acdp://registry.example.com/12345678-1234-4321-8123-123456781234",
    "lineage_id": "lin:sha256:c7fef01c000f8edaa9cb46122ceb5d7bca38328f002fb0f40e362e3b289bbb2a",
    "origin_registry": "registry.example.com",
    "created_at": "2026-04-16T10:30:15.123Z",
    "content_hash": "sha256:f170150ddbf59d99794e7797824591b374d459782084597b644ecc57a41031b5",
    "key_fingerprint": out["producer_key_fingerprint"],
}
receipt_canonical = canon(receipt_unsigned)
receipt_hash = "sha256:" + sha256_hex(receipt_canonical)
receipt_sig = reg_priv.sign(receipt_hash.encode("ascii"))
out["rcpt_001"] = {
    "canonical_form": receipt_canonical.decode("utf-8"),
    "receipt_hash": receipt_hash,
    "signature_value_hex": receipt_sig.hex(),
    "signature_value_base64": base64.b64encode(receipt_sig).decode(),
}
# tampered created_at variant for rcpt-002
tampered = dict(receipt_unsigned, created_at="2026-04-15T10:30:15.123Z")
out["rcpt_002_tampered"] = {
    "canonical_form": canon(tampered).decode("utf-8"),
    "receipt_hash": "sha256:" + sha256_hex(canon(tampered)),
}

# ── sig-003: did:key golden (ed25519 seed = 32 bytes of 0x42) ────────────────
dk_priv, dk_pub = ed25519_from_seed("42" * 32)
multicodec = bytes([0xED, 0x01]) + dk_pub
mb = "z" + b58encode(multicodec)
did_key = "did:key:" + mb
sig003_content = {
    "version": 1,
    "supersedes": None,
    "agent_id": did_key,
    "contributors": [],
    "title": "Golden test vector — did:key first version",
    "type": "data_snapshot",
    "data_refs": [],
    "derived_from": [],
    "visibility": "public",
    "acdp_version": "0.2.0",
}
sig003_canonical = canon(sig003_content)
sig003_hash = "sha256:" + sha256_hex(sig003_canonical)
sig003_sig = dk_priv.sign(sig003_hash.encode("ascii"))
out["sig_003"] = {
    "private_seed_hex": "42" * 32,
    "public_key_hex": dk_pub.hex(),
    "public_key_base64": base64.b64encode(dk_pub).decode(),
    "did_key": did_key,
    "key_id": did_key + "#" + mb,
    "fingerprint": fingerprint(dk_pub),
    "canonical_form": sig003_canonical.decode("utf-8"),
    "content_hash": sig003_hash,
    "signature_value_hex": sig003_sig.hex(),
    "signature_value_base64": base64.b64encode(sig003_sig).decode(),
}

# ── can-012: divergence corpus vectors ───────────────────────────────────────
base = {
    "version": 1,
    "supersedes": None,
    "agent_id": "did:agent:test",
    "contributors": [],
    "title": "Divergence corpus vector",
    "type": "data_snapshot",
    "data_refs": [],
    "derived_from": [],
    "visibility": "public",
}


def vec(obj):
    c = canon(obj)
    return {"canonical_form": c.decode("utf-8"), "sha256_hex": sha256_hex(c)}


out["can_012"] = {
    "omitted": vec(base),
    "explicit_010": vec(dict(base, acdp_version="0.1.0")),
    "explicit_020": vec(dict(base, acdp_version="0.2.0")),
    "microsecond_ts": vec(dict(base, expires_at="2026-04-16T10:30:15.123456Z")),
    "millisecond_ts": vec(dict(base, expires_at="2026-04-16T10:30:15.123Z")),
    "metadata_empty": vec(dict(base, metadata={})),
    "metadata_null_member": vec(dict(base, metadata={"note": None})),
}

print(json.dumps(out, indent=2, ensure_ascii=False))
