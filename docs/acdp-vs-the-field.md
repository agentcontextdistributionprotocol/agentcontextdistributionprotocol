# ACDP vs. the Field

This document is non-normative. It positions ACDP against the protocols evaluators most often ask about: MCP, A2A, C2PA, AT Protocol, and DIDComm. The short version: none of these is a competitor for ACDP's actual job — a durable, signed, content-addressed publication substrate for agent knowledge — but several are near neighbors, and each does something ACDP deliberately does not. Where a neighbor does a job better, this document says so.

For what ACDP is, read [why-acdp.md](why-acdp.md) and [overview.md](overview.md) first. For what ACDP deliberately excludes, read [non-goals.md](non-goals.md); several comparisons below turn on those exclusions.

---

## The one-line map

| Protocol | Primary job | Temporal shape | ACDP relationship |
|---|---|---|---|
| **MCP** | Provision tools/context *into* a model session | Session-scoped, ephemeral | Complementary — an MCP server can serve ACDP-verified contexts |
| **A2A** | Live task delegation *between* agents | Task-scoped, ephemeral | Complementary — coordination that can cite ACDP contexts |
| **C2PA** | Signed provenance manifests for media assets | Permanent, travels with the asset | Closest overlap — different binding and distribution model |
| **AT Protocol** | DID-identified, signed, content-addressed records in personal repos | Permanent, replicated via relays | Closest architectural cousin — different topology and visibility model |
| **DIDComm** | Encrypted, transport-agnostic messaging between DIDs | Message-scoped, confidential | Different layer — private transport vs. published artifact |

---

## MCP (Model Context Protocol)

**What it does.** MCP standardizes how an application provisions tools, resources, and prompts *into* a model session. An MCP server exposes capabilities; a client (the model host) discovers and invokes them during a conversation. The unit of exchange is a live capability surface, scoped to a running session.

**How that differs from ACDP.** MCP moves context *into a model, now*. ACDP persists and distributes context *between agents and organizations, over time*. An MCP resource has no identity outside the session that fetched it: no content address, no producer signature, no lineage, no supersession. When the session ends, nothing remains that a third agent — in another org, next quarter — can find, verify, and build on. ACDP's unit is exactly that artifact: a JCS-canonicalized, SHA-256-content-addressed body, signed by its producer's DID, with a `derived_from` chain that is itself part of the signed content (RFC-ACDP-0001, RFC-ACDP-0002).

**Complementary, not competing.** The natural composition is an MCP server whose resources are backed by an ACDP consumer: the server retrieves contexts from a registry, verifies signatures and hashes locally per the `acdp-consumer` profile, and provisions only verified knowledge into the session. MCP answers "how does this model get context?"; ACDP answers "where did that context come from, who signed it, and is it still current?"

**What MCP does better.** Everything session-shaped. Interactive tool invocation, streaming, capability negotiation with a live host — ACDP has none of this and never will; discovery is poll-based keyword search and retrieval is plain HTTP GET (non-goals §2, §8).

---

## A2A (Agent2Agent)

**What it does.** A2A standardizes live task delegation between agents: agent cards for capability discovery, task lifecycles, message exchange, artifacts produced within a task. It is a coordination protocol — its core abstraction is *a task in flight between two parties*.

**How that differs from ACDP.** ACDP is deliberately coordination-agnostic (non-goals §1): it does not define sessions, delegation, negotiation, or task state. What it defines is the durable substrate such coordination can cite. When an A2A task completes, its artifact is — in A2A terms — a payload handed back to the requester. Published as an ACDP context, the same result becomes a permanent, signed, content-addressed commitment that agents *outside the task* can discover, verify, and derive from, with the evidence chain (`derived_from`) frozen into the signed body.

**Complementary, not competing.** An A2A agent can publish its deliverables as ACDP contexts and pass the `ctx_id` in its task response; the requester — or anyone else, later — verifies the producer signature locally rather than trusting the session that delivered it. Conversely, `acdp://` references in a task give delegated work an auditable evidence trail. Coordination protocols evolve quickly; the substrate is designed to outlive whichever one wins (see the manifesto's "Coordination without coordination").

**What A2A does better.** The live half of the problem: multi-turn negotiation, long-running task status, cancellation, capability matchmaking. ACDP has no request semantics at all — "ask an agent to produce X" is explicitly out of scope (non-goals §2).

---

## C2PA

**What it does.** C2PA defines signed provenance manifests for media assets — images, video, audio, documents. A manifest records assertions about how the asset was created and modified, is cryptographically bound to the asset's bytes via hard bindings (content hashes over the media data), and travels embedded in the file (with remote-manifest fallback). Trust flows from X.509 certificate chains to known signers.

**How that differs from ACDP.** This is the closest overlap in the field: both produce signed, hash-bound provenance artifacts designed to survive crossing organizational boundaries. The differences are structural:

- **What the signature binds.** C2PA binds to *media bytes* — the manifest asserts "this exact file". ACDP binds to *structured JSON* — the signature covers the JCS-canonical form of the producer's content, so the artifact is the claim itself (a fraud score, an analysis, a model card), not a wrapper around opaque bytes. Bulk data stays external behind `data_refs`, each with its own optional `content_hash`.
- **Where the artifact lives.** A C2PA manifest is embedded: it travels with the asset, works offline, and needs no infrastructure — but is silently *strippable* (remove the metadata and the provenance is simply gone; absence proves nothing). An ACDP context is a registry record: content-addressed under a stable `acdp://` URI, discoverable via search, and impossible to strip without breaking retrieval — but dependent on a registry staying reachable.
- **Lineage and correction.** C2PA records edit history *within* an asset's manifest chain. ACDP's `derived_from` is a signed cross-artifact, cross-registry DAG, and supersession gives corrections first-class semantics (`status: superseded`, the predecessor retrievable forever) rather than re-issuing the asset. Registry-attested identity (`ctx_id`, `created_at`) is bound by registry honesty in v0.1.0 and cryptographically attested by registry receipts since v0.2.0 (RFC-ACDP-0010).
- **Identity.** C2PA trusts certificate authorities; ACDP trusts DID documents the producer publishes (`did:web` in v0.1.0), with no issuing authority in the loop.

**What C2PA does better.** Binding to bytes. If the artifact *is* the media file — a photograph whose pixels must be attested — C2PA's hard bindings and embedded travel are the right design, and ACDP has no equivalent: it can hash-reference a file via `data_refs` but cannot make the provenance travel inside it. C2PA also has a mature ecosystem of capture-device and editing-tool integrations that a registry protocol will never have. Use C2PA for media authenticity; use ACDP when the unit of exchange is a structured claim between agents.

---

## AT Protocol

**What it does.** AT Protocol (Bluesky's foundation) gives every account a DID, a signed Merkle-tree repository of content-addressed records (DAG-CBOR, CIDs), a personal data server (PDS) hosting it, and relays that aggregate repos into a firehose for application-level indexers. Accounts can migrate between PDSes because identity and data are self-certifying.

**How that differs from ACDP.** This is the closest *architectural* cousin: DID-identified actors, signed content-addressed records, verification independent of the host. The divergences are topology and audience:

- **Repo/firehose vs. registry.** ATProto organizes records per-*account* and distributes by replication — relays crawl repos and rebroadcast everything as a stream that indexers consume. ACDP organizes records per-*registry* and distributes by reference: nothing is pushed anywhere; a consumer resolves an `acdp://` URI to exactly the context it needs and walks `derived_from` from there (RFC-ACDP-0006). For a global social feed, replication is the point; for cross-org agent knowledge, most of which no global observer should ever see, pull-by-reference is.
- **Account portability vs. registry-anchored lineage.** ATProto's signature move is that an account can pick up its whole repo and move hosts with identity intact. ACDP contexts are anchored to their origin registry: `ctx_id` carries the minting registry's authority, and lineage continues where it began — cross-registry supersession is an explicit v0.1.0 non-goal (reserved in RFC-ACDP-0009). If the producer's registry disappears, its contexts become unresolvable at their original URIs. This is a real trade-off ATProto handles better; ACDP accepts it to keep lineage verification simple, and treats migration as a future-version problem rather than a v0.1.0 invariant.
- **Visibility.** ATProto is public-by-design: repos are crawlable, and the firehose exists precisely so anyone can index everything. ACDP has registry-enforced visibility as a protocol feature — `public` / `restricted` / `private` with audience lists, 404-indistinguishability for unauthorized requesters, and scoped search counts (RFC-ACDP-0002 §7, RFC-ACDP-0008 §4.5). An agent publishing a fraud analysis to a defined cohort has no home on a public firehose.

**What AT Protocol does better.** Account portability (genuinely unsolved in ACDP v0.1.0), high-volume replication and real-time dissemination (ACDP is poll-based — non-goals §8), and a proven large-scale deployment. If the workload looks like "many small public records from human accounts, globally indexed", ATProto's shape is better. If it looks like "signed machine conclusions with evidence chains, mostly non-public, resolved on demand across org boundaries", that is what ACDP was shaped for.

---

## DIDComm

**What it does.** DIDComm v2 is encrypted, transport-agnostic *messaging* between DIDs: authenticated encryption from keys in DID documents, routing through mediators, higher-level protocols (credential issuance, proof presentation) layered on top. Its unit is a confidential message from one party to specific recipients.

**How that differs from ACDP.** Almost everything except the shared reliance on DIDs. A DIDComm message is encrypted to its recipients and exists only for them; there is no discovery, no content addressing, no public artifact — by design. An ACDP context is the opposite object: a *published, discoverable* artifact, signed but **not** encrypted ([non-goals.md §11](non-goals.md): end-to-end encryption drags in a key-distribution model the substrate deliberately avoids). ACDP's confidentiality story is structural instead: keep sensitive payloads out of the body behind `data_refs` under the source system's own ACLs, and scope the metadata with `visibility`.

**Complementary, not competing.** They meet in practice: a `private` context's `ctx_id` has to reach its audience out-of-band (RFC-ACDP-0005 §2.5.5), and a DIDComm channel is a natural way to carry it. DIDComm moves the pointer confidentially; ACDP holds the artifact durably.

**What DIDComm does better.** Confidentiality, full stop. If the content itself must be unreadable to everyone but named recipients — not just undiscoverable — ACDP cannot do that and does not try; a registry operator can always read the bodies it stores. Use DIDComm (or any E2E channel) for the secret; use ACDP for the signed, citable record that a secret-referencing conclusion exists.

---

## What this adds up to

ACDP occupies a spot none of these fill: **permanent, signed, content-addressed, discoverable, visibility-scoped JSON artifacts with verifiable lineage, distributed by reference across registries.** MCP and A2A are session layers that can sit on top of it. DIDComm is a confidential channel beside it. C2PA and ATProto share its cryptographic instincts but bind to different objects (media bytes; personal repos) and distribute through different topologies (embedded manifests; firehose replication).

The honest scorecard: C2PA binds provenance to bytes better, ATProto does portability and scale-out replication better, DIDComm does confidentiality better, and MCP/A2A do live interaction better. ACDP's bet — argued in the [manifesto](../manifesto/manifesto.md) — is that the missing layer under agent ecosystems is none of those things: it is the durable substrate on which agent knowledge accumulates and stays verifiable. That is the one job this protocol does, and the non-goals exist to keep it doing only that.

---

## Questions evaluators actually ask

**"Why not just extend C2PA to JSON claims?"**
C2PA's manifest store, hard bindings, and trust lists are all shaped around an asset file that the manifest travels inside. ACDP's core operations — registry search, `acdp://` resolution, lineage walks across registries, supersession with registry-attested `status`, visibility-scoped retrieval — have no C2PA analog, and bolting a registry protocol onto an embedded-manifest format would reproduce ACDP with C2PA's certificate model attached. Where the two meet naturally: an ACDP context can *reference* a C2PA-signed media asset via `data_refs` (with its own `content_hash`), giving an agent-authored claim about a provenance-carrying asset.

**"Why not build on AT Protocol?"**
It was seriously considered as prior art — the record layer is genuinely close. Three requirements broke it: registry-enforced non-public visibility (ATProto records are crawlable by design), pull-by-reference distribution without a firehose dependency (agent knowledge should not require relay infrastructure to be resolvable), and a JSON/JCS wire format that any HTTP-speaking agent can verify without a DAG-CBOR/CID/Merkle-repo stack. What was kept: DID-based identity, signature-over-content-address, and the self-certifying-record instinct.

**"Is ACDP a blockchain?"**
No. There is no global ledger, no consensus, and no token. Registries are ordinary HTTPS services; trust comes from producer signatures verified locally, not from replication. [why-acdp.md](why-acdp.md) covers why DAG/ledger systems were rejected as the substrate: they solve permanence and provenance at an operational cost (coordination, consensus) that HTTP + JSON + signatures does not require for this problem. The v0.3.0 transparency log (RFC-ACDP-0012, promoting the RFC-ACDP-0009 §2.11 reservation) borrows Merkle checkpoints from certificate-transparency practice — an audit structure, not a chain.

**"Does using MCP or A2A mean I don't need ACDP?"**
They answer different audits. MCP/A2A can tell you *what an agent was given or asked to do in a session*. Neither leaves an artifact that a third party can verify after the session is gone — no content address, no producer signature, no lineage. If a regulator, a downstream team, or a future agent needs "what did the system know when it decided, and who signed for it" (the manifesto's 03:11 scenario), that is the substrate question, and it is the only question ACDP answers.

**"Which one wins?"**
Wrong frame — the realistic deployment stacks them: DIDComm (or any secure channel) carries pointers, MCP provisions verified contexts into model sessions, A2A coordinates the work, C2PA attests any media artifacts, and ACDP holds the signed knowledge those layers produce and cite.

---

## See also

- [why-acdp.md](why-acdp.md) — the problem statement and what existing *data* tools don't solve.
- [non-goals.md](non-goals.md) — the design boundaries several comparisons above rest on.
- [version-matrix.md](version-matrix.md) — which spec versions and implementations exist today.
