# Action 18: who may approve OSIRIS actions

**Decision recorded:** 2026-10-26. The owner (Devin Phillip Davis) approved the policy in session.
**Spec:** `OSIRIS_DUAL_NODE_REPL_MASTER_SPEC_v1.2.md`, sections 5.2 and 5.2.1, SYS-021, and action 18.
**Status:** the decision is recorded and the trust root is enrolled. The SYS-021 verifier is
`osiris_cli/grants.py` (section 7, items 1 and 2), pending the owner's review. No production
operation calls it yet, so the spec's rule still stands: production execution stays blocked.

## 1. Principal

There is exactly one approving principal: the owner. No agent, model, provider, script,
environment variable, slash command or generated certificate can approve anything. A sentence
such as "approve" or "go ahead" in a chat is not a grant (spec 5.2).

Both GitHub accounts (`osiris-dnalang`, `devinphillipdavis`) belong to the owner. They control
repository changes through GitHub's own authentication. They are not OSIRIS grant principals.

## 2. Trust root and enrollment

- The trust root is the owner's SSH ed25519 keys, listed in `governance/allowed_signers`
  (OpenSSH format, principal `owner`, namespace `osiris-grant`). A key is enrolled or removed
  only by a reviewed commit to that file. The public key is the only thing ever committed.
- Enrolled: the Node Beta key, `SHA256:u1IvoILluYw9F5SRPPVZNK5QjXa72nxRBMuDNk3P6YQ`.
- Pending: a backup key generated on Node Alpha (the phone), enrolled by a commit from Node Beta.
  It serves as the recovery key (section 6).

## 3. Authentication and channel

The owner signs the canonical grant at the node's own terminal:

```
ssh-keygen -Y sign -f ~/.ssh/id_ed25519 -n osiris-grant grant.json
ssh-keygen -Y verify -f governance/allowed_signers -I owner -n osiris-grant -s grant.json.sig < grant.json
```

`grant.json` is the canonical payload of spec 5.2 plus `scope`, `signed_at` and `expires_s`. The
private key never leaves its node.

`python -m osiris_cli.grants draft --payload-digest <sha256> --scope <scope>` prints one to sign:
`payload_digest` (the operation's SHA-256, lowercase hex), `scope`, `signed_at` (UTC, written
`YYYY-MM-DDTHH:MM:SSZ`), `expires_s` (default 900) and a random `nonce`, as sorted compact JSON.
Spec v1.2 was not available when the verifier was written, so these names follow the action
record above and `ExecutionGrant.payload_digest`; other fields are allowed and ignored. A grant's
id is the SHA-256 of grant.json. `python -m osiris_cli.grants check grant.json ...` checks a
signed grant without using it, and `python -m osiris_cli.grants revoke <id> --reason ...`
revokes one. Events go to `~/.osiris/authorization_ledger.jsonl`, a hash chain. On 2026-10-26 I checked the mechanism with a throwaway key: a
matching grant verifies, and both a single changed payload byte and a wrong namespace are refused
(exit 255).

The authorization record holds: the principal (`owner`), the key fingerprint, the scope, the method
(`ssh-sig`), the node, `signed_at`, the payload digest, the expiry and the consumption state.
It never holds key material.

## 4. Scope mapping

| Action class | Approval |
|---|---|
| Tier 0–1: read, propose, session state | None; allowed by the session mode |
| Tier 3–4 developer actions on the local working tree (`/apply`, `run_command`) | Interactive y/N at the terminal, per action and per digest, as the governor does today. Recorded as `method: terminal-presence`. |
| Production operations: releasing a campaign run, submitting to quantum hardware, promoting evidence, publishing (Zenodo/DOI), any unattended run | A signed `osiris-grant` (section 3). y/N is **not** sufficient. |

## 5. Lifetime, time source and consumption

- A grant is single-use and becomes `CONSUMED` atomically before the operation starts.
  A retry needs a new grant.
- The default expiry is 15 minutes from `signed_at`, which is inside the signed payload.
- Time source: the clock of the node that verifies the grant. Production grants are verified on Node
  Beta only, and only while the system clock reports NTP synchronization. If that status cannot be
  read, or reports unsynchronized, verification fails closed. Node Alpha may verify only after its
  synchronization status is readable from PRoot.
- Every state change is an append-only event (spec 5.2.1) in the trusted evidence ledger.

## 6. Revocation and recovery

- **Revoke a grant:** append `AUTHORIZATION_REVOKED`. The grant event is never edited or deleted.
- **Revoke a key:** remove its line from `governance/allowed_signers` in a reviewed commit, and append
  `AUTHORIZATION_REVOKED` for every outstanding grant signed by it.
- **Recovery:** if the Beta key is lost or compromised, the enrolled Alpha key signs the commit that
  enrolls its replacement. If both keys are lost, the owner re-enrolls through a pull request from
  either of their GitHub accounts. GitHub account control is the last-resort recovery root.

## 7. What remains (exit condition of action 18)

1. Implement the verifier (`ssh-keygen -Y verify` behind one function), the 5.2.1 events, the
   NTP check and atomic consumption. *Implemented in `osiris_cli/grants.py` (`authorize`,
   `revoke`); pending review.*
2. Tests: a missing, unbound, expired, revoked, tampered, wrong-namespace or wrong-principal grant
   leaves the operation unauthorized; a valid grant authorizes only the matching digest, once.
   *Implemented in `tests/test_grants.py`; pending review.*
3. Enroll the Node Alpha backup key.

Production execution stays blocked until items 1 and 2 are done and pass.
