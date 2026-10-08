# NCLM-1 Manual Collection + Auto-Analysis Workflow

> **v4.5.2:** every bits/byte figure below, including the 7.60 baseline, was scored before the phase-conjugate corrector ran with gradients off, so it describes a different network from the one trained. Rescore (`osiris train --rescore-only`) before comparing; see `RELEASE_NOTES_v4.5.2.md`.

## Overview

You interact with OSIRIS manually. The memory engine and analysis pipeline work automatically in the background.

**Timeline:** Oct 7-14 (Week 3-4)  
**Goal:** Collect 150+ exchanges, measure BPB improvement from 7.60 → ≤2.0 for speaking gate

---

## Step 1: Start OSIRIS with Memory Enabled

```bash
cd /root/osiris-cli
export OSIRIS_PG_URL='<your Neon connection string>'
export OSIRIS_QUANTUM_BACKEND=aer
osiris
```

**What happens automatically:**
- Hook 1: Memory engine initializes (Neon connection)
- Hook 2: Every mentor reply stored with embedding
- Hook 3: Top-3 similar past exchanges retrieved for context
- Hook 4: Quantum hypotheses detected and tested asynchronously
- Hook 5: All metrics tracked to local ledger

---

## Step 2: Interact Naturally

Type research questions about quantum computing, geometric algebra, and continuous learning.

**Example prompts:**
- "How does staggered XY4 improve coherence time?"
- "Implement a Bell state preparation circuit"
- "Analyze quantum error correction codes"
- "Compare DD vs. echo sequences on near-term hardware"
- "What are the limits of gate fidelity optimization?"

**System automatically:**
1. Embeds your input (1024-dim)
2. Retrieves similar past exchanges
3. Augments mentor prompt with retrieved context
4. Mentor generates response (qwen2.5:7b)
5. Core trains on response + context
6. Stores exchange to Neon Postgres
7. Tracks BPB metrics

---

## Step 3: Monitor Progress (Optional)

**In a separate terminal:**

```bash
# Real-time monitoring (updates every 30 seconds)
cd /root/osiris-cli
python3 nclm_analysis.py --watch

# Or check status once
python3 nclm_analysis.py --report
```

**Metrics shown:**
- Total exchanges collected
- Mean BPB (target: ≤2.0)
- Learning curve (last 5 mean)
- Gate status (PASS/FAIL/IN_PROGRESS)
- Progress toward target

---

## Step 4: Evaluate When Done

After collecting 30-50 exchanges (or when you want to check progress):

```bash
python3 nclm_analysis.py --report --csv nclm_evaluation_final.csv
```

**Output:**
- `nclm_evaluation_final.csv` — BPB progression by exchange
- Console report — statistics and gate verdict

---

## Architecture

### Memory Engine Flow

```
Your prompt
    ↓
[Neon: Store exchange + embed (1024-dim)]
    ↓
[Semantic search: Top-3 similar past]
    ↓
[Mentor prompt augmented with context]
    ↓
[Mentor response (qwen2.5:7b)]
    ↓
[Core trains on: response + retrieved context + ledger history]
    ↓
[BPB computed and stored to ledger]
    ↓
[Analysis pipeline extracts metrics]
```

### Data Flow

```
OSIRIS Console (manual interaction)
    ↓
Local Ledger (~/.osiris/living/exchanges.jsonl)
    ↓
Neon Postgres (embeddings + hypotheses + insights)
    ↓
Analysis Pipeline (nclm_analysis.py)
    ↓
Reports (CSV + console output)
```

---

## Success Criteria

**Must-Have (≥1 of these = PASS):**
- [ ] Core BPB improves from 7.60
- [ ] 30+ held-out exchanges collected
- [ ] Learning curve visible in data

**Nice-to-Have (all = excellent):**
- [ ] Core BPB reaches ≤2.0 (gate PASS)
- [ ] Last 5 mean ≤2.5 (trend positive)
- [ ] Memory retrieval accelerates learning 2-3x
- [ ] Quantum hypotheses tested and tracked

---

## Expected Improvements

**With Memory Engine:**

| Phase | Exchanges | BPB | Notes |
|-------|-----------|-----|-------|
| Baseline | — | 7.60 | No memory |
| Init | 1-30 | 6.5-5.0 | Mentor learns patterns |
| Accel | 30-60 | 5.0-3.5 | Memory kicks in |
| Convergence | 60-100 | 3.5-2.5 | Context-augmented learning |
| Target | 100+ | ≤2.0 | Gate PASS |

**Without Memory:** ~7.60 (static)  
**With Memory:** ~3-5 range (expected)  
**Target Deadline:** Oct 7 (today)

---

## Troubleshooting

### "Memory engine not connected"
- Check `OSIRIS_PG_URL` is set
- Verify Neon database is accessible: `psql $OSIRIS_PG_URL`
- Restart osiris

### "No BPB metrics showing"
- Ledger hasn't recorded BPB yet (wait for more exchanges)
- Check `~/.osiris/living/exchanges.jsonl` exists

### "Slow responses"
- Neon I/O is non-blocking; mentor is bottleneck
- Quantum tests run async (no blocker)
- Normal: first response ~5-10s, subsequent ~3-5s

### "Gate says FAIL but BPB looks good"
- Gate requires ≤2.0 mean BPB
- Check: `python3 nclm_analysis.py --report | grep "Mean BPB"`

---

## Files

- `nclm_analysis.py` — Monitoring and reporting pipeline
- `NCLM1_MANUAL_WORKFLOW.md` — This guide
- `~/.osiris/living/exchanges.jsonl` — Local ledger (immutable)
- `nclm_evaluation_final.csv` — Analysis output

---

## Next Steps

1. **Now:** Start OSIRIS with memory enabled
2. **Collect:** 30-50+ exchanges over next few hours/days
3. **Monitor:** Run `python3 nclm_analysis.py --watch` in background
4. **Measure:** Check learning curves with `--report`
5. **Optimize:** Tune retrieval thresholds if needed (Week 4)
6. **Publish:** Export final report and results to Zenodo (DOI)

---

**Status:** ✅ Memory engine deployed  
**Ready:** ✅ Neon Postgres live  
**Next:** 🚀 Start interactive OSIRIS session
