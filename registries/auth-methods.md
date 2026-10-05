# Read-Authentication Methods Registry

ACDP read-authentication method identifiers used in `capabilities.read_authentication_methods`. Identifiers are lowercase ASCII matching `^[a-z][a-z0-9_]*$`.

The schema vocabulary is open. Registries advertise the methods they accept; consumers select one to authenticate read requests for non-public contexts.

## Registered values

| Identifier | Status | Reference |
|---|---|---|
| `http_signatures` | Optional | [RFC 9421 — HTTP Message Signatures](https://datatracker.ietf.org/doc/html/rfc9421) |
| `mtls` | Optional | [RFC 8705 — OAuth 2.0 Mutual-TLS](https://datatracker.ietf.org/doc/html/rfc8705) |
| `oauth` | Optional | [RFC 6749 — OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749) |
| `bearer_jwt` | Optional (Provisional, 0.5.0) | Registry-issued bearer JWT obtained by a DID challenge (the registry verifies proof of control of the requester's DID key), presented per [RFC 6750](https://datatracker.ietf.org/doc/html/rfc6750) with claims per [RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519). Normative rules: RFC-ACDP-0008 §6.2. |

## Adding a method

Open a PR adding a row to the table above. Methods MUST:

- Be lowercase ASCII matching `^[a-z][a-z0-9_]*$`.
- Have a public, stable specification.
- Carry the requesting agent's DID (so the registry can apply visibility scoping).

Reserved future identifiers: `webauthn`, `oidc4vp`, `dpop`.

`did_jwt` is deliberately NOT registered: in the DID ecosystem it names a JWT signed by the DID's own key, which is not what `bearer_jwt` is (the token is signed by the *registry*). Using that name for `bearer_jwt` would mislead clients into self-signing tokens the registry rejects.
