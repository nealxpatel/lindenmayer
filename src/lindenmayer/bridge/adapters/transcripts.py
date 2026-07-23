"""Harvest per-request token usage from agent session transcripts.

Reads ONLY append-only per-request usage fields (written at response time; they survive
compaction), never parses conversational structure. Fractal's DB stores only derived USD,
so ground-truth token counts come from the agent session transcripts (42020 needs both).

This harvester is isolated behind its own module so future compaction-design changes
ripple through exactly one place (architect condition 3, verdict 8266A685).
"""


class TranscriptUsageHarvester:
    """Harvest per-request usage from JSONL transcript files."""

    def __init__(self, transcript_path: str):
        """Initialize the harvester.

        Args:
            transcript_path: Path to a .jsonl transcript file
        """
        pass

    def get_total_usage(self) -> dict:
        """Return aggregated usage (input_tokens, output_tokens, cache fields).

        Returns:
            Dict with keys: input_tokens, output_tokens, cache_creation_input_tokens,
            cache_read_input_tokens
        """
        pass

    def iter_requests(self):
        """Iterate over individual request cost records (cost type events)."""
        pass
