# NCLM-GATE-1 — Pre-Registration Protocol: Speaking Gate Crossing (Held-Out Chat Loss ≤ 2.000 BPB)

**Registered commit:** (to be committed before launch)  
**Registered by:** Devin Phillip Davis / Node Beta (Standalone)  
**Target Invariant:** SYS-026 Speaking Gate Activation (`heldout_chat_bpb <= 2.0000`)

---

## 1. Scientific Objective & Thesis

In `NCLM-SCALE-1`, the Standard Transformer architecture (`standard_scale512`) demonstrated overwhelming superiority over the CRSM bundle across both seeds, outcompressing CRSM by **`> 1.29 BPB`** on held-out chat and **`> 1.57 BPB`** on held-out documents. At step 6,000, `standard_scale512` reached **`3.5087 BPB`** with an ongoing linear descent slope of $\sim 0.12\text{ BPB}$ per 1,000 steps without plateauing.

However, `NCLM-SCALE-1` utilized an exploratory pool weight distribution of `0.5, 0.3, 0.2` (50% docs, 30% chat lessons, 20% archive), devoting 70% of model capacity to modeling raw Python code and markdown documents rather than conversational grammar.

`NCLM-GATE-1` is an optimization experiment designed to drive held-out conversational loss below the **`2.000 BPB`** threshold required for autonomous speech permission (SYS-026) by:
1. Resuming directly from the verified 76 MB checkpoint (`organism.best.npz` at step 6,000);
2. Applying a conversational curriculum weighting (`--mix 0.1,0.8,0.1`), allocating 80% of training tokens directly to conversational exchanges;
3. Executing a 16,000-step extended training sweep with warm cosine schedule restart.

---

## 2. Model & Training Architecture

* **Architecture**: `standard_scale512` (Standard Pre-Norm Autoregressive Byte Transformer)
* **Parameters**: 4,077,568 ($d = 256$, $L = 6$, $H = 4$, $d_{ff} = 768$)
* **Receptive Field / Context**: 512 bytes
* **Positional Encoding**: Sinusoidal Base-10,000
* **Batch Size**: 2 ($1,024\text{ bytes / step}$)
* **Optimization**: AdamW ($\beta_1 = 0.9, \beta_2 = 0.98, \text{eps} = 10^{-9}$), cosine learning rate schedule with 50-step warm restart
* **Initial State**: Checkpoint `~/.osiris/experiments/nclm_scale1/ckpt/standard_scale512_s301/organism.best.npz` (Step 6,000, train loss `2.5555`)
* **Training Steps**: 16,000 steps (Total model steps: 6,000 $\rightarrow$ 22,000)

---

## 3. Curriculum & Pool Mix

* **Docs Weight**: 0.10 (General corpus documents)
* **Chat Lessons Weight**: 0.80 (Conversational exchanges & distilled lessons)
* **Archive Weight**: 0.10 (De-duplicated system archive)
* **Frozen Inputs**: Frozen snapshot from `~/.osiris/experiments/nclm_scale1/inputs/` (`corpus.json`, `distill.jsonl`, `exchanges.jsonl`, `frozen_corpus.json`)

---

## 4. Evaluation & The Speaking Gate (SYS-026)

* **Periodic Evaluation**: Evaluated every 200 steps across 48 held-out chat windows (512 bytes each) and 48 held-out document windows.
* **Primary Metric**: `heldout_chat_bpb` (mean cross-entropy bits per byte over held-out chat windows).
* **Target Threshold**: **`heldout_chat_bpb <= 2.0000 BPB`**.
* **Gate Transition**: If `heldout_chat_bpb <= 2.0000`, the SYS-026 Speaking Gate switches from **`CLOSED`** to **`OPEN (AUTONOMOUS)`**, enabling autonomous conversational generation.
