# transcripts/

Raw Claude Code session logs from the development of Lindenmayer, published as an
intentional public record.

Each file is one session's transcript in JSONL format, named `<session-id>.jsonl`.
A `Stop` hook in `.claude/settings.json` (see `.claude/hooks/save-transcript.sh`)
copies the session's transcript here automatically every time the agent finishes a
turn, so the latest copy of each session always reflects the full conversation up
to that point.

These logs are unedited: they contain the prompts, tool calls, and outputs that
produced this repository. Lindenmayer's development is itself managed by a Fractal
tree, and these transcripts are part of the telemetry that the project's own demo
observes.
