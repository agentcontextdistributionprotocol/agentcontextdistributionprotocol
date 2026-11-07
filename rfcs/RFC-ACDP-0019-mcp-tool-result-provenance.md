# RFC-ACDP-0019
# Agent Context Distribution Protocol (ACDP) — MCP Tool-Result Provenance: the MCP Signing Proxy

**Document:** RFC-ACDP-0019
**Version:** 0.5.0
**Status:** Community Standards Track (Final)

This RFC specifies the **MCP signing proxy**: a process that sits between an MCP client and an MCP server, relays every message unchanged, and publishes each tool result it relays as a signed ACDP body. The client gets back the same result plus an `acdp://` link, and anyone holding the result can later prove that this proxy observed it from that server at that time. No MCP server changes; the developer changes the server command in the client configuration.

It defines:

- the context type **`acdp:mcp-tool-result`** and its metadata record, **`acdp-mcp-tool-result/1`** (§4);
- the hashing rules, including a per-body **salt** that keeps low-entropy arguments and results from being guessed from a public hash (§4.3);
- when the result itself is published (§5: only for allowlisted tools);
- how the link is returned to the client (§6: `_meta` key `io.agentcontextdistributionprotocol/provenance`);
- what happens when publishing fails (§7);
- the OPTIONAL producer profile **`acdp-producer-mcp-proxy`** (§10).

It depends on RFC-ACDP-0001 (Core), -0002 (Context Body), -0003 (Publish & Supersession), -0006 (Cross-Registry References, for the `acdp://` grammar) and -0008 (Security).

---

## 1. Status of This Memo

This document is a **Final** ACDP specification at version `0.5.0`, promoted 2026-10-30, ahead of the `acdp/0.5.0` line, which was promoted to Final as a whole on 2026-11-06 (VERSIONING.md). Breaking changes now require a new RFC and a version bump.

**Body, hashes and link: Final (2026-10-30).** The body and how a holder checks it: the `acdp:mcp-tool-result` type and the `acdp-mcp-tool-result/1` record (§4.1–§4.2), the call hashes and the salt with the consumer recomputation (§4.3), the `derived_from` rule (§4.4), and the `io.agentcontextdistributionprotocol/provenance` value and its link rules (§6). These are pinned by `mcp-001` and `mcp-003`, which pass against two independent interoperating implementations, both run at spec `546b8c8`:
- acdp-rs 0.18.2 (`acdp-mcp-proxy`, `acdp-chain`);
- acdp-verifier-py at `3928ee1`, written from this text alone.

Both reproduce every `mcp-001` known answer byte for byte: the three salted hashes, `endpoint_hash`, `derived_from`, the canonical form, `content_hash`, the signature, the `Idempotency-Key` and the returned `_meta`. Both also pass `mcp-003`, including the §4.3 holder recomputation and its negatives.

**Proxy side: Final (2026-11-06).** The proxy's own obligations were promoted with the acdp/0.5.0 line under the acdp/0.5.0 single-implementation gate exception ([VERSIONING.md](../VERSIONING.md)): embedding (§5), publish failure and retries (§7), the handling of MCP revisions without an `initialize` handshake and of results that are not yet complete (§3.1–§3.2, *(0.5.0, 2026-11-06)*), and the `acdp-producer-mcp-proxy` profile (§10) with its behavioral fixtures `mcp-002` and `mcp-004`..`mcp-008`. Only one proxy implementation (acdp-rs `acdp-mcp-proxy`) exercises them; acdp-verifier-py is a consumer and runs no proxy. It passes `mcp-001`..`mcp-008` at spec `ce39078`: acdp-rs `55f40c3` (require-mode conformance at spec `ce39078`, [CI run](https://github.com/agentcontextdistributionprotocol/acdp-rs/actions/runs/42328766458)).

The profile it defines (§10) is OPTIONAL. A registry needs nothing new to accept these bodies: an `acdp:mcp-tool-result` body is an ordinary signed body under the existing custom-type grammar. Nothing in this document invalidates any existing body, signature or `content_hash`.

---

## 2. Conventions and Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are to be interpreted as described in RFC 2119 and RFC 8174 when, and only when, they appear in all capitals.

| Term | Meaning |
|---|---|
| **Upstream server** | The MCP server the proxy forwards to. |
| **Client** | The MCP client (the agent host) that called the proxy as if it were the server. |
| **Call** | One `tools/call` request and the result that completes it (§3.2). |
| **Arguments** | The request's `params.arguments` object (`{}` when absent). |
| **Result** | The `CallToolResult` the upstream server returned. |
| **Hashed result** | The result restricted to those of `content`, `structuredContent` and `isError` that are present (§4.3). |
| **Record** | The `acdp-mcp-tool-result/1` object carried as the body's `metadata` (§4). |
| **Operator** | Whoever runs the proxy and holds its signing key. |
| **JCS** | RFC 8785 canonicalization, as in RFC-ACDP-0001 §5.2. |
| **H(x)** | `"sha256:"` ‖ lowercase hex of SHA-256 over the byte string `x`. |

---

## 3. Model

The proxy is the **producer** (NORMATIVE). It signs every body with the operator's own key, under the operator's own DID (`did:key` or `did:web`, RFC-ACDP-0001 §5.11), and that DID is the body's `agent_id`. The signature therefore means exactly this: *the holder of this key observed this call to this upstream server and this result coming back.* It does not mean the upstream server vouches for the result, and a consumer MUST NOT read it that way. A consumer decides which proxies it trusts by `agent_id`, as for any producer.

The proxy relays every MCP message unchanged except that it adds one `_meta` key to `tools/call` results (§6). It publishes one body per call it relays, for every tool it is configured to cover (the RECOMMENDED default is every tool).

(NORMATIVE) Edge cases of "a call it relays":
- A `tools/call` answered with a JSON-RPC **error** (no `CallToolResult`) produces no body. The proxy relays the error unchanged and adds nothing to it.
- Under an MCP revision with an `initialize` handshake, a `tools/call` result that arrives before the upstream `initialize` result is a publish failure (§7), handled under the tool's fail-open or fail-closed policy (§3.1).
- A result that is not yet complete (`input_required`, or a task handle) produces no body of its own (§3.2).
- In a JSON-RPC batch (MCP revisions before 2025-06-18), each element is handled as if it had arrived alone. The proxy MAY hold the batch until every element's publish has settled.

Upstream servers that sign their own results, and proxies that carry such a signature alongside their own, are out of scope for this version. A proxy MUST NOT claim a result was upstream-signed.

### 3.1 Protocol revision and server identity (NORMATIVE) *(0.5.0, 2026-11-06)*

The proxy fills `mcp_protocol_version` and `server.name` / `server.version` (§4.2) from what it observed upstream. Where they come from depends on the request's era. A server may serve both eras at once, so the proxy classifies **each request**, not the connection:

- **Without the handshake** (MCP 2026-07-28 and later): the forwarded request's `_meta` carries `io.modelcontextprotocol/protocolVersion`.
  - `mcp_protocol_version` is that value. Over HTTP the `MCP-Protocol-Version` header must equal it; a server rejects a mismatch with a JSON-RPC error, which produces no body (§3).
  - `server.name` and `server.version` come from `io.modelcontextprotocol/serverInfo` in the result's `_meta`. For a task-delivered result (§3.2) that is the `_meta` of the `tasks/get` response, falling back to the inner `result`'s `_meta`.
  - If the result carries none, they MAY come from the `io.modelcontextprotocol/serverInfo` of a `server/discover` response from the same upstream endpoint, while that response is within its `ttlMs`. The proxy MAY send `server/discover` itself for this.
  - If no server identity is available, `server.name` is `unknown` and `server.version` is absent. This is **not** a publish failure.
- **With the handshake** (any other request, including a legacy session on a server that supports both eras): from the upstream `initialize` result's `protocolVersion` and `serverInfo`. A result that arrives before that `initialize` result is a publish failure (§7), because the proxy cannot yet know either value.

These values are self-reported, and MCP does not verify them. They describe the server; `endpoint_hash`, not `server.name`, identifies it (§4.2).

### 3.2 Results that are not yet complete (NORMATIVE) *(0.5.0, 2026-11-06)*

From MCP 2026-07-28, a `tools/call` result has a `resultType`. An absent `resultType` means `complete`. `resultType` is outside the hashed result (§4.3), so it never changes `result_hash`.

- **`complete`.** This is the call's outcome. The proxy publishes for it as in §4–§7.
- **`input_required`** (multi-round requests). The server needs more input before it can finish. The proxy relays the result unchanged, publishes no body for it, and adds no `io.agentcontextdistributionprotocol/provenance`. The client then sends a new `tools/call` request with its own `id`, carrying `inputResponses` and possibly `requestState`. That request is a call of its own. When its result is `complete`, the proxy publishes for it exactly as in §4, from that request alone:
  - `arguments_hash` covers its `params.arguments`, and `request_id_hash` its `id`;
  - `started_at` is when the proxy forwarded it.

  `inputResponses` and `requestState` are not hashed. Earlier rounds are not bound, even if their arguments differed. The record proves the arguments of the completing request and the result, not the input the client supplied along the way.
- **`task`** (the `io.modelcontextprotocol/tasks` extension). The task handle is not the outcome. The proxy relays it unchanged and publishes no body for it. Covering task-delivered results is OPTIONAL. A proxy that does not cover them MUST say so in its documentation, and a holder of such a result has no link. A proxy that covers them:
  - publishes **once per task**, when it first relays a `tasks/get` response whose task is `completed`. That body records the `result` that response carries. The record takes `tool`, `arguments_hash` and `request_id_hash` from the `tools/call` request that created the task. `started_at` is when the proxy forwarded that request, and `completed_at` is when it received the first completed response.
  - adds `io.agentcontextdistributionprotocol/provenance` (§6) to that inner `result`'s `_meta`, and returns the **same** value on every later `tasks/get` for the task. It never publishes a second body for a repeated poll.
  - treats a completed task whose creating request it no longer holds (for example after a restart) as a publish failure (§7).
  - publishes no body for a task that ends `failed` or `cancelled`, as for a JSON-RPC error (§3).
  - under fail-closed (§7), replaces the inner `result` with the §7 failure result and leaves the task's `status` unchanged.
  - delivers a completed task's `result` to the client only in a `tasks/get` response that carries the link. A task-status notification that would carry the `result` is relayed with the `result` removed, so the client fetches it with `tasks/get`.
- **Any other value.** MCP treats it as invalid. The proxy relays the message unchanged and publishes no body.

In §6, "the result" for a task-delivered body is the inner `result`. "The request" in §4.2–§4.3 is always the request that §3.2 names, so the record, the hashes and the §4.3 recomputation are unchanged.

---

## 4. The Body

### 4.1 Body fields (NORMATIVE)

| Field | Value |
|---|---|
| `type` | `acdp:mcp-tool-result` (`registries/context-types.md`). |
| `agent_id` | The operator's DID (§3). |
| `title` | `MCP tool result: <server.name>/<tool>`, truncated to the body's title limit. |
| `schema_uri` | `https://schemas.agentcontextdistributionprotocol.io/v0.1.0/acdp-mcp-tool-result.schema.json` |
| `metadata` | The record (§4.2). |
| `data_refs` | `[]`, unless the tool is allowlisted for embedding (§5). |
| `derived_from` | Per §4.4. |
| `visibility` | Per §8.3. |
| `acdp_version` | `0.5.0` or later. |
| `version`, `supersedes`, `contributors` | `1`, `null`, `[]`. A proxy never supersedes its own records: each call is its own fact. |

### 4.2 The record (NORMATIVE)

The record is closed: `schemas/json/acdp-mcp-tool-result.schema.json` (`$defs/record`). Unknown members are a schema violation for this record version.

| Member | Required | Value |
|---|---|---|
| `record_version` | Yes | `acdp-mcp-tool-result/1` |
| `mcp_protocol_version` | Yes | The MCP protocol revision in use with the upstream server (§3.1): negotiated at `initialize`, or carried in the request's `_meta` from 2026-07-28 (e.g. `2025-06-18`, `2026-07-28`), or `unknown` if none was reported. |
| `server.name` | Yes | `serverInfo.name` as observed per §3.1, or `unknown` if the server reported none. |
| `server.version` | No | `serverInfo.version`, when the server reported one (§3.1). |
| `server.transport` | Yes | `stdio`, `streamable-http` or `sse`. |
| `server.endpoint_hash` | Yes | H(JCS(endpoint descriptor)), unsalted (below). |
| `tool` | Yes | The request's `params.name`. |
| `arguments_hash` | Yes | §4.3 over the arguments. |
| `result_hash` | Yes | §4.3 over the hashed result. |
| `request_id_hash` | No | §4.3 over the JSON-RPC `id` value of the request (a string or number). |
| `is_error` | Yes | The result's `isError`, `false` when absent. |
| `salted` | Yes | `true` when the three hashes above are salted (§4.3). |
| `embedded` | Yes | `true` when `data_refs` carries the hashed result (§5). |
| `started_at` | Yes | When the proxy forwarded the request upstream, canonical millisecond RFC 3339 UTC (`.000Z` form). |
| `completed_at` | Yes | When the proxy received the result, same form. |

*(0.5.0, 2026-11-06)* The three rows above now refer to §3.1 for where the values come from on an MCP revision without `initialize`. Their values and meaning are unchanged, and every existing record stays valid.

**Length limits (NORMATIVE).** `server.name`, `server.version` and `mcp_protocol_version` longer than their schema limits are truncated to the limit, counted in Unicode scalar values. These fields describe the server; truncating them loses detail but does not misidentify anything, because `endpoint_hash` identifies the server. `tool` is never truncated, because a truncated tool name could name a different tool. A call whose tool name exceeds the limit is a publish failure (§7).

**Endpoint descriptor.** For `stdio`, the object `{"command": <executable>, "args": [<arguments>]}`. For the HTTP transports, `{"url": <url>}` where `<url>` is the server URL with userinfo, query and fragment removed. Environment variables and HTTP headers are never part of it (NORMATIVE). An operator whose launch arguments contain a credential MUST remove it from `args` (or replace it with a fixed placeholder) before hashing. The hash is unsalted on purpose: the same server yields the same `endpoint_hash` in every body, so consumers can recognise it.

### 4.3 Call hashes and the salt (NORMATIVE)

For each of the arguments, the hashed result and the request `id`, the proxy computes the following. The **arguments** are `params.arguments`, or `{}` when the request omits it (the MCP default); the hash is computed over the value the server acted on, never over an absent member.

- **salted**: H(`salt` ‖ JCS(value)), where `salt` is 32 bytes and ‖ is byte concatenation;
- **unsalted**: H(JCS(value)).

The **hashed result** is the result object restricted to those of `content`, `structuredContent` and `isError` that are present, with their values unchanged. `_meta`, and any other member, is excluded. An absent `isError` stays absent; it is not defaulted before hashing.

**Why the salt.** A body is often public, and a tool's arguments or result can come from a small space: a yes/no answer, an account number, a short query. Anyone could hash every candidate and compare. The salt stops that: without it, the hashes reveal nothing.

- A proxy MUST salt whenever the result is not embedded (`embedded: false`). It MAY leave an embedded record unsalted, since the result is already published.
- The salt MUST be 32 bytes from a cryptographically secure random source, fresh for every body. One salt covers all three hashes of that body.
- The salt is never in the body. The proxy reveals it only to the client, in `_meta` (§6), as base64url without padding (43 characters). Whoever holds the salt and the result can prove the link; anyone who holds neither learns nothing.
- `salted` records which form was used. A verifier MUST use the form `salted` names.

**Verification.** A verifier holding a result and its `io.agentcontextdistributionprotocol/provenance` value:

1. retrieves `ctx_id` and verifies the body as for any body (RFC-ACDP-0001 §5.11). It MUST check that the retrieved body's `ctx_id` equals the link's `ctx_id` (RFC-ACDP-0006 §4.1 step 7), that its `origin_registry` equals the link's `registry`, and that its `content_hash` equals the link's;
2. checks that `agent_id` is a proxy it trusts, that `type` is `acdp:mcp-tool-result`, and that `metadata` is a valid record of a version it knows. The record is closed (§4.2), so a verifier MUST reject unknown members rather than ignore them;
3. decodes the salt when `salted` is true. Only the canonical encoding is accepted: exactly 43 base64url characters, no padding, and zero trailing bits (RFC 4648 §3.5). Anything else is rejected;
4. recomputes `result_hash` from the result it holds and requires equality, requires `tool` to equal the `params.name` it called, and requires `is_error` to equal the held result's `isError` (`false` when absent);
5. MAY recompute `arguments_hash` and `request_id_hash` from the request it sent. An absent `request_id_hash` leaves the request id unchecked. It is not a mismatch.

The outcome is a local verification verdict, not a wire condition, so there is no error code for it (§9). A verifier SHOULD report which step failed, and SHOULD at least distinguish an untrusted or unrecognised record (steps 1–2) from a record that does not match the held call (steps 3–5).

A mismatch at step 4 means the body is not a record of this result. It says nothing about the body itself, which remains validly signed.

### 4.4 derived_from (NORMATIVE)

The proxy SHOULD fill `derived_from` with the contexts the call's arguments cite. When it does, it MUST compute it this way:

1. Walk the arguments value in JCS order and preorder: object members in RFC 8785 §3.2.3 key order (UTF-16 code units), array elements in index order.
2. Take each **string value** (never an object key) that matches the whole `ctx_id` grammar (`acdp-common.schema.json#/$defs/ctx_id`). A string that merely contains one is not taken.
3. Keep the first occurrence of each, and stop after 1000 (the RFC-ACDP-0002 `derived_from` maximum).

Only the arguments count. A ctx_id that appears only in the result is an output, not an input, and is not added.

---

## 5. Publishing the Result Itself (NORMATIVE) *(0.5.0)*

By default the result is not published: `data_refs` is `[]` and `embedded` is `false`. Tool results can carry secrets and personal data, and many registries are public.

An operator MAY allowlist individual tools for embedding. For an allowlisted tool:

- `data_refs` is exactly one DataRef `{"type": "primary_result", "format": "json", "embedded": {"encoding": "json", "content": <hashed result>}}` (RFC-ACDP-0002 §6.3), within the 64 KB embedded cap;
- or, when the operator configured an external location and the hashed result exceeds the cap, one location DataRef `{"type": "primary_result", "format": "json", "location": <https URL>, "content_hash": H(JCS(hashed result))}`, with `size_bytes` (the length of those bytes) RECOMMENDED. The proxy MUST write exactly the bytes JCS(hashed result) to that location before it publishes. The URL form is the operator's choice. The location is subject to the RFC-ACDP-0008 §4.9 fetch rules for consumers, so it MUST be a public `https` URL;
- `embedded` is `true`. If neither form fits, the proxy publishes the record unembedded and salted.

---

## 6. Returning the Link (NORMATIVE)

After the registry's publish response, the proxy adds one key to the result's `_meta` and returns the result:

```json
"_meta": {
  "io.agentcontextdistributionprotocol/provenance": {
    "ctx_id": "acdp://registry.example.com/3c2b1a09-8f7e-4d6c-9b5a-4e3d2c1b0a9f",
    "content_hash": "sha256:4aed49d224d126b7b941c8505a7f2019aa3c77a044cb1cf7a8d2159457217b7e",
    "registry": "registry.example.com",
    "salt": "QEFCQ0RFRkdISUpLTE1OT1BRUlNUVVZXWFlaW1xdXl8"
  }
}
```

- The key `io.agentcontextdistributionprotocol/provenance` follows MCP's `_meta` key-naming rule (a reverse-DNS prefix, then `/`). Its value is closed: `acdp-mcp-tool-result.schema.json#/$defs/provenance`. `ctx_id` is the publish response's. `content_hash` is that of the body the proxy published (the RFC-ACDP-0003 publish response does not echo it; the registry receipt binds it when present). `registry` is the `ctx_id`'s authority, which RFC-ACDP-0002 §3.1 makes equal to the body's `origin_registry`. A `ctx_id` is matched by the full RFC-ACDP-0001 §5.4 grammar, including its hostname length limits; the schema pattern is necessary, not sufficient. `salt` is present exactly when the record is salted.
- The proxy MUST NOT change `content`, `structuredContent` or `isError`, and MUST keep every other `_meta` key unchanged.
- If the upstream result already carries `io.agentcontextdistributionprotocol/provenance`, the proxy MUST leave that value unchanged and MUST NOT add its own. It still publishes its record. Under fail-closed (§7), the withheld result carries the proxy's failure value instead, because the upstream result, `_meta` included, is not returned.
- The proxy MUST NOT return a `ctx_id` before it has received the publish response carrying it. It MAY forward the request upstream and prepare the body concurrently, but the client sees the result only once the publish has succeeded or failed (§7).

---

## 7. Publish Failure (NORMATIVE) *(0.5.0)*

The publish request carries `Idempotency-Key: acdp-mcp-<hex of content_hash>` (the 64 hex characters after `sha256:`). Retries MUST resend the byte-identical body under the same key, so a retry never creates a second publication (RFC-ACDP-0003 §6).

When publishing fails after the proxy's retries, or does not finish within its publish timeout:

- **Fail-open (the default).** The proxy returns the result unchanged, with `io.agentcontextdistributionprotocol/provenance` set to `{"failed": true, "error": <code>}`. `error` is the registry's `error.code` when the registry answered with an ACDP error, and is absent otherwise (unreachable, timeout).
- **Fail-closed (per tool, configured by the operator).** The proxy withholds the result. It returns a `CallToolResult` with `isError: true`, one text content item saying that provenance publishing failed, and the same `io.agentcontextdistributionprotocol/provenance` failure value. This is the one case where the proxy does not relay the upstream content; it is what the operator asked for. The wording of the text item is implementation-defined; it SHOULD name the tool.

A failed publish never produces a link.

---

## 8. Security Considerations

### 8.1 What the signature proves

That the operator's key signed a record of a call. The proxy can lie: it can sign a result the server never returned. The record is exactly as trustworthy as the operator. Consumers MUST scope trust per proxy `agent_id`, and an operator SHOULD use a dedicated key for the proxy (not a key it uses for its own analyses), so that revoking the key (RFC-ACDP-0014) withdraws exactly the proxy's records.

### 8.2 No secrets in bodies

Environment variables, HTTP headers, URL userinfo, query strings and fragments never enter a body (§4.2). Credentials in launch arguments are removed before hashing. The arguments and result enter only as salted hashes unless the operator allowlists embedding (§5), and an operator SHOULD NOT allowlist a tool whose results may contain personal or secret data.

### 8.3 Visibility

A proxy SHOULD publish with `visibility: private`, or `restricted` with an `audience`, when the registry supports it. Even salted, a public record discloses that the operator called this tool on this server at this time. `public` is appropriate when the operator wants that fact discoverable. (NORMATIVE) Capabilities do not advertise which visibilities a registry accepts, so the operator configures the visibility, and the proxy publishes with exactly that value. If the registry rejects it, that is a publish failure (§7). The proxy MUST NOT fall back to a wider visibility on its own.

### 8.4 Replay and freshness

A `_meta` link copied onto a different result fails §4.3 step 4. A link replayed with the result it was issued for proves only what it always proved: that call, at `completed_at`. Consumers that care about freshness compare `completed_at` with their own clock and policy. When the upstream result already carried `io.agentcontextdistributionprotocol/provenance` (§6), the holder receives the upstream link, and nothing in the result points to the proxy's own record. That record stays findable by search (`agent_id`, `type`), but a holder cannot tell from the result alone whether the link came from the proxy or from upstream. The salt is a capability to prove the link; a client that forwards the result with its `_meta` lets the recipient prove it too, which is the intent.

### 8.5 SSRF

The proxy fetches nothing on behalf of a body: it publishes to its configured registry and connects to its configured upstream server. RFC-ACDP-0008's fetch-time SSRF rules apply to consumers that later dereference an external DataRef (§5), not to the proxy.

---

## 9. Errors

None new. The proxy reports the registry's ACDP error codes verbatim in `io.agentcontextdistributionprotocol/provenance.error`, and a registry rejects a malformed record with `schema_violation` only if it validates `schema_uri`, which no registry is required to do.

---

## 10. Profile: `acdp-producer-mcp-proxy` (OPTIONAL) *(0.5.0)*

A producer-side profile with no prerequisite. A proxy claiming it:

- publishes one `acdp:mcp-tool-result` body per relayed call, signed with the operator's own key (§3–§4);
- salts the call hashes whenever the result is not embedded, and keeps credentials out of `endpoint_hash` (§4.2–§4.3);
- fills `derived_from` per §4.4 when it fills it at all;
- embeds only for allowlisted tools (§5);
- never alters the relayed result and returns the link per §6;
- handles failures per §7;
- handles MCP revisions without `initialize` and results that are not yet complete per §3.1–§3.2, and states in its documentation whether it covers task-delivered results;
- passes `mcp-001`..`mcp-008`.

A proxy is not a registry and advertises the profile in its own documentation; nothing on the ACDP wire carries it.

---

## 11. Conformance Fixtures

| Fixture | Pins |
|---|---|
| `mcp-001` | Known answer, executed by `scripts/conformance-runner.py`: from pinned arguments, result, request id, endpoint descriptor and salt, the three salted hashes, `endpoint_hash`, `derived_from`, canonical form, `content_hash`, the Ed25519 signature of the `did:key` proxy (the sig-001 zero test seed), the `Idempotency-Key` and the returned `_meta` |
| `mcp-002` | The relayed result is never altered; upstream `_meta` kept; an upstream `io.agentcontextdistributionprotocol/provenance` left alone |
| `mcp-003` | The `io.agentcontextdistributionprotocol/provenance` shape; `salt` iff salted; link only after the publish response; consumer recomputation (§4.3) |
| `mcp-004` | Fail-open, fail-closed and idempotent retries (§7) |
| `mcp-005` | `derived_from` extraction order, near-misses, arguments only, cap (§4.4) |
| `mcp-006` | Embedding only by allowlist, and the DataRef shapes (§5) |
| `mcp-007` | Salting rules and keeping secrets out (§4.2–§4.3, §8.2) |
| `mcp-008` | *(0.5.0, 2026-11-06)* MCP 2026-07-28 sessions: revision and server identity from `_meta` without `initialize`, a missing server identity is not a failure, `input_required` and task handles publish nothing, the completing result is published, and the legacy before-`initialize` failure (§3.1–§3.2) |

The `mcp-001` known-answer values:

| Value | Digest |
|---|---|
| `arguments_hash` | `sha256:010d05bef8881a150d20a0ee0305180990b6ca4660d7c89c665c355929a1341a` |
| `result_hash` | `sha256:8262a4f266f704366e5c66c0060d9ddc9ccee7dd6cefaa7df97a3710781f936d` |
| `request_id_hash` | `sha256:7cd156f85826f187bab397d47716e4ebe0ef2e5f7ba4a759268eb2af877e55da` |
| `content_hash` | `sha256:4aed49d224d126b7b941c8505a7f2019aa3c77a044cb1cf7a8d2159457217b7e` |

---

## 12. IANA-Style Registrations

- `registries/context-types.md`: `acdp:mcp-tool-result`, Stable (since the 0.5.0 Final promotion, 2026-11-06).
- `registries/profiles.json` / `profiles.md`: `acdp-producer-mcp-proxy`; fixture family `mcp`.
- MCP `_meta` key: `io.agentcontextdistributionprotocol/provenance`, defined here.
