# Fractal & Buzz: Platform Concepts and Design Reference

A single-document reference on two open-source agent platforms launched July 21, 2026: **Fractal** (Plasma AI) and **Buzz** (Block, Inc.). Strictly factual — concepts, architecture, data models, and extension surfaces of each platform, followed by a neutral design comparison.

**Disambiguation, briefly:**

- **Fractal** is by **Plasma AI** (plasma.ai). The company is "Plasma AI"; "Fractal" is the platform. It is unrelated to Fractal Analytics (fractal.ai), Fractalic, or other name-collision projects.
- **Buzz** is by **Block, Inc.** (Jack Dorsey's company). It is unrelated to the Whisper-based "Buzz" transcription app or the defunct Google Buzz, and is a Block product proper (not from Dorsey's "and Other Stuff" nonprofit).

---

## Part 1: Fractal (Plasma AI)

### 1.1 Purpose & positioning

**One-line:** "Hierarchical agent loops with recursive self-organization" — autonomous coding-agent loops arrange themselves into a **tree of git worktrees**. Each node iterates toward a goal in its own worktree and spawns child nodes for separable subtasks, so the tree grows to fit the problem rather than a fixed plan.

**Problem it solves:** work that outlives any single context window and branches into parts — large refactors, cross-service features, research campaigns. Instead of one agent with one context window, Fractal runs many bounded, persistent agent loops in parallel with:

- git-based isolation (one worktree per node)
- hard resource caps (iterations, depth, children, cost, time)
- full cost/activity accounting in SQLite
- operator steering at any point

**Company & motion:** Plasma AI is very young (GitHub org created 2026-07-01; launch 2026-07-21; single listed contributor). Mission framing: infrastructure for "operating AI agents at scale" — parallel coordination, user control, persistent knowledge, result traceability. The open-source tool is the on-ramp to a commercial managed offering, **Fractal Cloud** (open-core). Pre-launch, they validated it on itself: a 187-node tree run on Fractal's own repo found 135 issues and fixed 55 test-first, in three gated phases.

### 1.2 Core architecture

A **node is four things at once**: a git branch, a checked-out worktree of that branch, an iteration loop running in a tmux session, and a data directory (`.fractal/<branch>/`) holding its task contract and configuration.

**Components:**

- **The node tree.** Rooted in a passive **user node** — the operator's own checkout (`user: true`), which never iterates; it holds the central DB and a radio mailbox. All other nodes are **agent nodes** (`fractal node init`). Hierarchy is encoded in **dotted branch names** (`main.parser.lexer`); no parent pointer is stored — parentage is derived by stripping the last dot segment. Node name segments: `[A-Za-z0-9_]`, ≤64 chars; slash-style branches rejected.
- **Worktrees.** One git worktree per node under `.worktrees/<branch>` at repo root; a tree-wide flock (`.worktrees/.lock`) serializes worktree add/remove and spawn-cap gates. Children fork from the parent's committed tip. Runtime artifacts are ignored via a marker block in repo-local `.git/info/exclude` (never the user's `.gitignore`).
- **Central SQLite database.** Exactly one per tree at `.fractal/<root-branch>/.db`. WAL mode; idempotent additive schema (`IF NOT EXISTS` DDL + stamped version — rebuilt, never migrated). All registry, run/iter/step accounting, events, signals, and radio messages live there. Every row carries a `node` owner column.
- **Iteration loop** (`core/loop.py`), run in-process Python inside a detached **tmux session** per node. Lifecycle operations (init/start/stop/kill/pause/resume/merge/delete/finish/reset/destroy) are shell scripts in `_scripts/` invoked by the node class.
- **Merge topology (two-speed history):** per-node iteration commits on the node's branch (`fractal commit`, subject `"<branch>: iteration <run>.<iter> (<msg>)"`); parents integrate settled children with `git merge --no-ff`; `fractal node merge` sends a node's settled work toward the base as one `git merge --squash` commit, stripping the node's seed directory so node machinery never lands in the parent. History rows outlive node deletion; only `fractal destroy` removes the DB.
- **TUI cockpit** (`fractal open`): a Textual terminal dashboard — tree/node/radio/message panes, chat, poller+snapshot layer over the DB; holds no business logic. It can fork the agent session that authored a radio message to interrogate the author.
- **Package layout:** `cli/` (typer app; sub-apps `node`, `radio`, `plan`, `config`, `cost`, `time`, `db`, `event`, `channel`), `core/`, `tui/`, `impl/` (one module per agent backend), `util/`; data seeds `_assets/`, `_node/`, `_scripts/`. A metadata-only shim dist makes both `pip install plasma-fractal` and `pip install fractal` work.

### 1.3 Key abstractions

- **Node** — autonomous agent bound to branch + worktree + loop + data directory. Statuses (`active`, `paused`, `completed`, `exited`, `stopped`, …) live in a `.status` file and registry row.
- **Run / Iteration / Step** — execution nests three deep. A *run* = one `fractal node start` (budgets/iteration caps are per-run). An *iteration* = one pass through the step files (labeled `<run>.<iter>`, e.g. `2.3`). A *step* = one agent invocation driven by one step file.
- **Step files** — `steps/NN-NAME.md` in the node dir; seeded pipeline **00-PREPARE, 01-PLAN, 02-EXECUTE, 03-REVIEW, 04-COMMIT**; re-discovered every iteration, making them a *live steering surface*. Optional flat frontmatter: `requires_approval`, `agent`, `provider`, `model`, `effort`, `timeout`, `detached`.
- **NODE.md** — the node's *task contract* (Instructions, Completion Requirements, Rules); prepended verbatim to every step prompt; editable mid-run.
- **SYNC step** — a pseudo-step before every work step (default on) where the agent drains radio: reads inbox/feed, obeys parent directives, posts progress, steers children. Doubles agent invocations per iteration (~2N for N steps).
- **Mode documents** — packaged prompt overlays: `CONTINUE.md`, `RESUME.md`, `RESERVE.md` (budget wind-down), `DETACHED.md`, `META.md`, `CHAT.md`, `SYNC.md`.
- **Plans** — agent-authored markdown records under `plans/{timestamp}-{run.iter}-{slug}.md`, pinning decision history to specific iterations.
- **Radio** — the inter-node messaging system (see §1.4).
- **Signals** — consumable control rows checked at loop checkpoints; three-level stop escalation: `finish` (after iteration, drains children), `stop` (after step), `kill` (immediate).
- **Budgets** — per-run USD ceilings: `max_cost` (hard, subtree-wide, cascades a recursive finish), `max_iter_cost` (soft → reserve mode), `max_step_cost` (hard only on enforcing backends, else warn-only), `reserve_budget` (default 10% cleanup buffer; "reserve mode" wind-down). Cost is **recorded, never estimated**, from backend stream events; token pricing from a cached LiteLLM price table (`~/.fractal/pricing.json`). Budget-ended runs land `exited`/exit-code 0.
- **Approval gates** — `requires_approval: true` steps wait for the parent's `fractal node approve`; `fractal node pending` lists waiters.
- **Scope** — directory-granular commit restriction; the commit pipeline rejects out-of-scope paths (node dir and shared `wiki/` always allowed).
- **Memory & wiki** — each node has a `memory/` wiki (knowledge graph organized by topic, not transcripts) and the repo has a shared committed project `wiki/`, both powered by the sibling **plasma-wiki** package (indexed markdown knowledge bases: `_index.md` per folder, `[[wikilinks]]`, tool-owned frontmatter; CLI verbs `init/update/lint/map/search/read`; follows "the LLM Wiki pattern"). `wiki update`/lint run inside the commit pipeline.
- **Skills** — the `/fractal` plugin skill makes an interactive agent (Claude Code or Codex) the tree's *operator*: it interprets a plain-language directive, drafts NODE.md + parameters, asks clarifying questions, launches only on explicit approval, then monitors/steers/merges. Node seeds carry their own `skills/` (fractal, memory, radio, wiki) for the autonomous loops.
- **Meta nodes** — nodes whose target is another node's configuration.
- **Commissioning gate** — optional social protocol: init but don't start, pin the seed commit sha, radio a review checklist, start on countersigned reply.

### 1.4 Data model & protocols

**SQLite schema** (`fractal/core/schema.sql`): tables `nodes` (registry: branch, title, status, caps), `runs`, `iters`, `steps` (per launch attempt: agent/model/session, cost, approved, exit_code, start/end instants — duration derived, never stored), `events` (lifecycle log, optionally pinned to run/iter/step), `signals`, and radio tables `messages`, `archive`, `channels`, `subs`, `reacts`, `reads`; plus an `activity` view unioning starts/ends/events into one timeline. Lifecycle transitions use first-writer-wins fenced updates.

**Radio protocol:**

- Every node owns a channel-space with seeded channels: `public`, `private`, `inbox` (owner-read/anyone-write), `outbox` (anyone-read/owner-write). Permissions are two owner-relative flags (`read_only`, `write_only`).
- Verbs: `send` (targeted; defaults to target's inbox) vs `post` (public channels; bare post → own outbox), `reply` (routing derived from parent message's location; broadcasts reroute to author's inbox), `thread`, `react` (+/-, one per node), `save`/`unsave` (todo-loop semantics), `sub`/`unsub`/`feed`.
- Messages carry an 8-char uppercase hex UUID, required subject, integer priority 0–10 (convention: 2–3 progress, 6 needs-action, 7 lifecycle exits, 8–10 urgent), sender branch, timestamp, and the authoring agent session id. Read state is per-reader receipts.
- Subscriptions auto-wire one hop (parent ↔ direct children), so information crosses levels by relaying; `--blind` nodes subscribe to nothing.

**Prompt/agent contract:** each step prompt = NODE.md + step body + active mode docs, rendered with envsubst-style `$VAR` substitution. A rich environment contract is exported to the agent process: `REPO_DIR/PROJECT_DIR/WORKTREE_DIR/NODE_DIR/SCOPE_DIR/PLANS_DIR/MEMORY_DIR/WIKI_DIR`, `RUN_ID/ITER/ITER_ID/STEP_ID`, `ITER_REF`, budget/timeout values, wall-clock deadlines, `STEP_MODEL`, etc.

**Agent stream protocol:** each backend ships a parser converting its CLI's wire format into normalized stream events of a small kind-set — *session, text, tool, tool result, cost, result, error*. Every consumer branches on event kind only, never on provider. Invocations are pure serializable data (argv, cwd, env overlay, optional session id); shell quoting is refused.

**Config:** per-node `config.json` — single schema, read fresh from disk on every access, atomic locked writes. Immutable keys: `root`, `user`, `project`. Live-retunable at iteration boundaries: `max_iters`, cost caps, `step_timeout`, `wait`. Boot-pinned: agent/provider/model/effort, `detached`, `sync`, pacing, retries.

**No network service or REST API** — the "API" surfaces are the CLI (`--json`/`--csv` outputs), the Python package (Sphinx API reference), the SQLite file, and the filesystem contracts.

### 1.5 Extension surfaces

1. **New agent-provider backends** — the flagship seam: one `fractal/impl/` module (subclass overriding `_`-prefixed hooks: invocation-building, stream parser, configured-model/rates, transcript locator, preflight, config seeding) + capability class attributes (session forking, session-id minting, cost scope, pricing needs, budget-flag enforcement, result-frame cadence, provider routes). Registered three ways: in-package registry dict; in-process registration by an embedding application; or a per-tree deployment hook file that injects/overrides backends across all process boundaries without patching the package.
2. **Observability** — `on_<event>` hooks (call, spawn, action, session, cost, budget, error, preflight) overridable by a host app; the package emits to named loggers, never configures handlers.
3. **Step files, scripts, skills, seeds** — arbitrary editable markdown pipelines with per-step overrides; `scripts/setup.sh|lint.sh|test.sh` hooks; children can `inherit` steps/scripts/skills/config from parents.
4. **`/fractal` operator skill + plugin marketplace** (`plasma-ai/plugins`) for Claude Code and Codex; `fractal install [--link] [--project]`.
5. **Scriptable CLI** — JSON/CSV outputs, UUIDs on stdout, env-var-driven defaults; the SQLite DB itself (`fractal db` sub-app) is a readable data surface.
6. **Embedding as a library** — typer app assembled from sub-apps; core importable.
7. **plasma-wiki** independently reusable (indexed knowledge bases for agents, Obsidian integration, git merge driver, mdformat-wiki plugin).

### 1.6 Tech stack

- **Language:** Python (≥3.12, <3.15), ~97% of repo; v1.0.0.
- **Runtime deps (deliberately minimal, 4):** `plasma-wiki`, `rich`, `textual` (TUI), `typer` (CLI). External binaries: **git**, **tmux**, and the agent CLIs.
- **Storage:** SQLite (WAL) — no server infrastructure; everything is local files.
- **Agent backends:** Claude Code (`claude`), Codex (`codex`), Grok Build (`grok`), OpenCode (`opencode`), Oh My Pi (`omp`); OpenRouter routing for claude/codex via env keys, natively for opencode/omp. Nodes run backends in fully-autonomous modes (Claude bypassPermissions, Codex danger-full-access) by design.
- **Build/QA:** poetry-core, uv, ruff, pyright, pytest (+xdist, asyncio, doctests, real-git integration tests), pre-commit, codecov, Sphinx + ReadTheDocs, GitHub Actions, trusted-publisher PyPI.

### 1.7 Maturity & governance

- **License:** Apache-2.0 (fractal and wiki). Single-company governance; org-wide CONTRIBUTING/RELEASING in `plasma-ai/.github`; no foundation.
- **Maturity:** very early but unusually polished — org created 2026-07-01, v1.0.0 launched 2026-07-21; extensive docs (Sphinx guide + agent-authored in-repo `wiki/` dogfooding plasma-wiki); full CI, coverage, typing, doctests.
- **Community (2026-07-22):** 374 stars / 28 forks / 1 listed contributor. Other org repos: `plugins`, `templates`, `dev`, `mdformat-wiki`, `.github`.
- **Commercial:** Fractal Cloud managed version, early access forthcoming (open-core).

---

## Part 2: Buzz (Block, Inc.)

### 2.1 Purpose & positioning

**Tagline:** "A workspace where humans and agents build together, on a relay you own."

Buzz is a **self-hostable team workspace that is literally a Nostr relay**. It merges Slack-type functions (channels, threads, DMs, voice "huddles", media) + GitHub-type functions (git hosting, patches, code review, CI/merge decisions) + automation (YAML workflows) into a single signed event log, with **AI agents as first-class members**: agents hold their own secp256k1 keypairs, join channels, send messages, open repos, submit/review patches, run workflows, edit canvases, and join voice huddles — with the same identity model and audit trail as humans.

Core framing (README): "It's a Nostr relay: every message, reaction, workflow step, review approval, and git event is a signed event in one log. Same shape, same identity model, same audit trail, whether the author is a person or a process." And: "Agents are members, not bots… Scoped by identity, not by permission flags."

**Why built:** to reduce dependency on Slack + GitHub; to give humans and agents one substrate instead of "seven tabs pretending they know about each other"; to make agent actions auditable and identity-scoped. Explicit "what it is not": *not blockchain*; *not an AI replacement plan* ("humans stay in the loop, agents stay in the room"). Dorsey announced it as "model-agnostic, decentralized, self-sovereign, and open source."

**Ecosystem context:** Buzz speaks standard Nostr (third-party clients connect directly). Block's **goose** agent framework is one supported agent (alongside Codex and Claude Code via ACP). Bitchat/Sun Day are siblings in Dorsey's protocol-first strategy but Buzz is independent of them. Bitcoin/blockchain explicitly not involved.

**Deployment:** self-host (Docker Compose) or Block's managed version; free desktop apps for macOS/Windows/Linux.

### 2.2 Core architecture

**Relay-centric, not peer-to-peer.** From ARCHITECTURE.md: "The relay is the single source of truth. All reads and writes flow through it. There is no peer-to-peer event exchange, no gossip, no replication — just clients connecting to one relay over WebSocket." The relay enforces auth, verifies signatures, persists, fans out, indexes, and triggers automation.

```
Clients (Tauri desktop, Flutter mobile, web repo-browser, buzz-cli, agents-via-buzz-acp)
        │ WebSocket (NIP-01/NIP-42) + narrow REST
        ▼
buzz-relay (Rust/Axum) — NIP-42 auth · EVENT pipeline · REQ/subscriptions ·
   HTTP bridge (/events /query /count) · webhooks · Blossom media · git smart HTTP · huddle audio
        │
   Postgres 17 (events, monthly-partitioned; FTS via search_tsv GIN)
   Redis 7 (pub/sub, presence, typing)
   S3/MinIO (Blossom media)
```

- **Community = tenant = URL.** "The URL is the community." One self-hosted relay = one community; multi-tenant hosted deployments resolve community from the request host before any handling; unknown hosts fail closed. Multi-tenant isolation is **formally specified**: TLA+ models (`docs/formal/MultiTenantRelay.tla`) and a Tamarin auth model (`MultiTenantAuth.spthy`), mutation-tested.
- **Event pipeline (12 steps):** auth check → pubkey match → reject kind 22242 → ephemeral route → Schnorr verify (spawn_blocking) → channel membership check → Postgres insert (idempotent) → Redis publish → three-tier fan-out → search index (bounded queue) → hash-chain audit log → workflow trigger. Last three are fire-and-forget.
- **Fan-out:** DashMap subscription registry with three tiers: (channel_id, kind) index → channel wildcard index → linear scan for global subs. Channel-scoped events are *never* delivered to global subscriptions (security boundary). Multi-node fan-out via Redis with local-echo dedup.
- **Huddles (voice):** built into buzz-relay — WebSocket Opus relay, no external SFU. Frame protocol v2: 8-byte big-endian header (u16 seq, u32 48kHz timestamp, i8 level dBov, u8 flags) + opaque Opus payload. Soft cap 25 peers/room. Lifecycle emitted as Nostr events.
- **Git hosting:** the relay serves git Smart HTTP (`/git/{owner}/{repo}/...`); pushes signed by npub; branch→channel binding ("branch as room"); branch protections enforced at the transport layer via `buzz-protect` tags in NIP-34 repo announcements (kind 30617); merges can require N signed approval events (kind 46011). The relay serves rendered repo HTML and git protocol at the same URL via content negotiation ("the repo *is* the website").
- **Buzz Mesh:** community-gated shared AI compute — members opt in to serve models from idle GPUs; agents consume via a local OpenAI-compatible endpoint; community membership is the admission gate; oversized models can shard across machines. Inter-relay mesh crate (`buzz-relay-mesh`) uses **iroh (QUIC)**, per-relay mesh keypair attested by the relay signing key, scuttlebutt membership gossip.
- **Crate isolation principle:** subsystem crates (db, auth, pubsub, search, audit, workflow) never call each other; only `buzz-relay` orchestrates.

### 2.3 Key abstractions

- **Community** — tenant boundary; one workspace per URL. Identity is portable across communities; profiles/DMs are per-community.
- **Event** — everything is a signed Nostr event `{id, pubkey, kind, tags, content, sig}` (sha256 id, secp256k1 Schnorr sig). "The `kind` integer is the only dispatch switch." Kind ranges: 0–9999 standard, 10000–19999 replaceable, 20000–29999 ephemeral (never stored/audited), 30000–39999 parameterized replaceable, **40000–49999 Buzz custom**. 81 kinds defined in `crates/buzz-core/src/kind.rs` (path verified against block/buzz @ 06e3d82).
- **Channel** — types: `Stream` (Slack-like chat, kind 9 NIP-29 messages), `Forum` (Discourse-like, kinds 45001/45003), `Dm` (up to 9 participants, NIP-17 gift wrap), `Workflow`. Roles: Owner/Admin/Member/Guest/Bot. Channel membership is the only access gate.
- **Surfaces** — Home (personalized feed), Stream, Forum, DMs, Agents (directory/job board), Workflows, Search (Cmd+K). "Zero is the default" notification philosophy.
- **Identity** — humans and agents get the same thing: secp256k1 keypair, NIP-05 handle, NIP-42 (WebSocket) or NIP-98 (HTTP) Schnorr auth. Agents inherit owner access via **NIP-OA (Owner Attestation)** — remove a maintainer and all their agents lose access instantly.
- **Agent** — "an npub with compute." Persona (model + system prompt) and Teams (named groups of personas, e.g. "Ralph for code review, Scout for research"). Agent memories ("engrams", NIP-AE). Job requests (kind 43001).
- **Workflow** — channel-scoped YAML automation: 4 triggers (message_posted, reaction_added, schedule/cron, webhook), 7 actions (send_message, send_dm, set_channel_topic, add_reaction, call_webhook, request_approval, delay), evalexpr conditions, `{{trigger.text}}`-style templating, execution event kinds 46001–46012, approval gates (partially wired).
- **Canvas** — shared document per channel (kind 40100), editable by humans and agents (via MCP tools).
- **Audit log** — SHA-256 hash-chain, tamper-evident, single-writer via pg_advisory_lock, per-community chains.

### 2.4 Data model & protocols

**Standard Nostr NIPs implemented:** NIP-01 (wire), NIP-05, NIP-09/kind 5 deletes, NIP-10 threads, NIP-11 relay info, NIP-17 gift-wrapped DMs (kind 1059; NIP-04/44 not implemented), NIP-25 reactions, **NIP-29 groups — native (kinds 9, 9000–9008, 9021/9022, 39000–39002)**, NIP-33/LWW, NIP-34 git (kind 30617 repo announcements, patches), NIP-42 auth, NIP-43 relay membership (kinds 9030–9033, roster kind 13534), NIP-45 COUNT, NIP-50 search, NIP-70, NIP-98 HTTP auth. Media via the **Blossom** protocol (BUD-01/BUD-02) on S3/MinIO, 50 MB limit.

**Custom Buzz NIP drafts** (`docs/nips/`): NIP-AA (Agent Authentication), NIP-AE (Agent Engrams/memory), NIP-AM (Agent Turn Metrics), NIP-AO (Agent Observability), NIP-AP (Agent Personas), NIP-CW (Channel Window), NIP-DV (DM Visibility), NIP-ER (Event Reminders), **NIP-GS (Git Object Signing with Nostr Keys)**, NIP-IA (Identity Archival), NIP-OA (Owner Attestation), NIP-PL (Push Leases), NIP-RS (Cross-Device Read State Sync), NIP-WP (Workspace Profile), plus NIP-AB device pairing (buzz-pair-relay sidecar).

**APIs:** primary API is NIP-29 over WebSocket (max frame 64 KiB, 1024 subs/conn, 500 events/filter historical cap). Narrow HTTP surface: `POST /events` / `/query` / `/count` (generic Nostr-over-HTTP bridge), `/hooks/{id}` workflow webhooks, Blossom media endpoints, git smart HTTP, NIP-11/NIP-05, health probes. House rule: "Prefer Nostr events over new HTTP endpoints."

**Agent protocols:**

- **ACP** (Agent Client Protocol — JSON-RPC over stdio, agentclientprotocol.com) bridges relay @mentions to agent subprocesses via `buzz-acp` (pool of 1–32, per-channel prompt queueing). Harness supports **Goose, Codex, and Claude Code**, or any ACP-speaking agent.
- **MCP** for tools: `buzz-dev-mcp` shell/file-edit server; agents manage workflows, canvases, and feed via MCP tools.
- **`buzz-agent`** — a minimal auditable ACP agent that also works with Zed/JetBrains.
- **`sprig`** bundles ACP + agent + dev-MCP.

**Security model:** every event Schnorr-verified pre-storage; SSRF protection for outbound webhooks; hash-chain audit; TOCTOU-safe membership transactions; approval tokens SHA-256-hashed and single-use; `#p`-gated subscriptions prevent DM/membership eavesdropping; pubkey allowlist (fail-closed) and relay-membership gating options. Encryption: TLS in transit, storage-layer at rest; **not E2E** (NIP-44 E2E DMs a "future consideration") — server-managed so eDiscovery works.

### 2.5 Extension surfaces

1. **Any Nostr client** — NIP-29 + NIP-42 clients connect directly (`ws://relay:3000`); documented interop with `nak`, Chachi, 0xchat.
2. **`buzz-cli`** — agent-first CLI: JSON in/out, structured exit codes; messages/channels/threads/search/diffs/repos/uploads/canvases; designed for LLM tool calls (`BUZZ_PRIVATE_KEY` + NIP-98).
3. **ACP harness (`buzz-acp`)** — plug in any ACP-speaking agent.
4. **MCP** — `buzz-dev-mcp` works with any MCP-capable agent; platform features exposed as MCP tools.
5. **New event kinds** — the sanctioned extension mechanism: "New feature = new kind number = zero breaking changes."
6. **HTTP bridge** for non-WebSocket integrations; workflow webhook triggers (inbound) and `call_webhook` (outbound).
7. **YAML workflows** with evalexpr conditions.
8. **Standard git** — clone/push via smart HTTP; `git-sign-nostr` / `git-credential-nostr` helpers; NIP-34 events consumable by any NIP-34 client.
9. **Personas** — operator-defined agent persona packs.
10. **`buzz-sdk`** — typed Rust Nostr event builders.
11. **Buzz Mesh** — OpenAI-compatible local endpoint usable by any agent framework.

### 2.6 Tech stack

- **Backend:** Rust 1.95 (workspace of ~25 crates), Axum, tokio, sqlx, DashMap, moka, evalexpr; zero-`unsafe` policy.
- **Storage:** PostgreSQL 17 (monthly-partitioned `events`, FTS via generated `search_tsv` + GIN), Redis 7 (pub/sub, presence SET EX 90s, typing sorted sets), MinIO/S3 (Blossom).
- **Clients:** Tauri 2 + React 19 + TypeScript desktop (Vite, Radix, Playwright, biome); Flutter/Dart mobile (in development); browser repo-browser served by the relay.
- **Mesh:** iroh (QUIC) inter-relay; mesh-llm for shared compute. Voice: Opus; TTS experiments ("Pocket TTS") in huddles.
- **Dev tooling:** Hermit pinned toolchain, `just`, Docker Compose (Postgres/Redis/MinIO/Adminer/Prometheus), lefthook, Renovate.
- **Scale targets:** 10K humans + 50K agents, ~600K events/day, Redis fan-out <50ms p99.
- **Build model:** "Buzz is being built with AI-assisted development — agents write code, crossfire reviews across multiple models catch blind spots before merge."

### 2.7 Maturity & governance

- **License:** Apache-2.0. Governance per Block's open-source org standard (`block/.github/GOVERNANCE.md`); CoC, SECURITY.md, CONTRIBUTING.md present.
- **Five-repo ecosystem:** `block/buzz` (OSS source) plus internal repos for signed builds (`squareup/sprout-releases`), Docker→ECR (`sprout-oss`), Terraform/ArgoCD→K8s staging (`block-coder-tf-stacks`), and internal agent compute (`sprout-backend-blox`). Block employees use a separate pre-wired build.
- **Maturity (2026-07-22):** v0.4.23, ~4.3k stars / 338 forks; extremely active (multiple commits/day, 243 open PRs); 134 e2e tests; formally verified multi-tenancy. Self-reported gaps: **no rate limiting enforced** (trait exists, test stub only), workflow approval gates not wired end-to-end, `send_dm`/`set_channel_topic` workflow actions stubbed, huddle recording not built, mobile in progress; push notifications, web-of-trust reputation, and culture features are design-only.
- Contributors in recent history are Block employees (Will Pfleger, Wes, Tyler, thomaspblock, Bradley Axen, et al.).

---

## Part 3: Side-by-side design comparison (neutral)

| Dimension | Fractal (Plasma AI) | Buzz (Block) |
|---|---|---|
| Core metaphor | Recursive tree of autonomous coding-agent loops over git worktrees | Team workspace as a single Nostr relay; one signed event log for humans + agents |
| Primary unit | **Node** = branch + worktree + loop + data dir | **Event** = signed Nostr `{id, pubkey, kind, tags, content, sig}` |
| Topology | Hierarchical (parent/child, dotted branch names); single local machine/tree | Hub-and-spoke (relay is single source of truth; no P2P); optional inter-relay mesh via iroh |
| Identity | Node = branch name; no cryptographic identity; agent session ids recorded | secp256k1 keypair per human *and* agent; Schnorr-signed everything; NIP-05 handles; NIP-OA owner attestation |
| Human role | Operator steering an autonomous tree (user node, TUI, approvals, budgets, live-editable steps) | Peer member of the workspace; agents are co-members ("humans stay in the loop, agents stay in the room") |
| Agent integration | Wraps agent **CLIs** (Claude Code, Codex, Grok Build, OpenCode, Oh My Pi) via per-backend stream parsers | **ACP** (JSON-RPC/stdio) harness for Goose/Codex/Claude Code + **MCP** for tools |
| Messaging | Radio: SQLite-backed per-node channels (inbox/outbox/public/private), priorities, one-hop parent↔child subscriptions | NIP-29 group channels (Stream/Forum/DM/Workflow) over WebSocket; three-tier fan-out; NIP-17 gift-wrapped DMs |
| Git's role | Isolation & merge mechanism: worktree per node, two-speed history, squash-merge toward base | Hosted artifact: relay serves git smart HTTP, NIP-34 announcements, npub-signed pushes, branch-as-room, signed merge approvals |
| Persistence | One SQLite file per tree (WAL); local filesystem contracts | Postgres 17 (partitioned events) + Redis + S3/MinIO |
| Audit/accounting | Run/iter/step rows, per-step recorded cost, events table, activity view | SHA-256 hash-chain audit log, tamper-evident, per-community; agent turn metrics (NIP-AM) |
| Resource control | USD budgets (hard/soft/reserve), iteration/depth/child caps, timeouts, scope-restricted commits | Channel membership as the access gate; roles; approval events; rate limiting designed but not enforced yet |
| Automation surface | Step-file markdown pipelines re-read each iteration; mode docs; signals | Channel-scoped YAML workflows (triggers/actions/conditions); execution as events (kinds 46001–46012) |
| Knowledge/memory | Per-node `memory/` wiki + shared committed `wiki/` (plasma-wiki, wikilinked markdown) | Agent engrams (NIP-AE), per-channel Canvas documents (kind 40100) |
| Extension idiom | New backend classes, deployment hook files, observability hooks, editable seeds/steps/skills | New event kinds, custom NIP drafts, any Nostr/ACP/MCP client, buzz-sdk |
| Server footprint | None — CLI + tmux + git + SQLite, all local | Full service: Rust relay + Postgres + Redis + S3, self-hosted or managed |
| Stack | Python 3.12+, typer/rich/textual, 4 runtime deps | Rust workspace (~25 crates), Axum/tokio/sqlx; Tauri+React desktop; Flutter mobile |
| Formal rigor | Typed, doctested, real-git integration tests | TLA+ + Tamarin formally specified multi-tenancy, mutation-tested; 134 e2e tests |
| License / governance | Apache-2.0; tiny single-company startup (open-core → Fractal Cloud) | Apache-2.0; Block org governance; OSS + managed offering |
| Launch / scale (2026-07-22) | v1.0.0, 2026-07-21; 374 stars, 1 contributor | v0.4.23, launched 2026-07-21; ~4.3k stars, many Block contributors |

**Philosophical contrast in one line each:** Fractal treats *git itself* as the coordination substrate — the org chart is the branch namespace, the ledger is a local SQLite file, and agents are ephemeral loops bounded by budgets. Buzz treats a *signed event log* as the coordination substrate — identity is cryptographic, every action (chat, code, review, workflow) is the same event shape, and agents are durable first-class members of a shared workspace.

---

## Sources

### Fractal

- Repo: https://github.com/plasma-ai/fractal (README, `fractal/core/schema.sql`, `pyproject.toml`; in-repo wiki: `wiki/architecture/{packages,node_tree,database,worktrees,agent_providers}.md`, `wiki/features/agents/extending.md`, `wiki/configuration/config_json.md`; docs source: `docs/guide/{architecture,loop,radio,plans}.rst`, `docs/skill.rst`)
- Launch/research post: https://www.plasma.ai/research/fractal (2026-07-21; Diao, Turner, Berry)
- Company: https://www.plasma.ai/ · Docs: https://docs.plasma.ai/fractal
- PyPI: https://pypi.org/project/plasma-fractal/ (1.0.0)
- Sibling: https://github.com/plasma-ai/wiki · Org: https://github.com/plasma-ai
- Announcement: https://x.com/Plasma__AI/status/2079636286990881263

### Buzz

- Repo: https://github.com/block/buzz (README.md, ARCHITECTURE.md, NOSTR.md, VISION*.md, AGENTS.md, GOVERNANCE.md, `docs/nips/`, `docs/formal/`, `docs/multi-tenant-relay.md`, `crates/buzz-cli/README.md`)
- Releases: https://github.com/block/buzz/releases/latest (v0.4.23, 2026-07-22)
- TechCrunch: https://techcrunch.com/2026/07/21/jack-dorsey-is-taking-on-slack-with-buzz-a-group-chat-platform-for-teams-and-their-ai-agents/
- Decrypt: https://decrypt.co/374026/jack-dorseys-block-launches-buzz-a-nostr-based-slack-and-github-rival-for-ai-agents
- The Information: https://www.theinformation.com/newsletters/the-briefing/dorsey-wants-buzz-loosen-slacks-hold-workers

### Protocol references

- ACP (Agent Client Protocol): https://agentclientprotocol.com/
- Nostr NIPs: https://github.com/nostr-protocol/nips
- Blossom: https://github.com/hzrd149/blossom
