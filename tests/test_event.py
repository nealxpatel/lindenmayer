"""Event model tests: published vectors, round-trips, tamper detection.

Vector provenance:
- tests/vectors/bip340_vectors.csv — the published BIP-340 test vectors from
  bitcoin/bips (bip-0340/test-vectors.csv), verbatim.
- tests/vectors/nip_oa_signed_event.json — the published signed NIP-01 event
  from block/buzz docs/nips/NIP-OA.md ("Signed Event Example"), verbatim.
  Its id and sig were produced by an independent implementation, which makes
  it an end-to-end NIP-01 id/sig vector for us.
"""

import csv
import json
from pathlib import Path

import pytest

from lindenmayer.core import (
    Event,
    EventValidationError,
    Keypair,
    compute_event_id,
    schnorr_sign,
    schnorr_verify,
)

VECTORS = Path(__file__).parent / "vectors"


def load_bip340_rows():
    with open(VECTORS / "bip340_vectors.csv", newline="") as fh:
        return list(csv.DictReader(fh))


def load_nip_oa_event() -> dict:
    return json.loads((VECTORS / "nip_oa_signed_event.json").read_text())


# -- BIP-340 published vectors -------------------------------------------


@pytest.mark.parametrize("row", load_bip340_rows(), ids=lambda r: f"vec{r['index']}")
def test_bip340_verify_vectors(row):
    """Every published vector's verification result must be reproduced."""
    expected = row["verification result"] == "TRUE"
    ok = schnorr_verify(
        row["public key"].lower(),
        bytes.fromhex(row["message"]),
        bytes.fromhex(row["signature"]),
    )
    assert ok is expected, row["comment"]


@pytest.mark.parametrize(
    "row",
    # Vectors 15-18 exercise BIP-340's variable-length message support, which
    # coincurve's signing API rejects (32-byte digests only). Nostr signs only
    # 32-byte SHA-256 event ids, so those vectors are out of scope for signing;
    # they still run through test_bip340_verify_vectors above.
    [r for r in load_bip340_rows() if r["secret key"] and len(r["message"]) == 64],
    ids=lambda r: f"vec{r['index']}",
)
def test_bip340_sign_vectors(row):
    """Signing with the vector's secret and aux randomness reproduces the
    vector signature exactly (BIP-340 signing is deterministic given aux)."""
    sig = schnorr_sign(
        bytes.fromhex(row["secret key"]),
        bytes.fromhex(row["message"]),
        aux_rand=bytes.fromhex(row["aux_rand"]),
    )
    assert sig.hex().upper() == row["signature"]


# -- NIP-01 id computation and full verification --------------------------


def test_nip01_id_matches_published_event():
    ev = load_nip_oa_event()
    assert (
        compute_event_id(ev["pubkey"], ev["created_at"], ev["kind"], ev["tags"], ev["content"])
        == ev["id"]
    )


def test_nip01_full_verify_published_event():
    event = Event.from_dict(load_nip_oa_event())
    assert event.id_valid()
    assert event.sig_valid()
    assert event.verify()


def test_nip01_canonical_escaping():
    """Content with quotes, backslashes, newlines, and non-ASCII must follow
    JSON.stringify-style minimal escaping (NIP-01)."""
    event_id = compute_event_id(
        "a" * 64, 1700000000, 1, [], 'quote " backslash \\ newline \n unicode é'
    )
    assert len(event_id) == 64
    # Independent recomputation with explicit expected serialization:
    import hashlib

    expected = (
        '[0,"' + "a" * 64 + '",1700000000,1,[],'
        '"quote \\" backslash \\\\ newline \\n unicode é"]'
    ).encode()
    assert event_id == hashlib.sha256(expected).hexdigest()


# -- round-trips and tamper detection --------------------------------------


def test_sign_verify_roundtrip():
    kp = Keypair.generate()
    event = Event.build(pubkey=kp.public_key_hex, kind=1, tags=[["t", "test"]], content="hello")
    signed = kp.sign_event(event)
    assert signed.verify()
    # JSON round-trip preserves validity
    assert Event.from_json(signed.to_json()).verify()


def test_tampered_content_fails():
    kp = Keypair.generate()
    signed = kp.sign_event(Event.build(pubkey=kp.public_key_hex, kind=1, content="original"))
    data = signed.to_dict()
    data["content"] = "tampered"
    assert not Event.from_dict(data).verify()


def test_tampered_id_fails():
    kp = Keypair.generate()
    signed = kp.sign_event(Event.build(pubkey=kp.public_key_hex, kind=1, content="x"))
    data = signed.to_dict()
    data["id"] = "0" * 64
    assert not Event.from_dict(data).verify()


def test_wrong_key_signature_fails():
    kp, other = Keypair.generate(), Keypair.generate()
    event = Event.build(pubkey=kp.public_key_hex, kind=1, content="x")
    with pytest.raises(ValueError):
        other.sign_event(event)  # pubkey mismatch refused at signing time


def test_unsigned_event_does_not_verify():
    kp = Keypair.generate()
    assert not Event.build(pubkey=kp.public_key_hex, kind=1, content="x").verify()


# -- structural validation --------------------------------------------------


@pytest.mark.parametrize(
    "mutation",
    [
        {"pubkey": "not-hex"},
        {"pubkey": "AB" * 32},  # uppercase refused
        {"id": "00"},
        {"sig": "zz" * 64},
        {"created_at": "1700000000"},
        {"kind": 70000},
        {"kind": True},
        {"content": 5},
        {"tags": [["ok"], "not-a-list"]},
        {"tags": [[1, 2]]},
    ],
)
def test_from_dict_rejects_malformed(mutation):
    data = load_nip_oa_event() | mutation
    with pytest.raises(EventValidationError):
        Event.from_dict(data)


def test_tag_access():
    event = Event.build(
        pubkey="a" * 64,
        kind=42010,
        tags=[["branch", "main.core"], ["status", "active"], ["e", "f" * 64, "relay"]],
        content="",
    )
    assert event.first_tag_value("branch") == "main.core"
    assert event.first_tag_value("missing") is None
    assert list(event.tag_values("e")) == [("f" * 64, "relay")]
