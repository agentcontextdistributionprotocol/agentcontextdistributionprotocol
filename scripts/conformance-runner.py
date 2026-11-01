#!/usr/bin/env python3
"""
ACDP conformance runner.

Reads every fixture under schemas/conformance/ and verifies arithmetic claims:
  - can-* fixtures: JCS canonicalization + SHA-256 + lineage_id derivation
  - lin-* fixtures: lineage_id derivation golden vectors
  - sig-* fixtures: full Ed25519 / ECDSA-P256 sign/verify cycle, full content_hash
    computation, and (for did:key fixtures) pure did:key identity derivation
  - rev-* fixtures carrying a test_keypair: key-revocation context golden cycle
    (same arithmetic as sig-*, plus the RFC-ACDP-0014 §4/§5 shape checks)
  - rcpt-* fixtures carrying a registry_test_keypair: full receipt golden cycle
    (preimage, receipt hash, signature, producer key_fingerprint) per RFC-ACDP-0010
  - lhr-* fixtures carrying a registry_test_keypair: full lineage-head-receipt
    golden cycle (preimage, receipt hash, signature, binding consistency) per
    RFC-ACDP-0011
  - log-* fixtures carrying a registry_test_keypair: full transparency-log
    golden cycle (JCS leaf encoding, 0x00/0x01 domain-separated Merkle tree,
    root, signed checkpoint, inclusion-proof and consistency-proof generation
    AND verification-algorithm folding) per RFC-ACDP-0012
  - wit-* fixtures carrying a witness_test_keypair(s): full witness-cosignature
    golden cycle (JCS preimage, cosignature hash, witness-keyed signature,
    checkpoint chaining, and the N-witnessed quorum count) per RFC-ACDP-0015
  - fp-* fixtures: key-fingerprint encoding vectors (RFC-ACDP-0010 §6)
  - chain-* fixtures with a vectors array: RFC-ACDP-0017 verdict digest known answers

Behavioral fixtures (pub-*, vis-*, dk-*, rcpt-002..004, lhr-002..004,
log-002/log-004, wit-002/wit-004, lc-*, rev-002/rev-003, rot-*, fed-*, ...) are not executed; they
describe request/response scenarios for live implementations.
Exits 0 if all vectors pass, 1 otherwise.

Requires: pip install jcs cryptography
(jcs handles JCS canonicalization including the -0.0 normalization that stdlib json.dumps misses.)
"""

import argparse
import json
import hashlib
from datetime import datetime
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

_parser = argparse.ArgumentParser(description="ACDP conformance runner")
_parser.add_argument(
    "--only",
    metavar="PREFIX",
    help="run only fixtures whose id or filename starts with PREFIX "
    "(e.g. --only sig-002 or --only can). The golden-example checks are "
    "skipped when a filter is active.",
)
ARGS = _parser.parse_args()

failures = []
passes = 0
skipped_behavioral = []

# Known fixture families come from the machine-readable conformance manifest,
# so a typo'd fixture prefix fails loudly instead of being silently skipped.
KNOWN_FAMILIES = set(
    json.loads((ROOT / "registries" / "profiles.json").read_text()).get("fixture_families", {})
)


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


_ED_P = 2**255 - 19
_ED_L = 2**252 + 27742317777372353535851937790883648493
_ED_D = (-121665 * pow(121666, -1, _ED_P)) % _ED_P


def _ed_decode(b):
    y = int.from_bytes(b, "little")
    sign, y = y >> 255, y & ((1 << 255) - 1)
    x2 = (y * y - 1) * pow(_ED_D * y * y + 1, -1, _ED_P) % _ED_P
    x = pow(x2, (_ED_P + 3) // 8, _ED_P)
    if (x * x - x2) % _ED_P:
        x = x * pow(2, (_ED_P - 1) // 4, _ED_P) % _ED_P
    if (x * x - x2) % _ED_P:
        raise ValueError("not a curve point")
    return ((-x) % _ED_P if x & 1 != sign else x), y


def _ed_add(P, Q):
    t = _ED_D * P[0] * Q[0] * P[1] * Q[1] % _ED_P
    return ((P[0] * Q[1] + Q[0] * P[1]) * pow(1 + t, -1, _ED_P) % _ED_P,
            (P[1] * Q[1] + P[0] * Q[0]) * pow(1 - t, -1, _ED_P) % _ED_P)


def _ed_mul(k, P):
    R = (0, 1)
    while k:
        if k & 1:
            R = _ed_add(R, P)
        P = _ed_add(P, P)
        k >>= 1
    return R


def check_ed25519_strict_negative(fixture, fixture_data, vector):
    """sig-004: pure-arithmetic check of the strict-verification negative vector
    (RFC-ACDP-0001 §5.10). Confirms the cofactorless equation [s]B = R + [k]A holds
    (so a non-strict verifier accepts) while A and R are small-order (so a strict
    verifier MUST reject). Uses no crypto library: OpenSSL's verdict is not the oracle."""
    name = vector.get("name", "?")
    import hashlib
    exp = vector.get("expected", {})
    if exp.get("strict_result") != "reject" or exp.get("error") != "invalid_signature":
        fail(fixture, name, "negative vector MUST pin strict_result=reject / error=invalid_signature")
        return False
    sig = bytes.fromhex(vector["signature_value_hex"])
    a_enc, r_enc, s = bytes.fromhex(vector["public_key_hex"]), sig[:32], int.from_bytes(sig[32:], "little")
    A, R = _ed_decode(a_enc), _ed_decode(r_enc)
    B = _ed_decode((4 * pow(5, -1, _ED_P) % _ED_P).to_bytes(32, "little"))
    k = int.from_bytes(hashlib.sha512(r_enc + a_enc + vector["signature_input"].encode("ascii")).digest(), "little") % _ED_L
    if s >= _ED_L:
        fail(fixture, name, "s >= L: this vector must isolate the small-order defect, not malleable s")
        return False
    holds = _ed_mul(s, B) == _ed_add(R, _ed_mul(k, A))
    small = lambda P: _ed_mul(8, P) == (0, 1)
    got = {"loose_equation_holds": holds, "public_key_small_order": small(A), "r_small_order": small(R)}
    for key, val in got.items():
        if exp.get(key) is not val:
            fail(fixture, name, f"{key}: expected {exp.get(key)!r}, computed {val!r}")
            return False
    for pt in fixture_data.get("small_order_points", []):
        if not small(_ed_decode(bytes.fromhex(pt["encoding_hex"]))):
            fail(fixture, name, f"listed small-order encoding is not small-order: {pt['encoding_hex']}")
            return False
    return True


def check_signature_vector(fixture, fixture_data, vector):
    keypair = fixture_data.get("test_keypair", {})
    algorithm = keypair.get("algorithm")
    if algorithm == "ecdsa-p256":
        return check_ecdsa_p256_vector(fixture, fixture_data, vector)
    # Default: ed25519. sig-001 predates the per-fixture algorithm field.
    return check_ed25519_vector(fixture, fixture_data, vector)


def check_revocation_vector(fixture, fixture_data, vector):
    """rev-* golden vectors: a key-revocation context (RFC-ACDP-0014) is an ordinary
    signed body, so the arithmetic is check_ed25519_vector verbatim; on top we pin
    the §4 shape and the §5 not-self-signed constraint."""
    name = vector.get("name", "?")
    if not check_ed25519_vector(fixture, fixture_data, vector):
        return False

    pc = vector.get("producer_content", {})
    meta = pc.get("metadata", {})
    if pc.get("type") != "key-revocation":
        fail(fixture, name, f"type MUST be 'key-revocation', got {pc.get('type')!r}")
        return False
    if pc.get("visibility") != "public":
        fail(fixture, name, f"visibility MUST be 'public' (RFC-ACDP-0014 §4), got {pc.get('visibility')!r}")
        return False
    import re
    fp = meta.get("revoked_key_fingerprint", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", fp):
        fail(fixture, name, f"metadata.revoked_key_fingerprint not in RFC-ACDP-0010 §6 form: {fp!r}")
        return False
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", meta.get("compromised_since", "")):
        fail(fixture, name, f"metadata.compromised_since not canonical millisecond RFC 3339 UTC: {meta.get('compromised_since')!r}")
        return False

    # §5 step 2: the signing key MUST NOT be the revoked key.
    signer_pub_hex = fixture_data.get("test_keypair", {}).get("public_key_hex", "")
    if signer_pub_hex and key_fingerprint(bytes.fromhex(signer_pub_hex)) == fp:
        fail(fixture, name, "revocation is self-signed by the revoked key (RFC-ACDP-0014 §5 step 2)")
        return False

    # Cross-check the declared revoked-key fingerprint against its raw key bytes.
    revoked = fixture_data.get("revoked_key", {})
    if revoked.get("public_key_hex"):
        derived = key_fingerprint(bytes.fromhex(revoked["public_key_hex"]))
        if derived != revoked.get("key_fingerprint") or derived != fp:
            fail(fixture, name, f"revoked_key fingerprint inconsistency: derived={derived}")
            return False

    return True


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


# ── RFC-ACDP-0012 transparency log: Merkle primitives (RFC 6962 §2.1) ─────────

LOG_LEAF_PREFIX = b"\x00"
LOG_NODE_PREFIX = b"\x01"


def _log_node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(LOG_NODE_PREFIX + left + right).digest()


def _log_largest_pow2_lt(n: int) -> int:
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def _log_mth(hashes):
    """RFC 6962 §2.1 Merkle Tree Hash over leaf hashes (RFC-ACDP-0012 §5.2)."""
    n = len(hashes)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return hashes[0]
    k = _log_largest_pow2_lt(n)
    return _log_node_hash(_log_mth(hashes[:k]), _log_mth(hashes[k:]))


def _log_inclusion_path(m, hashes):
    """RFC 6962 §2.1.1 PATH(m, D[n])."""
    n = len(hashes)
    if n == 1:
        return []
    k = _log_largest_pow2_lt(n)
    if m < k:
        return _log_inclusion_path(m, hashes[:k]) + [_log_mth(hashes[k:])]
    return _log_inclusion_path(m - k, hashes[k:]) + [_log_mth(hashes[:k])]


def _log_consistency_proof(m, hashes):
    """RFC 6962 §2.1.2 PROOF(m, D[n])."""

    def subproof(m, d, b):
        n = len(d)
        if m == n:
            return [] if b else [_log_mth(d)]
        k = _log_largest_pow2_lt(n)
        if m <= k:
            return subproof(m, d[:k], b) + [_log_mth(d[k:])]
        return subproof(m - k, d[k:], False) + [_log_mth(d[:k])]

    return subproof(m, hashes, True)


def _log_verify_inclusion(lh, leaf_index, tree_size, path, root):
    """RFC-ACDP-0012 §9.1 folding algorithm (RFC 9162 §2.1.3.2)."""
    if leaf_index >= tree_size:
        return False
    fn, sn, r = leaf_index, tree_size - 1, lh
    for p in path:
        if sn == 0:
            return False
        if fn % 2 == 1 or fn == sn:
            r = _log_node_hash(p, r)
            if fn % 2 == 0:
                while fn % 2 == 0 and fn != 0:
                    fn >>= 1
                    sn >>= 1
        else:
            r = _log_node_hash(r, p)
        fn >>= 1
        sn >>= 1
    return sn == 0 and r == root


def _log_verify_consistency(first, second, path, first_root, second_root):
    """RFC-ACDP-0012 §9.2 verification algorithm (RFC 9162 §2.1.4.2)."""
    if first == second:
        return path == [] and first_root == second_root
    if not (0 < first < second) or not path:
        return False
    path = list(path)
    if first & (first - 1) == 0:
        path = [first_root] + path
    fn, sn = first - 1, second - 1
    while fn % 2 == 1:
        fn >>= 1
        sn >>= 1
    fr = sr = path[0]
    for c in path[1:]:
        if sn == 0:
            return False
        if fn % 2 == 1 or fn == sn:
            fr = _log_node_hash(c, fr)
            sr = _log_node_hash(c, sr)
            if fn % 2 == 0:
                while fn % 2 == 0 and fn != 0:
                    fn >>= 1
                    sn >>= 1
        else:
            sr = _log_node_hash(sr, c)
        fn >>= 1
        sn >>= 1
    return fr == first_root and sr == second_root and sn == 0


def _hex_of(prefixed: str) -> bytes:
    """Decode a 'sha256:<hex>' string to its raw 32-byte digest."""
    if not prefixed.startswith("sha256:"):
        raise ValueError(f"expected sha256:-prefixed hash, got {prefixed!r}")
    return bytes.fromhex(prefixed[len("sha256:"):])


def _log_verify_checkpoint(fixture, name, fixture_data, unsigned, exp_prefix, exp):
    """Shared checkpoint cycle: JCS preimage, checkpoint hash, sign, verify (RFC-ACDP-0012 §6).

    Returns (signature_b64, ok)."""
    keypair = fixture_data.get("registry_test_keypair", {})
    seed_hex = keypair.get("private_seed_hex", "")
    if not seed_hex:
        fail(fixture, name, "missing registry_test_keypair.private_seed_hex")
        return None, False
    priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex))
    pub = priv.public_key()
    pub_raw = pub.public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    declared_pub_hex = keypair.get("public_key_hex", "")
    if declared_pub_hex and pub_raw.hex() != declared_pub_hex:
        fail(fixture, name, f"registry public_key_hex mismatch. declared={declared_pub_hex} derived={pub_raw.hex()}")
        return None, False

    if unsigned.get("checkpoint_version") != "acdp-log/1":
        fail(fixture, name, f"checkpoint_version MUST be 'acdp-log/1', got {unsigned.get('checkpoint_version')!r}")
        return None, False

    canonical_bytes = jcs.canonicalize(unsigned)
    canonical = canonical_bytes.decode("utf-8")
    if f"{exp_prefix}canonical_form" in exp and canonical != exp[f"{exp_prefix}canonical_form"]:
        fail(fixture, name, f"checkpoint canonical_form mismatch.\n    expected: {exp[f'{exp_prefix}canonical_form']}\n    actual:   {canonical}")
        return None, False

    checkpoint_hash = "sha256:" + hashlib.sha256(canonical_bytes).hexdigest()
    if f"{exp_prefix}checkpoint_hash" in exp and checkpoint_hash != exp[f"{exp_prefix}checkpoint_hash"]:
        fail(fixture, name, f"checkpoint_hash mismatch. expected={exp[f'{exp_prefix}checkpoint_hash']} actual={checkpoint_hash}")
        return None, False

    sig_bytes = priv.sign(checkpoint_hash.encode("ascii"))
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")
    if f"{exp_prefix}signature_value_base64" in exp and sig_b64 != exp[f"{exp_prefix}signature_value_base64"]:
        fail(fixture, name, "checkpoint signature_value_base64 mismatch")
        return None, False
    if f"{exp_prefix}signature_value_hex" in exp and sig_bytes.hex() != exp[f"{exp_prefix}signature_value_hex"]:
        fail(fixture, name, "checkpoint signature_value_hex mismatch")
        return None, False

    try:
        pub.verify(sig_bytes, checkpoint_hash.encode("ascii"))
    except Exception as e:
        fail(fixture, name, f"checkpoint signature verification failed: {e}")
        return None, False

    return sig_b64, True


def check_log_vector(fixture, fixture_data, vector):
    """log-* golden vectors: full RFC-ACDP-0012 transparency-log cycle."""
    import re

    name = vector.get("name", "?")
    exp = vector.get("expected", {})

    # ── Leaf-and-root vectors (log-001) ───────────────────────────────────────
    if "leaves" in vector:
        leaves = vector["leaves"]
        leaf_hashes = []
        for i, leaf in enumerate(leaves):
            if leaf.get("leaf_version") != "acdp-log-leaf/1":
                fail(fixture, name, f"leaf {i}: leaf_version MUST be 'acdp-log-leaf/1'")
                return False
            canonical_bytes = jcs.canonicalize(leaf)
            canonical = canonical_bytes.decode("utf-8")
            exp_forms = exp.get("leaf_canonical_forms", [])
            if i < len(exp_forms) and canonical != exp_forms[i]:
                fail(fixture, name, f"leaf {i} canonical_form mismatch.\n    expected: {exp_forms[i]}\n    actual:   {canonical}")
                return False
            lh = hashlib.sha256(LOG_LEAF_PREFIX + canonical_bytes).digest()
            exp_hashes = exp.get("leaf_hashes", [])
            if i < len(exp_hashes) and "sha256:" + lh.hex() != exp_hashes[i]:
                fail(fixture, name, f"leaf {i} leaf_hash mismatch. expected={exp_hashes[i]} actual=sha256:{lh.hex()}")
                return False
            leaf_hashes.append(lh)
            # Version-1 lineage derivation (all golden leaves are v1 publishes).
            derived = "lin:sha256:" + hashlib.sha256(leaf.get("ctx_id", "").encode("utf-8")).hexdigest()
            if derived != leaf.get("lineage_id"):
                fail(fixture, name, f"leaf {i} lineage_id mismatch. expected={leaf.get('lineage_id')} derived={derived}")
                return False
            # created_at canonical millisecond form.
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", leaf.get("created_at", "")):
                fail(fixture, name, f"leaf {i} created_at is not canonical millisecond RFC 3339 UTC")
                return False
            # key_fingerprint binds the producer key (RFC-ACDP-0010 §6).
            producer_key_hex = fixture_data.get("producer_key", {}).get("public_key_hex", "")
            if producer_key_hex and leaf.get("key_fingerprint") != key_fingerprint(bytes.fromhex(producer_key_hex)):
                fail(fixture, name, f"leaf {i} key_fingerprint does not match the producer key")
                return False

        root = _log_mth(leaf_hashes)
        if "root_hash" in exp and "sha256:" + root.hex() != exp["root_hash"]:
            fail(fixture, name, f"root_hash mismatch. expected={exp['root_hash']} actual=sha256:{root.hex()}")
            return False
        if "empty_tree_root_hash" in exp:
            if "sha256:" + hashlib.sha256(b"").hexdigest() != exp["empty_tree_root_hash"]:
                fail(fixture, name, "empty_tree_root_hash mismatch")
                return False

        _, ok = _log_verify_checkpoint(fixture, name, fixture_data, vector.get("checkpoint_unsigned", {}), "checkpoint_", exp)
        if not ok:
            return False
        assembled = exp.get("log_checkpoint")
        if assembled:
            stripped = {k: v for k, v in assembled.items() if k != "signature"}
            if stripped != vector.get("checkpoint_unsigned", {}):
                fail(fixture, name, "expected.log_checkpoint minus signature != checkpoint_unsigned")
                return False

        incl = exp.get("log_inclusion")
        if incl:
            m, n = incl["leaf_index"], incl["tree_size"]
            path = [_hex_of(p) for p in incl["inclusion_path"]]
            generated = _log_inclusion_path(m, leaf_hashes[:n])
            if generated != path:
                fail(fixture, name, f"inclusion_path mismatch with RFC 6962 PATH({m}, D[{n}])")
                return False
            if not _log_verify_inclusion(leaf_hashes[m], m, n, path, root):
                fail(fixture, name, "inclusion-proof folding (§9.1) did not reproduce the root")
                return False
            # Negative self-check: a tampered path element MUST NOT verify.
            if path:
                bad = list(path)
                bad[0] = bytes([bad[0][0] ^ 0x01]) + bad[0][1:]
                if _log_verify_inclusion(leaf_hashes[m], m, n, bad, root):
                    fail(fixture, name, "folding algorithm accepted a tampered inclusion_path — fixture cannot exercise rejection")
                    return False
        return True

    # ── Consistency vectors (log-003) ─────────────────────────────────────────
    if "first_checkpoint_unsigned" in vector:
        leaf_hashes = [_hex_of(h) for h in vector.get("leaf_hashes", [])]
        first_cp = vector["first_checkpoint_unsigned"]
        second_cp = vector["second_checkpoint_unsigned"]
        m, n = first_cp["tree_size"], second_cp["tree_size"]

        first_root = _log_mth(leaf_hashes[:m])
        second_root = _log_mth(leaf_hashes[:n])
        if "first_root_hash" in exp and "sha256:" + first_root.hex() != exp["first_root_hash"]:
            fail(fixture, name, f"first_root_hash mismatch. expected={exp['first_root_hash']} actual=sha256:{first_root.hex()}")
            return False
        if "second_root_hash" in exp and "sha256:" + second_root.hex() != exp["second_root_hash"]:
            fail(fixture, name, f"second_root_hash mismatch. expected={exp['second_root_hash']} actual=sha256:{second_root.hex()}")
            return False
        if _hex_of(first_cp["root_hash"]) != first_root or _hex_of(second_cp["root_hash"]) != second_root:
            fail(fixture, name, "checkpoint root_hash does not match the recomputed tree root")
            return False

        _, ok = _log_verify_checkpoint(fixture, name, fixture_data, first_cp, "first_", exp)
        if not ok:
            return False
        _, ok = _log_verify_checkpoint(fixture, name, fixture_data, second_cp, "second_", exp)
        if not ok:
            return False

        resp = exp.get("consistency_proof_response", {})
        path = [_hex_of(p) for p in resp.get("consistency_path", [])]
        generated = _log_consistency_proof(m, leaf_hashes[:n])
        if generated != path:
            fail(fixture, name, f"consistency_path mismatch with RFC 6962 PROOF({m}, D[{n}])")
            return False
        if not _log_verify_consistency(m, n, path, first_root, second_root):
            fail(fixture, name, "consistency-proof verification (§9.2) failed on the golden path")
            return False
        # Negative self-checks: tampered path or wrong roots MUST NOT verify.
        bad = list(path)
        bad[0] = bytes([bad[0][0] ^ 0x01]) + bad[0][1:]
        if _log_verify_consistency(m, n, bad, first_root, second_root):
            fail(fixture, name, "consistency algorithm accepted a tampered path — fixture cannot exercise rejection")
            return False
        if _log_verify_consistency(m, n, path, second_root, first_root):
            fail(fixture, name, "consistency algorithm accepted swapped roots — fixture cannot exercise rejection")
            return False
        return True

    fail(fixture, name, "log vector carries neither 'leaves' nor 'first_checkpoint_unsigned'")
    return False


def check_witness_cosignature_vector(fixture, fixture_data, vector):
    """wit-* golden vectors: full RFC-ACDP-0015 §5 witness-cosignature cycle.

    The signing construction is RFC-ACDP-0010 §5 verbatim (JCS preimage minus
    'signature' -> SHA-256 -> sign the ASCII "sha256:<hex>" string) but keyed by
    the WITNESS's own key (RFC-ACDP-0015 §5), not the registry receipt key. The
    object shape and binding rules are RFC-ACDP-0015 §4/§8.
    """
    import re

    name = vector.get("name", "?")
    keypair = vector.get("witness_test_keypair") or fixture_data.get("witness_test_keypair", {})
    seed_hex = keypair.get("private_seed_hex", "")
    if not seed_hex:
        fail(fixture, name, "missing witness_test_keypair.private_seed_hex")
        return False

    try:
        priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex))
        pub = priv.public_key()
        pub_raw = pub.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
    except Exception as e:
        fail(fixture, name, f"witness keypair load failed: {e}")
        return False

    declared_pub_hex = keypair.get("public_key_hex", "")
    if declared_pub_hex and pub_raw.hex() != declared_pub_hex:
        fail(fixture, name, f"witness public_key_hex mismatch. declared={declared_pub_hex} derived={pub_raw.hex()}")
        return False

    unsigned = vector.get("cosignature_unsigned", {})
    exp = vector.get("expected", {})

    if unsigned.get("cosignature_version") != "acdp-cosig/1":
        fail(fixture, name, f"cosignature_version MUST be 'acdp-cosig/1', got {unsigned.get('cosignature_version')!r}")
        return False

    canonical_bytes = jcs.canonicalize(unsigned)
    canonical = canonical_bytes.decode("utf-8")
    if "canonical_form" in exp and canonical != exp["canonical_form"]:
        fail(fixture, name, f"cosignature canonical_form mismatch.\n    expected: {exp['canonical_form']}\n    actual:   {canonical}")
        return False

    cosignature_hash = "sha256:" + hashlib.sha256(canonical_bytes).hexdigest()
    if "cosignature_hash" in exp and cosignature_hash != exp["cosignature_hash"]:
        fail(fixture, name, f"cosignature_hash mismatch. expected={exp['cosignature_hash']} actual={cosignature_hash}")
        return False

    sig_bytes = priv.sign(cosignature_hash.encode("ascii"))
    if "signature_value_hex" in exp and sig_bytes.hex() != exp["signature_value_hex"]:
        fail(fixture, name, "cosignature signature_value_hex mismatch")
        return False
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")
    if "signature_value_base64" in exp and sig_b64 != exp["signature_value_base64"]:
        fail(fixture, name, "cosignature signature_value_base64 mismatch")
        return False

    try:
        pub.verify(sig_bytes, cosignature_hash.encode("ascii"))
    except Exception as e:
        fail(fixture, name, f"cosignature signature verification failed: {e}")
        return False

    # The assembled log_cosignature object must be cosignature_unsigned + the signature.
    assembled = exp.get("log_cosignature")
    if assembled:
        stripped = {k: v for k, v in assembled.items() if k != "signature"}
        if stripped != unsigned:
            fail(fixture, name, "expected.log_cosignature minus signature != cosignature_unsigned")
            return False
        if assembled.get("signature", {}).get("value") != sig_b64:
            fail(fixture, name, "expected.log_cosignature.signature.value != computed signature")
            return False
        # Witness binding (RFC-ACDP-0015 §8 step 3): key_id DID portion == witness_id.
        did_part = assembled.get("signature", {}).get("key_id", "").split("#", 1)[0]
        if did_part != unsigned.get("witness_id"):
            fail(fixture, name, f"signature.key_id DID portion {did_part!r} != witness_id {unsigned.get('witness_id')!r}")
            return False

    # Canonical millisecond form for both timestamps (RFC-ACDP-0015 §4).
    wc = unsigned.get("witnessed_checkpoint", {})
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", unsigned.get("witnessed_at", "")):
        fail(fixture, name, f"witnessed_at not canonical millisecond RFC 3339 UTC: {unsigned.get('witnessed_at')!r}")
        return False
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", wc.get("timestamp", "")):
        fail(fixture, name, "witnessed_checkpoint.timestamp not canonical millisecond RFC 3339 UTC")
        return False

    # Chain to the log golden checkpoint being cosigned (RFC-ACDP-0015 §5).
    chain = fixture_data.get("chains_to_log_fixture")
    if chain:
        log_fx = json.loads((CONFORMANCE / chain).read_text())
        cp = log_fx["vectors"][0]["expected"]["log_checkpoint"]
        for field in ("log_id", "tree_size", "root_hash"):
            if wc.get(field) != cp.get(field):
                fail(fixture, name, f"witnessed_checkpoint.{field} does not match {chain} checkpoint ({cp.get(field)})")
                return False

    return True


def check_witness_quorum(fixture, fixture_data):
    """RFC-ACDP-0015 §8: a checkpoint is N-witnessed = number of DISTINCT witness_id
    values whose cosignatures verify over one (log_id, tree_size, root_hash)."""
    exp = fixture_data.get("expected_quorum")
    if not exp:
        return None
    seen = {}  # (log_id, tree_size, root_hash) -> set(witness_id)
    for v in fixture_data.get("vectors", []):
        u = v.get("cosignature_unsigned", {})
        wc = u.get("witnessed_checkpoint", {})
        tup = (wc.get("log_id"), wc.get("tree_size"), wc.get("root_hash"))
        seen.setdefault(tup, set()).add(u.get("witness_id"))
    target = (exp["log_id"], exp["tree_size"], exp["root_hash"])
    n = len(seen.get(target, set()))
    if n != exp["witnessed_count"]:
        fail(fixture, "quorum", f"N-witnessed mismatch. expected {exp['witnessed_count']} distinct witnesses over {target}, got {n}")
        return False
    return True


def check_chain_kat(fixture, vector):
    """chain-* known-answer vectors (RFC-ACDP-0017 §9.2, §14): recompute evidence_digest,
    verdict_digest and as_of_digest from the pinned bundle and verdict files and compare
    them with the pinned values and with the digests the verdict itself carries. This
    pins the digest arithmetic and the as-of projection; the stage values inside the
    verdict are produced by verify_chain implementations, not re-derived here."""
    name = vector.get("name", "?")
    try:
        evidence = json.loads((ROOT / vector["evidence"]).read_text())
        verdict = json.loads((ROOT / vector["verdict"]).read_text())
    except (KeyError, OSError, ValueError) as e:
        fail(fixture, name, f"cannot load KAT files: {e}")
        return False

    def digest(obj):
        return "sha256:" + hashlib.sha256(jcs.canonicalize(obj)).hexdigest()

    computed = {"evidence_digest": digest(evidence),
                "verdict_digest": digest({k: v for k, v in verdict.items()
                                          if k not in ("as_of_digest", "verdict_digest")})}
    if verdict.get("as_of") is None:
        computed["as_of_digest"] = None
    else:
        projection = {k: verdict[k] for k in (
            "verdict_version", "roots", "as_of", "limits", "require_attested_events",
            "options_digest", "complete", "control", "frontier")}
        projection["nodes"] = [{k: n[k] for k in ("ctx_id", "depth", "derived_from", "as_of") if k in n}
                               for n in verdict["nodes"]]
        projection["chain"] = {"as_of": verdict["chain"]["as_of"]}
        projection["tainted_paths"] = {"as_of": verdict["tainted_paths"]["as_of"]}
        computed["as_of_digest"] = digest(projection)

    ok = True
    for key, value in computed.items():
        if vector.get(key) != value:
            fail(fixture, name, f"{key}: pinned {vector.get(key)} != computed {value}")
            ok = False
        if verdict.get(key) != value:
            fail(fixture, name, f"{key}: verdict carries {verdict.get(key)} != computed {value}")
            ok = False
    if verdict.get("roots") != vector.get("roots") or verdict.get("as_of") != vector.get("as_of"):
        fail(fixture, name, "verdict roots/as_of differ from the vector's inputs")
        ok = False
    return ok


def check_revocation_class(fixture, vector):
    """rev-007 known answers (RFC-ACDP-0014 §7): classify one context's key_revocation
    stage from already-verified inputs and compare class, boundary and attribution."""
    name = vector.get("name", "?")
    inp, exp = vector["input"], vector["expected"]
    ctx = inp["context"]

    def ts(s):
        return datetime.fromisoformat(s.replace("Z", "+00:00"))

    def applies(r):
        if r.get("type") not in ("key-revocation", "acdp:key-revocation"):
            return False
        if r.get("revoked_key_fingerprint") != ctx["key_fingerprint"]:
            return False
        if r.get("trust_class") == "producer-signed":
            return r.get("agent_id") == ctx["agent_id"]
        if r.get("trust_class") == "registry-attested":
            return r.get("revoked_key_controller") == ctx["agent_id"]
        return False

    members = [r for r in inp["revocations"] if applies(r)]
    if not members:
        got = {"key_revocation": "not-revoked", "boundary": None, "revocation_ctx_id": None}
    else:
        first = min(members, key=lambda r: ts(r["compromised_since"]))
        boundary = first["compromised_since"]
        rc = inp["receipt"]
        if not rc or not rc.get("verified") or rc.get("key_status") != "current":
            cls = "unplaceable"
        elif ts(rc["created_at"]) < ts(boundary):
            cls = "pre-compromise"
        else:
            cls = "revoked"
        got = {"key_revocation": cls, "boundary": boundary, "revocation_ctx_id": first["ctx_id"]}
    if inp.get("unknown_lookups", 0) and got["key_revocation"] in ("not-revoked", "pre-compromise"):
        got = {"key_revocation": "unknown", "boundary": None, "revocation_ctx_id": None}
    if got != exp:
        fail(fixture, name, f"expected {exp}, got {got}")
        return False
    return True


def check_hint_hmac(fixture, vector):
    """rec-007 change-hint HMAC known answer (RFC-ACDP-0018 §8.2): v1 =
    hex(HMAC-SHA-256(key = UTF-8 bytes of the secret string as served, t + "." + body)).
    The base64-decoded secret is NOT the key; not_header pins that wrong reading."""
    import hmac
    name = vector.get("name", "?")
    msg = f"{vector['t']}.".encode() + vector["body"].encode()
    v1 = hmac.new(vector["secret"].encode(), msg, hashlib.sha256).hexdigest()
    header = f"t={vector['t']},v1={v1}"
    decoded = hmac.new(base64.b64decode(vector["secret"]), msg, hashlib.sha256).hexdigest()
    ok = True
    if header != vector.get("expected_header"):
        fail(fixture, name, f"expected_header {vector.get('expected_header')} != computed {header}")
        ok = False
    if vector.get("not_header") != f"t={vector['t']},v1={decoded}" or decoded == v1:
        fail(fixture, name, "not_header must be the (rejected) MAC under the base64-decoded key")
        ok = False
    return ok


def change_envelope_verdict(entry, served):
    """RFC-ACDP-0018 §7 envelope consistency, in rec-009's check_order.
    Returns (verdict, reason)."""
    kind = entry.get("kind")
    ev = "event_receipt" if kind == "lifecycle" else "registry_receipt"
    t = entry[ev]["accepted_at" if kind == "lifecycle" else "created_at"]
    if entry.get("recorded_at") != t:
        return "reject", "recorded_at_mismatch"
    if kind == "lifecycle":
        if entry["event"].get("ctx_id") != entry["ctx_id"] or entry["event_receipt"].get("ctx_id") != entry["ctx_id"]:
            return "reject", "ctx_id_mismatch"
    elif kind == "key_revocation":
        if entry["registry_receipt"].get("ctx_id") != entry["ctx_id"]:
            return "reject", "ctx_id_mismatch"
    elif kind == "superseded":
        if entry["registry_receipt"].get("ctx_id") != entry.get("superseded_by"):
            return "reject", "ctx_id_mismatch"
        if entry.get("superseded_by") == entry["ctx_id"]:
            return "reject", "self_supersession"
        if entry["registry_receipt"].get("lineage_id") != entry.get("lineage_id"):
            return "reject", "lineage_id_mismatch"
    else:
        return "reject", "unknown_kind"
    mine, theirs = (entry["event"], served.get("lifecycle_event")) if kind == "lifecycle" \
        else (entry["registry_receipt"], served.get("registry_receipt"))
    if theirs is None or jcs.canonicalize(mine) != jcs.canonicalize(theirs):
        return "reject", "evidence_mismatch"
    return "accept", None


def check_change_envelope(fixture, vector):
    """rec-009 entry-envelope known answer (RFC-ACDP-0018 §7)."""
    name = vector.get("name", "?")
    verdict, reason = change_envelope_verdict(vector["entry"], vector.get("served", {}))
    exp = vector.get("expected", {})
    if verdict != exp.get("verdict") or reason != exp.get("reason"):
        fail(fixture, name, f"expected {exp.get('verdict')}/{exp.get('reason')}, computed {verdict}/{reason}")
        return False
    return True


_CTX_ID_RE = None


def _mcp_derived_from(value, out):
    """RFC-ACDP-0019 §4.4: preorder walk in JCS order (object members sorted by
    UTF-16 code units, arrays in index order); a string VALUE that is a whole
    ctx_id is extracted, first occurrence kept."""
    import re
    global _CTX_ID_RE
    if _CTX_ID_RE is None:
        _CTX_ID_RE = re.compile(r"^acdp://[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*"
                                r"/[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
    if isinstance(value, dict):
        for k in sorted(value, key=lambda s: s.encode("utf-16-be")):
            _mcp_derived_from(value[k], out)
    elif isinstance(value, list):
        for x in value:
            _mcp_derived_from(x, out)
    elif isinstance(value, str) and _CTX_ID_RE.match(value) and value not in out and len(out) < 1000:
        out.append(value)
    return out


def check_mcp_vector(fixture, fixture_data, vector):
    """mcp-001 known answer (RFC-ACDP-0019 §4–§6): the salted call hashes, the
    unsalted endpoint_hash, derived_from extraction, the Idempotency-Key, the
    returned _meta, and (via check_ed25519_vector) the body's hash and signature."""
    name = vector.get("name", "?")
    if not check_ed25519_vector(fixture, fixture_data, vector):
        return False
    inp, exp = vector["inputs"], vector["expected"]
    pc = vector["producer_content"]
    rec = pc["metadata"]
    salt_b64 = inp["salt"]
    try:
        salt = base64.urlsafe_b64decode(salt_b64 + "=")
    except ValueError as e:
        fail(fixture, name, f"salt is not base64url: {e}")
        return False
    if len(salt) != 32 or salt.hex() != exp["salt_hex"]:
        fail(fixture, name, "salt MUST decode to exactly the 32 pinned bytes")
        return False

    def h(pre):
        return "sha256:" + hashlib.sha256(pre).hexdigest()

    result = inp["call_tool_result"]
    hashed = {k: result[k] for k in ("content", "structuredContent", "isError") if k in result}
    computed = {
        "endpoint_hash": h(jcs.canonicalize(inp["endpoint"])),
        "arguments_hash": h(salt + jcs.canonicalize(inp["arguments"])),
        "result_hash": h(salt + jcs.canonicalize(hashed)),
        "request_id_hash": h(salt + jcs.canonicalize(inp["request_id"])),
    }
    ok = True
    if hashed != exp["hashed_result"]:
        fail(fixture, name, "hashed_result must be the CallToolResult restricted to content/structuredContent/isError")
        ok = False
    for k, val in computed.items():
        pinned = rec["server"]["endpoint_hash"] if k == "endpoint_hash" else rec.get(k)
        if val != exp[k] or val != pinned:
            fail(fixture, name, f"{k}: computed {val}, expected {exp[k]}, record {pinned}")
            ok = False
    if rec.get("is_error") != bool(result.get("isError", False)) or rec.get("salted") is not True:
        fail(fixture, name, "record is_error/salted inconsistent with the inputs")
        ok = False
    derived = _mcp_derived_from(inp["arguments"], [])
    if derived != exp["derived_from"] or derived != pc["derived_from"]:
        fail(fixture, name, f"derived_from extraction mismatch: computed {derived}")
        ok = False
    if exp["idempotency_key"] != "acdp-mcp-" + exp["content_hash"][len("sha256:"):]:
        fail(fixture, name, "idempotency_key MUST be acdp-mcp-<content_hash hex>")
        ok = False
    returned = exp["returned_result"]
    if {k: returned[k] for k in hashed} != hashed:
        fail(fixture, name, "returned result altered content/structuredContent/isError")
        ok = False
    meta = dict(returned.get("_meta", {}))
    prov = meta.pop("io.acdp/provenance", None)
    upstream = {k: v for k, v in result.get("_meta", {}).items()}
    if meta != upstream:
        fail(fixture, name, "returned _meta must keep every upstream key unchanged")
        ok = False
    reg = vector.get("registry_assigned", {})
    want = {"ctx_id": reg.get("ctx_id"), "content_hash": exp["content_hash"],
            "registry": reg.get("origin_registry"), "salt": salt_b64}
    if prov != want:
        fail(fixture, name, f"io.acdp/provenance {prov} != {want}")
        ok = False
    return ok


_TRUST_PRECEDENCE = ["trusted", "expired", "out_of_scope", "untrusted_registry", "list_invalid"]


def trust_evaluate(tl, case):
    """Reference RFC-ACDP-0020 §6.2 evaluation of one body against one selected,
    verified trust-list version (single pin, so the §6.2 step 4 union is trivial).
    Timestamps are canonical millisecond UTC, so string order is time order."""
    body, receipt, caps, t = case["body"], case.get("receipt"), case.get("capabilities_profiles"), case["T"]
    out = {"profiles_checked": caps is not None}
    authority = body["ctx_id"].split("/")[2].lower()
    origin = body["origin_registry"].lower()
    if authority != origin:
        return {**out, "outcome": "untrusted_registry", "reason": "origin_mismatch"}
    if not (tl["valid_from"] <= t < tl["valid_until"]):
        return {**out, "outcome": "expired", "reason": "list_window"}
    best = None
    for i, e in enumerate(tl["entries"]):
        if e["origin"] != origin:
            continue
        pins = e.get("receipt_key_fingerprints")
        profiles = e.get("required_profiles", [])
        scope = e.get("scope")
        if receipt is not None and receipt["registry_did"] != e["registry_did"]:
            res = ("untrusted_registry", "registry_mismatch")
        elif (pins is not None or "acdp-registry-receipts" in profiles) and receipt is None:
            res = ("untrusted_registry", "receipt_required")
        elif pins is not None and receipt["registry_key_fingerprint"] not in pins:
            res = ("untrusted_registry", "receipt_key_unpinned")
        elif caps is not None and any(p not in caps for p in profiles):
            res = ("untrusted_registry", "profile_missing")
        elif ("valid_from" in e and t < e["valid_from"]) or ("valid_until" in e and t >= e["valid_until"]):
            res = ("expired", "entry_window")
        elif scope is not None and ("agent_ids" in scope or "agent_id_prefixes" in scope) and not (
                body["agent_id"] in scope.get("agent_ids", [])
                or any(body["agent_id"].startswith(p) for p in scope.get("agent_id_prefixes", []))):
            res = ("out_of_scope", "scope_agent")
        elif scope is not None and "did_methods" in scope and \
                ":".join(body["agent_id"].split(":")[:2]) not in scope["did_methods"]:
            res = ("out_of_scope", "scope_did_method")
        elif scope is not None and "types" in scope and body["type"] not in scope["types"]:
            res = ("out_of_scope", "scope_type")
        else:
            res = ("trusted", None)
        if best is None or _TRUST_PRECEDENCE.index(res[0]) < _TRUST_PRECEDENCE.index(best[0]):
            best = (res[0], res[1], i)
    if best is None:
        return {**out, "outcome": "untrusted_registry", "reason": "no_entry"}
    r = {**out, "outcome": best[0], "entry_index": best[2]}
    if best[1]:
        r["reason"] = best[1]
    return r


def check_trust_vector(fixture, fixture_data, vector):
    """trust-* known answers (RFC-ACDP-0020). A vector carrying producer_content is
    a golden trust-list body: the arithmetic is check_ed25519_vector verbatim
    (JCS, content_hash, Ed25519 over the ASCII content_hash, did:key identity), plus
    the §4.1 body constraints and the §5.2 step 4 runtime rules. A vector carrying
    evaluations replays the §6.2 algorithm against that golden list."""
    name = vector.get("name", "?")
    golden = next((v for v in fixture_data["vectors"] if "producer_content" in v), None)
    if golden is None:
        fail(fixture, name, "no golden trust-list vector")
        return False
    if "producer_content" in vector:
        if not check_ed25519_vector(fixture, fixture_data, vector):
            return False
        pc = vector["producer_content"]
        tl = pc.get("metadata", {})
        if pc.get("type") != "acdp:trust-list" or tl.get("trust_list_version") != "acdp-trust-list/1":
            fail(fixture, name, "type MUST be 'acdp:trust-list' with an acdp-trust-list/1 metadata object (§4.1)")
            return False
        if pc.get("agent_id") != fixture_data["test_keypair"].get("did_key"):
            fail(fixture, name, "issuer (agent_id) MUST be the test did:key")
            return False
        if not tl["valid_from"] < tl["valid_until"]:
            fail(fixture, name, "valid_from MUST be before valid_until (§5.2 step 4)")
            return False
        for i, e in enumerate(tl["entries"]):
            if e["registry_did"] != "did:web:" + e["origin"]:
                fail(fixture, name, f"entry {i}: registry_did MUST equal 'did:web:' + origin (§5.2 step 4)")
                return False
        return True
    tl = golden["producer_content"]["metadata"]
    ok = True
    for case in vector.get("evaluations", []):
        got = trust_evaluate(tl, case)
        if got != case["expected"]:
            fail(fixture, f"{name} / {case.get('name', '?')}", f"expected {case['expected']} got {got}")
            ok = False
    if not vector.get("evaluations"):
        fail(fixture, name, "evaluation vector has no cases")
        ok = False
    return ok


def _b64u(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _ms(ts):
    """Canonical RFC 3339 millisecond UTC timestamp -> datetime (for window arithmetic)."""
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")


def keyless_classify(window, case):
    """RFC-ACDP-0021 §8.2: the keyless key status, in the normative check order."""
    att = case["attestation"]
    if not att["valid"]:
        return {"status": "refused", "reason": "attestation_invalid"}
    if not att["registry_accepted"]:
        return {"status": "refused", "reason": "untrusted_attester"}
    if not att["bindings_ok"]:
        return {"status": "refused", "reason": "attestation_mismatch"}
    r = case["receipt"]
    if not r or not (r["verified"] and r["registry_is_attester"] and r["fingerprint_matches"]):
        return {"status": "refused", "reason": "unplaceable"}
    t = r["created_at"]
    if not (window["not_before"] <= t < window["not_after"]):
        return {"status": "refused", "reason": "outside_attestation_window"}
    if not case["signature_valid"]:
        return {"status": "refused", "reason": "invalid_signature"}
    if att["retracted"]:
        return {"status": "refused", "reason": "attestation_withdrawn"}
    revs = case.get("revocations", [])
    if revs:
        boundary = min(rv["compromised_since"] for rv in revs)
        if t >= boundary:
            return {"status": "refused", "reason": "revoked"}
        return {"status": "historically_authorized_pre_compromise"}
    listed = case["identity_listed_now"]
    if listed == "unreachable":
        return {"status": "refused", "reason": "controller_unreachable"}
    return {"status": "currently_authorized" if listed else "historically_authorized"}


def keyless_supersede(pred, succ):
    """RFC-ACDP-0021 §7: who may supersede a body under the same agent_id."""
    if succ["kind"] == "controller" or succ.get("org_wide"):
        return {"result": "allowed"}
    if pred["kind"] == "keyless" and pred["identity"] == succ["identity"]:
        return {"result": "allowed"}
    return {"result": "refused", "reason": "keyless_identity_mismatch"}


def check_keyless_vector(fixture, fixture_data, vector):
    """kl-* known answers (RFC-ACDP-0021). The attestation and the keyless body are
    ordinary signed bodies (JCS, content_hash, Ed25519 over the ASCII content_hash),
    signed by the registry key and the ephemeral key respectively; on top we pin the
    §5.3 attestation rules, the §5.1 proof of possession, and replay the §8.2 and §7
    tables."""
    name = vector.get("name", "?")
    kind = vector.get("kind")
    exp = vector.get("expected", {})
    vectors = fixture_data["vectors"]
    att_vec = next((v for v in vectors if v.get("kind") == "attestation"), None)
    eph = fixture_data["ephemeral_test_keypair"]
    eph_priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(eph["private_seed_hex"]))
    eph_raw = eph_priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    if eph_raw.hex() != eph["public_key_hex"]:
        fail(fixture, name, "ephemeral public_key_hex does not match its seed")
        return False

    def body_sig(priv):
        _, content_hash, ok = _canonicalize_and_hash(fixture, name, vector)
        if not ok:
            return None, None
        return content_hash, priv.sign(content_hash.encode("ascii"))

    if kind == "attestation":
        reg = fixture_data["registry_test_keypair"]
        reg_priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(reg["private_seed_hex"]))
        content_hash, sig = body_sig(reg_priv)
        if content_hash is None:
            return False
        if sig.hex() != exp.get("signature_value_hex") or base64.b64encode(sig).decode() != exp.get("signature_value_base64"):
            fail(fixture, name, "registry signature mismatch")
            return False
        pc = vector["producer_content"]
        m = pc["metadata"]
        if pc.get("type") != "acdp:key-attestation" or m.get("attestation_version") != "acdp-key-attestation/1":
            fail(fixture, name, "type MUST be acdp:key-attestation with an acdp-key-attestation/1 metadata object (§5.3)")
            return False
        if pc.get("visibility") != "public":
            fail(fixture, name, "an attestation MUST be public (§5.3)")
            return False
        if pc.get("agent_id") != reg["key_id"].split("#")[0] or not vector["ctx_id"].startswith("acdp://" + pc["agent_id"][len("did:web:"):] + "/"):
            fail(fixture, name, "agent_id MUST be the attesting registry's DID, matching the ctx_id authority (§5.3)")
            return False
        jwk = m["public_key_jwk"]
        if jwk != {"crv": "Ed25519", "kty": "OKP", "x": _b64u(eph_raw)}:
            fail(fixture, name, "public_key_jwk is not the canonical Ed25519 JWK of the ephemeral key")
            return False
        thumb = _b64u(hashlib.sha256(jcs.canonicalize(jwk)).digest())
        if thumb != exp.get("jwk_thumbprint") or thumb != eph["jwk_thumbprint"]:
            fail(fixture, name, f"RFC 7638 thumbprint mismatch: {thumb}")
            return False
        fp = key_fingerprint(eph_raw)
        if m["key_fingerprint"] != fp or eph["key_fingerprint"] != fp:
            fail(fixture, name, "key_fingerprint is not the RFC-ACDP-0010 §6 fingerprint of the attested key")
            return False
        if m["key_id"] != f"{m['controller']}#acdp-kl-{fp[len('sha256:'):]}":
            fail(fixture, name, "key_id MUST be <controller>#acdp-kl-<fingerprint hex> (§6.1)")
            return False
        span = (_ms(m["not_after"]) - _ms(m["not_before"])).total_seconds()
        if not 0 < span <= 3600:
            fail(fixture, name, f"window MUST be non-empty and at most 3600 s (§5.2), got {span}")
            return False
        return True

    if kind == "keyless_body":
        content_hash, sig = body_sig(eph_priv)
        if content_hash is None:
            return False
        pc = vector["producer_content"]
        am = att_vec["producer_content"]["metadata"]
        want = {"algorithm": am["algorithm"], "key_id": am["key_id"], "value": base64.b64encode(sig).decode()}
        if exp.get("signature") != want:
            fail(fixture, name, f"signature mismatch: expected {exp.get('signature')} got {want}")
            return False
        if pc.get("agent_id") != am["controller"]:
            fail(fixture, name, "agent_id MUST equal the attestation controller (§6.2)")
            return False
        ka = pc.get("key_attestation", {})
        if ka.get("ctx_id") != att_vec["ctx_id"] or ka.get("content_hash") != att_vec["expected"]["content_hash"]:
            fail(fixture, name, "key_attestation MUST name the attestation's ctx_id and content_hash (§6.2)")
            return False
        return True

    if kind == "pop":
        token_hash = "sha256:" + hashlib.sha256(vector["token"].encode("ascii")).hexdigest()
        pre = vector["pop_preimage"]
        am = att_vec["producer_content"]["metadata"]
        if token_hash != exp.get("token_hash") or pre.get("token_hash") != token_hash or am["token_hash"] != token_hash:
            fail(fixture, name, "token_hash mismatch")
            return False
        if pre.get("key_fingerprint") != am["key_fingerprint"] or pre.get("controller") != am["controller"]:
            fail(fixture, name, "proof-of-possession preimage does not bind the attested key and controller")
            return False
        canon = jcs.canonicalize(pre)
        if canon.decode() != exp.get("pop_canonical_form"):
            fail(fixture, name, "pop_canonical_form mismatch")
            return False
        if base64.b64encode(eph_priv.sign(canon)).decode() != exp.get("pop_value_base64"):
            fail(fixture, name, "pop_value_base64 mismatch")
            return False
        return True

    if kind == "pop_p256":
        # RFC-ACDP-0021 §5.1: an ecdsa-p256 PoP is the 64-byte r||s form of
        # RFC-ACDP-0001 §5.10; DER is rejected. ECDSA is not deterministic, so verify only.
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
        from cryptography.exceptions import InvalidSignature
        kp = fixture_data["p256_test_keypair"]
        priv = ec.derive_private_key(int(kp["private_scalar_hex"], 16), ec.SECP256R1())
        pub = priv.public_key()
        comp = pub.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.CompressedPoint)
        nums = pub.public_numbers()
        jwk = {"crv": "P-256", "kty": "EC", "x": _b64u(nums.x.to_bytes(32, "big")), "y": _b64u(nums.y.to_bytes(32, "big"))}
        if comp.hex() != kp["public_key_compressed_sec1_hex"] or jwk != kp["public_key_jwk"]:
            fail(fixture, name, "p256_test_keypair public key does not match its scalar")
            return False
        if _b64u(hashlib.sha256(jcs.canonicalize(jwk)).digest()) != kp["jwk_thumbprint"]:
            fail(fixture, name, "p256 RFC 7638 thumbprint mismatch")
            return False
        fp = key_fingerprint(comp)
        pre = vector["pop_preimage"]
        if kp["key_fingerprint"] != fp or pre.get("key_fingerprint") != fp:
            fail(fixture, name, "P-256 fingerprint MUST be over the 33-byte SEC1-compressed point (§5.3)")
            return False
        token_hash = "sha256:" + hashlib.sha256(vector["token"].encode("ascii")).hexdigest()
        if pre.get("token_hash") != token_hash:
            fail(fixture, name, "token_hash mismatch")
            return False
        canon = jcs.canonicalize(pre)
        if canon.decode() != exp.get("pop_canonical_form"):
            fail(fixture, name, "pop_canonical_form mismatch")
            return False

        def verify_p1363(sig):
            if len(sig) != 64:
                return False
            der = encode_dss_signature(int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big"))
            try:
                pub.verify(der, canon, ec.ECDSA(hashes.SHA256()))
                return True
            except InvalidSignature:
                return False

        if verify_p1363(base64.b64decode(vector["pop_value_base64"])) is not exp.get("p1363_accepted"):
            fail(fixture, name, "the r||s PoP MUST verify")
            return False
        der_sig = base64.b64decode(vector["pop_value_der_base64"])
        try:
            pub.verify(der_sig, canon, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            fail(fixture, name, "pop_value_der_base64 must be the same signature, DER-encoded")
            return False
        if (not verify_p1363(der_sig)) is not exp.get("der_rejected"):
            fail(fixture, name, "a DER-encoded PoP MUST be rejected")
            return False
        return True

    ok = True
    cases = vector.get("cases", [])
    for case in cases:
        if kind == "classification":
            got = keyless_classify(vector["window"], case)
        elif kind == "supersession":
            got = keyless_supersede(case["predecessor"], case["successor"])
        else:
            fail(fixture, name, f"unknown vector kind {kind!r}")
            return False
        if got != case["expected"]:
            fail(fixture, f"{name} / {case.get('name', '?')}", f"expected {case['expected']} got {got}")
            ok = False
    if not cases:
        fail(fixture, name, "table vector has no cases")
        ok = False
    return ok


def _vectors(data, fixture_id):
    """Vectors of an executable fixture; an empty/missing list is a fixture bug
    (the fixture would otherwise pass with zero assertions)."""
    vectors = data.get("vectors", [])
    if not vectors:
        fail(fixture_id, "-", "executable fixture has no vectors")
    return vectors


for path in sorted(CONFORMANCE.glob("*.json")):
    with open(path) as f:
        data = json.load(f)
    fixture_id = data.get("id", path.stem)

    if ARGS.only and not (fixture_id.startswith(ARGS.only) or path.stem.startswith(ARGS.only)):
        continue

    if not any(fixture_id.startswith(fam + "-") for fam in KNOWN_FAMILIES):
        fail(fixture_id, "-", f"unknown fixture family — id prefix not in registries/profiles.json fixture_families; the runner would silently skip it")
        continue

    if fixture_id.startswith("can-") or fixture_id.startswith("lin-"):
        # can-* fixtures carry JCS/SHA-256 vectors and (some) lineage vectors;
        # lin-* fixtures are dedicated lineage_id derivation golden vectors.
        # Both are verified by the same arithmetic check.
        for v in _vectors(data, fixture_id):
            result = check_canonicalization_and_hash(fixture_id, v)
            if result is True:
                passes += 1
            # result is None → descriptive vector, skipped silently
    elif fixture_id.startswith("sig-"):
        for v in _vectors(data, fixture_id):
            if v.get("negative"):
                ok = check_ed25519_strict_negative(fixture_id, data, v)
            else:
                ok = check_signature_vector(fixture_id, data, v)
            if ok:
                passes += 1
    elif fixture_id.startswith("rev-") and "test_keypair" in data:
        # rev golden vectors (rev-001) are executed; rev-002 is behavioral
        # (no test_keypair) and is skipped here.
        for v in _vectors(data, fixture_id):
            if check_revocation_vector(fixture_id, data, v):
                passes += 1
    elif fixture_id.startswith("fp-"):
        for v in _vectors(data, fixture_id):
            if check_fingerprint_vector(fixture_id, v):
                passes += 1
    elif fixture_id.startswith("rcpt-") and "registry_test_keypair" in data:
        # rcpt golden vectors (rcpt-001) are executed; rcpt-002..004 are behavioral
        # scenarios without a registry_test_keypair and are skipped here.
        for v in _vectors(data, fixture_id):
            if check_receipt_vector(fixture_id, data, v):
                passes += 1
    elif fixture_id.startswith("lhr-") and "registry_test_keypair" in data:
        # lhr golden vectors (lhr-001) are executed; lhr-002..004 are behavioral
        # scenarios without a registry_test_keypair and are skipped here.
        for v in _vectors(data, fixture_id):
            if check_lineage_head_receipt_vector(fixture_id, data, v):
                passes += 1
    elif fixture_id.startswith("log-") and "registry_test_keypair" in data:
        # log golden vectors (log-001, log-003) are executed; log-002 and log-004
        # are behavioral scenarios without a registry_test_keypair, skipped here.
        for v in _vectors(data, fixture_id):
            if check_log_vector(fixture_id, data, v):
                passes += 1
    elif fixture_id.startswith("wit-") and ("witness_test_keypair" in data or "witness_test_keypairs" in data):
        # wit golden vectors (wit-001, wit-003) are executed; wit-002 and wit-004
        # are behavioral scenarios without a witness test keypair, skipped here.
        for v in _vectors(data, fixture_id):
            if check_witness_cosignature_vector(fixture_id, data, v):
                passes += 1
        if check_witness_quorum(fixture_id, data) is True:
            passes += 1
    elif fixture_id.startswith("anc-") and "vectors" in data:
        # anc-004 is an arithmetic content_hash golden (a body carrying anchors,
        # proving the field enters the JCS preimage) verified by the same check
        # as can-/lin-; anc-001/002/003/005 are behavioral scenarios without a
        # top-level vectors array and are skipped here.
        for v in _vectors(data, fixture_id):
            result = check_canonicalization_and_hash(fixture_id, v)
            if result is True:
                passes += 1
    elif fixture_id.startswith("rev-") and "vectors" in data:
        # rev-007 carries the RFC-ACDP-0014 §7 classification known answers.
        for v in _vectors(data, fixture_id):
            if check_revocation_class(fixture_id, v):
                passes += 1
    elif fixture_id.startswith("rec-") and "vectors" in data:
        # rec-007 carries the change-hint HMAC known answer and rec-009 the
        # entry-envelope known answers; dispatched per vector on its shape
        # ("secret" vs "entry"). Every other rec-* scenario is behavioral.
        for v in _vectors(data, fixture_id):
            if "entry" in v:
                ok = check_change_envelope(fixture_id, v)
            elif "secret" in v:
                ok = check_hint_hmac(fixture_id, v)
            else:
                fail(fixture_id, v.get("name", "?"), "rec-* vector has neither 'entry' nor 'secret'")
                ok = False
            if ok:
                passes += 1
    elif fixture_id.startswith("mcp-") and "vectors" in data:
        # mcp-001 carries the tool-result known answer; mcp-002..007 are
        # behavioral and verified by proxy implementations.
        for v in _vectors(data, fixture_id):
            if check_mcp_vector(fixture_id, data, v):
                passes += 1
    elif fixture_id.startswith("trust-") and "vectors" in data:
        # trust-001 carries the golden trust-list body and the §6.2 evaluation
        # table; trust-002..007 are behavioral.
        for v in _vectors(data, fixture_id):
            if check_trust_vector(fixture_id, data, v):
                passes += 1
    elif fixture_id.startswith("kl-") and "vectors" in data:
        # kl-001 carries the keyless-signing known answers; kl-002..009 are
        # behavioral.
        for v in _vectors(data, fixture_id):
            if check_keyless_vector(fixture_id, data, v):
                passes += 1
    elif fixture_id.startswith("chain-") and "vectors" in data:
        # chain-001/002/003/010 carry known-answer vectors (pinned bundle +
        # verdict + digests); their remaining scenarios, and chain-004..009,
        # are behavioral and verified by verify_chain implementations.
        for v in _vectors(data, fixture_id):
            if check_chain_kat(fixture_id, v):
                passes += 1
    else:
        # pub-, vis-, ret-, dk-, rot-, lc-, fed- (and keypair-less rcpt-/lhr-/log-/rev-/wit-/
        # vectors-less anc-)
        # fixtures describe scenarios (request -> expected error code), not arithmetic
        # vectors. Their conformance is checked by registry/consumer implementations,
        # not by this static runner.
        skipped_behavioral.append(fixture_id)

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


if ARGS.only:
    if passes == 0 and not failures:
        print(f"✗ --only {ARGS.only!r} matched no executable fixtures "
              f"(behavioral matches: {', '.join(skipped_behavioral) or 'none'})", file=sys.stderr)
        sys.exit(1)
else:
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
    print(f"✓ All {passes} arithmetic conformance vectors passed "
          f"({len(skipped_behavioral)} behavioral fixtures left to live implementations).")
    sys.exit(0)
