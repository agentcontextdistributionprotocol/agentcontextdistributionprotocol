#!/usr/bin/env python3
"""One-shot generator for the ACDP 0.5.0 golden-vector values (RFC-ACDP-0016).

Computes the canonical form and SHA-256 digest for the anc-004 conformance
fixture — a body carrying the new `anchors` field, proving the field enters
the JCS content_hash preimage (RFC-ACDP-0001 §5.7 unknown-producer-field
rule made first-class by RFC-ACDP-0016). Uses the same `jcs` library the
conformance runner uses. No signing is involved (content_hash only, same
shape as the can-* vectors) — follows scripts/gen-0.4.0-vectors.py.
"""

import json
import hashlib

import jcs


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# The external artifact's own content hash — an opaque producer claim, not
# derived from anything in this repo. A fixed test value, same spirit as the
# all-zero signature in schema fixtures.
anchor_content_hash = "sha256:" + sha256_hex(b"external-artifact-test-vector")

body_with_anchors = {
    "version": 1,
    "supersedes": None,
    "agent_id": "did:agent:test",
    "contributors": [],
    "title": "settlement finalized",
    "type": "data_snapshot",
    "data_refs": [],
    "anchors": [
        {
            "scheme": "macp.commitment",
            "content_hash": anchor_content_hash,
        }
    ],
}

canonical = jcs.canonicalize(body_with_anchors)

out = {
    "anchor_content_hash": anchor_content_hash,
    "anc_004": {
        "input": body_with_anchors,
        "canonical_form": canonical.decode("utf-8"),
        "sha256_hex": sha256_hex(canonical),
        "content_hash_field_value": "sha256:" + sha256_hex(canonical),
    },
}

print(json.dumps(out, indent=2, ensure_ascii=False))
