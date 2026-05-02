# Media Types Registry

Content types used in ACDP transport bindings.

| Media type | Status | Description |
|---|---|---|
| `application/acdp+json; version=0.0.1` | Stable | Canonical JSON encoding of ACDP messages (HTTP transport). All ACDP endpoints accept and emit this type. |
| `application/acdp+proto; version=v1` | Provisional | Canonical Protobuf encoding of ACDP messages (gRPC and binary transports). The proto mirror is at [`schemas/proto/acdp/v1/`](../schemas/proto/acdp/v1/). |
| `application/acdp-context+json; version=0.0.1` | Provisional | A bare body or full `{body, registry_state}` payload, used in caching headers and inline payloads. |

## Content negotiation

When negotiating content types, clients SHOULD send:

```
Accept: application/acdp+json
```

Servers SHOULD honor the preference where supported. The default if no `Accept` header is supplied is `application/acdp+json`.

## Versioning

The `version` parameter on the media type tracks the ACDP protocol version (`acdp_version` field of the capabilities document — see [RFC-ACDP-0007 §3](../rfcs/RFC-ACDP-0007-capabilities.md#3-capabilities-document)). Consumers receiving a media type with an unknown version SHOULD treat it as a higher version and degrade gracefully.

## Registration status

`application/acdp+json` is requested for IANA registration in [RFC-ACDP-0001 §11.2](../rfcs/RFC-ACDP-0001-core.md#112-media-type-registration). Until accepted, implementations SHOULD use this media type and accept `application/json` as a fallback for legacy clients.
