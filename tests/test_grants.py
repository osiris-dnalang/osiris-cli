"""SYS-021 grants (action 18, section 7): a missing, unbound, expired, revoked, tampered,
wrong-namespace or wrong-principal grant leaves the operation unauthorized, and a valid grant
authorizes only the matching digest, once.

The keys here are made for the tests, in tmp_path, and sign only test grants."""

import json
import shutil
import subprocess
import threading
import time
from types import SimpleNamespace

import pytest

from osiris_cli import grants

pytestmark = pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="needs OpenSSH ssh-keygen")

NOW = 1_800_000_000
DIGEST = "ab" * 32
SCOPE = "qpu.submit"


def synced():
    return True, "test clock"


def keygen(directory, name):
    key = directory / name
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", name, "-f", str(key)],
                   check=True)
    return key


def signers_line(key, principal="owner", namespace="osiris-grant"):
    kind, blob = (key.parent / (key.name + ".pub")).read_text().split()[:2]
    return f'{principal} namespaces="{namespace}" {kind} {blob}\n'


def fingerprint(key):
    out = subprocess.run(["ssh-keygen", "-lf", str(key) + ".pub"], check=True,
                         capture_output=True, text=True).stdout
    return out.split()[1]


@pytest.fixture
def owner(tmp_path):
    key = keygen(tmp_path, "owner")
    signers = tmp_path / "allowed_signers"
    signers.write_text(signers_line(key))
    return SimpleNamespace(key=key, signers=signers, ledger=tmp_path / "ledger.jsonl", dir=tmp_path)


def sign(path, key, namespace="osiris-grant"):
    (path.parent / (path.name + ".sig")).unlink(missing_ok=True)
    subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", str(key), "-n", namespace, str(path)],
                   check=True, capture_output=True)


def grant_file(owner, digest=DIGEST, scope=SCOPE, signed_at=NOW - 60, expires_s=900,
               namespace="osiris-grant", key=None, name="grant.json", data=None):
    path = owner.dir / name
    path.write_bytes(data if data is not None else grants.draft(digest, scope, expires_s, now=signed_at))
    sign(path, key or owner.key, namespace)
    return path


def attempt(owner, path, digest=DIGEST, scope=SCOPE, now=NOW, clock=synced):
    return grants.authorize(str(path), digest, scope, allowed_signers=str(owner.signers),
                            ledger_path=str(owner.ledger), node="test-node", now=now, clock=clock)


def events(owner):
    if not owner.ledger.exists():
        return []
    return [json.loads(line)["kind"] for line in owner.ledger.read_text().splitlines()]


def test_a_signed_grant_authorizes_its_operation_once(owner):
    path = grant_file(owner)
    first = attempt(owner, path)
    assert first and first.record["consumption"] == "CONSUMED"
    assert first.record["key_fingerprint"] == fingerprint(owner.key)
    assert (first.record["principal"], first.record["method"], first.record["node"]) == ("owner", "ssh-sig", "test-node")
    assert first.record["payload_digest"] == DIGEST and first.record["scope"] == SCOPE
    assert events(owner) == [grants.GRANTED, grants.CONSUMED]
    again = attempt(owner, path)
    assert not again and "already used" in again.reason
    assert events(owner) == [grants.GRANTED, grants.CONSUMED]


def test_the_ledger_chains_each_event_to_the_last(owner):
    attempt(owner, grant_file(owner, name="one.json"))
    attempt(owner, grant_file(owner, name="two.json"))
    rows = [json.loads(line) for line in owner.ledger.read_text().splitlines()]
    assert [r["prev"] for r in rows] == [grants.GENESIS] + [r["hash"] for r in rows[:-1]]
    with open(owner.ledger, "rb") as f:
        assert grants._read_chain(f)[0] == rows


def test_a_missing_grant_or_signature_authorizes_nothing(owner):
    assert "no grant" in attempt(owner, owner.dir / "absent.json").reason
    path = owner.dir / "unsigned.json"
    path.write_bytes(grants.draft(DIGEST, SCOPE, now=NOW))
    assert "no signature" in attempt(owner, path).reason
    assert events(owner) == []


def test_a_grant_for_another_payload_or_scope_authorizes_nothing(owner):
    path = grant_file(owner)
    assert "bound to payload" in attempt(owner, path, digest="cd" * 32).reason
    assert "for scope" in attempt(owner, path, scope="zenodo.publish").reason
    assert events(owner) == []
    assert attempt(owner, path)


def test_an_expired_or_early_grant_authorizes_nothing_and_its_window_includes_its_ends(owner):
    path = grant_file(owner, signed_at=NOW, expires_s=900)
    assert "expired" in attempt(owner, path, now=NOW + 901).reason
    assert "not valid before" in attempt(owner, path, now=NOW - 1).reason
    assert events(owner) == []
    assert attempt(owner, path, now=NOW + 900)
    assert attempt(owner, grant_file(owner, signed_at=NOW, name="start.json"), now=NOW)


def test_a_revoked_grant_authorizes_nothing(owner):
    path = grant_file(owner)
    grant_id = grants._sha256(path.read_bytes())
    grants.revoke(grant_id, "owner withdrew it", str(owner.ledger))
    denied = attempt(owner, path)
    assert not denied and "revoked" in denied.reason
    assert events(owner) == [grants.REVOKED]
    with pytest.raises(ValueError):
        grants.revoke(grant_id, "  ", str(owner.ledger))
    with pytest.raises(ValueError):
        grants.revoke("not-an-id", "reason", str(owner.ledger))


def test_a_changed_byte_breaks_the_signature(owner):
    path = grant_file(owner)
    original = path.read_bytes()
    path.write_bytes(original.replace(DIGEST.encode(), ("cd" * 32).encode()))
    denied = attempt(owner, path, digest="cd" * 32)
    assert not denied and "signature refused" in denied.reason
    path.write_bytes(original + b" ")
    assert "signature refused" in attempt(owner, path).reason
    assert events(owner) == []


def test_ssh_keygen_is_believed_only_with_exit_0_and_a_good_line(owner, monkeypatch):
    path = grant_file(owner)
    good = f'Good "osiris-grant" signature for owner with ED25519 key {fingerprint(owner.key)}'
    fake_dir = owner.dir / "fakebin"
    fake_dir.mkdir()
    fake = fake_dir / "ssh-keygen"
    monkeypatch.setenv("PATH", str(fake_dir))
    for script in (f"echo '{good}'; exit 255", "exit 0"):
        fake.write_text(f"#!/bin/sh\n{script}\n")
        fake.chmod(0o755)
        denied = attempt(owner, path)
        assert not denied and "signature refused" in denied.reason
    assert events(owner) == []


def test_a_signature_in_another_namespace_is_refused(owner):
    denied = attempt(owner, grant_file(owner, namespace="git"))
    assert not denied and "signature refused" in denied.reason


def test_a_key_for_another_principal_or_not_enrolled_is_refused(owner):
    stranger = keygen(owner.dir, "stranger")
    assert "signature refused" in attempt(owner, grant_file(owner, key=stranger)).reason
    owner.signers.write_text(signers_line(owner.key, principal="someone"))
    assert "signature refused" in attempt(owner, grant_file(owner, name="other.json")).reason
    owner.signers.write_text(signers_line(owner.key, namespace="git"))
    assert "signature refused" in attempt(owner, grant_file(owner, name="third.json")).reason
    assert events(owner) == []


def test_an_unsynchronized_clock_authorizes_nothing(owner):
    denied = attempt(owner, grant_file(owner), clock=lambda: (False, "clock not synchronized"))
    assert not denied and denied.reason == "clock not synchronized"
    assert events(owner) == []


@pytest.mark.parametrize("script, ok, text", [
    ("echo yes", True, "NTP-synchronized"),
    ("echo no", False, "NTPSynchronized=no"),
    ("echo", False, "NTPSynchronized=empty"),
    ("echo 'System has not been booted with systemd' >&2; exit 1", False, "cannot be read"),
])
def test_the_clock_check_reads_timedatectl_and_fails_closed(tmp_path, monkeypatch, script, ok, text):
    fake = tmp_path / "timedatectl"
    fake.write_text(f"#!/bin/sh\n{script}\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    result = grants.clock_synchronized()
    assert result[0] is ok and text in result[1]


def test_without_ssh_keygen_timedatectl_or_trust_root_nothing_is_authorized(owner, monkeypatch):
    path = grant_file(owner)
    signers = owner.signers.read_text()
    owner.signers.unlink()
    assert "no trust root" in attempt(owner, path).reason
    owner.signers.write_text(signers)
    monkeypatch.setenv("PATH", str(owner.dir / "empty"))
    assert "ssh-keygen not found" in attempt(owner, path).reason
    assert grants.clock_synchronized()[0] is False
    assert events(owner) == []


def test_a_broken_ledger_authorizes_nothing_and_is_left_as_it_was(owner):
    attempt(owner, grant_file(owner, name="one.json"))
    rows = owner.ledger.read_text().splitlines()
    edited = json.loads(rows[0])
    edited["payload"]["scope"] = "zenodo.publish"
    for broken in ([json.dumps(edited)] + rows[1:], rows[1:], rows + ["not json"]):
        owner.ledger.write_text("\n".join(broken) + "\n")
        denied = attempt(owner, grant_file(owner, name="two.json"))
        assert not denied and "ledger" in denied.reason
        assert owner.ledger.read_text() == "\n".join(broken) + "\n"


def test_concurrent_attempts_use_a_grant_once(owner):
    path = grant_file(owner)
    results = []

    def run():
        results.append(attempt(owner, path))

    threads = [threading.Thread(target=run) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(bool(r) for r in results) == 1
    assert events(owner) == [grants.GRANTED, grants.CONSUMED]


@pytest.mark.parametrize("data, text", [
    (b"[]", "not a JSON object"),
    (b"not json", "not JSON"),
    (b'{"payload_digest": "%s", "payload_digest": "%s", "scope": "s", "signed_at": "2027-01-15T08:00:00Z", "expires_s": 900}'
     % (DIGEST.encode(), ("cd" * 32).encode()), "twice"),
    (b'{"scope": "s", "signed_at": "2027-01-15T08:00:00Z", "expires_s": 900}', "lacks payload_digest"),
    (('{"payload_digest": "%s", "scope": "s", "signed_at": "2027-01-15T08:00:00Z", "expires_s": 900}'
      % DIGEST.upper()).encode(), "lowercase"),
    (('{"payload_digest": "%s", "scope": " ", "signed_at": "2027-01-15T08:00:00Z", "expires_s": 900}'
      % DIGEST).encode(), "scope"),
    (('{"payload_digest": "%s", "scope": "s", "signed_at": "2027-01-15 08:00:00", "expires_s": 900}'
      % DIGEST).encode(), "signed_at"),
    (('{"payload_digest": "%s", "scope": "s", "signed_at": "2027-1-15T08:00:00Z", "expires_s": 900}'
      % DIGEST).encode(), "signed_at"),
    (('{"payload_digest": "%s", "scope": "s", "signed_at": "2027-01-15T08:00:00Z", "expires_s": true}'
      % DIGEST).encode(), "expires_s"),
    (('{"payload_digest": "%s", "scope": "s", "signed_at": "2027-01-15T08:00:00Z", "expires_s": 0}'
      % DIGEST).encode(), "expires_s"),
    (('{"payload_digest": "%s", "scope": "s", "signed_at": "2027-01-15T08:00:00Z", "expires_s": 9.5}'
      % DIGEST).encode(), "expires_s"),
])
def test_a_signed_but_malformed_grant_authorizes_nothing(owner, data, text):
    assert grants.parse_grant(data)[0] is None and text in grants.parse_grant(data)[1]
    denied = attempt(owner, grant_file(owner, data=data))
    assert not denied and text in denied.reason
    assert events(owner) == []


def test_the_command_line_drafts_checks_without_using_and_revokes(owner, monkeypatch, capsys):
    monkeypatch.setattr(grants, "clock_synchronized", synced)
    assert grants.main(["draft", "--payload-digest", DIGEST, "--scope", SCOPE]) == 0
    path = owner.dir / "cli.json"
    path.write_text(capsys.readouterr().out)
    sign(path, owner.key)
    check = ["check", str(path), "--payload-digest", DIGEST, "--scope", SCOPE,
             "--allowed-signers", str(owner.signers), "--ledger", str(owner.ledger)]
    assert grants.main(check) == 0
    assert "nothing authorized" in capsys.readouterr().out
    assert events(owner) == []
    assert grants.main(check[:3] + ["cd" * 32] + check[4:]) == 1
    grant_id = grants._sha256(path.read_bytes())
    assert grants.main(["revoke", grant_id, "--reason", "test", "--ledger", str(owner.ledger)]) == 0
    capsys.readouterr()
    assert grants.main(check) == 1
    assert "revoked" in capsys.readouterr().out
    assert grants.main(["draft", "--payload-digest", "xyz", "--scope", SCOPE]) == 1


def test_the_command_line_check_refuses_an_expired_grant(owner, monkeypatch, capsys):
    monkeypatch.setattr(grants, "clock_synchronized", synced)
    path = grant_file(owner, signed_at=int(time.time()) - 1000, expires_s=900)
    assert grants.main(["check", str(path), "--payload-digest", DIGEST, "--scope", SCOPE,
                        "--allowed-signers", str(owner.signers), "--ledger", str(owner.ledger)]) == 1
    assert "expired" in capsys.readouterr().out


def test_the_enrolled_trust_root_names_only_the_owner_for_grants():
    lines = [ln.split() for ln in open(grants.ALLOWED_SIGNERS) if ln.strip() and not ln.startswith("#")]
    assert lines and all(ln[:3] == ["owner", 'namespaces="osiris-grant"', "ssh-ed25519"] for ln in lines)
