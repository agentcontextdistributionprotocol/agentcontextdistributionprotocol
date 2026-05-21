# The Substrate of Agent Knowledge
## When agents reason at the edge of organizations, the bottleneck is not capability — it is whether other agents can find, verify, and build on what was just produced.

*We are past the question of whether AI agents can produce useful work. The live question is whether the work an agent produces today is legible, attributable, and reusable by an agent that has never met it. This is a proposal for the missing substrate: a context as a first-class, signed, content-addressed artifact.*

---

## After capability, after coordination — substrate

The first wave of agent infrastructure asked whether software could reason. Models became capable. Agents acquired tools. Frameworks orchestrated calls. Single agents solve multi-step problems.

The second wave asked whether agents could *coordinate*. How do they vote, converge, divide work, and share state? That problem is far from settled, but it has dedicated standards, runtimes, and design patterns.

There is a third question, lying underneath both, that has no name yet: **how does an agent's *output* become an artifact that another agent — anywhere, in any organization, at any later time — can find, verify, and reuse?**

That question is not about capability. It is not about coordination. It is about the *substrate* on which agent knowledge accumulates.

Today, every framework answers it implicitly. Outputs live in a database the producing system happens to use. Discovery is a SQL join, an Elasticsearch index, or a vector store. "Provenance" is whatever the producing system thought to log. Cross-organization reuse is somewhere between "ad hoc API integration" and "we email each other CSVs". The result is the data equivalent of pre-Unix: every system inventing its own format for what is fundamentally the same artifact.

Capability made agents impressive. Coordination is making them collaborative. **Substrate will make their work compound.**

---

## The hidden cost of redundant analysis

Production agent systems often look productive from the outside. Reports get generated. Dashboards update. Alerts fire. Decisions get made.

Beneath the surface, the same analysis is happening in three places.

There is rarely a single, signed artifact that says *"this agent, signing with this key, examined these inputs at this time, produced this conclusion, and is committing to it permanently."* Instead the conclusion lives inside the producing system, in a format that system happens to use, behind whatever authentication it happens to require, with whatever lineage it happened to log. When a downstream agent needs the same conclusion, it has three choices:

- **Re-derive it** from raw inputs (expensive, time-consuming, and stochastic — the new agent may reach a different conclusion);
- **Integrate** with the upstream system point-to-point (custom adapter, custom auth, brittle, doesn't scale);
- **Pass plain text around** between agents (lossy, untraceable, unverifiable).

This is the same shape distributed systems were in before content addressing. It works in prototypes. It compounds at scale, where the cost of every new agent grows with the number of agents already in the system.

---

## A request at 03:11

To see why this matters, imagine an agent inside a large organization. At 03:11 an analyst-agent decides whether to act on a fraud signal. The signal has a confidence number, a feature vector, an internal reference to a model version. It was produced two hours earlier by a different agent in a different cluster.

The analyst-agent has to decide. It is, in that moment, looking at:

- *what* the signal claims (fraud likelihood for transaction T),
- *who* produced it (some upstream service, identified by an internal hostname),
- *when* it was produced (two hours ago — does that match the data window the signal is computed over?),
- *what evidence* the signal was derived from (the hard part).

The first three are routine. The fourth — *what other contexts did this conclusion build on* — is where every system improvises. If the signal was derived from a sentiment context and a data snapshot and a baseline model, the analyst has no portable way to walk back through that chain. There is no signed provenance traveling with the conclusion.

If the regulator asks at 03:14 *what was this decision based on?*, the answer is "we trusted the upstream service." That is a network trust statement, not a knowledge statement.

---

## Two temporal shapes of agent knowledge

Agent knowledge has two distinct lifecycles, and most systems blur them.

The first is **operational state**: the variables an agent maintains while it is running. Memory. Caches. Working set. This evolves continuously, is mostly local, and is mostly disposable. Operational state lives inside an agent's runtime.

The second is **published commitment**: the moment an agent says "I am willing to put my name on this conclusion, and I want other agents to be able to find it." Published commitments are not local state. They are shareable artifacts. They have an issuer, a time, evidence, and a payload. They should be addressable independent of the agent that produced them.

Most systems collapse the two. The conclusion is "stored" wherever the producing agent's database happens to be. There is no separate artifact representing the *commitment*. The result is that "what does the system know" becomes a lookup against running infrastructure, not a query against an artifact registry.

The Context is the published artifact.

---

## The structural shift: a context as a signed, content-addressed artifact

Now imagine the same agent, with one architectural change.

Before the analyst-agent decides whether to act, it walks back through the signed provenance chain. The fraud signal is an ACDP context. Its `derived_from` lists three other contexts: a sentiment analysis, a transaction snapshot, and a baseline model card. Each is fetched independently — possibly from a different registry, possibly from a different organization. Each carries its producer's signature. Each is content-addressed: any modification would change its `content_hash`, breaking the lineage.

The analyst-agent does five small things:

1. Fetch each context referenced in `derived_from`.
2. Verify each context's signature against its producing agent's DID document.
3. Verify each context's `content_hash` over the JCS-canonicalized body.
4. Check each context's `data_period` against the decision window.
5. Confirm the chain ends at primary data, not in another reasoning loop.

That is the entire epistemic check. No introspection call against the producing system. No upstream lookup. No re-derivation. The artifact is the evidence.

If the regulator calls at 03:14, there is one thing to point at: the chain. Each link's issuer, evidence, and timestamp are inspectable. Each signature ties a conclusion to a specific producer at a specific moment in time. **Knowledge becomes legible.**

---

## A context is a phase change

The core insight is structural. A published agent conclusion is not just another row in a database. It is a *contraction*: many evaluations — input data, model state, intermediate reasoning, the producer's confidence — collapse into a single signed statement. Phase changes deserve their own artifact.

Once the artifact exists, the rest of the system simplifies. Consumers stop carrying integration logic for every producer. Producers stop maintaining bespoke read APIs. Per-organization data formats stop multiplying. Every consumer becomes a *context verifier*: it fetches a body, checks a signature, walks a chain. Vendor lock-in dissolves at exactly the layer where it has been most painful — knowledge reuse.

This is the same lesson the rest of computing already learned in adjacent layers. Git didn't dictate code semantics; it gave you a content-addressed object store. JSON didn't dictate application semantics; it gave you a serialization format. ACDP doesn't dictate analysis semantics or reasoning semantics; it gives you a *substrate* — the smallest signed object that can travel across systems without dragging its production process behind it.

---

## Permanence is the real requirement

The deeper reason this matters is not elegance. It is *defensibility over time*.

In a mesh of mutable state, the past is unreachable. The fraud signal that fired at 03:11 is overwritten the moment the next score is computed. The analyst-agent's decision exists; the evidence it relied on does not, two hours later. Each integration has plausible-deniability shape: *we acted on what the upstream system told us at the time*. Nothing in the chain is signed by the actor that actually produced the evidence.

In an ACDP-based model, ownership is concrete. The fraud-signal context is signed by a specific agent. Its `content_hash` binds the signature to specific evidence. Its `derived_from` chain is part of the signed body — it cannot be backfilled later. There is no place for a producer to silently rewrite history.

Autonomous systems that influence finance, healthcare, logistics, energy, science, or governance will be judged by their ability to defend *what they knew when they decided*, not just by their ability to produce intelligent answers. The systems that endure will be the ones whose knowledge state is *structurally legible* — auditable, replayable, attributable, and bound to a specific producer at a specific moment.

---

## Coordination without coordination

Worth saying plainly: ACDP is not a coordination protocol. It does not specify sessions, voting, consensus, marketplaces, or reputation. Those are real problems and they have their own protocols.

ACDP specifies the *substrate* under all of them. Two agents that have never coordinated, that have no shared session, that may not even know each other exist, can still build on each other's work — provided one publishes its conclusions as ACDP contexts and the other can resolve `acdp://` URIs. The protocol is the rendezvous point.

This is intentional. Coordination protocols evolve quickly and tend to centralize on whatever framework wins this year. Substrate evolves slowly and tends to become invisible plumbing — like Git, like JSON, like JWT. ACDP is designed to be plumbing.

---

## The Substrate Layer

The first era of AI asked whether machines could reason. The second asked whether they could collaborate. The era we are entering must ask whether the *output* of machine reasoning can be **discovered, verified, and reused** at the speed of the work itself.

As agent ecosystems scale — thousands of agents, cross-vendor invocations, multi-organization workflows — the cost of ad hoc knowledge sharing grows exponentially. Each integration reinvents the same primitives. Each downstream agent re-derives the same conclusions. Each incident produces the same forensic mess: *what did the system actually know, and when?*

The systems that thrive in the next decade will not merely be capable. They will treat *published agent knowledge* as a first-class primitive. They will produce, transport, verify, and reuse signed contexts the same way they handle TLS, the same way they handle JSON, the same way they handle Git objects — as plumbing that everyone shares.

The substrate layer is not an optimization.

It is the missing foundation.

In the era after capability and coordination, *epistemic legibility* — not power, not throughput — will determine which autonomous systems endure.

---

*ACDP v0.1.0 is the first concrete realization of this substrate: a signed, content-addressed, JCS-canonicalized context body with an end-to-end-verifiable lineage chain. To move from this argument to the protocol itself, start with the [README](../README.md) and [RFC-ACDP-0001 — Core](../rfcs/RFC-ACDP-0001-core.md).*
