# Read-Authentication Methods Registry

ACDP read-authentication method identifiers used in `capabilities.read_authentication_methods`. Identifiers are lowercase ASCII matching `^[a-z][a-z0-9_]*$`.

The schema vocabulary is open. Registries advertise the methods they accept; consumers select one to authenticate read requests for non-public contexts.

## Registered values

| Identifier | Status | Reference |
|---|---|---|
| `http_signatures` | Optional | [RFC 9421 — HTTP Message Signatures](https://datatracker.ietf.org/doc/html/rfc9421) |
| `mtls` | Optional | [RFC 8705 — OAuth 2.0 Mutual-TLS](https://datatracker.ietf.org/doc/html/rfc8705) |
| `oauth` | Optional | [RFC 6749 — OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749) |

## Adding a method

Open a PR adding a row to the table above. Methods MUST:

- Be lowercase ASCII matching `^[a-z][a-z0-9_]*$`.
- Have a public, stable specification.
- Carry the requesting agent's DID (so the registry can apply visibility scoping).

Reserved future identifiers: `webauthn`, `oidc4vp`, `dpop`.
