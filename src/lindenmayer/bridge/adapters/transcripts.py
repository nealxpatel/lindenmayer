"""Harvest per-request token usage from agent session transcripts.

Reads ONLY append-only per-request usage fields (written at response time; they survive
compaction), never parses conversational structure. Fractal's DB stores only derived USD,
so ground-truth token counts come from the agent session transcripts (42020 needs both).

This harvester is isolated behind its own module so future compaction-design changes
ripple through exactly one place (architect condition 3, verdict 8266A685).
"""

import json
from pathlib import Path


class TranscriptUsageHarvester:
    """Harvest per-request usage from JSONL transcript files."""

    def __init__(self, transcript_path: str):
        """Initialize the harvester.

        Args:
            transcript_path: Path to a .jsonl transcript file
        """
        self.transcript_path = transcript_path

    def get_total_usage(self) -> dict:
        """Return aggregated usage (input_tokens, output_tokens, cache fields).

        Returns:
            Dict with keys: input_tokens, output_tokens, cache_creation_input_tokens,
            cache_read_input_tokens
        """
        total = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        for request in self.iter_requests():
            total["input_tokens"] += request.get("input_tokens", 0)
            total["output_tokens"] += request.get("output_tokens", 0)
            total["cache_creation_input_tokens"] += request.get("cache_creation_input_tokens", 0)
            total["cache_read_input_tokens"] += request.get("cache_read_input_tokens", 0)
        return total

    def iter_requests(self):
        """Iterate over individual request cost records (cost type events)."""
        with open(self.transcript_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                event = json.loads(line)
                if event.get("type") == "cost":
                    usage = event.get("usage", {})
                    yield {
                        "model": event.get("model"),
                        "input_tokens": usage.get("input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0),
                        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
                        "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                    }
