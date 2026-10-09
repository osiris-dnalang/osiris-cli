# OSIRIS v4.5.1 → v4.5.2 Upgrade Checklist

**Release Date:** 2026-10-08  
**Risk Level:** Medium (stale scores must be rescored)  
**Estimated Time:** 10–30 minutes (depending on held-out score count)

---

## Why This Upgrade Matters

**Critical Fix:** Before v4.5.2, held-out scores measured a **different network** from the one that was trained. A layer (the phase-conjugate corrector) ran during training but was skipped during scoring, generation, and early stopping. This made every bits/byte figure on record incomparable to training loss.

**v4.5.2 fixes this.** Scores are now tagged with their scorer version, and old scores no longer count toward the speaking gate until rescored. Your checkpoints are still valid and do not need to be retrained.

---

## Pre-Upgrade Checklist

### ☐ 1. Back Up Your Data

```bash
# Save current stats in case you need to revert
cp ~/.osiris/living/stats.json ~/.osiris/living/stats.v4.5.1.json

# Save the ledger (optional, but good practice)
cp ~/.osiris/living/exchanges.jsonl ~/.osiris/living/exchanges.v4.5.1.jsonl

# Optional: Save the training logs
cp ~/.osiris/living/nclm_loss.log ~/.osiris/living/nclm_loss.v4.5.1.log
```

**Why:** If rescoring produces unexpected results, you can restore the v4.5.1 stats as a reference.

---

### ☐ 2. Check for Running Trainer

```bash
osiris train --status
```

**Expected Output (one of):**
- `Training in progress: step X / Y` → **Stop it** (see step 3)
- `Not running` → **Proceed to step 4**
- `Error: unable to acquire lock` → Another console is running; quit it first

**If training is running:**
```bash
osiris train --stop
# Wait 10–30 seconds for it to save
sleep 30
osiris train --status  # Confirm it stopped
```

---

### ☐ 3. Quit All Open OSIRIS Consoles (v4.5.1)

**Critical:** A v4.5.1 console still running can overwrite rescored scores with old scores.

```bash
# Find all running OSIRIS processes
ps aux | grep osiris

# Kill any running consoles (replace PID with the actual process ID)
kill <PID>

# Verify they are gone
ps aux | grep osiris  # Should show no matches
```

**Why:** v4.5.1 merges scores by step only; it does not know about scorer tagging. If it writes to `stats.json` after rescoring, it can revert rescored entries.

---

## Upgrade Steps

### ☐ 4. Update OSIRIS

```bash
# If installed from pip:
pip install --upgrade osiris-cli

# If installed from source:
cd ~/path/to/osiris-cli
git pull origin main
pip install -e .
```

**Verify the version:**
```bash
osiris --version
# Expected: OSIRIS v4.5.2
```

---

### ☐ 5. Verify the Model Code is Loaded

```bash
python -c "import osiris.nclm as n; print(f'Path: {n.__file__}'); print(f'Scorer: {getattr(n, \"SCORING_FORWARD\", 1)}')"
```

**Expected Output:**
```
Path: /path/to/osiris-cli/osiris/nclm/__init__.py
Scorer: 2
```

**If Scorer is 1:**  
❌ **Stop.** An older version of `osiris.nclm` is on your `PYTHONPATH`. Check:
```bash
echo $PYTHONPATH
# Remove any stale or wheel install paths that point to v4.5.1
```

---

## Rescoring & Gate Verification

### ☐ 6. Rescore Held-Out Exchanges

**This is the key step.** Rescoring scores the same held-out exchanges with the fixed scorer using the weights you already trained.

```bash
osiris train --rescore-only
```

**Expected Output:**
```
rescored N held-out exchanges at step M (scorer 2); 
before: gate closed (9.1 bits/byte held-out; speaks at <= 2.0); 
now: gate closed (5.2 bits/byte held-out; speaks at <= 2.0).
```

**What this means:**
- `rescored N held-out exchanges`: The number of old scores that were refreshed.
- `scorer 2`: v4.5.2 scorer is active.
- `before: ...` and `now: ...`: The gate state before and after rescoring.

**Possible outcomes:**

| Scenario | Action |
|---|---|
| `now: gate open` | 🎉 **Success!** Your core now qualifies to speak. Run `/osiris` in the console to see its voice activate. |
| `now: gate closed (X bits/byte)` | ✅ **Expected.** If X > 2.0 or above unigram, the core still needs training. This is normal. |
| `Error: not rescored: loaded version 1` | ❌ **A stale copy of osiris.nclm is on PYTHONPATH.** See step 5. |
| `rescored 0 held-out exchanges` | ⚠️ **No old scores found.** Either you had no held-out exchanges yet, or they're already v4.5.2. Proceed to step 7. |

---

### ☐ 7. Check the Gate Status

Open a new console:

```bash
osiris
```

Then in the console:

```
/osiris
```

**Expected Output:**
```
gate          OPEN: the core answers in its own voice
              [if it opened], or
gate          CLOSED: needs 30 held-out exchanges at <= 2.0 bpb and below unigram
```

**Also check:**
```
held-out      N scored (X bits/byte vs. Y unigram)
              M older scores predate the v4.5.2 scoring fix and are not counted
```

**If it says "M older scores ... not counted":**  
✅ Expected. Those are v4.5.1 scores being tracked but not used. They will be replaced as new held-out exchanges are scored.

---

### ☐ 8. Verify Stale Scores Are Not Used

Check the stats file directly:

```bash
python -c "
import json
stats = json.load(open('~/.osiris/living/stats.json'.replace('~', '/root')))
scores = stats.get('heldout_scores', {})
current = [s for s in scores.values() if len(s) > 4 and s[4] == 2]
stale = [s for s in scores.values() if len(s) <= 4 or s[4] != 2]
print(f'Current (v4.5.2): {len(current)}')
print(f'Stale (pre-v4.5.2): {len(stale)}')
if stale:
    print('Stale scores will be replaced during training or rescoring.')
"
```

**Expected Output:**
```
Current (v4.5.2): 30
Stale (pre-v4.5.2): 0
```

or

```
Current (v4.5.2): 30
Stale (pre-v4.5.2): N  # where N > 0
Stale scores will be replaced during training or rescoring.
```

---

## Phone Harness Update (If Applicable)

### ☐ 9. Update the Phone (osiris-mobile-termux)

If you use the Termux harness on a phone, update it too:

```bash
# On the phone, in Termux:
cd ~/crsm/osiris-cli
git pull origin main
pip install -e .

# Verify:
python -c "import osiris.nclm as n; print(getattr(n, 'SCORING_FORWARD', 1))"
# Expected: 2
```

**Why:** The phone's fallback checkout is used if `osiris.nclm` is not in the main install. If it's still v4.5.1, it will write scores tagged as 1 (stale).

---

## Training After Upgrade

### ☐ 10. Start New Training (Optional)

If you want to resume training, the process is unchanged:

```bash
osiris train --hours 8 --detach
# or in console:
/train start 8
```

**What's different:**
- New held-out scores will automatically be tagged with scorer 2.
- Early stopping and checkpoint selection will use the corrected scorer.
- Benchmark comparability: see **Comparability** section below.

---

## Verification Checklist Summary

Run this script to verify all steps:

```bash
#!/bin/bash
set -e

echo "=== v4.5.1 → v4.5.2 Upgrade Verification ==="
echo

# 1. Version check
echo "✓ Version:"
osiris --version
echo

# 2. Scorer check
echo "✓ Scorer:"
python -c "import osiris.nclm as n; print(f'  {n.__file__}'); print(f'  SCORING_FORWARD: {getattr(n, \"SCORING_FORWARD\", 1)}')"
echo

# 3. No trainer running
echo "✓ Trainer status:"
osiris train --status 2>/dev/null | head -1
echo

# 4. Backup exists
echo "✓ Backup:"
if [ -f ~/.osiris/living/stats.v4.5.1.json ]; then
  echo "  stats.v4.5.1.json exists"
else
  echo "  (optional; create one if you want a fallback)"
fi
echo

# 5. Gate status
echo "✓ Gate status (run in console: /osiris)"
echo "  Check for:"
echo "  - 'gate open' or 'gate closed' with a reason"
echo "  - 'held-out N scored' (the count of rescored exchanges)"
echo "  - Any mention of 'stale' scores (should decrease as you train)"
echo

echo "=== Upgrade Complete ==="
```

Save this as `verify_upgrade.sh` and run:

```bash
chmod +x verify_upgrade.sh
./verify_upgrade.sh
```

---

## Benchmark Comparability

**Important:** Your v4.5.1 metrics are no longer comparable to v4.5.2. Here's what changed and what didn't:

### ❌ NOT Comparable After Upgrade

| Metric | Reason |
|---|---|
| Held-out scores (all benchmarks) | Scored with corrector skipped; now scored with corrector applied. |
| Gate status (7.60 vs 5.03 bits/byte in README) | Measured before the fix. |
| NCLM-GATE-PILOT scores (+0.043, +0.067 bits/byte) | Measured before the fix. |
| Early stopping checkpoint selection | Used pre-fix scores to decide best checkpoint. |
| Live generation quality | Different network was used in v4.5.1. |
| `nclm_final_report.csv` (if you have one) | Based on pre-fix scores. |

### ✅ Still Comparable

| Metric | Reason |
|---|---|
| Training loss (`nclm_loss.log`) | Loss during training is unaffected; corrector always ran then. |
| Unigram baselines | Computed from text alone; independent of model. |
| Exchange hash chain | Deterministic; unchanged. |
| Checkpoints | Weights unchanged; same network loads. |

**Recommendation:** If you have published or shared v4.5.1 metrics, add a note:
> "Held-out scores in this report were computed before v4.5.2 (2026-10-08) and do not measure the trained network. See OSIRIS Release Notes v4.5.2."

---

## Troubleshooting

### Problem: `osiris train --rescore-only` Fails

**Error:** `Error: not rescored: loaded version 1`

**Cause:** An old version of `osiris.nclm` is being imported.

**Fix:**
```bash
# Find the stale copy:
python -c "import osiris.nclm as n; print(n.__file__)"

# If it's not from your main osiris-cli install, remove it from PYTHONPATH:
unset PYTHONPATH
# or edit ~/.bashrc / ~/.zshrc to remove stale paths

# Verify:
python -c "import osiris.nclm as n; print(f'Scorer: {getattr(n, \"SCORING_FORWARD\", 1)}')"
# Should print: Scorer: 2

# Retry:
osiris train --rescore-only
```

---

### Problem: Gate Doesn't Open After Rescoring

**Scenario:** Scores were rescored, but gate still shows "closed."

**Diagnosis:**
```bash
python -c "
import json
stats = json.load(open('~/.osiris/living/stats.json'.replace('~', '/root')))
scores = list(stats.get('heldout_scores', {}).values())
current = [s for s in scores if len(s) > 4 and s[4] == 2]
if current:
    bpbs = [s[0] for s in current]
    print(f'Current scores: {len(current)}')
    print(f'Mean: {sum(bpbs) / len(bpbs):.2f} bits/byte')
    print(f'Min: {min(bpbs):.2f}, Max: {max(bpbs):.2f}')
else:
    print('No v4.5.2 scores found; rescore again.')
"
```

**Interpretation:**
- If mean > 2.0 → Core is not yet good enough. Continue training.
- If mean ≤ 2.0 but gate still closed → Check that there are ≥ 30 rescored exchanges:
  ```bash
  python -c "import json; stats = json.load(open('~/.osiris/living/stats.json'.replace('~', '/root'))); current = [s for s in stats.get('heldout_scores', {}).values() if len(s) > 4 and s[4] == 2]; print(f'{len(current)} current scores')"
  ```
  - If < 30 → Gate needs 30 held-out exchanges. Keep training; every 5th exchange is held out.

---

### Problem: Phone Harness Scores Reverted to "Stale"

**Scenario:** You rescored on desktop, but the phone wrote old scores.

**Cause:** Phone still runs v4.5.1.

**Fix:**
1. Update the phone (step 9).
2. Manually re-rescore on desktop (step 6) to replace phone-written v4.5.1 scores.

---

## Post-Upgrade Steps

### ☐ 11. Document Your Baseline

Create a file recording your v4.5.2 baseline:

```bash
cat > ~/.osiris/v4.5.2_baseline.txt <<EOF
Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Version: v4.5.2
Rescored exchanges: [run "osiris train --status" to see current count]
Gate status: [run "/osiris" in console]
Mean held-out bits/byte: [see python command above]
EOF
```

This helps you track progress over time.

---

### ☐ 12. Archive Old Experiments (Optional)

If you had v4.5.1 experiment runs you want to keep for reference:

```bash
mkdir -p ~/.osiris/archive_v4.5.1
cp -r ~/.osiris/experiments/nclm_gate_pilot1 ~/.osiris/archive_v4.5.1/
# Archive other pre-v4.5.2 experiment runs here
```

This keeps your active directory clean and saves old data for comparison.

---

### ☐ 13. Update Dependencies (Optional)

If you installed from source, check for updates to sibling repos:

```bash
cd ~/dnalang-core && git pull origin main && pip install -e .
cd ~/organism_sim && git pull origin main && pip install -e .
cd ~/bridge && git pull origin main && pip install -e .
```

(Only if you have these sibling repos checked out.)

---

## Success Criteria

✅ **You have successfully upgraded when:**

1. `osiris --version` shows **v4.5.2**.
2. `python -c "import osiris.nclm as n; print(getattr(n, 'SCORING_FORWARD', 1))"` shows **2**.
3. `osiris train --status` runs without error.
4. `/osiris` in console shows gate status (open or closed with a reason).
5. No errors in `/check ledger`.
6. `/train rescore` (if needed) completes without "version 1" error.

---

## Questions?

- **Release notes:** See `RELEASE_NOTES_v4.5.2.md`.
- **Known issues:** See "Known issues" section at the end of release notes.
- **Pre-registered test:** See `experiments/nclm_arch1/PRE_REGISTRATION.md` (NCLM-ARCH-1).
- **Claims about the fix:** See `osiris_cli/claims.py` (entries: `NCLM_PC_CORRECTOR`, `NCLM_CORE`).

---

## Quick Reference: One-Liner Checklist

```bash
# 1. Backup
cp ~/.osiris/living/stats.json ~/.osiris/living/stats.v4.5.1.json

# 2. Stop trainer
osiris train --stop

# 3. Quit old consoles (manually)

# 4. Upgrade
pip install --upgrade osiris-cli

# 5. Verify version
osiris --version

# 6. Verify scorer
python -c "import osiris.nclm as n; print(getattr(n, 'SCORING_FORWARD', 1))"

# 7. Rescore
osiris train --rescore-only

# 8. Check gate
# (Open console and run: /osiris)
```

---

**Version:** 1.0  
**Last Updated:** 2026-10-08  
**Next Review:** When v4.5.3 or later is released.
