#!/usr/bin/env python3
"""
ACDP conformance runner.

Reads every fixture under schemas/conformance/ and verifies arithmetic claims:
  - can-* fixtures: JCS canonicalization + SHA-256 + lineage_id derivation
  - sig-* fixtures: full Ed25519 sign/verify cycle, full content_hash computation

Exits 0 if all vectors pass, 1 otherwise.

Requires: pip install jcs cryptography
(jcs handles JCS canonicalization including the -0.0 normalization that stdlib json.dumps misses.)
"""

import json
import hashlib
import sys
import base64
from pathlib import Path

try:
    import jcs
except ImportError:
    print("ERROR: pip install jcs", file=sys.stderr)
    sys.exit(2)

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("ERROR: pip install cryptography", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
CONFORMANCE = ROOT / "schemas" / "conformance"

failures = []
passes = 0


def fail(fixture, vector_name, msg):
    failures.append(f"{fixture} :: {vector_name}: {msg}")


def check_canonicalization_and_hash(fixture, vector):
    name = vector.get("name", "?")
    inp = vector.get("input", {})
    exp = vector.get("expected", {})

    try:
        canonical_bytes = jcs.canonicalize(inp)
    except Exception as e:
        fail(fixture, name, f"JCS canonicalization raised: {e}")
        return False
    canonical = canonical_bytes.decode("utf-8")

    if "canonical_form" in exp:
        if canonical != exp["canonical_form"]:
            fail(fixture, name, f"canonical_form mismatch.\n    expected: {exp['canonical_form']}\n    actual:   {canonical}")
            return False

    if "sha256_hex" in exp:
        actual = hashlib.sha256(canonical_bytes).hexdigest()
        if actual != exp["sha256_hex"]:
            fail(fixture, name, f"sha256_hex mismatch. expected={exp['sha256_hex']} actual={actual}")
            return False
        if "content_hash_field_value" in exp:
            expected_field = f"sha256:{exp['sha256_hex']}"
            if exp["content_hash_field_value"] != expected_field:
                fail(fixture, name, "content_hash_field_value mismatch")
                return False

    if "lineage_id" in exp:
        ctx_id = inp.get("ctx_id", "")
        actual = "lin:sha256:" + hashlib.sha256(ctx_id.encode("utf-8")).hexdigest()
        if actual != exp["lineage_id"]:
            fail(fixture, name, f"lineage_id mismatch. expected={exp['lineage_id']} actual={actual}")
            return False

    return True


def check_signature_vector(fixture, fixture_data, vector):
    name = vector.get("name", "?")
    keypair = fixture_data.get("test_keypair", {})
    seed_hex = keypair.get("private_seed_hex", "")
    if not seed_hex:
        fail(fixture, name, "missing test_keypair.private_seed_hex")
        return False

    try:
        seed = bytes.fromhex(seed_hex)
        priv = Ed25519PrivateKey.from_private_bytes(seed)
        pub = priv.public_key()
        pub_raw = pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    except Exception as e:
        fail(fixture, name, f"keypair load failed: {e}")
        return False

    declared_pub_hex = keypair.get("public_key_hex", "")
    if declared_pub_hex and pub_raw.hex() != declared_pub_hex:
        fail(fixture, name, f"public_key_hex mismatch. declared={declared_pub_hex} derived={pub_raw.hex()}")
        return False

    producer_content = vector.get("producer_content", {})
    exp = vector.get("expected", {})

    canonical_bytes = jcs.canonicalize(producer_content)
    canonical = canonical_bytes.decode("utf-8")
    if "canonical_form" in exp and canonical != exp["canonical_form"]:
        fail(fixture, name, f"canonical_form mismatch.\n    expected: {exp['canonical_form']}\n    actual:   {canonical}")
        return False

    hash_hex = hashlib.sha256(canonical_bytes).hexdigest()
    content_hash = f"sha256:{hash_hex}"
    if "content_hash" in exp and content_hash != exp["content_hash"]:
        fail(fixture, name, f"content_hash mismatch. expected={exp['content_hash']} actual={content_hash}")
        return False

    sig_bytes = priv.sign(content_hash.encode("ascii"))
    sig_hex = sig_bytes.hex()
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")
    if "signature_value_hex" in exp and sig_hex != exp["signature_value_hex"]:
        fail(fixture, name, f"signature_value_hex mismatch. expected={exp['signature_value_hex']} actual={sig_hex}")
        return False
    if "signature_value_base64" in exp and sig_b64 != exp["signature_value_base64"]:
        fail(fixture, name, "signature_value_base64 mismatch")
        return False

    try:
        pub.verify(sig_bytes, content_hash.encode("ascii"))
    except Exception as e:
        fail(fixture, name, f"signature verification failed: {e}")
        return False

    reg = vector.get("registry_assigned", {})
    if "ctx_id" in reg and "lineage_id" in reg:
        derived = "lin:sha256:" + hashlib.sha256(reg["ctx_id"].encode("utf-8")).hexdigest()
        if derived != reg["lineage_id"]:
            fail(fixture, name, f"lineage_id mismatch. expected={reg['lineage_id']} actual={derived}")
            return False

    return True


for path in sorted(CONFORMANCE.glob("*.json")):
    with open(path) as f:
        data = json.load(f)
    fixture_id = data.get("id", path.stem)

    if fixture_id.startswith("can-"):
        for v in data.get("vectors", []):
            if check_canonicalization_and_hash(fixture_id, v):
                passes += 1
    elif fixture_id.startswith("sig-"):
        for v in data.get("vectors", []):
            if check_signature_vector(fixture_id, data, v):
                passes += 1
    # pub-, vis-, ret- fixtures describe scenarios (request → expected error code), not arithmetic
    # vectors. Their conformance is checked by registry implementations, not by this static runner.

if failures:
    print(f"\n✗ {len(failures)} conformance failure(s):", file=sys.stderr)
    for f in failures:
        print(f"  {f}", file=sys.stderr)
    print(f"\nPassed: {passes}\nFailed: {len(failures)}", file=sys.stderr)
    sys.exit(1)
else:
    print(f"✓ All {passes} arithmetic conformance vectors passed.")
    sys.exit(0)
