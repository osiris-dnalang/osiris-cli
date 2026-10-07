import json
import os
import genome_ledger


def test_proposal():
    path = "bench_ledger.jsonl"
    if os.path.exists(path):
        os.remove(path)
    led = genome_ledger.GenomeLedger(path)
    e1 = led.append("generation", {"n": 1})
    e2 = led.append("trait", {"name": "a"})
    assert e1["prev"] == "0" * 64 and e2["prev"] == e1["hash"]
    with open(path) as f:
        first = f.readline()
    led.append("trait", {"name": "b"})
    with open(path) as f:
        lines = f.readlines()
    assert len(lines) == 3 and lines[0] == first, "storage must be append-only JSON Lines"
    assert led.verify() is True
    again = genome_ledger.GenomeLedger(path)
    e4 = again.append("trait", {"name": "c"})
    assert e4["prev"] == json.loads(lines[2])["hash"], "a reopened ledger must continue the chain"
    assert again.verify() is True
    with open(path) as f:
        current = f.readlines()
    tampered = json.loads(current[1])
    tampered["payload"] = {"name": "z"}
    current[1] = json.dumps(tampered) + "\n"
    with open(path, "w") as f:
        f.writelines(current)
    assert genome_ledger.GenomeLedger(path).verify() is False, "tampering must be detected"
