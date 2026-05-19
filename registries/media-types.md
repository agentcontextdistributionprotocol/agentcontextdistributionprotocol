# Media Types Registry

Content types used in ACDP transport bindings.

| Media type | Status | Description |
|---|---|---|
| `application/acdp+json` | Stable | Canonical JSON encoding of ACDP messages (HTTP transport). All ACDP endpoints accept and emit this type. Protocol version is carried in JSON (`acdp_version` in capabilities, optional `body.acdp_version` in bodies — RFC-ACDP-0001 §6); the media type itself does NOT carry a `version` parameter. Implementations MAY include `; charset=utf-8` per RFC 8259. |
| `application/acdp-context+json` | Provisional | A bare body or full `{body, registry_state}` payload, used in caching headers and inline payloads. Same versioning rules as `application/acdp+json` — version lives in JSON, not in a media-type parameter. |

ACDP v0.1.0 is JSON-only. Binary transport bindings are out of scope for this version; if added in a future version, additional media types will be registered here.

## Content negotiation

When negotiating content types, clients SHOULD send:

```
Accept: application/acdp+json
```

Servers SHOULD honor the preference where supported. The default if no `Accept` header is supplied is `application/acdp+json`.

## Versioning

Protocol version is carried in JSON, not in the Content-Type header. The authoritative version sources are `acdp_version` on the capabilities document (RFC-ACDP-0007 §3) and the optional `body.acdp_version` on a context body (RFC-ACDP-0001 §6). The media type does NOT carry a `version` parameter; doing so would create two competing version sources and is forbidden.

## Registration status

`application/acdp+json` is requested for IANA registration in [RFC-ACDP-0001 §11.2](../rfcs/RFC-ACDP-0001-core.md#112-media-type-registration). Until accepted, implementations SHOULD use this media type and accept `application/json` as a fallback for legacy clients.
