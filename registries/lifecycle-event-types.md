# Lifecycle Event Type Registry

The `event_type` field of a lifecycle event (`registry_state.lifecycle_events[]`, [RFC-ACDP-0013 §4](../rfcs/RFC-ACDP-0013-lifecycle-events.md)) names the state action the event records. The vocabulary is **open** — the same forward-compatibility posture as context types ([context-types.md](context-types.md)) and the registry-state `status` pattern (RFC-ACDP-0004 §4.1) — but, unlike context types, values are not producer-free-form: registries MUST NOT accept unregistered values through the RFC-ACDP-0013 §6 endpoints; new values enter through this registry via the [RFC process](../governance/RFC-PROCESS.md).

Values MUST match `^[a-z][a-z0-9_]*$` and be 1–64 characters.

## Registered values (v1)

| Value | Status | Status effect (RFC-ACDP-0013 §7) | Initiator | Spec |
|---|---|---|---|---|
| `retracted` | Proposed (0.3.0, Final) | Enters retraction: `status` becomes `retracted` (dominates `superseded` and `expired`). | Producer (`POST /contexts/{ctx_id}/retract`) or registry (policy/legal, recorded directly). | [RFC-ACDP-0013 §6–§7](../rfcs/RFC-ACDP-0013-lifecycle-events.md) |
| `republished` | Proposed (0.3.0, Final) | Reverses a retraction: `status` re-derives per RFC-ACDP-0004 §4 as though never retracted; both events remain in history. | Producer (`POST /contexts/{ctx_id}/republish`) or registry. | [RFC-ACDP-0013 §6–§7](../rfcs/RFC-ACDP-0013-lifecycle-events.md) |

Retraction state is derived from the **last** `retracted`/`republished` event in array order; the RFC-ACDP-0013 §6 transition rule enforces strict alternation.

## Deliberately not registered

- **`status_changed`** — considered and rejected for `lifecycle_events`: `status` is *derived* registry state (RFC-ACDP-0004 §4) and never transitions by fiat, so a generic status-change event would either duplicate the derivation or contradict it. The name remains in use only inside the reserved RFC-ACDP-0009 §2.10 **webhook event** envelope, which is a separate, notification-only vocabulary (registry-to-operator delivery, no `lifecycle_events` interaction). Do not conflate the two.

## Unknown-event tolerance (NORMATIVE)

Consumers encountering a lifecycle event whose `event_type` matches the pattern but is not registered in their known vocabulary MUST tolerate it, MUST preserve it verbatim on re-serialization, and MUST treat it as having **no effect on retraction state** until they upgrade to a version that defines it (RFC-ACDP-0013 §7.3). An event violating the closed object schema (`acdp-lifecycle-event.schema.json`) is malformed registry state and MUST be rejected as structurally non-conformant.

## Adding a value

Open a PR adding a row above via the [RFC process](../governance/RFC-PROCESS.md). New values MUST:

- Match the pattern, be lowercase snake_case, and not collide with existing entries (nor with `status_changed`, reserved to RFC-ACDP-0009 §2.10).
- Define their status effect explicitly — including "none" — so the RFC-ACDP-0013 §7.1 derivation stays computable by every implementation.
- Define their initiator and authentication rule (producer-signed, registry-recorded, or both).
- State whether existing transition constraints (§6 alternation) apply.
