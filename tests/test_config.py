"""Config tests: capability attestations gate on explicit presence; key
material resolves from env or 0600 file and never from config content."""

import pytest

from lindenmayer.core import (
    CAP_PRIVATE_READ_GATING,
    CapabilityAttestation,
    ConfigError,
    CoreConfig,
    Keypair,
)

ATTESTATION = {
    "capability": CAP_PRIVATE_READ_GATING,
    "attested_by": "operator@example",
    "attested_at": 1770000000,
    "note": "buzz relay, enforcement verified by construction",
}


def make_config(**overrides) -> CoreConfig:
    return CoreConfig.model_validate({"relay_url": "wss://relay.example"} | overrides)


def test_capability_absent_means_no():
    cfg = make_config()
    assert not cfg.has_capability(CAP_PRIVATE_READ_GATING)
    assert cfg.attestation_for(CAP_PRIVATE_READ_GATING) is None


def test_capability_present_when_attested():
    cfg = make_config(capability_attestations=[ATTESTATION])
    assert cfg.has_capability(CAP_PRIVATE_READ_GATING)
    attestation = cfg.attestation_for(CAP_PRIVATE_READ_GATING)
    assert attestation is not None and attestation.attested_by == "operator@example"


def test_attestation_requires_non_empty_fields():
    with pytest.raises(ValueError):
        CapabilityAttestation(capability=" ", attested_by="x", attested_at=1)
    with pytest.raises(ValueError):
        CapabilityAttestation(capability="x", attested_by="", attested_at=1)


def test_relay_url_must_be_websocket():
    with pytest.raises(ValueError):
        make_config(relay_url="https://relay.example")


def test_keypair_from_env(monkeypatch):
    secret_hex = "11" * 32
    monkeypatch.setenv("LINDENMAYER_SECRET_KEY", secret_hex)
    loaded = make_config().load_keypair()
    assert loaded.public_key_hex == Keypair.from_hex(secret_hex).public_key_hex


def test_keypair_missing_everywhere(monkeypatch):
    monkeypatch.delenv("LINDENMAYER_SECRET_KEY", raising=False)
    with pytest.raises(ConfigError):
        make_config().load_keypair()


def test_keypair_from_file_requires_0600(monkeypatch, tmp_path):
    monkeypatch.delenv("LINDENMAYER_SECRET_KEY", raising=False)
    key_file = tmp_path / "key.hex"
    key_file.write_text("22" * 32)
    key_file.chmod(0o644)
    cfg = make_config(secret_key_file=str(key_file))
    with pytest.raises(ConfigError, match="group/world-accessible"):
        cfg.load_keypair()
    key_file.chmod(0o600)
    assert cfg.load_keypair().public_key_hex == Keypair.from_hex("22" * 32).public_key_hex


def test_invalid_secret_not_echoed(monkeypatch):
    monkeypatch.setenv("LINDENMAYER_SECRET_KEY", "deadbeef")  # wrong length
    with pytest.raises(ConfigError) as excinfo:
        make_config().load_keypair()
    assert "deadbeef" not in str(excinfo.value)


def test_from_toml(tmp_path):
    config_file = tmp_path / "lindenmayer.toml"
    config_file.write_text(
        'relay_url = "wss://relay.example"\n\n'
        "[[capability_attestations]]\n"
        f'capability = "{CAP_PRIVATE_READ_GATING}"\n'
        'attested_by = "operator@example"\n'
        "attested_at = 1770000000\n"
    )
    cfg = CoreConfig.from_toml(config_file)
    assert cfg.has_capability(CAP_PRIVATE_READ_GATING)


def test_from_toml_invalid(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text('relay_url = "https://nope"\n')
    with pytest.raises(ConfigError):
        CoreConfig.from_toml(bad)
