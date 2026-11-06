# RFC-ACDP-0022
# Agent Context Distribution Protocol (ACDP) — A2A Artifact Provenance: Agent-Signed Artifacts

**Document:** RFC-ACDP-0022
**Version:** 0.5.0
**Status:** Community Standards Track (Draft)

This RFC binds ACDP to the Agent2Agent protocol (A2A, v1.0.1, package `lf.a2a.v1`). An A2A server agent publishes each artifact it completes as a body it signs itself, and returns the `acdp://` link inside the artifact. Anyone who later holds the artifact can prove that the agent published exactly this content, check whether the agent has since replaced or retracted it, and follow its inputs.

It defines:

- the granularity: one body per completed artifact, keyed `(artifact_id, role)`, with supersession on re-emission and `derived_from` on continuation (§4);
- the record **`acdp-a2a-artifact/1`**, carried in `metadata["acdp:a2a"]` of a body whose `type` is the agent's own (§4.4–§4.5);
- the salted hashes that bind the body to the task, the context and the parts (§5);
- the link in `Artifact.metadata["io.acdp/provenance"]`, and what happens when publishing fails (§6);
- how a client cites its inputs in `Message.metadata` (§7);
- how a holder verifies a held artifact (§8);
- the Agent Card pointer `https://acdp.io/ext/a2a/v1` (§9) and the optional `a2a.artifact` anchor (§10);
- what is out of scope (§11), and the OPTIONAL profiles **`acdp-producer-a2a`** and **`acdp-consumer-a2a`** (§12).

It depends on RFC-ACDP-0001 (Core), -0002 (Context Body), -0003 (Publish & Supersession), -0006 (Cross-Registry References), -0008 (Security), -0013 (Lifecycle Events), -0016 (Typed External Anchors), -0018 (Retraction Recall) and -0019 (MCP Tool-Result Provenance, for the link value and the salt construction).

---

## 1. Status of This Memo

This document is a **Draft** ACDP specification on the `0.5.0` line, which as a whole is Draft (VERSIONING.md). Nothing in it is frozen. It is promoted when two independent implementations pass its fixtures: an agent and a holder in acdp-rs, and an independent holder in acdp-verifier-py, all reproducing `a2a-001` byte for byte.

Both profiles (§12) are OPTIONAL. A registry needs nothing new: a body published under this RFC is an ordinary signed body of the agent's own type, and the record is ordinary producer `metadata`. Nothing in this document invalidates any existing body, signature or `content_hash`.

---

## 2. Conventions and Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are to be interpreted as described in RFC 2119 and RFC 8174 when, and only when, they appear in all capitals.

| Term | Meaning |
|---|---|
| **Agent** | The A2A server agent that produces the artifact. It is the ACDP producer. |
| **Client** | The A2A client that sent the task's messages. |
| **Holder** | Anyone who holds the artifact later: the client, or whoever the artifact was forwarded to. |
| **Artifact** | An A2A `Artifact` (`artifactId`, `name`, `description`, `parts`, `metadata`, `extensions`). |
| **Chunk** | One `TaskArtifactUpdateEvent` (`taskId`, `contextId`, `artifact`, `append`, `lastChunk`). |
| **Key** | The pair `(artifact_id, role)` that identifies an artifact within a task (§4.2). |
| **Record** | The `acdp-a2a-artifact/1` object at `metadata["acdp:a2a"]` (§4.4). |
| **A2A JSON** | The JSON form A2A defines for its messages: ProtoJSON with camelCase member names (A2A §5.5). |
| **JCS** | RFC 8785 canonicalization, as in RFC-ACDP-0001 §5.2. |
| **H(x)** | `"sha256:"` ‖ lowercase hex of SHA-256 over the byte string `x`. |

Member names of A2A objects are written in their A2A JSON form (`artifactId`, `lastChunk`, `mediaType`). Members of ACDP objects keep their ACDP names (`artifact_id_hash`, `agent_id`).

---

## 3. Model

The agent is the **producer** (NORMATIVE). It signs every body with its own key, under its own DID (`did:web` or `did:key`, RFC-ACDP-0001 §5.11), and that DID is the body's `agent_id`. The signature means exactly this: *the holder of this key published this artifact content.* It is a claim of authorship.

Contrast RFC-ACDP-0019. There a proxy signs what it *observed* another server return, and its signature says nothing about the server. Here no third party is involved: the party that made the artifact signs it. The claim is still only as good as the agent. A signature does not make the content correct, and a consumer decides which agents it trusts by `agent_id`, as for any producer.

The agent adds one key to the artifact's `metadata` (§6) and changes nothing else in the artifact.

### 3.1 Identity binding (NORMATIVE)

An agent may also advertise an AITP identity on its Agent Card (RFC-AITP-0014, `params.aid` of the extension `https://agentidentitytrustprotocol.io/ext/a2a/v1`). When it does:

- A `did:key` `agent_id` MUST encode the same key as the AID: the same algorithm and the same public key bytes. An Ed25519 AID (`aid:pubkey:<43 chars>` or `aid:pubkey:ed25519:<43 chars>`, which RFC-AITP-0001 §5.3 treats as the same key) maps to a `z6Mk…` `did:key` over the same 32 bytes. A P-256 AID (`aid:pubkey:p256:…`, 33-byte SEC1 compressed point) maps to a `zDn…` `did:key` over the same 33 bytes.
- A `did:web` DID document SHOULD list the AID's key as an `assertionMethod`, so that both identities verify with one key.

Whatever the DID method, the Card pointer's `params.agentId` (§9) MUST equal the `agent_id` of every body the agent publishes under this RFC.

### 3.2 Nothing new in ACDP's trust machinery (NORMATIVE)

This binding adds no lifecycle event kind (RFC-ACDP-0013), no change kind (RFC-ACDP-0018), no key-authorization rule and no revocation trust class (RFC-ACDP-0014). In particular:

- A re-emission in the same task (§4.3) is an ordinary `supersedes`. A feed consumer sees it as the existing `superseded` change.
- A continuation in a new task (§4.3) is ordinary `derived_from`.
- An agent signs with an ordinary `did:web` or `did:key` and is verified as RFC-ACDP-0001 §5.11 says, with nothing added.

---

## 4. The Body

### 4.1 Body fields (NORMATIVE)

| Field | Value |
|---|---|
| `type` | The agent's own domain type: any standard type (`analysis`, `data_snapshot`, …) or custom `<namespace>:<type>` (RFC-ACDP-0002 §5). There is no A2A-specific type. The type MUST NOT be one whose `metadata` is itself an ACDP-defined record: `acdp:mcp-tool-result`, `acdp:trust-list`, `acdp:key-attestation`, `key-revocation` or `acdp:key-revocation`. |
| `agent_id` | The agent's DID (§3). |
| `title` | The agent's choice. When it has none, RECOMMENDED: the artifact's `name`, or `A2A artifact` when the name is absent or not recorded (§4.4), truncated to the title limit. |
| `metadata` | The agent's own members, plus the record at `acdp:a2a` (§4.4–§4.5). |
| `schema_uri` | Absent, or the agent's own schema for its `metadata`. It is never the record's schema (§4.5). |
| `data_refs` | Per §5.3–§5.4: `[]` unless the parts are embedded or a `url` part is mapped. |
| `derived_from` | Per §4.3 and §7. |
| `anchors` | Absent, or per §10. |
| `visibility` | Per §13.3. |
| `acdp_version` | `0.5.0` or later. |
| `version`, `supersedes` | `1` and `null`, except for a re-emission (§4.3). |
| `contributors` | `[]`, or DIDs the agent chooses to credit. |

Other optional fields (`description`, `domain`, `tags`, `summary`, `data_period`, `expires_at`) are the agent's choice. They are not part of the binding.

### 4.2 Completion and assembly (NORMATIVE)

An agent publishes **one body per completed artifact**. It never publishes one body per Task, and never one per chunk.

**Key.** An artifact is identified within a task by `(artifact_id, role)`. A2A v1.0.1 Artifacts carry no role, so today the key is `artifact_id` alone and the record has no `role`. A2A #2411 proposes `role` on Artifacts and makes `(artifact_id, role)` the per-task key. Under an A2A revision that carries it, the record's `role` is present and is the role's ProtoJSON name. An agent signs only artifacts it authored, so that name is always `ROLE_AGENT`. An agent MUST NOT publish a body for a client-written artifact (`ROLE_USER`), or for an artifact it relays unchanged from another agent.

**Assembly.** The agent assembles the artifact from its chunks for that key, in the order it emits them:

- a chunk with `append` false or absent starts the artifact afresh: its parts replace any earlier parts;
- a chunk with `append` true appends its parts to the parts so far;
- `name` and `description` are those of the last chunk that carries them.

**Completion.** An artifact is complete at the earlier of:

1. the chunk for its key with `lastChunk` true; or
2. the task entering a terminal state (`TASK_STATE_COMPLETED`, `TASK_STATE_FAILED`, `TASK_STATE_CANCELED`, `TASK_STATE_REJECTED`) while the artifact is present and not yet complete. This covers an artifact that is only ever returned in a Task snapshot and never streamed.

An interrupted state (`TASK_STATE_INPUT_REQUIRED`, `TASK_STATE_AUTH_REQUIRED`) does not complete an artifact.

The completed artifact's `parts` are the assembled parts. The agent MUST return the same parts for that key in every later `Task.artifacts` snapshot, because a holder hashes what it holds (§8). `completed_at` is the time of completion, as canonical millisecond RFC 3339 UTC (`.000Z` form).

Agent replies that are plain `Message`s, not artifacts, produce no body. Their parts are messages, not outputs of a task.

### 4.3 Re-emission and continuation (NORMATIVE)

**Same key, same task.** After an artifact completes, the agent may send further chunks for the same key in the same task: an `append` false chunk that replaces it, or `append` true chunks that extend it. When the artifact completes again, the agent publishes a new version that **supersedes** the previous body (RFC-ACDP-0003 §3.1):

- same `agent_id` and same registry as the previous body, `supersedes` set to its `ctx_id`, `version` one higher;
- `parts_hash` over the parts as now assembled (all of them, not only the new chunks), and a fresh salt.

If the agent holds no published body for the key (the earlier publish failed, §6.2), the new body is version 1. A registry rejection of the supersession (for example `already_superseded`) is a publish failure (§6.2).

**A new task.** An artifact in a later task that continues or revises an artifact of an earlier task (for example in a task whose message lists the earlier task in `referenceTaskIds`) is a new key, because `artifactId` is unique only within a task. The agent publishes a new version-1 body, and its `derived_from` lists the earlier body's `ctx_id` **first**, before the cited inputs (§7). It does not supersede across tasks: each task's artifact stays its own fact.

### 4.4 The record (NORMATIVE)

The record is closed: `schemas/json/acdp-a2a-artifact.schema.json` (`$defs/record`). Unknown members are a schema violation for this record version.

| Member | Required | Value |
|---|---|---|
| `record_version` | Yes | `acdp-a2a-artifact/1` |
| `a2a_protocol_version` | Yes | The A2A protocol version the task was served under: the `protocolVersion` of the `AgentInterface` the request arrived on (e.g. `1.0`). |
| `artifact_id_hash` | Yes | §5 over `artifactId`. |
| `role` | No | `ROLE_AGENT`, present only under an A2A revision whose Artifact carries a role (§4.2). |
| `task_id_hash` | Yes | §5 over the task's `id`. |
| `context_id_hash` | Yes | §5 over the task's `contextId`. |
| `parts_hash` | Yes | §5 over the assembled `parts` (§5.1). |
| `salted` | Yes | `true` when the four hashes are salted (§5.2). |
| `embedded` | Yes | `true` when `data_refs` carries the parts (§5.3). |
| `name` | No | The artifact's `name`, when it has one and the agent records it. |
| `description` | No | The artifact's `description`, when it has one and the agent records it. |
| `completed_at` | Yes | §4.2. |

**`artifact_id` is hashed, not plaintext.** An agent chooses `artifactId` freely, and A2A's own examples use descriptive ids such as `research-summary-001`. A plaintext id can leak what the artifact is about. It also gives a public reader nothing usable: the id is unique only within a task, which the reader cannot see. A holder has the artifact, so it can recompute the hash. Hashing it under the same salt keeps the record consistent with the privacy decision for the task, the context and the parts.

**`name` and `description`.** They are copied in plaintext, because they are labels a reader of the body may need. An agent MAY leave them out when they would disclose too much (§13.2). When present, each is the artifact's value truncated to its schema limit (256 and 1024 Unicode scalar values). Truncation loses detail but cannot make the record name a different artifact, because `parts_hash` and `artifact_id_hash` bind it.

**What is not bound.** `Artifact.metadata` is not hashed: it carries the link (§6), which names the body, so hashing it would be circular. `Artifact.extensions` is not hashed and not used (§6.1).

### 4.5 The `acdp:a2a` metadata member (NORMATIVE)

The record is the value of the top-level member `acdp:a2a` of the body's `metadata`. The agent's own metadata members sit beside it.

Why this name:

- **It cannot be mistaken for an ordinary key.** Producer metadata keys are typically plain identifiers or reverse-DNS names (`quarter`, `com.example/report`). A colon-namespaced key does not collide with either.
- **`acdp:` is ACDP's own namespace.** ACDP already uses the `acdp:` prefix for the types it defines (`registries/context-types.md`). A top-level `metadata` member whose name starts with `acdp:` is reserved for ACDP-defined records. An agent MUST NOT use such a name for its own data.
- **It is not the link key.** `io.acdp/provenance` names the link in A2A and MCP metadata (§6). Using a different name inside the body keeps the record and the link apart.

Rules:

- The body's `metadata` MUST carry exactly one `acdp:a2a` member, and it MUST be a valid record. A body never carries the record anywhere else, and never shares its `metadata` with another ACDP record schema (§4.1 excludes the types that carry one).
- `schema_uri` describes the agent's own metadata. When the agent sets one, that schema MUST allow the `acdp:a2a` member. Verifiers identify the record by `record_version`, never by `schema_uri`.
- The record counts against RFC-ACDP-0002 §3.3's metadata limits: one top-level member of the 100, depth 2 of the 8, and roughly 600 bytes of the 64 KB. The agent's own metadata MUST leave room for it.

---

## 5. Hashes and the Salt (NORMATIVE)

The four record hashes use exactly RFC-ACDP-0019 §4.3's construction. For a value `v`:

- **salted**: H(`salt` ‖ JCS(`v`)), where `salt` is exactly 32 bytes and ‖ is byte concatenation: the 32 salt bytes, then the UTF-8 bytes of JCS(`v`);
- **unsalted**: H(JCS(`v`)).

The output is `"sha256:"` followed by 64 lowercase hex characters. There is **no domain tag**: no label, length prefix or separator is added, for parity with RFC-ACDP-0019 §4.3. The four hashes need no tag to stay apart, because a verifier knows which member it is checking.

The values are:

| Member | `v` |
|---|---|
| `artifact_id_hash` | the `artifactId` string |
| `task_id_hash` | the task's `id` string |
| `context_id_hash` | the task's `contextId` string |
| `parts_hash` | the assembled `parts` array, in A2A JSON (§5.1) |

JCS of a string is its JSON string form, quotes included. `a2a-001` pins every value and the parts preimage, so an independent implementation can recompute all four from the ids, the parts and the salt alone.

### 5.1 The parts in A2A JSON (NORMATIVE)

`parts_hash` covers the `parts` array, in order, with each Part in its A2A JSON form:

- exactly one content member, `text`, `raw`, `url` or `data`, present even when its value is empty;
- `metadata` present exactly when the Part's metadata is set;
- `filename` and `mediaType` present exactly when they are non-empty strings (ProtoJSON omits empty strings);
- no other member.

Every Part member is covered, including the Part's own `metadata`.

**`raw` parts.** The hash covers the `raw` member as A2A JSON carries it: a base64 string, which JCS hashes as text. The bytes themselves are not hashed separately. The string MUST be in RFC 4648 §4 form: the standard alphabet, with padding, which is what ProtoJSON emits. ProtoJSON parsers also accept the URL-safe alphabet and missing padding. A holder that received `raw` in such a form MUST decode it and re-encode the bytes in the standard padded form before hashing. One rule then covers every part kind, and the hash does not depend on the encoder.

**`data` parts.** `data` is a JSON value. Its numbers are IEEE 754 doubles, as in both `google.protobuf.Value` and JCS, so they canonicalize the same way on every side.

A holder that received the artifact over gRPC first renders the parts as A2A JSON by these rules.

### 5.2 The salt (NORMATIVE)

As RFC-ACDP-0019 §4.3, and for the same reason. A body is often readable by more parties than the task was. Task ids, context ids and short artifacts can come from a small space, and anyone could hash every candidate. The salt stops that.

- An agent MUST salt whenever the parts are not embedded (`embedded: false`). It MAY leave an embedded record unsalted, since its parts are already published. The task and context ids then become guessable if they have low entropy, so an agent whose ids are not random UUIDs SHOULD salt anyway.
- The salt MUST be 32 bytes from a cryptographically secure random source, fresh for every body, including each re-emission (§4.3). One salt covers all four hashes of that body.
- The salt is never in the body. The agent reveals it only in the link (§6), as base64url without padding (RFC 4648 §5): exactly 43 characters.
- `salted` records which form was used. A verifier MUST use the form `salted` names.

### 5.3 Embedding (NORMATIVE)

By default the parts are not published: `embedded` is `false`. Artifacts can carry personal or confidential data, and many registries are public.

An agent MAY allowlist artifacts for embedding by its own configuration (for example by skill or artifact name). For an allowlisted artifact, the first entry of `data_refs` is exactly one DataRef carrying the hashed `parts` value:

- `{"type": "primary_result", "format": "json", "embedded": {"encoding": "json", "content": <parts>}}`, within the 64 KB embedded cap (RFC-ACDP-0002 §6.3); or
- when the agent configured an external location and the parts exceed the cap, `{"type": "primary_result", "format": "json", "location": <https URL>, "content_hash": H(JCS(parts))}`, with `size_bytes` RECOMMENDED. The agent MUST write exactly the bytes JCS(parts) to that location before it publishes. The location is a public `https` URL, subject to RFC-ACDP-0008 §4.9 for consumers.

`embedded` is then `true`. If neither form fits, the agent publishes unembedded and salted.

### 5.4 `url` parts (NORMATIVE)

A `url` part points at content the agent serves elsewhere. For each `url` part, in part order and after any §5.3 entry, the agent SHOULD add one DataRef:

- `type`: `primary_result`;
- `location`: the part's `url`, unchanged;
- `content_hash`: H(the bytes at the URL), when the agent knows them, which it usually does, having produced them;
- `format`: the part's `mediaType`, when present; `size_bytes` RECOMMENDED when known.

A DataRef's `location` is plaintext in a signed, permanent body. So:

- The agent MUST NOT add a DataRef whose URL carries a credential or capability: userinfo (which the DataRef schema rejects anyway), or a query or fragment holding a token, signature or expiry, as signed URLs do. When in doubt, it omits the DataRef.
- The agent SHOULD NOT add one to a body readable by parties who should not learn the URL.

An omitted DataRef loses nothing for integrity: `parts_hash` still covers the URL string. The DataRef adds the fetched bytes' hash, which `parts_hash` cannot carry.

---

## 6. The Link (NORMATIVE)

After the registry's publish response, the agent adds one key to the completed artifact's `metadata`:

```json
"metadata": {
  "com.example/trace": "abc123",
  "io.acdp/provenance": {
    "ctx_id": "acdp://registry.example.com/5e8a2c71-9d4b-4f3e-a6c2-1b7d9e0f3a48",
    "content_hash": "sha256:73a4b28819c470e198578b6c8a180fdb748ceef67690609188aa1484bb7b4a98",
    "registry": "registry.example.com",
    "salt": "QEFCQ0RFRkdISUpLTE1OT1BRUlNUVVZXWFlaW1xdXl8"
  }
}
```

- The value is exactly RFC-ACDP-0019 §6's value, with the same meaning for each member: `acdp-a2a-artifact.schema.json#/$defs/link`, which references `acdp-mcp-tool-result.schema.json#/$defs/provenance` rather than copying it. `salt` is present exactly when the record is salted.
- The link goes on the `metadata` of the Artifact in the chunk that completes it (§4.2, the `lastChunk` chunk). It also goes on that artifact in every later `Task.artifacts` snapshot, with the same value until a re-emission (§4.3) replaces it with the new body's link. An artifact completed by the task ending (§4.2 case 2) carries the link only in snapshots.
- The agent MUST keep every other `metadata` key unchanged, and MUST NOT change `artifactId`, `name`, `description` or `parts`.
- **Publish before the final chunk.** The agent MUST NOT emit the completing chunk, or a snapshot carrying the completed artifact, before it has received the publish response. It buffers the final chunk while the publish settles. A link therefore only ever names a body that is already published.
- The publish request carries `Idempotency-Key: acdp-a2a-<hex of content_hash>` (the 64 hex characters after `sha256:`). Retries MUST resend the byte-identical body under the same key (RFC-ACDP-0003 §6).

The key name `io.acdp/provenance` is the one RFC-ACDP-0019 uses in MCP `_meta`, so one name and one value shape serve both protocols. A2A's own examples key extension metadata by the extension URI. This RFC uses the shared key instead, so a holder that already reads MCP links reads A2A links unchanged.

The agent adds the link whenever it published, whether or not the client activated the extension (A2A §4.6). A client that did not activate it ignores an unknown metadata key. A holder further down the line may never have talked to the agent, and its ability to verify must not depend on the first client's activation.

### 6.1 Artifact.extensions MUST NOT be used (NORMATIVE)

An agent MUST NOT add the extension URI, or anything else, to `Artifact.extensions` for this binding. A2A #1461 proposes removing that field, because extension data already lives in `metadata`. A holder MUST NOT require the URI in `Artifact.extensions`, and MUST NOT treat its presence or absence as part of verification.

### 6.2 Publish failure (NORMATIVE)

When publishing fails after the agent's retries, or does not finish within its publish timeout:

- **Fail-open (the default).** The agent emits the artifact unchanged, with `io.acdp/provenance` set to `{"failed": true, "error": <code>}`. `error` is the registry's `error.code` when the registry answered with an ACDP error, and is absent otherwise.
- **Fail-closed (by the agent's configuration).** The agent does not emit the artifact. It MAY end the task in `TASK_STATE_FAILED` with a status message saying that provenance publishing failed. It MUST NOT emit the parts without a link. A self-signing agent has no relayed content to protect, so fail-closed is simply its choice not to ship an unpublished output.

A failed publish never produces a link.

---

## 7. Inputs (NORMATIVE)

A client MAY cite the ACDP contexts it supplies as inputs, in a message's `metadata`:

```json
"metadata": {
  "io.acdp/provenance": {
    "inputs": [
      "acdp://registry.example.com/7b1d0c52-3e4f-4a6b-8c9d-0e1f2a3b4c5d",
      "acdp://registry.example.com/0f9e8d7c-6b5a-4c3d-9e2f-1a0b9c8d7e6f"
    ]
  }
}
```

The value is closed: `acdp-a2a-artifact.schema.json#/$defs/inputs`, an object whose one member `inputs` is an array of 1 to 1000 `ctx_id`s. The object form leaves room for later members under a new record of this RFC. An invalid value is ignored for provenance. The agent processes the message as if it carried none, and MUST NOT fail the task because of it.

The agent fills `derived_from` this way:

1. If the artifact continues an earlier task's artifact (§4.3), that body's `ctx_id` comes first.
2. Then the cited inputs from the task's client messages received before completion, in message order and then array order.
3. It keeps only inputs it has **verified**: retrieved, and verified as RFC-ACDP-0001 §5.11 says (fetching under RFC-ACDP-0006 §7 and RFC-ACDP-0008). An input it cannot retrieve or verify is left out.
4. It keeps the first occurrence of each, and stops after 1000 (the RFC-ACDP-0002 `derived_from` maximum).
5. After these, the agent MAY append contexts it retrieved and used on its own, within the same cap.

Only explicit citations count. An `acdp://` string inside a Part is content, not a citation, and is not extracted. RFC-ACDP-0019 §4.4 scrapes tool arguments because MCP has no citation slot. A2A has one, and scraping would turn quoted text into lineage.

---

## 8. Verification by a Holder (NORMATIVE)

A holder with an artifact and its `io.acdp/provenance` value:

1. **Body.** Retrieves `ctx_id` and verifies the body as for any body (RFC-ACDP-0001 §5.11, including the `did:key` and `did:web` paths with nothing added, §3.2). It MUST check that the body's `ctx_id` equals the link's (RFC-ACDP-0006 §4.1 step 7), that its `origin_registry` equals the link's `registry`, and that its `content_hash` equals the link's. A link with `failed: true` names no body and verifies nothing.
2. **Agent and record.** Checks that `agent_id` is an agent it trusts. When it reached the agent through the Agent Card, `agent_id` MUST equal the Card's `params.agentId` (§9). When that Card also carries an AITP AID and `agent_id` is a `did:key`, the holder MUST check §3.1's key equality. It then checks that `metadata["acdp:a2a"]` is a valid record of a version it knows. The record is closed, so it MUST reject unknown members rather than ignore them.
3. **Salt.** When `salted` is true, it decodes the salt. Only the canonical encoding is accepted: exactly 43 base64url characters, no padding, and zero trailing bits (RFC 4648 §3.5). When `salted` is false, the link MUST have no `salt`.
4. **Artifact.** Recomputes, in this order, and requires equality: `parts_hash` from the parts it holds (§5.1); `artifact_id_hash` from the `artifactId` it holds; `name` and `description`, when the record carries them, against the held values truncated as §4.4 says; and `role`, when present, against the held artifact's role.
5. **Task.** MAY recompute `task_id_hash` and `context_id_hash` when it knows the ids, as the client does. A holder that received the artifact forwarded, without the ids, leaves them unchecked. That is not a mismatch.
6. **Status.** Checks the body's status: retraction through RFC-ACDP-0013 and supersession through retrieval, or both through the RFC-ACDP-0018 feed. A `superseded` body means the agent published a later version of this artifact in the same task. A `retracted` body means the agent no longer stands behind it. What the holder does with that is its own policy.

The outcome is a local verdict, not a wire condition, so there is no error code for it (§14). A holder SHOULD report which step failed. It SHOULD at least distinguish an untrusted or unrecognised record (steps 1–3) from a record that does not match the held artifact (steps 4–5).

A mismatch at step 4 or 5 means the body is not a record of this artifact. It says nothing about the body itself, which remains validly signed.

No status change is pushed to holders. Nothing in this RFC fans a retraction out into tasks, agents or clients. A holder that cares watches the feed (RFC-ACDP-0018), or checks again when it relies on the artifact.

---

## 9. Discovery: the Agent Card Pointer (NORMATIVE)

An agent that publishes under this RFC SHOULD declare it on its Agent Card, as exactly one `AgentExtension` in `capabilities.extensions`:

```json
{
  "uri": "https://acdp.io/ext/a2a/v1",
  "description": "Completed artifacts are published as signed ACDP bodies (RFC-ACDP-0022).",
  "required": false,
  "params": {
    "registry": "registry.example.com",
    "agentId": "did:key:z6MkiTBz1ymuepAQ4HEHYSF1H8quG5GLVVQR3djdX3mDooWp"
  }
}
```

- The URI is compared byte for byte. A change a `v1` holder cannot process takes a new URI (A2A §4.6.3).
- `required` MUST be `false`. Provenance never makes an agent unusable for a client that ignores it.
- `params` follows `acdp-a2a-artifact.schema.json#/$defs/card_params`. The names are camelCase, as A2A's JSON convention requires. `registry` is the hostname of the registry the agent publishes to. `agentId` is the agent's DID and MUST equal every body's `agent_id` (§3.1). A holder MUST ignore `params` members it does not recognise.
- A Card with more than one entry for this URI, or with malformed `params`, gives the holder no pointer. It treats the Card as if it had none.

**The Card is an untrusted pointer.** It is fetched from a host, a registry or a cache, and any of them can change it. It tells a holder where to look and which DID to expect. It is never evidence: the body's signature is. A rewritten `agentId` makes §8 step 2 fail, or binds the holder to a DID it then has to decide to trust on its own.

**Fetching.** Every registry fetch a holder makes, whether from `params.registry` or a link's `ctx_id` authority, follows RFC-ACDP-0006 §7 and RFC-ACDP-0008 §4.8–§4.9 (HTTPS only, no private, loopback or link-local addresses, mixed-answer rejection, same-authority redirects), honours `Retry-After` under RFC-ACDP-0008 §4.3, and stays within the holder's own registry allowlist. A Card cannot widen that allowlist. A link that names a registry other than `params.registry` is not a failure by itself; the allowlist decides.

**Coexistence with AITP.** RFC-AITP-0014 defines `https://agentidentitytrustprotocol.io/ext/a2a/v1`. The two URIs differ, so they never collide, and both MAY appear on one Card. They answer different questions: AITP says who the agent is for a live session; this extension says where the agent's signed outputs are. §3.1 binds the two keys when both appear.

---

## 10. The `a2a.artifact` Anchor (OPTIONAL)

A2A #1140 proposes a Content Integrity Profile: an inline `hash` on artifacts, of the form `sha256:<64 hex>` over the artifact's canonical JSON. When the agent has computed that hash for the completed artifact, it MAY carry it as an RFC-ACDP-0016 anchor:

```json
"anchors": [
  { "scheme": "a2a.artifact", "content_hash": "sha256:<the #1140 hash>" }
]
```

- ACDP carries the value and never re-derives it. Core verification MUST NOT recompute or resolve it (RFC-ACDP-0016 §6). A verifier that implements #1140 MAY check it for its own purposes.
- The anchor is present only when the agent computed the #1140 hash over the same artifact content the record binds. It has no `uri`.
- The #1140 hash is unsalted, so it undoes §5.2's salt for anyone who can read the body. An agent MUST NOT add it to a salted record of a `public` body.
- RFC-ACDP-0016 does not require a scheme to be registered, and `registries/anchor-schemes.md` admits a scheme only from its owner. This RFC therefore does not register `a2a.artifact`. The row is A2A's to add once #1140 lands.

---

## 11. Out of Scope (NORMATIVE)

This binding provides verification of authorship only. The following are out of scope, and an implementation of this RFC MUST NOT present any of them as part of it:

- **Reliance ledgers.** No record that a task, agent or client relied on an artifact or a context.
- **Acceptance state.** No accepted, approved, committed or rejected state for an artifact, a task or an outcome. A verified body is authored content, not an accepted result.
- **Per-task receipts.** No receipt or lineage record per Task ("this task used these refs"). The unit is the artifact, and lineage is `derived_from` (§7).
- **Recall fan-out.** No retraction or supersession pushed into A2A tasks, agents or clients. Holders pull status (§8 step 6).
- **Audit export.** No export format for task or artifact histories.

Lifecycle goes only through RFC-ACDP-0013 and the RFC-ACDP-0018 feed.

**Agents that cannot sign (non-normative).** An agent that cannot hold a key could sit behind an observer proxy in the style of RFC-ACDP-0019, which would sign what it saw the agent return. That is a weaker, observation claim (§3). It is not specified here, and there is no profile for it.

---

## 12. Profiles (OPTIONAL) *(0.5.0, Draft)*

### 12.1 `acdp-producer-a2a`

An agent-side profile with no prerequisite. An agent claiming it:

- publishes one body per completed artifact, under its own DID, of its own type, with the record at `metadata["acdp:a2a"]` (§3–§4);
- supersedes on re-emission in the same task, and cites the earlier body on continuation in a new task (§4.3);
- salts the four hashes whenever the parts are not embedded, embeds only by allowlist, and maps `url` parts per §5.4 (§5);
- returns the link per §6, never uses `Artifact.extensions`, and handles failure per §6.2;
- fills `derived_from` per §7;
- advertises the Card pointer per §9 and keeps the AITP key binding of §3.1;
- passes `a2a-001`, `a2a-002`, `a2a-003` and `a2a-005`..`a2a-008`.

An agent is not a registry. It advertises the profile in its own documentation and through the Card pointer; nothing on the ACDP wire carries it.

### 12.2 `acdp-consumer-a2a`

A holder-side profile, prerequisite `acdp-consumer`. A holder claiming it verifies held artifacts per §8, treats the Card as an untrusted pointer per §9, and passes `a2a-001` (including its holder negatives), `a2a-003` and `a2a-004`.

### 12.3 Separation from `acdp-consumer` (NORMATIVE)

No `a2a-*` fixture ever appears in `acdp-consumer`'s `required_fixtures` or `conditional_fixtures` in `registries/profiles.json`. The `a2a-*` fixtures belong only to `acdp-producer-a2a` and `acdp-consumer-a2a`. A consumer that does not handle A2A artifacts stays fully conformant.

---

## 13. Security Considerations

### 13.1 What the signature proves

That the agent's key signed a record binding this artifact's content to a task. The agent can sign false content as easily as true. Consumers MUST scope trust per `agent_id`. An agent SHOULD use a key dedicated to its A2A outputs, so that revoking it (RFC-ACDP-0014) withdraws exactly those bodies. A `did:key` agent cannot rotate; a new key starts new lineages (RFC-ACDP-0001 §5.4).

### 13.2 What a body discloses

Even salted, a body discloses that this agent completed an artifact at `completed_at`, and the body's own type, title, plaintext metadata and any `name` or `description` in the record. An agent SHOULD keep confidential labels out of `title` and the record (§4.4), SHOULD NOT embed (§5.3) or map `url` parts (§5.4) for artifacts that may hold personal or secret data, and MUST NOT put credentials in any body field.

### 13.3 Visibility

As RFC-ACDP-0019 §8.3. An agent SHOULD publish with `visibility: private`, or `restricted` with an `audience` (for example the client's DID), when the registry supports it. The operator configures the visibility, and the agent publishes with exactly that value. If the registry rejects it, that is a publish failure (§6.2). The agent MUST NOT fall back to a wider visibility on its own.

### 13.4 Replay and substitution

A link copied onto a different artifact fails §8 step 4. A link replayed with the artifact it was issued for proves only what it always proved. A Card that points at another agent's DID is caught at §8 step 2, or leaves the holder trusting a DID it chose. The salt is a capability to prove the link: a holder that forwards the artifact with its metadata lets the recipient prove it too, which is the intent.

### 13.5 SSRF

The agent fetches cited inputs (§7), and holders fetch bodies (§8–§9). Every such fetch follows RFC-ACDP-0006 §7 and RFC-ACDP-0008 §4.8–§4.9. A Card, a link and a message's `inputs` are all attacker-controllable strings, and none of them may widen a fetcher's allowlist. A consumer dereferencing a §5.4 DataRef follows RFC-ACDP-0008 §4.9.

---

## 14. Errors

None new. The agent reports the registry's ACDP error codes verbatim in `io.acdp/provenance.error`. Holder verification (§8) is a local verdict with no wire code.

---

## 15. Conformance Fixtures

| Fixture | Pins |
|---|---|
| `a2a-001` | Known answer, executed by `scripts/conformance-runner.py`: from two pinned chunks, the task and context ids, the cited inputs and the salt, the assembled parts and parts preimage, the four salted hashes, the record, `derived_from`, the canonical form, `content_hash`, the Ed25519 signature of the `did:key` agent (the sig-001 zero test seed), the `Idempotency-Key`, the link on the final chunk and the Task snapshot, the Card binding to the agent's AITP AID, and ten holder negatives with the step each fails |
| `a2a-002` | Chunk assembly, completion, and supersede on re-emission; continuation in a new task by `derived_from` (§4.2–§4.3) |
| `a2a-003` | The Card pointer: one entry, `required` false, `agentId` equal to `agent_id`; a mismatched `agentId` fails; coexistence with the AITP extension and the §3.1 key binding (§3.1, §9) |
| `a2a-004` | Holder recomputation and its negatives, status checks, unchecked task ids when unknown (§8) |
| `a2a-005` | Cited inputs to `derived_from`: order, verification, deduplication, cap, no scraping of parts (§7) |
| `a2a-006` | No use of `Artifact.extensions`; only `metadata` gains the link (§6–§6.1) |
| `a2a-007` | Fail-open, fail-closed and idempotent retries; publish before the final chunk (§6–§6.2) |
| `a2a-008` | Salting, embedding by allowlist, `url` parts to `data_refs`, the `raw` base64 rule, and the `a2a.artifact` anchor rule (§5, §10) |

The ACDP `a2a-*` family is distinct from AITP's `a2a-*` vectors for RFC-AITP-0014, which live in the AITP repository and test a different binding.

The `a2a-001` known-answer values (salt = bytes `0x40`..`0x5f`):

| Value | Digest |
|---|---|
| `artifact_id_hash` | `sha256:5917dccf6292d2a7564c9d6b467bd72b988c97ab69dba174245224b5c4b66156` |
| `task_id_hash` | `sha256:13fdf32204313ca4cbe4376d2fd544c131e9edb4d37cbf53fdea937836316e6c` |
| `context_id_hash` | `sha256:9eb6ace274bb43e7095cffdd0b5c7ac975c6ebade2e4b5385be048f0f87dc260` |
| `parts_hash` | `sha256:11fe7c879a5f786129b918ac9b087666942da00d60d9aa6eba248e5d76fc24a8` |
| `content_hash` | `sha256:73a4b28819c470e198578b6c8a180fdb748ceef67690609188aa1484bb7b4a98` |

---

## 16. IANA-Style Registrations

- `registries/profiles.json` / `profiles.md`: `acdp-producer-a2a` and `acdp-consumer-a2a`; fixture family `a2a`.
- A2A extension URI: `https://acdp.io/ext/a2a/v1`, defined here (§9). It depends on the `acdp.io` domain being held for the project.
- A2A metadata key: `io.acdp/provenance` on `Artifact.metadata` (§6) and `Message.metadata` (§7), with the values defined here. The key itself is RFC-ACDP-0019's.
- Body metadata member: `acdp:a2a` (§4.5), and the reservation of `acdp:`-prefixed top-level metadata members for ACDP-defined records.
- No context type, DataRef type, error code or anchor scheme (§10).

---

## 17. References

- A2A Protocol Specification v1.0.1 (`lf.a2a.v1`): §4.6 Extensions, §5.5 JSON field naming; `specification/a2a.proto` (`Part`, `Artifact`, `Message`, `TaskArtifactUpdateEvent`, `AgentExtension`).
- a2aproject/A2A #1140 (Content Integrity Profile), #1461 (remove `extensions` from Message and Artifact), #2411 (artifact key `(artifact_id, role)`).
- RFC-AITP-0001 §5.3 (Agent ID), RFC-AITP-0014 (A2A Agent Card binding).
- RFC 4648 (Base16, Base32, and Base64), RFC 8785 (JCS).
