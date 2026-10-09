#!/usr/bin/env python3
"""Write docs/rqc/S2/AMENDMENT_5_MANIFEST.json (artifact C) for an implementation snapshot (artifact A).

  python docs/rqc/S2/make_bundle_manifest.py --implementation-commit <full hash>

Run from the repository after the amendment (artifact B) cites that commit. Refuses unless every code file on disk
is byte-identical to `git show <commit>:<path>`, so the manifest cannot name a snapshot that git does not hold.
No artifact embeds its own hash: A is a commit; B cites A; C lists A's file hashes and B's hash; the intent payload
(at run time) carries all of them. Status stays 'draft' with no DOI until a deposit is recorded by hand.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SUPPORTING = ["docs/rqc/S2/CONTROL_NOTES.md", "docs/rqc/S2/budget_audit.json", "docs/rqc/S2/amendment5_analysis.py",
              "docs/rqc/S2/amendment5_analysis.json", "docs/rqc/S2/make_bundle_manifest.py",
              "tests/test_rqc.py", "tests/test_rqc_batch.py", "tests/test_rqc_control.py",
              "tests/test_rqc_s2_bundle.py", "docs/rqc/S1/results.json", "docs/rqc/S1_willow/results.json"]


def driver():
    spec = importlib.util.spec_from_file_location("s2_run_batched", os.path.join(HERE, "s2_run_batched.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(path):
    with open(os.path.join(ROOT, path), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--implementation-commit", required=True)
    a = ap.parse_args()
    commit = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--verify", a.implementation_commit + "^{commit}"],
                                     text=True).strip()
    d = driver()
    for p in d.CODE_FILES:
        blob = subprocess.check_output(["git", "-C", ROOT, "show", f"{commit}:{p}"])
        if hashlib.sha256(blob).hexdigest() != sha(p):
            sys.exit(f"{p} on disk differs from {commit[:12]}; the manifest would misstate the snapshot")
    amend = "docs/rqc/S2/S2_AMENDMENT_5.md"
    with open(os.path.join(ROOT, amend), encoding="utf-8") as f:
        if commit not in f.read():
            sys.exit(f"{amend} does not cite {commit}")
    m = {"schema": "rqc-s2-amendment5-bundle/1", "status": "draft", "amendment_doi": None,
         "note": "DRAFT - NOT APPROVED FOR DEPOSIT OR EXECUTION",
         "implementation": {"commit": commit, "scope": "code only: files the S2 run executes or analyses with",
                            "files": {p: sha(p) for p in d.CODE_FILES}},
         "documents": {p: sha(p) for p in d.DOCUMENT_FILES},
         "amendment_path": amend,
         "supporting": {p: sha(p) for p in SUPPORTING if os.path.exists(os.path.join(ROOT, p))},
         "frozen": {"prereg_commit": "964efe1931ead531ad4408945e03d6f2b2ddf3aa",
                    "tooling_commit": "86e3a3f4db6e449044fa0d7c173fc107b1b74452",
                    "search_code_commit": "0676107155d3ca5c5777937f49ce56a99085ca5c",
                    "prereg_sha256": "ee179e8f53b9b81c336db09ff68ff1fd7617edd728000a50f7a34d95cfa00e5d",
                    "prereg_doi_operator_supplied_unverified": "10.5281/zenodo.23241223"}}
    out = os.path.join(ROOT, d.MANIFEST)
    with open(out, "w") as f:
        json.dump(m, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"wrote {out}; sha256 {sha(d.MANIFEST)}")


if __name__ == "__main__":
    main()
