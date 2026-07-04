#!/usr/bin/env python3
"""
ACDP conformance runner.

Reads every fixture under schemas/conformance/ and verifies arithmetic claims:
  - can-* fixtures: JCS canonicalization + SHA-256 + lineage_id derivation
  - lin-* fixtures: lineage_id derivation golden vectors
  - sig-* fixtures: full Ed25519 / ECDSA-P256 sign/verify cycle, full content_hash
    computation, and (for did:key fixtures) pure did:key identity derivation
  - rcpt-* fixtures carrying a registry_test_keypair: full receipt golden cycle
    (preimage, receipt hash, signature, producer key_fingerprint) per RFC-ACDP-0010
  - lhr-* fixtures carrying a registry_test_keypair: full lineage-head-receipt
    golden cycle (preimage, receipt hash, signature, binding consistency) per
    RFC-ACDP-0011
  - fp-* fixtures: key-fingerprint encoding vectors (RFC-ACDP-0010 §6)

Behavioral fixtures (pub-*, vis-*, dk-*, rcpt-002..004, lhr-002..004, rot-*,
fed-*, …) are not executed; they describe request/response scenarios for live
implementations.

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
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import (
        decode_dss_signature,
        encode_dss_signature,
    )
    from cryptography.hazmat.primitives import hashes, serialization
except ImportError:
    print("ERROR: pip install cryptography", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
CONFORMANCE = ROOT / "schemas" / "conformance"

failures = []
passes = 0


def fail(fixture, vector_name, msg):
    failures.append(f"{fixture} :: {vector_name}: {msg}")


B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58encode(data: bytes) -> str:
    """base58-btc encode (for did:key identity derivation, RFC-ACDP-0001 §5.11.1)."""
    n = int.from_bytes(data, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = B58_ALPHABET[r] + out
    pad = 0
    for b in data:
        if b == 0:
            pad += 1
        else:
            break
    return "1" * pad + out


def key_fingerprint(raw_public_key_bytes: bytes) -> str:
    """RFC-ACDP-0010 §6: sha256:<lowercase hex SHA-256(raw public key bytes)>."""
    return "sha256:" + hashlib.sha256(raw_public_key_bytes).hexdigest()


def check_canonicalization_and_hash(fixture, vector):
    name = vector.get("name", "?")
    inp = vector.get("input", {})
    exp = vector.get("expected", {})

    # Descriptive vectors (no canonical_form/sha256_hex/lineage_id claim and no `input`)
    # are skipped — they document a normative requirement that has no arithmetic
    # round-trip to verify (e.g. can-007's registry-side timestamp rule).
    has_arithmetic_claim = any(k in exp for k in ("canonical_form", "sha256_hex", "lineage_id"))
    if not has_arithmetic_claim and "input" not in vector:
        return None

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


def _check_lineage(fixture, name, vector):
    reg = vector.get("registry_assigned", {})
    if "ctx_id" in reg and "lineage_id" in reg:
        derived = "lin:sha256:" + hashlib.sha256(reg["ctx_id"].encode("utf-8")).hexdigest()
        if derived != reg["lineage_id"]:
            fail(fixture, name, f"lineage_id mismatch. expected={reg['lineage_id']} actual={derived}")
            return False
    return True


def _canonicalize_and_hash(fixture, name, vector):
    """Return (canonical_bytes, content_hash, ok). ok is False if a pinned expectation diverged."""
    producer_content = vector.get("producer_content", {})
    exp = vector.get("expected", {})

    canonical_bytes = jcs.canonicalize(producer_content)
    canonical = canonical_bytes.decode("utf-8")
    if "canonical_form" in exp and canonical != exp["canonical_form"]:
        fail(fixture, name, f"canonical_form mismatch.\n    expected: {exp['canonical_form']}\n    actual:   {canonical}")
        return canonical_bytes, None, False

    hash_hex = hashlib.sha256(canonical_bytes).hexdigest()
    content_hash = f"sha256:{hash_hex}"
    if "content_hash" in exp and content_hash != exp["content_hash"]:
        fail(fixture, name, f"content_hash mismatch. expected={exp['content_hash']} actual={content_hash}")
        return canonical_bytes, content_hash, False

    return canonical_bytes, content_hash, True


def check_ed25519_vector(fixture, fixture_data, vector):
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

    # did:key fixtures (sig-003): derive the pure did:key identity from the public
    # key (multicodec 0xed01 + base58-btc multibase) and byte-compare against the
    # declared DID. RFC-ACDP-0001 §5.11.1.
    declared_did_key = keypair.get("did_key", "")
    if declared_did_key:
        derived_did_key = "did:key:z" + b58encode(bytes([0xED, 0x01]) + pub_raw)
        if derived_did_key != declared_did_key:
            fail(fixture, name, f"did:key derivation mismatch. declared={declared_did_key} derived={derived_did_key}")
            return False
        sig = vector.get("expected", {}).get("publish_request_body", {}).get("signature", {})
        if sig:
            expected_key_id = f"{declared_did_key}#{declared_did_key.split(':', 2)[2]}"
            if sig.get("key_id") != expected_key_id:
                fail(fixture, name, f"did:key key_id fragment mismatch. expected={expected_key_id} actual={sig.get('key_id')}")
                return False

    _, content_hash, ok = _canonicalize_and_hash(fixture, name, vector)
    if not ok:
        return False

    exp = vector.get("expected", {})
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

    return _check_lineage(fixture, name, vector)


def _ieee1363_to_der(rs_bytes):
    """Convert a 64-byte IEEE 1363 (r‖s) signature to DER for cryptography.verify()."""
    if len(rs_bytes) != 64:
        raise ValueError(f"expected 64 bytes for P-256 r||s, got {len(rs_bytes)}")
    r = int.from_bytes(rs_bytes[:32], "big")
    s = int.from_bytes(rs_bytes[32:], "big")
    return encode_dss_signature(r, s)


def _der_to_ieee1363(der_bytes):
    """Convert a DER-encoded ECDSA signature to 64-byte IEEE 1363 r||s."""
    r, s = decode_dss_signature(der_bytes)
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def check_ecdsa_p256_vector(fixture, fixture_data, vector):
    """Verify an ecdsa-p256 fixture: load the public key, verify the pinned signature.

    Signing is non-deterministic in cryptography.io's API (no RFC 6979 helper),
    so we DO NOT re-sign and byte-compare. We instead verify that the pinned
    signature_value_base64 verifies under the declared public key.

    Vectors with expected.expected_outcome == "failure" exercise the
    DER-rejection rule from registries/signature-algorithms.md: the wire blob
    is intentionally not 64 bytes (e.g. 70-byte DER), and a conformant
    implementation MUST detect and reject it.
    """
    name = vector.get("name", "?")
    keypair = fixture_data.get("test_keypair", {})
    x_hex = keypair.get("public_key_hex_x", "")
    y_hex = keypair.get("public_key_hex_y", "")
    if not (x_hex and y_hex):
        fail(fixture, name, "missing test_keypair.public_key_hex_x or .public_key_hex_y")
        return False

    try:
        x_int = int(x_hex, 16)
        y_int = int(y_hex, 16)
        pub_numbers = ec.EllipticCurvePublicNumbers(x_int, y_int, ec.SECP256R1())
        pub = pub_numbers.public_key()
    except Exception as e:
        fail(fixture, name, f"public key load failed: {e}")
        return False

    _, content_hash, ok = _canonicalize_and_hash(fixture, name, vector)
    if not ok:
        return False

    exp = vector.get("expected", {})
    expected_outcome = exp.get("expected_outcome", "success")

    if expected_outcome == "failure":
        # DER-rejection (and similar negative) vectors. The fixture pins a wire
        # blob that is NOT 64 bytes; this runner verifies that the rejection
        # path is observable by the wire form alone (length != 64), without
        # any cryptographic operation. A conformant registry MUST reject with
        # `invalid_signature`; this static check confirms the test data is
        # consistent with that requirement.
        der_b64 = exp.get("der_encoded_signature_base64")
        if not der_b64:
            fail(fixture, name, "failure vector missing expected.der_encoded_signature_base64")
            return False
        try:
            der_bytes = base64.b64decode(der_b64)
        except Exception as e:
            fail(fixture, name, f"DER base64 decode failed: {e}")
            return False
        # Sanity-check the DER does at least parse and hold the same (r, s) as
        # the success vector for this fixture — i.e. the negative vector is
        # the same mathematical signature, just wrong wire form.
        try:
            rs_recovered = _der_to_ieee1363(der_bytes)
        except Exception as e:
            fail(fixture, name, f"DER parse failed: {e}")
            return False
        if len(der_bytes) == 64:
            fail(fixture, name, "negative vector wire length is 64 — indistinguishable from r||s, won't exercise rejection")
            return False
        # The negative vector's blob must mathematically verify when re-parsed
        # as DER, otherwise it doesn't isolate "DER wire form" from "broken
        # signature". This is a fixture-quality check.
        try:
            pub.verify(der_bytes, content_hash.encode("ascii"), ec.ECDSA(hashes.SHA256()))
        except Exception as e:
            fail(fixture, name, f"DER blob does not verify against the public key — fixture is testing the wrong thing: {e}")
            return False
        return _check_lineage(fixture, name, vector)

    sig_b64 = exp.get("signature_value_base64")
    if not sig_b64:
        fail(fixture, name, "missing expected.signature_value_base64")
        return False

    try:
        rs_bytes = base64.b64decode(sig_b64)
    except Exception as e:
        fail(fixture, name, f"signature base64 decode failed: {e}")
        return False

    if len(rs_bytes) != 64:
        fail(fixture, name, f"signature wire length is {len(rs_bytes)} bytes; ecdsa-p256 IEEE 1363 r||s MUST be 64")
        return False

    if "signature_value_hex" in exp and rs_bytes.hex() != exp["signature_value_hex"]:
        fail(fixture, name, f"signature_value_hex mismatch. expected={exp['signature_value_hex']} actual={rs_bytes.hex()}")
        return False

    try:
        der = _ieee1363_to_der(rs_bytes)
        pub.verify(der, content_hash.encode("ascii"), ec.ECDSA(hashes.SHA256()))
    except Exception as e:
        fail(fixture, name, f"signature verification failed: {e}")
        return False

    return _check_lineage(fixture, name, vector)


def check_signature_vector(fixture, fixture_data, vector):
    keypair = fixture_data.get("test_keypair", {})
    algorithm = keypair.get("algorithm")
    if algorithm == "ecdsa-p256":
        return check_ecdsa_p256_vector(fixture, fixture_data, vector)
    # Default: ed25519. sig-001 predates the per-fixture algorithm field.
    return check_ed25519_vector(fixture, fixture_data, vector)


def check_fingerprint_vector(fixture, vector):
    """fp-* vectors: RFC-ACDP-0010 §6 key_fingerprint encoding."""
    name = vector.get("name", "?")
    algorithm = vector.get("algorithm", "")
    key_hex = vector.get("input", {}).get("public_key_hex", "")
    expected_fp = vector.get("expected", {}).get("key_fingerprint", "")
    if not key_hex or not expected_fp:
        fail(fixture, name, "missing input.public_key_hex or expected.key_fingerprint")
        return False
    try:
        raw = bytes.fromhex(key_hex)
    except ValueError as e:
        fail(fixture, name, f"public_key_hex decode failed: {e}")
        return False
    if algorithm == "ed25519" and len(raw) != 32:
        fail(fixture, name, f"ed25519 raw key MUST be 32 bytes, got {len(raw)}")
        return False
    if algorithm == "ecdsa-p256":
        if len(raw) != 33 or raw[0] not in (0x02, 0x03):
            fail(fixture, name, f"ecdsa-p256 fingerprint input MUST be a 33-byte SEC1 compressed point, got {len(raw)} bytes (first byte {raw[0]:#04x})")
            return False
        # Cross-check the compressed point against the declared uncompressed pair.
        unc = vector.get("uncompressed_point", {})
        if unc:
            x = int(unc["x_hex"], 16)
            y = int(unc["y_hex"], 16)
            expected_prefix = 0x03 if y % 2 else 0x02
            if raw[0] != expected_prefix or raw[1:] != x.to_bytes(32, "big"):
                fail(fixture, name, "compressed point does not match the declared uncompressed (x, y) pair")
                return False
    actual = key_fingerprint(raw)
    if actual != expected_fp:
        fail(fixture, name, f"key_fingerprint mismatch. expected={expected_fp} actual={actual}")
        return False
    return True


def check_receipt_vector(fixture, fixture_data, vector):
    """rcpt-* golden vectors: full RFC-ACDP-0010 §5 receipt cycle with the registry test keypair."""
    name = vector.get("name", "?")
    keypair = fixture_data.get("registry_test_keypair", {})
    seed_hex = keypair.get("private_seed_hex", "")
    if not seed_hex:
        fail(fixture, name, "missing registry_test_keypair.private_seed_hex")
        return False

    try:
        priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex))
        pub = priv.public_key()
        pub_raw = pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    except Exception as e:
        fail(fixture, name, f"registry keypair load failed: {e}")
        return False

    declared_pub_hex = keypair.get("public_key_hex", "")
    if declared_pub_hex and pub_raw.hex() != declared_pub_hex:
        fail(fixture, name, f"registry public_key_hex mismatch. declared={declared_pub_hex} derived={pub_raw.hex()}")
        return False

    receipt_unsigned = vector.get("receipt_unsigned", {})
    exp = vector.get("expected", {})

    canonical_bytes = jcs.canonicalize(receipt_unsigned)
    canonical = canonical_bytes.decode("utf-8")
    if "canonical_form" in exp and canonical != exp["canonical_form"]:
        fail(fixture, name, f"receipt canonical_form mismatch.\n    expected: {exp['canonical_form']}\n    actual:   {canonical}")
        return False

    receipt_hash = "sha256:" + hashlib.sha256(canonical_bytes).hexdigest()
    if "receipt_hash" in exp and receipt_hash != exp["receipt_hash"]:
        fail(fixture, name, f"receipt_hash mismatch. expected={exp['receipt_hash']} actual={receipt_hash}")
        return False

    sig_bytes = priv.sign(receipt_hash.encode("ascii"))
    if "signature_value_hex" in exp and sig_bytes.hex() != exp["signature_value_hex"]:
        fail(fixture, name, "receipt signature_value_hex mismatch")
        return False
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")
    if "signature_value_base64" in exp and sig_b64 != exp["signature_value_base64"]:
        fail(fixture, name, "receipt signature_value_base64 mismatch")
        return False

    try:
        pub.verify(sig_bytes, receipt_hash.encode("ascii"))
    except Exception as e:
        fail(fixture, name, f"receipt signature verification failed: {e}")
        return False

    # key_fingerprint binds the producer key (RFC-ACDP-0010 §6).
    producer_key_hex = fixture_data.get("producer_key", {}).get("public_key_hex", "")
    if producer_key_hex:
        fp = key_fingerprint(bytes.fromhex(producer_key_hex))
        if fp != receipt_unsigned.get("key_fingerprint"):
            fail(fixture, name, f"producer key_fingerprint mismatch. expected={receipt_unsigned.get('key_fingerprint')} actual={fp}")
            return False

    # The assembled registry_receipt object must be receipt_unsigned + the signature.
    assembled = exp.get("registry_receipt")
    if assembled:
        stripped = {k: v for k, v in assembled.items() if k != "signature"}
        if stripped != receipt_unsigned:
            fail(fixture, name, "expected.registry_receipt minus signature != receipt_unsigned")
            return False
        if assembled.get("signature", {}).get("value") != sig_b64:
            fail(fixture, name, "expected.registry_receipt.signature.value != computed signature")
            return False

    # Intra-receipt authority consistency (RFC-ACDP-0010 §4).
    rd = receipt_unsigned.get("registry_did", "")
    authority = rd[len("did:web:"):] if rd.startswith("did:web:") else ""
    ctx_authority = receipt_unsigned.get("ctx_id", "").removeprefix("acdp://").split("/", 1)[0]
    if not authority or authority != receipt_unsigned.get("origin_registry") or authority != ctx_authority:
        fail(fixture, name, f"registry_did/origin_registry/ctx_id authority inconsistency: {rd} / {receipt_unsigned.get('origin_registry')} / {ctx_authority}")
        return False

    return True


def check_lineage_head_receipt_vector(fixture, fixture_data, vector):
    """lhr-* golden vectors: full RFC-ACDP-0011 §5 head-receipt cycle with the registry test keypair.

    The signing construction is RFC-ACDP-0010 §5 verbatim (JCS preimage minus
    'signature' → SHA-256 → sign the ASCII "sha256:<hex>" string) under the same
    registry receipt signing key; the object shape and binding rules are
    RFC-ACDP-0011 §4/§7.
    """
    import re

    name = vector.get("name", "?")
    keypair = fixture_data.get("registry_test_keypair", {})
    seed_hex = keypair.get("private_seed_hex", "")
    if not seed_hex:
        fail(fixture, name, "missing registry_test_keypair.private_seed_hex")
        return False

    try:
        priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex))
        pub = priv.public_key()
        pub_raw = pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    except Exception as e:
        fail(fixture, name, f"registry keypair load failed: {e}")
        return False

    declared_pub_hex = keypair.get("public_key_hex", "")
    if declared_pub_hex and pub_raw.hex() != declared_pub_hex:
        fail(fixture, name, f"registry public_key_hex mismatch. declared={declared_pub_hex} derived={pub_raw.hex()}")
        return False

    receipt_unsigned = vector.get("receipt_unsigned", {})
    exp = vector.get("expected", {})

    canonical_bytes = jcs.canonicalize(receipt_unsigned)
    canonical = canonical_bytes.decode("utf-8")
    if "canonical_form" in exp and canonical != exp["canonical_form"]:
        fail(fixture, name, f"head-receipt canonical_form mismatch.\n    expected: {exp['canonical_form']}\n    actual:   {canonical}")
        return False

    receipt_hash = "sha256:" + hashlib.sha256(canonical_bytes).hexdigest()
    if "receipt_hash" in exp and receipt_hash != exp["receipt_hash"]:
        fail(fixture, name, f"head-receipt receipt_hash mismatch. expected={exp['receipt_hash']} actual={receipt_hash}")
        return False

    sig_bytes = priv.sign(receipt_hash.encode("ascii"))
    if "signature_value_hex" in exp and sig_bytes.hex() != exp["signature_value_hex"]:
        fail(fixture, name, "head-receipt signature_value_hex mismatch")
        return False
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")
    if "signature_value_base64" in exp and sig_b64 != exp["signature_value_base64"]:
        fail(fixture, name, "head-receipt signature_value_base64 mismatch")
        return False

    try:
        pub.verify(sig_bytes, receipt_hash.encode("ascii"))
    except Exception as e:
        fail(fixture, name, f"head-receipt signature verification failed: {e}")
        return False

    # The assembled lineage_head_receipt object must be receipt_unsigned + the signature.
    assembled = exp.get("lineage_head_receipt")
    if assembled:
        stripped = {k: v for k, v in assembled.items() if k != "signature"}
        if stripped != receipt_unsigned:
            fail(fixture, name, "expected.lineage_head_receipt minus signature != receipt_unsigned")
            return False
        if assembled.get("signature", {}).get("value") != sig_b64:
            fail(fixture, name, "expected.lineage_head_receipt.signature.value != computed signature")
            return False

    # Intra-receipt consistency (RFC-ACDP-0011 §4, §7).
    if receipt_unsigned.get("receipt_version") != "acdp-lhr/1":
        fail(fixture, name, f"receipt_version MUST be 'acdp-lhr/1', got {receipt_unsigned.get('receipt_version')!r}")
        return False
    rd = receipt_unsigned.get("registry_did", "")
    authority = rd[len("did:web:"):] if rd.startswith("did:web:") else ""
    head_authority = receipt_unsigned.get("head_ctx_id", "").removeprefix("acdp://").split("/", 1)[0]
    if not authority or authority != head_authority:
        fail(fixture, name, f"registry_did/head_ctx_id authority inconsistency: {rd} / {receipt_unsigned.get('head_ctx_id')}")
        return False
    head_status = receipt_unsigned.get("head_status", "")
    if head_status == "superseded" or not re.fullmatch(r"[a-z][a-z0-9_]*", head_status) or len(head_status) > 64:
        fail(fixture, name, f"head_status invalid for a head: {head_status!r} (never 'superseded'; RFC-ACDP-0004 §4.1 pattern)")
        return False
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", receipt_unsigned.get("as_of", "")):
        fail(fixture, name, f"as_of is not canonical millisecond RFC 3339 UTC: {receipt_unsigned.get('as_of')!r}")
        return False
    hv = receipt_unsigned.get("head_version")
    if not isinstance(hv, int) or hv < 1:
        fail(fixture, name, f"head_version MUST be an integer >= 1, got {hv!r}")
        return False
    if hv == 1:
        # A version-1 head's lineage_id is derivable from its own ctx_id (RFC-ACDP-0001 §5.6).
        derived = "lin:sha256:" + hashlib.sha256(receipt_unsigned.get("head_ctx_id", "").encode("utf-8")).hexdigest()
        if derived != receipt_unsigned.get("lineage_id"):
            fail(fixture, name, f"lineage_id mismatch for a version-1 head. expected={receipt_unsigned.get('lineage_id')} derived={derived}")
            return False

    return True


for path in sorted(CONFORMANCE.glob("*.json")):
    with open(path) as f:
        data = json.load(f)
    fixture_id = data.get("id", path.stem)

    if fixture_id.startswith("can-") or fixture_id.startswith("lin-"):
        # can-* fixtures carry JCS/SHA-256 vectors and (some) lineage vectors;
        # lin-* fixtures are dedicated lineage_id derivation golden vectors.
        # Both are verified by the same arithmetic check.
        for v in data.get("vectors", []):
            result = check_canonicalization_and_hash(fixture_id, v)
            if result is True:
                passes += 1
            # result is None → descriptive vector, skipped silently
    elif fixture_id.startswith("sig-"):
        for v in data.get("vectors", []):
            if check_signature_vector(fixture_id, data, v):
                passes += 1
    elif fixture_id.startswith("fp-"):
        for v in data.get("vectors", []):
            if check_fingerprint_vector(fixture_id, v):
                passes += 1
    elif fixture_id.startswith("rcpt-") and "registry_test_keypair" in data:
        # rcpt golden vectors (rcpt-001) are executed; rcpt-002..004 are behavioral
        # scenarios without a registry_test_keypair and are skipped here.
        for v in data.get("vectors", []):
            if check_receipt_vector(fixture_id, data, v):
                passes += 1
    elif fixture_id.startswith("lhr-") and "registry_test_keypair" in data:
        # lhr golden vectors (lhr-001) are executed; lhr-002..004 are behavioral
        # scenarios without a registry_test_keypair and are skipped here.
        for v in data.get("vectors", []):
            if check_lineage_head_receipt_vector(fixture_id, data, v):
                passes += 1
    # pub-, vis-, ret-, dk-, rot-, fed- (and keypair-less rcpt-/lhr-) fixtures describe
    # scenarios (request → expected error code), not arithmetic vectors. Their conformance
    # is checked by registry/consumer implementations, not by this static runner.


def check_golden_retrieval_example():
    """Verify examples/retrieval/golden-context.json end-to-end against sig-001's test keypair.

    Treats the example as a derivative of sig-001: the body's signature MUST verify against
    the test public key, and the recomputed content_hash MUST match the body's content_hash.
    """
    name = "golden-context.json (derivative of sig-001)"
    fixture = "examples/retrieval"
    sig_001 = json.loads((CONFORMANCE / "sig-001-ed25519-golden.json").read_text())
    keypair = sig_001["test_keypair"]
    pub_key_hex = keypair["public_key_hex"]

    example_path = ROOT / "examples" / "retrieval" / "golden-context.json"
    example = json.loads(example_path.read_text())
    body = example["body"]

    EXCLUSION_SET = {"ctx_id", "lineage_id", "origin_registry", "created_at", "content_hash", "signature"}
    producer_content = {k: v for k, v in body.items() if k not in EXCLUSION_SET}

    canonical = jcs.canonicalize(producer_content)
    recomputed = "sha256:" + hashlib.sha256(canonical).hexdigest()
    if recomputed != body["content_hash"]:
        fail(fixture, name, f"content_hash mismatch. body={body['content_hash']} recomputed={recomputed}")
        return False

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_key_hex))
    sig_bytes = base64.b64decode(body["signature"]["value"])
    try:
        pub.verify(sig_bytes, body["content_hash"].encode("ascii"))
    except Exception as e:
        fail(fixture, name, f"signature verification failed: {e}")
        return False

    derived_lineage = "lin:sha256:" + hashlib.sha256(body["ctx_id"].encode("utf-8")).hexdigest()
    if derived_lineage != body["lineage_id"]:
        fail(fixture, name, f"lineage_id mismatch. body={body['lineage_id']} derived={derived_lineage}")
        return False

    return True


def check_golden_receipt_example():
    """Verify examples/retrieval/golden-context-with-receipt.json end-to-end.

    The body is the sig-001 golden body (verified by check_golden_retrieval_example
    on its sibling file); here we verify the registry_receipt against the rcpt-001
    registry test keypair: preimage, receipt hash, signature, key_fingerprint, and
    the §8 cross-checks against the accompanying body.
    """
    name = "golden-context-with-receipt.json (derivative of rcpt-001)"
    fixture = "examples/retrieval"
    example_path = ROOT / "examples" / "retrieval" / "golden-context-with-receipt.json"
    if not example_path.exists():
        fail(fixture, name, "example file missing")
        return False
    example = json.loads(example_path.read_text())
    body = example["body"]
    receipt = example["registry_receipt"]

    rcpt_001 = json.loads((CONFORMANCE / "rcpt-001-receipt-golden.json").read_text())
    reg_pub_hex = rcpt_001["registry_test_keypair"]["public_key_hex"]

    preimage = {k: v for k, v in receipt.items() if k != "signature"}
    canonical = jcs.canonicalize(preimage)
    receipt_hash = "sha256:" + hashlib.sha256(canonical).hexdigest()

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    reg_pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(reg_pub_hex))
    try:
        reg_pub.verify(base64.b64decode(receipt["signature"]["value"]), receipt_hash.encode("ascii"))
    except Exception as e:
        fail(fixture, name, f"receipt signature verification failed: {e}")
        return False

    # RFC-ACDP-0010 §8 cross-checks against the body.
    EXCLUSION_SET = {"ctx_id", "lineage_id", "origin_registry", "created_at", "content_hash", "signature"}
    producer_content = {k: v for k, v in body.items() if k not in EXCLUSION_SET}
    recomputed = "sha256:" + hashlib.sha256(jcs.canonicalize(producer_content)).hexdigest()
    if receipt["content_hash"] != recomputed:
        fail(fixture, name, f"receipt content_hash != independently recomputed body hash ({recomputed})")
        return False
    for field in ("ctx_id", "lineage_id", "origin_registry", "created_at"):
        if receipt[field] != body[field]:
            fail(fixture, name, f"receipt.{field} != body.{field}")
            return False
    sig_001 = json.loads((CONFORMANCE / "sig-001-ed25519-golden.json").read_text())
    producer_fp = key_fingerprint(bytes.fromhex(sig_001["test_keypair"]["public_key_hex"]))
    if receipt["key_fingerprint"] != producer_fp:
        fail(fixture, name, f"receipt.key_fingerprint != producer key fingerprint ({producer_fp})")
        return False
    if not receipt["registry_did"].startswith("did:web:") or receipt["registry_did"][len("did:web:"):] != receipt["origin_registry"]:
        fail(fixture, name, "receipt registry_did does not bind to origin_registry authority")
        return False

    return True


if check_golden_retrieval_example():
    passes += 1

if check_golden_receipt_example():
    passes += 1

if failures:
    print(f"\n✗ {len(failures)} conformance failure(s):", file=sys.stderr)
    for f in failures:
        print(f"  {f}", file=sys.stderr)
    print(f"\nPassed: {passes}\nFailed: {len(failures)}", file=sys.stderr)
    sys.exit(1)
else:
    print(f"✓ All {passes} arithmetic conformance vectors passed.")
    sys.exit(0)
