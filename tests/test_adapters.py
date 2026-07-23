"""Tests for Fractal read adapters."""

import pytest
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lindenmayer.bridge.adapters.sqlite import FractalDBReader
from lindenmayer.bridge.adapters.transcripts import TranscriptUsageHarvester


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestFractalDBReader:
    """Test FractalDBReader against fixture database."""

    @pytest.fixture
    def reader(self):
        """Create a reader for the fixture database."""
        db_path = str(FIXTURES_DIR / "tree.db")
        return FractalDBReader(db_path)

    def test_get_nodes(self, reader):
        """Test reading nodes from database."""
        nodes = reader.get_nodes()
        assert isinstance(nodes, list)
        assert len(nodes) > 0
        assert all("node" in n for n in nodes)
        assert all("status" in n for n in nodes)
        assert all("created_at" in n for n in nodes)

    def test_get_nodes_structure(self, reader):
        """Test that nodes have expected fields."""
        nodes = reader.get_nodes()
        first_node = nodes[0]
        expected_fields = {"node_id", "node", "title", "status", "max_cost", "max_depth", "max_children", "max_descendants", "created_at"}
        assert set(first_node.keys()) == expected_fields

    def test_get_runs(self, reader):
        """Test reading runs for a node."""
        # First get a node
        nodes = reader.get_nodes()
        assert len(nodes) > 0
        node_name = nodes[0]["node"]

        runs = reader.get_runs(node_name)
        assert isinstance(runs, list)

    def test_get_runs_structure(self, reader):
        """Test that runs have expected fields."""
        nodes = reader.get_nodes()
        node_name = nodes[0]["node"]
        runs = reader.get_runs(node_name)

        if runs:
            first_run = runs[0]
            expected_fields = {"run_id", "node", "parent_run_id", "agent", "max_cost", "status", "exit_code", "metadata", "started_at", "ended_at"}
            assert set(first_run.keys()) == expected_fields

    def test_get_iters(self, reader):
        """Test reading iterations for a run."""
        nodes = reader.get_nodes()
        node_name = nodes[0]["node"]
        runs = reader.get_runs(node_name)

        if runs:
            run_id = runs[0]["run_id"]
            iters = reader.get_iters(run_id)
            assert isinstance(iters, list)

    def test_get_iters_structure(self, reader):
        """Test that iters have expected fields."""
        nodes = reader.get_nodes()
        node_name = nodes[0]["node"]
        runs = reader.get_runs(node_name)

        if runs:
            run_id = runs[0]["run_id"]
            iters = reader.get_iters(run_id)
            if iters:
                first_iter = iters[0]
                expected_fields = {"iter_id", "node", "run_id", "iter", "agent", "model", "session", "status", "exit_code", "metadata", "started_at", "ended_at"}
                assert set(first_iter.keys()) == expected_fields

    def test_get_steps(self, reader):
        """Test reading steps for an iteration."""
        nodes = reader.get_nodes()
        node_name = nodes[0]["node"]
        runs = reader.get_runs(node_name)

        if runs:
            run_id = runs[0]["run_id"]
            iters = reader.get_iters(run_id)
            if iters:
                iter_id = iters[0]["iter_id"]
                steps = reader.get_steps(iter_id)
                assert isinstance(steps, list)

    def test_get_steps_structure(self, reader):
        """Test that steps have expected fields."""
        nodes = reader.get_nodes()
        node_name = nodes[0]["node"]
        runs = reader.get_runs(node_name)

        if runs:
            run_id = runs[0]["run_id"]
            iters = reader.get_iters(run_id)
            if iters:
                iter_id = iters[0]["iter_id"]
                steps = reader.get_steps(iter_id)
                if steps:
                    first_step = steps[0]
                    expected_fields = {"step_id", "node", "iter_id", "run_id", "step", "step_name", "agent", "model", "session", "status", "exit_code", "cost", "approved", "metadata", "started_at", "ended_at"}
                    assert set(first_step.keys()) == expected_fields

    def test_get_latest_event(self, reader):
        """Test reading latest event for a node."""
        nodes = reader.get_nodes()
        node_name = nodes[0]["node"]

        event = reader.get_latest_event(node_name)
        # Event can be None if no events exist
        if event is not None:
            expected_fields = {"event_id", "node", "step_id", "iter_id", "run_id", "event", "actor", "status", "exit_code", "metadata", "created_at"}
            assert set(event.keys()) == expected_fields

    def test_get_latest_event_nonexistent_node(self, reader):
        """Test that nonexistent nodes return None."""
        event = reader.get_latest_event("nonexistent-node-xyz")
        assert event is None


class TestTranscriptUsageHarvester:
    """Test TranscriptUsageHarvester against fixture transcripts."""

    def test_iter_requests_transcript1(self):
        """Test iterating over requests in transcript-1."""
        harvester = TranscriptUsageHarvester(str(FIXTURES_DIR / "transcript-1.jsonl"))
        requests = list(harvester.iter_requests())
        assert len(requests) == 2

        # First request: 100 input, 50 output
        assert requests[0]["input_tokens"] == 100
        assert requests[0]["output_tokens"] == 50
        assert requests[0]["cache_creation_input_tokens"] == 0
        assert requests[0]["cache_read_input_tokens"] == 0

        # Second request: 150 input, 75 output
        assert requests[1]["input_tokens"] == 150
        assert requests[1]["output_tokens"] == 75

    def test_iter_requests_transcript2(self):
        """Test iterating over requests in transcript-2."""
        harvester = TranscriptUsageHarvester(str(FIXTURES_DIR / "transcript-2.jsonl"))
        requests = list(harvester.iter_requests())
        assert len(requests) == 2

        # First request: 200 input, 100 output
        assert requests[0]["input_tokens"] == 200
        assert requests[0]["output_tokens"] == 100

        # Second request: 250 input, 125 output
        assert requests[1]["input_tokens"] == 250
        assert requests[1]["output_tokens"] == 125

    def test_get_total_usage_transcript1(self):
        """Test aggregated usage for transcript-1."""
        harvester = TranscriptUsageHarvester(str(FIXTURES_DIR / "transcript-1.jsonl"))
        total = harvester.get_total_usage()

        assert total["input_tokens"] == 250  # 100 + 150
        assert total["output_tokens"] == 125  # 50 + 75
        assert total["cache_creation_input_tokens"] == 0
        assert total["cache_read_input_tokens"] == 0

    def test_get_total_usage_transcript2(self):
        """Test aggregated usage for transcript-2."""
        harvester = TranscriptUsageHarvester(str(FIXTURES_DIR / "transcript-2.jsonl"))
        total = harvester.get_total_usage()

        assert total["input_tokens"] == 450  # 200 + 250
        assert total["output_tokens"] == 225  # 100 + 125
        assert total["cache_creation_input_tokens"] == 0
        assert total["cache_read_input_tokens"] == 0

    def test_request_has_model(self):
        """Test that requests include model information."""
        harvester = TranscriptUsageHarvester(str(FIXTURES_DIR / "transcript-1.jsonl"))
        requests = list(harvester.iter_requests())

        for request in requests:
            assert "model" in request
            assert request["model"] == "claude-opus-4-8"

    def test_harvester_returns_dict_from_get_total_usage(self):
        """Test that get_total_usage returns a dict."""
        harvester = TranscriptUsageHarvester(str(FIXTURES_DIR / "transcript-1.jsonl"))
        total = harvester.get_total_usage()

        assert isinstance(total, dict)
        assert all(isinstance(v, int) for v in total.values())
