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

## Iteration 2: workstreams 2/4/5/6 (partial — hit step budget hard, see below)

Budget ran out much faster than expected this step (~$0.53 step budget burned
in ~4 targeted grep/read calls) — could not complete the planned full sweep.
Recording what was found before stopping; several items remain genuinely
UNVERIFIED, listed honestly below rather than guessed at.

### Workstream 2 (image escape hatch) — PARTIAL, not closed
- CONFIRMED: `desktop/src/features/messages/ui/MessageRow.tsx:35` imports
  `parseImetaTags` from `@/features/messages/lib/parseImeta`; `imetaByUrl`
  (line ~221-222) is computed from `message.tags` and passed down (line 370)
  — this is the NIP-92 imeta-tag-driven inline image rendering path,
  confirms prior claim that images render inline via a real tag-parsing
  mechanism (not just an `<img>` heuristic).
- CONFIRMED: custom emoji also render as `<img data-custom-emoji>` (line 358
  CSS selectors target this) — a SECOND `<img>`-based rendering path distinct
  from the imeta attachment path. Not chased further (could custom-emoji
  syntax be abused for larger images? UNVERIFIED, did not check the custom
  emoji renderer's size handling).
- UNVERIFIED (ran out of budget before checking): size/dimension caps, GIF/
  animation support, whether canvas (40100) also renders inline images,
  whether an agent/bot identity can construct an imeta tag via buzz-sdk
  without a human-driven upload UI (crates/buzz-sdk builders not checked this
  pass). **This was flagged as the single most likely refutation of C and
  is the top priority for anyone picking this up** — the imeta path is
  confirmed to exist and is real, but "how big/rich a graph-as-image can get
  through it" is unanswered.

### Workstream 4 (24200 render classes) — NOT ATTEMPTED this pass, UNVERIFIED
No budget reached this workstream. AgentSessionThreadPanel and its per-class
renderers (plan/tool_call/etc.) are still unread. Pure carry-forward from
iteration 1's plan.

### Workstream 5 (kind gate rigidity) — PARTIAL, notable finding
- CONFIRMED there are actually **at least two separate kind-gate definitions**,
  not one: a frontend one, `CHANNEL_TIMELINE_CONTENT_KINDS`
  (referenced at `desktop/src/features/messages/hooks.ts:79` as
  `CHANNEL_TIMELINE_KINDS = new Set(CHANNEL_TIMELINE_CONTENT_KINDS)`, and
  again at `desktop/src/features/messages/lib/channelWindowReconciliation.ts:11`),
  distinct from the backend `TIMELINE_KINDS` `[u32;11]` cited by the prior
  pass at `src-tauri/src/commands/messages.rs:30-42`. **The actual
  definition site of `CHANNEL_TIMELINE_CONTENT_KINDS` was NOT located this
  pass** (grep for the assignment with a `--include=*.ts*` glob failed
  silently — shell quoting issue, not a real negative result; needs a retry
  with a corrected grep, e.g. `grep -rn "CHANNEL_TIMELINE_CONTENT_KINDS ="`
  without the broken include flag). This matters: if the frontend list is a
  superset/different set from the backend list, the prior pass's claim that
  "the kind gate" is the single `[u32;11]` in messages.rs is **incomplete,
  not wrong** — there may be two gates to widen, or the frontend one may
  already be more permissive. Flag this as a place the prior pass's
  enumeration is unconfirmed, not as a refutation.
- Also noted `desktop/src/testing/e2eBridge.ts:4196` defines its own
  `TIMELINE_KINDS` — but this is clearly a **test-mock file** (e2e test
  bridge), not a real gate; do not cite as a lead.
- No settings/dev-mode toggle found that widens either kind list (searched
  desktop/src for "feature.flag|experimental|devMode|dev_mode" combined with
  the kind-list grep) — but see workstream 6 below, which found a REAL
  feature-flag system whose interaction with kind gating is unchecked.

### Workstream 6 (non-plugin extension points) — PARTIAL, real lead found
- CONFIRMED: Buzz desktop has a genuine **feature-flag / experimental-features
  system**, not just static compiled routes as the prior pass implied.
  Evidence: `desktop/src/shared/features/store.ts` (file header comment:
  "Persistence layer for feature flag overrides"), consumed by
  `desktop/src/features/settings/ui/ExperimentalFeaturesCard.tsx` (read in
  full) which renders a Settings > Experiments panel iterating over
  `desktopFeatures: FeatureDefinition[]` (imported from
  `@/shared/features`), each with a toggle Switch persisted via
  `useFeatureToggle(feature.id)`. One concrete flag confirmed:
  `feature.id === "agentManagedProfiles"` triggers
  `setAgentManagedProfiles(value)` (a Tauri command call) — i.e. this is a
  REAL toggleable capability, not cosmetic.
- **UNVERIFIED / not closed**: the full `desktopFeatures` list (what other
  flags exist besides agentManagedProfiles) was not enumerated — a grep for
  `id:\|name:` in `desktop/src/shared/features/*.ts` returned 0 matches,
  meaning the manifest is defined some other way (maybe a different file
  name/pattern, e.g. `features.ts` vs a subdirectory, or template literals
  not matching the grep pattern) — this needs a `find`/broader grep next
  pass, not a dead end. **This is the most promising unclosed lead**: if any
  experimental flag widens the timeline-kinds allowlist or enables a richer
  render path, that would be a direct refutation of C's "no config path"
  framing. Not confirmed either way.
- Did not reach: bots/webhooks/slash-commands/link-unfurl/buzz:// deep-link
  window-opening/Tauri WebviewWindow checks (planned grep for
  `WebviewWindow|shell::open|open_url|buzz://` in src-tauri/src failed on a
  shell glob quoting bug (`--include=*.rs` didn't expand) and was not
  retried before budget ran out — genuinely UNVERIFIED, not a negative
  result; this axis (arbitrary content via deep link/webview) is untested.

### What prior pass likely got right that we did NOT re-verify (per instructions)
Did not re-check file:line accuracy of the original TIMELINE_KINDS/
MessageRow.tsx citations, rehype-raw exclusion, or SVG blocking — per
instructions, spending budget on breadth not re-verification.

### What prior pass may have gotten WRONG or incomplete (for report item (e))
1. Implied the kind gate is a single compiled `[u32;11]` in
   `messages.rs:30-42` — we found a SECOND, frontend-side gate
   (`CHANNEL_TIMELINE_CONTENT_KINDS`) whose relationship to the backend list
   (same set? superset? independently maintained?) was never characterized
   by either pass. Two gates that must both be checked is a materially
   different picture than "one compiled list."
2. Implied Buzz desktop has no config/settings path relevant to
   extensibility ("routes are statically generated... no
   plugin/extension/custom-view system") — but a real, working
   feature-flag/experimental-settings system exists
   (`ExperimentalFeaturesCard.tsx`, `shared/features/store.ts`) and at least
   one flag (`agentManagedProfiles`) gates a real backend capability. This
   doesn't itself prove a render-path extension exists, but it undercuts the
   framing that nothing in the app is configurable-not-compiled — the prior
   pass's search for "plugin/extension" may have missed this because a
   feature-flag toggle doesn't look like a "plugin system" but functionally
   is an extension point in the sense the claim cares about (config beats
   forking).

## Iteration 2 additions (budget-constrained — partial)

Ran out of step budget mid-investigation (Bash tool cost spiked much faster
than expected this iteration — went from $0.92 to near-zero over ~4 grep/read
calls). Only got through fragments of workstreams 2, 4, 5 before forced to
stop. Recording exactly what was and wasn't checked so the gap is visible.

### Workstream 5 (kind gate rigidity) — PARTIAL, promising thread found
- `desktop/src/features/settings/ui/ExperimentalFeaturesCard.tsx` (read in
  full, ~60 lines): CONFIRMED there IS a live feature-flag system —
  `desktopFeatures` manifest + `useFeatureToggle(feature.id)` from
  `@/shared/features`, rendered as toggles in Settings > Experiments. Comment
  in the code: "Manifest is preview-only by definition; every desktop entry
  is a preview feature." Only ONE toggle's effect was actually traced:
  `agentManagedProfiles`, which calls `setAgentManagedProfiles(value)` (a
  Tauri command) — nothing to do with kind lists or rendering.
  **UNVERIFIED**: did NOT get to read `desktop/src/shared/features/*.ts` to
  enumerate the full `desktopFeatures` manifest and see if ANY entry toggles
  kind-list scope or rendering behavior. `shared/features/store.ts` has a
  comment "Persistence layer for feature flag overrides" (grepped, not read)
  — this is the single most promising unexplored thread for workstream 5.
  Next node/iteration should `grep -n "id:" desktop/src/shared/features/*.ts`
  and read the full manifest.
- Found a second, DIFFERENTLY-NAMED kind-gate symbol:
  `CHANNEL_TIMELINE_CONTENT_KINDS` (referenced in
  `desktop/src/features/messages/hooks.ts:79` and
  `desktop/src/features/messages/lib/channelWindowReconciliation.ts:11`, both
  building a `CHANNEL_TIMELINE_KINDS` Set from it) — this is DISTINCT from
  the prior pass's cited `TIMELINE_KINDS` at
  `src-tauri/src/commands/messages.rs:30-42` (that one's Rust/backend; this
  one's TypeScript/frontend). **UNVERIFIED whether they enumerate the same
  kind set** — did not find/read the definition of
  `CHANNEL_TIMELINE_CONTENT_KINDS` itself (only its two usage sites). If the
  frontend list is a superset of the backend list (or vice versa), that's a
  real gap in the prior pass's "closed switch" claim — worth a follow-up
  `grep -rn "CHANNEL_TIMELINE_CONTENT_KINDS\s*=" desktop/src` (last attempt
  used an invalid glob and returned no matches — retry with
  `--include=*.ts --include=*.tsx` as separate flags, not a brace pattern,
  or drop the include and just grep the whole desktop/src tree).
- Also unverified: a THIRD kind list exists at
  `desktop/src/testing/e2eBridge.ts:4196` (`TIMELINE_KINDS = new Set([...`)
  — this is test/mock infrastructure (e2eBridge), almost certainly not a
  production gate, but not confirmed as test-only vs. reachable in a built
  app. Low priority to chase but flagging so it isn't mistaken for a real
  hit later.

### Workstream 2 (image escape hatch) — barely started
- CONFIRMED: `MessageRow.tsx:35` imports `parseImetaTags` from
  `@/features/messages/lib/parseImeta`, used at line ~221-222
  (`imetaByUrl = parseImetaTags(message.tags)`) and passed as a prop at
  line 370. This confirms NIP-92 imeta-tag-based image rendering exists in
  the timeline, consistent with the prior pass's "PNG uploads render inline"
  claim, but the actual `<img>` render call, size caps, and whether
  non-human (bot/agent) identities can attach imeta tags via buzz-sdk were
  NOT reached this iteration. `parseImeta.ts` itself was not read.
- Did NOT check: canvas (40100) image rendering, GIF/animation handling,
  crates/buzz-sdk image/attachment builders, upload size/dimension limits.

### Workstream 6 (webview/deep-link/shell-open extension points) — NOT reached
Attempted one grep (`WebviewWindow|shell::open|open_url|buzz://` across
`src-tauri/src --include=*.rs`) but the `--include=*.rs` glob syntax failed
silently (zsh "no matches found" — the flag needs to be passed differently
to ripgrep/grep than what was tried) and was not retried before budget ran
out. **This entire axis is UNVERIFIED** — a Tauri `WebviewWindow` or
`shell.open` capability, if present, is exactly the kind of "arbitrary
content in a window" surface that could refute C, and it was never actually
searched successfully. Highest-value next step for a follow-up pass.

### What did NOT get attempted at all this iteration
- Workstream 4 (24200 render class enumeration) — zero progress, still only
  the brief's own summary to go on.
- Workstream 1 close-out (mobile pulse_models.dart, note_card.dart,
  activity/*.dart, pubspec.yaml mermaid check) — zero progress this
  iteration, still open from iteration 1.
- Workstream 3 (mermaid on mobile) — same, still open.

## Process note

Explore-agent (subagent) parallel launch failed across all 5 concurrent calls
with "You've reached your Fable 5 limit" — this appears to be a session-wide
model quota issue unrelated to this investigation. Direct Bash/Grep/Read from
the main loop worked fine and is the fallback. If retrying subagents, pass an
explicit `model` override (not the agent-type default) to avoid hitting the
same quota.
