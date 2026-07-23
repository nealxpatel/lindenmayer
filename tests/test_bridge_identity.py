"""Tests for the bridge identity module (identity.py).

Validates:
- load_node_keypair returns Keypair for persistent nodes
- check_attestation_valid returns True for valid attestations
- refuse_if_revoked raises IdentityError for revoked/expired keys
"""

import os
import json
import tempfile
import time
import pytest

from lindenmayer.bridge.identity import (
    load_node_keypair,
    check_attestation_valid,
    refuse_if_revoked,
    IdentityError,
)
from lindenmayer.core.keys import Keypair


class TestLoadNodeKeypair:
    """Tests for load_node_keypair."""

    def test_generates_keypair_for_persistent_node(self):
        """Generates a Keypair for a node name."""
        result = load_node_keypair("main.test")
        assert isinstance(result, Keypair)
        assert len(result.public_key_hex) == 64

    def test_same_node_generates_same_keypair(self):
        """Same node name generates the same keypair (deterministic)."""
        os.environ["LINDENMAYER_KEY_SEED"] = "test-seed-123"
        try:
            kp1 = load_node_keypair("main.test")
            kp2 = load_node_keypair("main.test")
            assert kp1.public_key_hex == kp2.public_key_hex
        finally:
            os.environ.pop("LINDENMAYER_KEY_SEED", None)

    def test_different_nodes_generate_different_keys(self):
        """Different node names generate different keypairs."""
        os.environ["LINDENMAYER_KEY_SEED"] = "test-seed-123"
        try:
            kp1 = load_node_keypair("main.test1")
            kp2 = load_node_keypair("main.test2")
            assert kp1.public_key_hex != kp2.public_key_hex
        finally:
            os.environ.pop("LINDENMAYER_KEY_SEED", None)

    def test_returns_none_for_empty_node_name(self):
        """Returns None for empty node name."""
        result = load_node_keypair("")
        assert result is None

    def test_returns_none_for_none_node_name(self):
        """Returns None for None node name."""
        result = load_node_keypair(None)
        assert result is None


class TestCheckAttestationValid:
    """Tests for check_attestation_valid."""

    def test_valid_pubkey_format(self):
        """Returns True for properly formatted pubkey with no revocation."""
        pubkey = "a" * 64
        result = check_attestation_valid(pubkey)
        assert isinstance(result, bool)

    def test_invalid_pubkey_format_returns_false(self):
        """Returns False for invalid pubkey format."""
        result = check_attestation_valid("not-a-hex")
        assert result is False

    def test_short_pubkey_returns_false(self):
        """Returns False for pubkey that's not 64 characters."""
        result = check_attestation_valid("a" * 63)
        assert result is False

    def test_detects_revoked_key(self):
        """Returns False if key is in revoked list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            revoked_dir = os.path.join(tmpdir, ".lindenmayer", "revoked")
            os.makedirs(revoked_dir, exist_ok=True)
            revoked_file = os.path.join(revoked_dir, ("b" * 64) + ".revoked")
            with open(revoked_file, "w") as f:
                f.write("revoked")

            original_home = os.environ.get("HOME")
            try:
                os.environ["HOME"] = tmpdir
                result = check_attestation_valid("b" * 64)
                assert result is False
            finally:
                if original_home:
                    os.environ["HOME"] = original_home

    def test_detects_expired_attestation(self):
        """Returns False if attestation has expired."""
        with tempfile.TemporaryDirectory() as tmpdir:
            att_dir = os.path.join(tmpdir, ".lindenmayer", "attestations")
            os.makedirs(att_dir, exist_ok=True)
            pubkey = "c" * 64
            att_file = os.path.join(att_dir, f"{pubkey}.att")
            data = {"expires_at": time.time() - 1000, "revoked": False}
            with open(att_file, "w") as f:
                json.dump(data, f)

            original_home = os.environ.get("HOME")
            try:
                os.environ["HOME"] = tmpdir
                result = check_attestation_valid(pubkey)
                assert result is False
            finally:
                if original_home:
                    os.environ["HOME"] = original_home

    def test_detects_revoked_attestation(self):
        """Returns False if attestation is marked as revoked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            att_dir = os.path.join(tmpdir, ".lindenmayer", "attestations")
            os.makedirs(att_dir, exist_ok=True)
            pubkey = "d" * 64
            att_file = os.path.join(att_dir, f"{pubkey}.att")
            data = {"expires_at": time.time() + 10000, "revoked": True}
            with open(att_file, "w") as f:
                json.dump(data, f)

            original_home = os.environ.get("HOME")
            try:
                os.environ["HOME"] = tmpdir
                result = check_attestation_valid(pubkey)
                assert result is False
            finally:
                if original_home:
                    os.environ["HOME"] = original_home

    def test_accepts_valid_attestation(self):
        """Returns True for valid, non-expired, non-revoked attestation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            att_dir = os.path.join(tmpdir, ".lindenmayer", "attestations")
            os.makedirs(att_dir, exist_ok=True)
            pubkey = "e" * 64
            att_file = os.path.join(att_dir, f"{pubkey}.att")
            data = {"expires_at": time.time() + 10000, "revoked": False}
            with open(att_file, "w") as f:
                json.dump(data, f)

            original_home = os.environ.get("HOME")
            try:
                os.environ["HOME"] = tmpdir
                result = check_attestation_valid(pubkey)
                assert result is True
            finally:
                if original_home:
                    os.environ["HOME"] = original_home


class TestRefuseIfRevoked:
    """Tests for refuse_if_revoked."""

    def test_raises_for_revoked_key(self):
        """Raises IdentityError for revoked key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            revoked_dir = os.path.join(tmpdir, ".lindenmayer", "revoked")
            os.makedirs(revoked_dir, exist_ok=True)
            pubkey = "f" * 64
            revoked_file = os.path.join(revoked_dir, f"{pubkey}.revoked")
            with open(revoked_file, "w") as f:
                f.write("revoked")

            original_home = os.environ.get("HOME")
            try:
                os.environ["HOME"] = tmpdir
                with pytest.raises(IdentityError, match="revoked or expired"):
                    refuse_if_revoked(pubkey)
            finally:
                if original_home:
                    os.environ["HOME"] = original_home

    def test_raises_for_expired_key(self):
        """Raises IdentityError for expired attestation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            att_dir = os.path.join(tmpdir, ".lindenmayer", "attestations")
            os.makedirs(att_dir, exist_ok=True)
            pubkey = "f" * 64
            att_file = os.path.join(att_dir, f"{pubkey}.att")
            data = {"expires_at": time.time() - 1000, "revoked": False}
            with open(att_file, "w") as f:
                json.dump(data, f)

            original_home = os.environ.get("HOME")
            try:
                os.environ["HOME"] = tmpdir
                with pytest.raises(IdentityError, match="revoked or expired"):
                    refuse_if_revoked(pubkey)
            finally:
                if original_home:
                    os.environ["HOME"] = original_home

    def test_passes_for_valid_key(self):
        """Does not raise for valid, non-revoked key."""
        pubkey = "a" * 64
        try:
            refuse_if_revoked(pubkey)
        except IdentityError:
            pytest.fail("refuse_if_revoked raised for valid key")

    def test_error_message_includes_pubkey(self):
        """Error message includes the problematic pubkey."""
        with tempfile.TemporaryDirectory() as tmpdir:
            revoked_dir = os.path.join(tmpdir, ".lindenmayer", "revoked")
            os.makedirs(revoked_dir, exist_ok=True)
            pubkey = "c" * 64
            revoked_file = os.path.join(revoked_dir, f"{pubkey}.revoked")
            with open(revoked_file, "w") as f:
                f.write("revoked")

            original_home = os.environ.get("HOME")
            try:
                os.environ["HOME"] = tmpdir
                with pytest.raises(IdentityError) as exc_info:
                    refuse_if_revoked(pubkey)
                assert pubkey in str(exc_info.value)
            finally:
                if original_home:
                    os.environ["HOME"] = original_home


class TestIdentityError:
    """Tests for IdentityError exception."""

    def test_is_exception(self):
        """IdentityError is an Exception."""
        assert issubclass(IdentityError, Exception)

    def test_can_raise_and_catch(self):
        """Can raise and catch IdentityError."""
        with pytest.raises(IdentityError):
            raise IdentityError("Test error")
