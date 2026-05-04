# Locator Scheme Registry

ACDP `data_refs[].location` accepts two forms (RFC-ACDP-0002 §6.2):

1. A URI string conforming to a registered URI scheme.
2. A structured locator object with a dotted-namespace `scheme` field.

This registry tracks **commonly used** dotted-namespace schemes for the structured form. ACDP does **not** maintain an exhaustive registry — producers using novel schemes SHOULD prefix the scheme with their organization or domain.

## Common URI-form schemes (informational)

These are standard internet URI schemes and require no ACDP registration:

| Scheme | Use |
|---|---|
| `https`, `http` | Web fetch. |
| `s3` | Amazon S3 / S3-compatible object stores. |
| `gs` | Google Cloud Storage. |
| `azure` | Azure Blob Storage (informal). |
| `file` | Local file path. |
| `postgres`, `mysql`, `mongodb` | Database row reference (producer-defined query semantics). |
| `kafka` | Kafka topic reference (informal). |
| `ipfs` | IPFS content identifier. |

## Structured locator schemes

| Scheme | Status | Required fields | Optional fields | Description |
|---|---|---|---|---|
| `kafka.offset` | Stable | `broker`, `topic`, `partition`, `offset` (or `offset_start`/`offset_end` for ranges) | `consumer_group`, `key` | A specific offset or offset range in a Kafka topic partition. |
| `db.row` | Provisional | `system`, `database`, `table`, `key` | `column`, `tx_id` | A specific row in a database. |
| `ipfs.cid` | Provisional | `cid` | `gateway`, `path` | An IPFS content identifier. |
| `vendor.handle` | Provisional | `vendor`, `handle` | `version` | An opaque handle in a vendor system. |

## Adding a scheme

Open a PR adding a row to the table above. Schemes MUST:

- Use dotted-namespace form (`<namespace>.<resource>` minimum).
- Document required fields (the `scheme` field is always required by `acdp-data-ref.schema.json`).
- Document optional fields and their semantics.
- Not collide with an existing scheme.

Producers using non-registered schemes SHOULD use a reverse-domain prefix (`com.example.feature`) to avoid collisions.

## Examples

Kafka offset range:

```json
"location": {
  "scheme": "kafka.offset",
  "broker": "kafka.prod.example.com:9092",
  "topic": "service-metrics",
  "partition": 7,
  "offset_start": 8421005,
  "offset_end": 8421847
}
```

Database row:

```json
"location": {
  "scheme": "db.row",
  "system": "postgres",
  "database": "analytics",
  "table": "sentiment_analysis",
  "key": "12345"
}
```

IPFS:

```json
"location": {
  "scheme": "ipfs.cid",
  "cid": "bafybeibcz3of6ywmlmjbe7w2a2dk7p4g5dfiu3aqwafs5rfaaj7kf72kpa"
}
```
