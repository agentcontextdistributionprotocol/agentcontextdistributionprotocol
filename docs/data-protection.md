# Data Protection and Erasure

This document is non-normative. It explains ACDP's posture toward data-protection regimes that grant erasure rights (GDPR Art. 17 "right to erasure", CCPA deletion requests, and similar), and what producers and operators should do about it. The underlying design decisions are normative and live elsewhere: bodies are permanent ([non-goals.md §5](non-goals.md), [§13](non-goals.md)), supersession is the only correction mechanism in v0.1.0 (RFC-ACDP-0003 §3), and retraction is reserved (RFC-ACDP-0009 §2.1).

The one-sentence posture: **an ACDP body is a permanent, signed, content-addressed record — so personal and sensitive data belongs *behind* the body, in an erasable system of record, not *inside* it.**

---

## 1. Why bodies are unerasable

Permanence is not an oversight; it is the substrate's core invariant. Every `derived_from` chain, every `content_hash`, every lineage verification assumes the referenced body still exists, byte-identical to what its producer signed. Deleting a body silently breaks every downstream context that cites it — the exact "the evidence it relied on no longer exists" failure the protocol was built to eliminate (see the [manifesto](../manifesto/manifesto.md)). v0.1.0 therefore has no delete, no redact, and no retract on the wire.

The consequence for data protection is direct: **anything placed in a body's producer-controlled fields (`title`, `summary`, `metadata`, embedded `data_refs`, …) must be assumed permanent and unerasable**, retrievable by the body's audience for as long as the registry exists.

## 2. Carry personal data by reference, not by value

Producers handling personal or otherwise erasable-on-demand data SHOULD keep it out of the body entirely and reference it instead: a `data_refs[].location` pointing at a system of record that *can* honor an erasure request (a database row, an object-store key, an internal API — under that system's own ACLs, per RFC-ACDP-0002 §6.4).

This split gives you both properties at once:

- The **body** stays permanent and verifiable: it records *that* a conclusion was produced, by whom, when, derived from what — typically legitimate-interest metadata rather than the personal data itself.
- The **data** stays erasable: when the data subject exercises their rights, the referenced record is deleted in its home system. The `data_refs[].location` then dereferences to nothing (or 403/410), and if the DataRef carried a `content_hash`, consumers can still prove what the bytes *were* committed to without the bytes existing anywhere.

Things that defeat this pattern, all of which producers SHOULD treat as review-blocking: personal data in `title`/`summary`/`tags` (these are also search-indexed — RFC-ACDP-0005), personal data in `metadata`, embedded `data_refs` carrying personal payloads (embedded content is part of the registry record and fully permanent), and personal data encoded into the `location` URI itself (query strings survive in the signed body forever).

## 3. What supersession remediates — and what it does not

Supersession-with-a-narrower-audience is the protocol's remediation for *over-shared* data: publish a v2 with `supersedes: <v1 ctx_id>` and a smaller (or absent) `audience`; v1 flips to `status: superseded` and honest consumers move to v2 (RFC-ACDP-0002 §7.1, RFC-ACDP-0003 §3).

Be precise about what this does **not** do:

- **The original stays retrievable to its original audience.** Supersession changes registry state, not the v1 body. Every DID in v1's audience (and, for `public`, everyone) can still retrieve v1 by `ctx_id`, forever, with `status: superseded` attached. Supersession is a correction signal, not an un-publish.
- **It does not claw back copies.** Anyone who already retrieved v1 has it; the protocol never pretended otherwise.
- **It does not shrink search exposure of what was already found.** It prevents *new* reliance by honest consumers; it does not undo disclosure.

So: supersession is the right tool for "I shared this more widely than I should have, stop the bleeding", and the wrong tool for "this must cease to exist". For the latter, the data had to be behind a reference (§2) — or the deployment is into §5 territory.

## 4. Retraction is reserved — and will mark, not delete

RFC-ACDP-0009 §2.1 reserves a lifecycle-events mechanism through which a producer can formally *withdraw* a context. Two things are worth knowing now: it is not specified in v0.1.0 (implementations must not invent it), and its design intent is **mark-not-delete** — a signed retraction event appended to registry state, with the body remaining retrievable as the record of what was withdrawn. Even future retraction is a reputational/epistemic operation, not an erasure mechanism. Do not defer a data-protection problem to it.

## 5. Deployment-policy hard deletes (legal holds)

A registry operator under a court order or a data-protection ruling may be legally compelled to hard-delete a body regardless of what this protocol says. ACDP cannot forbid that — but it can insist on how it surfaces:

- A hard delete is an **out-of-protocol override**, not an ACDP operation. A registry that performs one is, for the affected lineage, no longer serving the v0.1.0 contract.
- It **breaks lineage verifiability for every downstream derived context**: any body whose `derived_from` cites the deleted `ctx_id` now has an unverifiable evidence link, on this registry, permanently.
- The break MUST be surfaced to consumers *as a break*, never as silent absence. A registry that deletes should return an explicit "removed by deployment policy" signal (at minimum, distinguishable in operator documentation and audit logs from plain `not_found`), because a bare 404 is indistinguishable from "never existed" — and consumers walking a `derived_from` chain will misread silence as a forged or mistaken reference rather than a legal hold. Broken chain ≠ silent absence: the first is an auditable event; the second corrupts every downstream trust evaluation that touches it.
- Operators SHOULD record the deletion event (what was deleted, under what authority, when) in an out-of-band audit log, so the lineage break remains explainable years later.

A deployment that expects legal-hold deletions regularly has a design smell: it is putting erasable data in permanent records. Fix it at publication time (§2), not at subpoena time.

## 6. Quick checklist

**Producers**
- Personal/sensitive payloads: by reference (`data_refs[].location` into an erasable system of record), never embedded, never in `title`/`summary`/`tags`/`metadata`.
- Assume every producer-controlled byte you sign is permanent and, for its audience, retrievable forever.
- Over-shared? Supersede with a narrower audience immediately — and understand the original remains retrievable to its original audience.

**Operators**
- Treat any hard delete as an out-of-protocol legal-hold action: document it, audit-log it, and surface it to consumers as an explicit policy removal, not a silent 404.

**Consumers**
- A `derived_from` reference that no longer resolves is a broken evidence link, not proof the context never existed. Treat unexplained absence as reduced assurance, and expect conformant deployments to distinguish policy removal from `not_found`.

---

## See also

- [non-goals.md](non-goals.md) §5 (retraction), §11 (encrypted bodies), §13 (hard deletion) — the design boundaries this posture rests on.
- RFC-ACDP-0002 §6.4 (visibility scope vs. external data ACLs) and §7.1 (visibility is permanent for a given body).
- RFC-ACDP-0003 §3 (supersession), RFC-ACDP-0009 §2.1 (reserved retraction).
