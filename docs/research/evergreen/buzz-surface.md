---
title: Buzz Human-Surface Mapping for Lindenmayer Evergreen
author: main.platform_architect.buzz_surface
date: 2026-07-23
status: research findings
---

# Buzz Human-Surface Mapping for Lindenmayer Evergreen

## Overview

This document grounds the Buzz human-surface mapping for the Lindenmayer evergreen component. Per DESIGN.md §1, the bridge outputs two layers: Nostr core (signed events on the Lindenmayer relay, using standard and custom kinds) and Buzz layer (derived views, human-facing surfaces, relay-side behavior). Cross-posts into Buzz are derived views that carry the source timestamp and core event id in tags, deduplicated by that core-id reference.

This research enumerates:
1. **Buzz primitives** — NIP-29 channel/group mechanics, membership, DMs, agent surfaces
2. **Ingest constraints** — accepted kinds, timestamp drift, scope requirements
3. **Identity handling** — NIP-OA attestation on ingest and product surface
4. **Mapping table** — Lindenmayer core kinds → Buzz cross-post destinations and tag structures

**Source:** Buzz repository @ daeaf7c, DESIGN.md §1–2, §5–6.5.

---

## 1. Buzz Primitives

### 1.1 NIP-29 Groups and Channels

Buzz models collaboration around **channels**, the primary container for group communication. Each channel can bind to a **NIP-29 group** for external Nostr client interoperability.

**NIP-29 Group Lifecycle** (from `crates/buzz-core/src/kind.rs` @ daeaf7c):
- `KIND_NIP29_CREATE_GROUP` (9007): Creates a group; scoped to `ChannelsWrite`
- `KIND_NIP29_EDIT_METADATA` (9002): Updates group metadata; `ChannelsWrite` (or `AdminChannels` if the event has an `archived` tag)
- `KIND_NIP29_DELETE_GROUP` (9008): Deletes a group; scoped to `AdminChannels`
- `KIND_NIP29_JOIN_REQUEST` (9021): User requests to join; scoped to `ChannelsRead`
- `KIND_NIP29_LEAVE_REQUEST` (9022): User requests to leave; scoped to `ChannelsRead`
- `KIND_NIP29_CREATE_INVITE` (9009): Admin creates an invite; scoped to `ChannelsWrite`

**Group State Events** (kinds 39000–39003; stored by the relay, not broadcast):
- `KIND_NIP29_GROUP_METADATA` (39000): Current group metadata (name, about, picture, etc.)
- `KIND_NIP29_GROUP_ADMINS` (39001): List of admin pubkeys
- `KIND_NIP29_GROUP_MEMBERS` (39002): List of all members and their roles
- `KIND_NIP29_GROUP_ROLES` (39003): Role definitions (e.g., moderator, officer)

**Membership Model:**
- Groups maintain membership via `KIND_NIP29_GROUP_MEMBERS` (39002), an addressable event that lists all members and their roles.
- Role definitions (39003) specify permissions for each role; moderation commands (kind 9010–9016, per `is_moderation_command_kind()` @ `crates/buzz-relay/src/handlers/ingest.rs`) require role-based authorization.
- Invites and join/leave requests are signed events that traverse the group's control flow; the relay enforces membership gates via the group membership state event.

**Channel Type and Visibility** (from `crates/buzz-core/src/channel.rs` @ daeaf7c):
- **Channel Types**: Stream (linear), Forum (threaded), Dm (direct message), Workflow (internal execution)
- **Visibility**: Open (searchable, anyone can join) or Private (invite-only)
- Each channel has an optional `nip29_group_id` binding it to a NIP-29 group for Nostr interop.

### 1.2 Direct Messages (DMs)

Buzz models DMs as **DM channels** (`ChannelType::Dm`). DM lifecycle is governed by:
- `KIND_DM_OPEN` (41010): Initiates a DM conversation; scoped to `MessagesWrite`
- `KIND_DM_ADD_MEMBER` (41011): Adds a participant to an existing DM; scoped to `MessagesWrite`
- `KIND_DM_HIDE` (41012): Hides/archives a DM conversation locally; scoped to `MessagesWrite`

DMs do not require NIP-29 group membership; they are direct peer-to-peer or small-group conversations, opened on-demand via `KIND_DM_OPEN` and managed via add/hide commands.

### 1.3 Message Kinds

Text and threaded content is published via:
- `KIND_TEXT_NOTE` (1): Standard Nostr short-form text message
- `KIND_STREAM_MESSAGE` (9): Stream/channel message (Buzz's primary message kind for channels)
- `KIND_STREAM_MESSAGE_V2` (40002): Extended stream message with richer metadata
- `KIND_STREAM_MESSAGE_EDIT` (40003): Edit of a prior message
- `KIND_FORUM_POST` (kind in family ~40100–40199): Forum-style threaded post
- `KIND_FORUM_COMMENT` (related family): Comment within a forum thread

All message kinds are scoped to `MessagesWrite` (from `required_scope_for_kind()` @ `crates/buzz-relay/src/handlers/ingest.rs` @ daeaf7c).

### 1.4 Agent Surfaces

**Agent Profile** (from `crates/buzz-core/src/kind.rs` @ daeaf7c):
- `KIND_AGENT_PROFILE` (10100): A user-owned, globally-scoped event (like kind:0) published by or about an agent. Carries metadata: name, description, instructions, capabilities. Scoped to `UsersWrite`.
- Used by Buzz to surface agents in an "agent directory"—a searchable listing of available agents and their capabilities, indexed by pubkey.

**Agent Engram** (`KIND_AGENT_ENGRAM`, 30174):
- Encrypted memory record for AI agents, parameterized by `(pubkey, kind, d_tag)` where `d_tag` is an HMAC over the agent↔owner conversation key.
- Author-scoped (agent-readable only); used to store and retrieve long-lived context for the agent.
- Scoped to `UsersWrite` by default.

**Agent Attestation:**
- Agent identity is attested via NIP-OA `auth` tags (see §2 below); an agent's `KIND_AGENT_PROFILE` (10100) can carry an `auth` tag signed by the agent's human owner, proving ownership.
- On Buzz ingest, the `auth` tag is parsed and verified; the agent is surfaced to the user as "owned by [owner pubkey]" (see §3).

---

## 2. Ingest Constraints

### 2.1 Timestamp Drift

Buzz relay hard-rejects any event with `created_at` more than ±15 minutes from server time.

**Verified constraint** (from `crates/buzz-relay/src/handlers/ingest.rs` @ daeaf7c):
```
MAX_TIMESTAMP_DRIFT_SECS = 900 (±15 minutes)
```

This is a relay-enforced gate; events outside this window are dropped before any kind-based filtering. **Implication for cross-posts**: All Lindenmayer cross-posts into Buzz must have `created_at` within ±15 minutes of Buzz server time, or they will be rejected on ingest. The core event's timestamp is carried in tags (not the post's `created_at`); the cross-post's `created_at` is the publish time.

### 2.2 Accepted Kinds and Scopes

Buzz accepts a finite set of kinds via exhaustive matching in `required_scope_for_kind()`. **Message-capable kinds** (usable for carrying text content and suitable for cross-posting Lindenmayer events):

| Kind | Name | Scope | Use Case |
|------|------|-------|----------|
| 1 | `KIND_TEXT_NOTE` | `MessagesWrite` | Short-form text, any channel |
| 9 | `KIND_STREAM_MESSAGE` | `MessagesWrite` | Channel message (primary Buzz message kind) |
| 40002 | `KIND_STREAM_MESSAGE_V2` | `MessagesWrite` | Extended channel message with rich metadata |
| 41010 | `KIND_DM_OPEN` | `MessagesWrite` | Open a DM conversation |
| 41011 | `KIND_DM_ADD_MEMBER` | `MessagesWrite` | Add participant to DM |
| 9 (in forum) | `KIND_FORUM_POST` | `MessagesWrite` | Threaded forum post |
| (family ~40100+) | `KIND_FORUM_COMMENT` | `MessagesWrite` | Comment in thread |

**NIP-29 group management** (membership and governance):

| Kind | Name | Scope | Use Case |
|------|------|-------|----------|
| 9000 | `KIND_NIP29_PUT_USER` | `AdminChannels` | Admin: add/update user in group |
| 9001 | `KIND_NIP29_REMOVE_USER` | `AdminChannels` | Admin: remove user from group |
| 9002 | `KIND_NIP29_EDIT_METADATA` | `ChannelsWrite` (or `AdminChannels` if `archived` tag) | Update group metadata |
| 9007 | `KIND_NIP29_CREATE_GROUP` | `ChannelsWrite` | Create a new group |
| 9008 | `KIND_NIP29_DELETE_GROUP` | `AdminChannels` | Delete a group |
| 9009 | `KIND_NIP29_CREATE_INVITE` | `ChannelsWrite` | Create invite link |
| 9021 | `KIND_NIP29_JOIN_REQUEST` | `ChannelsRead` | User joins group |
| 9022 | `KIND_NIP29_LEAVE_REQUEST` | `ChannelsRead` | User leaves group |
| 9010–9016 | Moderation commands | `MessagesWrite` | Moderation (mute, kick, etc.) |
| 39000–39003 | Group state (metadata, admins, members, roles) | (Stored, not gated on ingest) | Relay-side group state |

**Scope Requirements Summary**:
- Message cross-posts: require `MessagesWrite` scope
- Channel/group operations: require `ChannelsWrite` (or `AdminChannels` for admin ops)
- DM operations: require `MessagesWrite` scope

---

## 3. Identity: NIP-OA Attestation

### 3.1 NIP-OA Mechanism (Buzz Implementation)

**NIP-OA (Nostr Owner Attestation)** is a signature-based attestation mechanism carried in an `auth` tag on any Nostr event (not a distinct event kind). The tag structure is:

```
["auth", <owner_pubkey_hex>, <conditions_json>, <bip340_signature_hex>]
```

**On Ingest** (from `crates/buzz-acp/src/lib.rs` @ daeaf7c):
- Buzz parses `auth` tags from events during ingest and in kind:0 profiles.
- `buzz_sdk::nip_oa::verify_auth_tag(&tag_json, &agent_pk)` cryptographically verifies the signature.
- If valid, the event's author is marked as attested by the owner pubkey.
- The attestation is **not relay-enforced**; Buzz stores it as metadata, ready for downstream consumption.

**Authorization Use**:
- NIP-OA proves delegation: an agent pubkey can carry an `auth` tag signed by a human owner, proving the human authorized this agent's actions.
- Buzz uses this to enforce agent access control: queries check if an author is the owner OR a "sibling" (another agent attested by the same owner).

### 3.2 Product Surface (Client Display)

**Agent Profile Display**:
- When a user views an `KIND_AGENT_PROFILE` (10100) in the product, Buzz displays the agent's attested owner if an `auth` tag is present and valid.
- Typical surface: "**Agent Name** — owned by @owner_npub" (with the owner's profile linked).

**Absence of Attestation**:
- If an `auth` tag is missing or invalid, the agent is surfaced as an anonymous agent: "**Agent Name** — no verified owner."
- This is a graceful degradation; the event is still accepted and displayed, but the human cannot verify who controls it.

**Relay Enforcement**:
- Instant revocation (removing the human, the subgraph loses access) is **Buzz-layer**, per DESIGN.md §1.
- The Lindenmayer relay (the core-log carrier) is permissive and accepts all events; Buzz relay-side policy and revocation enforcement is separate.

---

## 4. Mapping Table: Lindenmayer Core Kinds → Buzz Cross-Post Destinations

For each Lindenmayer core kind, the table below enumerates feasible Buzz cross-post destinations and tag structures for carrying the source timestamp and core event id (for dedup-by-reference per DESIGN.md §1).

**Tag Structure Convention**:
- `l:` tags (in Buzz) or `e` tags (in Nostr) carry references to source events.
- Cross-posts always carry: source kind, source event id (hash), and source `created_at` (timestamp) to enable dedup.
- Buzz cross-posts are **derived views**: their own `created_at` is publish time; source timestamp is in tags.

### 4.1 Node Lifecycle Events (42010)

**Lindenmayer Kind:** 42010 (node lifecycle: start, iteration, step event)

**Possible Buzz Cross-Posts:**

| Buzz Kind | Channel Shape | Tag Structure | Notes |
|-----------|---------------|---------------|-------|
| `KIND_STREAM_MESSAGE` (9) or `KIND_STREAM_MESSAGE_V2` (40002) | Subgraph channel (NIP-29 group bound to branch) | `["l", "lindenmayer:42010", {"source_id": "<event_id_hex>", "source_created_at": <timestamp>}]` OR `["e", "<event_id_hex>", "", "lindenmayer-source"]` + `["d_tag", "source_timestamp", "<timestamp>"]` | Node lifecycle events are observational; cross-post as a structured message into the subgraph's channel. Can include payload (step name, iteration count) in message body. |
| `KIND_TEXT_NOTE` (1) | Subgraph channel or global relay | Simple text summary + e-tag | Simpler variant for basic lifecycle announcements (e.g., "Node started"). Less structured; used if simple relay-wide broadcast is desired. |

**Dedup Invariant:** Source event id (42010 event hash) + source timestamp distinguish cross-posts; a consumer reads this tag to avoid re-ingesting the same lifecycle event from multiple Buzz channels.

---

### 4.2 Telemetry Rollups (42020)

**Lindenmayer Kind:** 42020 (run accounting: aggregated metrics, latency, cost, token usage)

**Possible Buzz Cross-Posts:**

| Buzz Kind | Channel Shape | Tag Structure | Notes |
|-----------|---------------|---------------|-------|
| `KIND_STREAM_MESSAGE` (9) or `KIND_STREAM_MESSAGE_V2` (40002) | Subgraph channel | `["l", "lindenmayer:42020", {"source_id": "<event_id_hex>", "source_created_at": <timestamp>}]` | Telemetry is observational; cross-post as a summary message (e.g., "Run summary: 5 iterations, 120s wall-clock, $2.50 cost"). |
| **Alternative**: Long-form post | Subgraph channel or global relay | `KIND_LONG_FORM` (30023) with embedded JSON metrics | Richer format for detailed telemetry (charts, tables embedded in markdown). Less common but feasible if detailed reports are desired. |

**Scope:** `MessagesWrite`

**Dedup Invariant:** Same as 42010 — source event id + source timestamp.

---

### 4.3 Radio Aggregates (42030)

**Lindenmayer Kind:** 42030 (subgraph digest: upward radio relay aggregates)

**Possible Buzz Cross-Posts:**

| Buzz Kind | Channel Shape | Tag Structure | Notes |
|-----------|---------------|---------------|-------|
| `KIND_STREAM_MESSAGE` (9) / `KIND_STREAM_MESSAGE_V2` (40002) | Subgraph channel OR parent's channel OR global relay | `["l", "lindenmayer:42030", {"source_id": "<event_id_hex>", "source_created_at": <timestamp>}]` | Radio aggregates bubble up; can cross-post into the subgraph's own channel, the parent's channel, or a global "radio feed" channel. Depends on visibility scope. |
| `KIND_TEXT_NOTE` (1) | Global relay | Simple text message + e-tag | Simple broadcast variant for widely-visible aggregates (e.g., "Subgraph X signaled issue Y"). |

**Scope:** `MessagesWrite`

**Dedup Invariant:** Source event id + source timestamp.

**Privacy Note:** Per DESIGN.md §6.1 (aggregates-up default), the subgraph controls which aggregates surface upward. A cross-post into the parent's channel respects the subgraph's privacy boundary.

---

### 4.4 Approval Requests (42040) and Verdicts (42041)

**Lindenmayer Kinds:** 42040 (approval request), 42041 (approval verdict)

**Possible Buzz Cross-Posts:**

| Buzz Kind | Channel Shape | Tag Structure | Notes |
|-----------|---------------|---------------|-------|
| `KIND_STREAM_MESSAGE` (9) / `KIND_STREAM_MESSAGE_V2` (40002) | Approvals inbox channel (a private NIP-29 group restricted to decision-makers) | `["l", "lindenmayer:42040", {"source_id": "<event_id_hex>", "source_created_at": <timestamp>, "approval_id": "<approval_event_id>"}]` | Approval requests are governance events; cross-post into a dedicated approvals inbox (a NIP-29 group scoped to approvers). Verdict cross-posts reply to the request (via e-tag threading). |
| `KIND_DM_OPEN` + messages | DM channel with approver(s) | `["l", "lindenmayer:42040", ...]` + `["p", "<approver_pubkey>"]` (recipient tag) | Alternative: Open a DM with each approver and send the approval request as a message. Less scalable but more intimate for small approval groups. |

**Scope:** `MessagesWrite` (messages) + `ChannelsWrite` (creating the approvals inbox group)

**Tag Details:**
- 42040 (request): Includes approval ID, decision-path (e.g., auto-approve, consensus, single-approver)
- 42041 (verdict): Includes approval ID, approval result (approved/rejected/escalated), and rationale
- Both carry source event id + timestamp for dedup

**Dedup Invariant:** Source event id + source timestamp ensure the same approval request/verdict is not re-ingested if posted to multiple channels.

---

### 4.5 Template Registration (42050 Template Version, 38150 Template Pointer)

**Lindenmayer Kinds:** 42050 (template version), 38150 (template pointer)

**Possible Buzz Cross-Posts:**

| Buzz Kind | Channel Shape | Tag Structure | Notes |
|-----------|---------------|---------------|-------|
| `KIND_AGENT_PROFILE` (10100) OR `KIND_STREAM_MESSAGE` (9) | Agent directory (global, human-searchable) OR template-registry channel | For 42050 (version): `["l", "lindenmayer:42050", {"source_id": "<event_id_hex>", "source_created_at": <timestamp>, "template_name": "<name>", "version": "<ver>"}]` | Template versions are publishable assets. Cross-post 42050 as an agent/template entry in the agent directory (if the template describes an agent; e.g., "dev-node v1"). Alternatively, post in a template-registry channel as a stream message. |
| `KIND_LONG_FORM` (30023) | Template documentation channel | Markdown-formatted template spec, system prompt, and linked version event id | Richer format for publishing detailed template docs alongside the signed event. |

**Scope:** `MessagesWrite` (channel messages) or `UsersWrite` (if registering as agent profile)

**Identity Attestation:**
- A template version (42050) published by a persistent node should carry the node's NIP-OA `auth` tag, proving the owner authorized this template version.
- The cross-post into Buzz preserves the `auth` tag; the product displays "Template by [owner]" in the directory.

**Dedup Invariant:** Source event id + source timestamp. (Note: 38150 template pointers may be short-lived or meta-level; they may not need cross-post visibility in Buzz—decision deferred to architect.)

---

### 4.6 Summary of All Cross-Post Destinations

| Lindenmayer Kind | Primary Buzz Kind | Channel Type | Scope | Notes |
|------------------|-------------------|--------------|-------|-------|
| **42010** (node lifecycle) | STREAM_MESSAGE (9) | Subgraph channel | MessagesWrite | Observational; includes step/iteration summary |
| **42020** (telemetry) | STREAM_MESSAGE (9) or LONG_FORM (30023) | Subgraph channel | MessagesWrite | Aggregated metrics; richer format optional |
| **42030** (radio aggregates) | STREAM_MESSAGE (9) or TEXT_NOTE (1) | Subgraph or parent channel | MessagesWrite | Upward privacy-respecting bubbling |
| **42040/42041** (approvals) | STREAM_MESSAGE (9) in approvals inbox OR DM | Approvals NIP-29 group or DM | MessagesWrite + ChannelsWrite | Governance gate; scoped to decision-makers |
| **42050** (template version) | AGENT_PROFILE (10100) or LONG_FORM (30023) | Agent directory or template registry | UsersWrite or MessagesWrite | Publishable asset; carries NIP-OA attestation |
| **38150** (template pointer) | (Optional) STREAM_MESSAGE or not surfaced | Not surfaced OR registry channel | MessagesWrite | Meta-level pointer; cross-post visibility TBD |

---

## 5. Key Findings and Tradeoffs

### 5.1 Buzz Accepted Kinds vs. Lindenmayer Core Kinds

Buzz relay accepts a **finite, exhaustive set** of kinds. Lindenmayer's custom kinds (42010, 42020, 42030, 42040/42041, 42050, 38110, 38150) are **not accepted by Buzz relay**. This is by design per DESIGN.md §1:
- **Nostr core**: Lindenmayer kinds live on the Lindenmayer relay (permissive, accepts custom kinds).
- **Buzz layer**: Cross-posts carry derived views into Buzz as Buzz-accepted kinds (1, 9, 40002, 30023, 41010, 41011, etc.).

**Implication**: Lindenmayer cannot directly publish 42010 events into Buzz; they must be translated (a "cross-post") into, e.g., KIND_STREAM_MESSAGE (9) with tags carrying the source kind, event id, and timestamp.

### 5.2 Timestamp Drift and Backfill

The ±15-minute `MAX_TIMESTAMP_DRIFT_SECS` gate is enforced on **ingest** (before kind filtering). Historical backfill from Fractal source rows is possible on the Lindenmayer relay (which accepts historical `created_at`), but **not on Buzz relay** without fresh timestamps.

**Implication**: Cross-posts to Buzz must be generated near real-time or with a fresh `created_at` within the drift window. Backfill from very old Fractal records into Buzz is not feasible (Buzz rejects stale timestamps).

### 5.3 NIP-OA Attestation: Presence and Absence

NIP-OA auth tags are optional on events; absence does not prevent acceptance or display, only affects identity/ownership signal to the user.

**For Lindenmayer node identity**:
- Persistent nodes (those with subgraph channels, radio subscriptions) should carry `auth` tags signed by the node's owner (human responsible for the node).
- The Buzz product will display "Node X — owned by [owner]" when the auth tag is valid.
- Ephemeral worker nodes (no subgraph channel, no radio identity) can omit attestation; their work surfaces via aggregate rollups from persistent parents.

**For agent profiles (42050 cross-posts)**:
- A template published by a persistent node should carry the node's `auth` tag in the cross-posted `KIND_AGENT_PROFILE` (10100).
- This proves the template is owner-attested; the Buzz directory surfaces it as such.

### 5.4 Cross-Post Dedup Invariant

All cross-posts carry source event id and source timestamp in tags:
```json
{
  "source_id": "<42010_event_id_hex>",
  "source_created_at": <unix_timestamp>
}
```

A consumer (Buzz client, downstream tool) can check for duplicates by matching `(source_id, source_created_at)` and discard redundant cross-posts from multiple channels. This invariant is **load-bearing** (per DESIGN.md §1) because:
1. A node's work may be relayed into multiple Buzz channels (subgraph channel, parent channel, global feed).
2. Cross-posts must be idempotent; re-posting the same 42010 event into Buzz twice should yield one logical event, not two.
3. The core event (42010 on Lindenmayer relay) remains the source-of-truth; the Buzz layer is a derived view.

### 5.5 Privacy Boundary: Subgraph Channels

Per DESIGN.md §5–6.1, aggregates flow up, details stay in the subgraph. This translates to channel topology:
- **Subgraph channel** (NIP-29 group, named after the branch): contains detailed lifecycle and telemetry cross-posts.
- **Parent channel** or **global relay**: receives only curated aggregates (42030 events) that the subgraph author chooses to publish.
- **Approvals inbox**: restricted to decision-makers (a separate NIP-29 group with membership limited to approvers).

**Implication**: A subgraph's members control which aggregates surface upward; privacy is structurally enforced by channel membership, not by a post-hoc policy filter.

---

## 6. Uncertainties and Open Questions

1. **Agent Directory Implementation**: Buzz's agent directory surfaces `KIND_AGENT_PROFILE` (10100) events in a searchable UI. Exact indexing and filtering (e.g., search by skill, by owner, pagination) is product-layer; the core mechanism is event-driven.

2. **Template Pointer (38150) Cross-Post Visibility**: Whether 38150 events should surface in Buzz at all (as directory pointers, in a registry channel, or not surfaced) is a design decision. This research documents the option; the architect determines shipping.

3. **Multi-Channel Approval Workflows**: Approval requests could go to an approvals inbox (NIP-29 group) for group consensus, or to individual DMs for federated approval. Tag structure is the same; the architect chooses the channel topology.

4. **Historical Backfill**: Lindenmayer may want to cross-post historical events (e.g., past runs' telemetry) into Buzz for archival. The ±15-minute timestamp gate prevents backfill of old events. Workaround: re-issue cross-posts with fresh `created_at` (losing original timestamp precision), or house the full history on Lindenmayer relay only and accept that Buzz sees only real-time events.

5. **Radio Aggregate Privacy Scope**: A radio message may be private to the subgraph (e.g., internal debugging signal) or public (e.g., approval request). How to mark this scope in the 42030 event itself (e.g., an `audience` tag) is open; this research assumes the node chooses the cross-post destination (subgraph channel vs. parent channel) based on sensitivity.

---

## 7. Verification and Source Citations

All findings verified against Buzz repository @ daeaf7c:

- **NIP-29 Kinds and Scopes**: `crates/buzz-core/src/kind.rs` (lines 199–215 for NIP-29 lifecycle; 286–292 for state events)
- **Ingest Constraints**: `crates/buzz-relay/src/handlers/ingest.rs` (function `required_scope_for_kind()` for scope mapping; line 900 for `MAX_TIMESTAMP_DRIFT_SECS = 900`)
- **Channel Model**: `crates/buzz-core/src/channel.rs` (ChannelType enum, ChannelVisibility enum; channel.rs line 45 for nip29_group_id binding)
- **NIP-OA Identity**: `crates/buzz-acp/src/lib.rs` (NIP-OA verification via `buzz_sdk::nip_oa::verify_auth_tag()` and agent sibling checks)
- **Agent Profiles**: `crates/buzz-core/src/kind.rs` (KIND_AGENT_PROFILE = 10100, KIND_AGENT_ENGRAM = 30174)
- **DM Kinds**: `crates/buzz-core/src/kind.rs` (KIND_DM_OPEN = 41010, KIND_DM_ADD_MEMBER = 41011, KIND_DM_HIDE = 41012)

---

## 8. Recommendations for Implementation (Architect Decision)

This section documents candidate options; the architect decides which cross-posts ship in v1.

### Recommended v1 Minimal Set

1. **42010 (Node Lifecycle)** → `KIND_STREAM_MESSAGE` (9) into subgraph channel
   - Reason: Enables observability of node execution in the human-facing channel where the branch is managed.
   
2. **42020 (Telemetry)** → `KIND_STREAM_MESSAGE` (9) into subgraph channel
   - Reason: Complements lifecycle; humans need cost/latency insights at a glance.
   
3. **42040/42041 (Approvals)** → `KIND_STREAM_MESSAGE` (9) into approvals inbox channel
   - Reason: Governance gate; essential for human-in-the-loop decision flows.
   
4. **42050 (Template Version)** → `KIND_AGENT_PROFILE` (10100) for agent directory
   - Reason: Publishable asset; agent directory is a key human surface per DESIGN.md §5.

### Optional v1+ Additions

- **42030 (Radio Aggregates)** → `KIND_STREAM_MESSAGE` into parent channel (if privacy scope permits)
- **38150 (Template Pointer)** → Not surfaced in v1 (meta-level; can defer)

---
