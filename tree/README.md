# tree/

Versioned definitions of the Fractal tree that manages Lindenmayer's development.

Fractal keeps node state in runtime directories (`.fractal/`, `.worktrees/`) that
are gitignored here. The *contracts* — who each node is, what it owns, how it is
consulted — belong in git, so they live in this directory and seed the runtime
nodes when the tree runs.

This is also deliberate dogfooding: Lindenmayer's product is a durable, evergreen
context environment for humans governing agent subgraphs. That product doesn't
exist yet, so the first root node is handrolled by hand in `root/`. It is the
prototype of the surface Lindenmayer will eventually maintain automatically.

## Layout

- `root/` — the human operator's node (Fractal user node, branch `main`,
  `user: true`, never iterates). `CONTEXT.md` is the handrolled evergreen
  context environment.
- `platform-architect/` — the first agent node (branch `main.platform_architect`;
  Fractal branch segments allow only `[A-Za-z0-9_]`, hence the underscore).
  `NODE.md` is its Fractal task contract.
- `evergreen/` — first-ply product surface (branch `main.evergreen`): the
  read plane over the signed log; generates the standing context surface.
- `templates/` — versioned Node Templates (DESIGN.md §3), registered as
  signed 42050 events via the registry.
- `core/` — the first-ply foundation node (branch `main.core`): event kinds,
  relay client, config. Merges first; the rest of the ply builds against it.

One directory per node, named for the role; the `branch:` line inside each
contract is the authoritative mapping to the Fractal branch namespace.
