---
name: findings
desc: Findings against claim C (Buzz desktop cannot render agent-activity tree/graph, no extension mechanism). ~/Code/buzz @ daeaf7c (HEAD; version string "0.4.24" not independently confirmed in package.json/Cargo.toml — worked from architect's citation).
created: 2026-07-24T01:05:56Z
updated: 2026-07-24T01:05:56Z
---

# findings

Status: workstream 1 (non-desktop clients) substantially done. Workstreams
2 (image escape hatch), 3 (mermaid/diagram deps — partially done via
package.json), 4 (24200 render classes), 5 (kind gate rigidity), 6 (non-plugin
extension points) still TODO. Parallel Explore-agent launch failed (hit a
"Fable 5" model usage limit on all 5 agents simultaneously — switch to direct
Bash/Grep investigation or retry Agent calls with an explicit model override
next time, e.g. model: "sonnet").

## Workstream 1: non-desktop clients — repo has FOUR clients, not one

pnpm-workspace.yaml (~/Code/buzz/pnpm-workspace.yaml) lists only
`desktop`, `web`, `admin-web` as workspace packages — **no shared UI/render
package between them**. `mobile/` is a separate Flutter/Dart app entirely
(not in the JS workspace, different language/toolchain).

- **desktop/**: the Tauri chat client. All of the prior evidence (TIMELINE_KINDS,
  MessageRow.tsx switch) is scoped here. deps: react-markdown ^10.1.0,
  remark-breaks, remark-gfm, shiki ^4.0.2. CONFIRMED present in
  desktop/package.json.
- **web/**: CONFIRMED NOT a chat/timeline client. Its routes
  (web/src/app/routes/*.tsx) are `repos.$repoId`, `repos.$repoId.blob.$`,
  `invite.$code` — this is a **git-repo browser** (Nostr git hosting UI:
  RepoTreeSection.tsx, RepoBlobViewer.tsx, RepoCommitsSection.tsx,
  RepoReadmeSection.tsx). Zero hits for "TIMELINE_KINDS" or MessageRow-style
  components in web/src (grepped: `TIMELINE_KINDS|timeline_kinds|timelineKinds`
  and filename patterns `*message*` — both zero). deps: react-markdown +
  remark-gfm only (renders README.md presumably), no shiki. **Not a lead for
  agent-activity rendering** — it doesn't subscribe to chat/timeline kinds at
  all. Note: it DOES have a literal "RepoTreeSection.tsx" but that's a git
  file tree, unrelated to agent-activity graphs — false-friend, don't cite as
  a win.
- **admin-web/**: CONFIRMED a bare, minimal admin app (package.json deps are
  just react/react-dom/vite, no markdown/render libs at all). Not a chat
  client, not investigated further — clearly out of scope for message
  rendering.
- **mobile/**: CONFIRMED a full separate Flutter chat client
  (mobile/lib/features/channels/{message_content.dart, timeline_message.dart,
  channel_messages_provider.dart, message_media.dart}) — genuinely
  independent render pipeline from desktop, written in Dart, could have
  different (looser or stricter) rendering rules. NOT YET checked: does
  mobile have its own TIMELINE_KINDS-equivalent kind filter, and what does
  message_content.dart's dispatch actually support (only checked for a
  `switch`/`case`/`Kind.` grep on message_content.dart — got only a video-kind
  media check at line 164, inconclusive, needs a full read next pass).

### BIG LEAD found but not yet fully chased: mobile `pulse` feature

`mobile/lib/features/pulse/` contains `agent_activity_card.dart` (177 lines,
read in full) and `pulse_models.dart` (139 lines, NOT yet read) — **this is a
mobile-only surface with no desktop equivalent** (grep for "pulse" or
"AgentActivityCard" in desktop/ not yet done — do that first next pass to
confirm it's really mobile-exclusive).

What `agent_activity_card.dart` actually shows (CONFIRMED, read the file):
a `AgentActivityCard` widget that renders a **group of notes from one agent
pubkey** (`AgentNoteGroup group` — has `.notes`, `.pubkey`, `.latestAt`),
collapsible when `group.notes.length > 1`, with a "BOT" badge, avatar with
green presence dot, and a "N updates · time" summary line. Tapping expands to
show each note via `NoteCard` (mobile/lib/features/pulse/note_card.dart, NOT
yet read). This reads as a **Twitter-like social feed of agent posts**, grouped
flat by author+time-window, NOT a tree/graph — same "flat" limitation pattern
as desktop's 24200 AgentSessionThreadPanel, just on a different client. Do NOT
overclaim this as a refutation without reading note_card.dart and
pulse_models.dart to see the actual note content shape (could still be a
lead if a note can embed rich content note_card.dart doesn't support on
desktop — unchecked).

`mobile/lib/features/activity/` (activity_page.dart, activity_provider.dart,
feed_item.dart) also unread — another mobile-only feature by name, unclear
if distinct from pulse or an overlapping notifications feed. TODO next pass.

## NOT YET DONE (pick up next iteration/step)

1. Read mobile/lib/features/pulse/{note_card.dart, pulse_models.dart} and
   mobile/lib/features/activity/*.dart fully — determine exact content shape,
   whether it's fed by kind 24200/44200/1 or something else, and whether it
   renders anything richer than desktop.
2. Full read of mobile/lib/features/channels/message_content.dart (only
   grepped, not read) — what kinds/media types does it actually dispatch on?
   Compare against desktop's closed switch.
3. Image escape hatch (workstream 2): trace PNG inline-render path in
   desktop, confirm SVG block, check size/count limits, check whether an
   agent/bot identity can post an image via crates/buzz-sdk without going
   through the upload UI (imeta tag construction), check if canvas (40100)
   also renders images.
4. Mermaid/diagram support (workstream 3): package.json check across all 4
   clients done — **ZERO hits for mermaid/d3/dagre/cytoscape/reactflow/
   graphviz/plantuml in any client's package.json** (desktop, web, admin-web
   checked via grep; mobile's pubspec.yaml NOT yet checked — Dart doesn't use
   package.json, check `mobile/pubspec.yaml` for a Dart mermaid/graph-viz
   package next). This is a real negative result but not fully closed until
   pubspec.yaml is checked and the actual remark/rehype plugin chain
   instantiation (not just deps) is confirmed unused-elsewhere.
5. 24200 render classes deep dive (workstream 4): AgentSessionThreadPanel
   full render-class enumeration not yet done at all.
6. Kind gate rigidity + non-plugin extension points (workstream 5+6): not
   started. Check TIMELINE_KINDS is truly compile-time-only, check for a
   dev/experimental settings path, check buzz:// deep link handler for
   Tauri webview-window-opening capability (could be an escape hatch to
   render arbitrary local/remote HTML — high value, unchecked), check bots/
   webhooks/custom-emoji/themes across all clients.

## Process note

Explore-agent (subagent) parallel launch failed across all 5 concurrent calls
with "You've reached your Fable 5 limit" — this appears to be a session-wide
model quota issue unrelated to this investigation. Direct Bash/Grep/Read from
the main loop worked fine and is the fallback. If retrying subagents, pass an
explicit `model` override (not the agent-type default) to avoid hitting the
same quota.
