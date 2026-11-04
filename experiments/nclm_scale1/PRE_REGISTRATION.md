# NCLM-SCALE-1 — Can Scaling Context Length and Model Geometry Drive Byte-Level Cross-Entropy Below the 2.0 BPB Speaking Gate? (pre-registered 2026-10-31)

Written and committed **before any run**. The result will be deposited in `RESULT.md` in this directory as PASS,
FAIL or INCONCLUSIVE against the pre-registered criteria below. No hyperparameters, evaluation windows, or
stopping rules are modified after launch.

---

## 1. Objective and Hypothesis

The **SYS-026 Speaking Gate** enforces an immutable epistemic threshold: the OSIRIS core is permitted to speak
in its own autonomous voice only when its mean held-out bits-per-byte (BPB) over the last 30 exchanges drops
to or below **`2.0 BPB`** (and strictly beats the unigram baseline).

As of October 31, 2026, the living core (`osiris.nclm.SovereignTransformerV2`, step 10,268) achieves:
- Held-out document loss: `3.485 BPB` (unigram `5.221 BPB`)
- Held-out conversational loss: `3.2529 BPB` (best individual exchange `2.9469 BPB`; unigram `4.775 BPB`)

While the core substantially outperforms unigram statistics, it remains bounded above `2.0 BPB`. Information-theoretic
analysis identifies two primary architectural bottlenecks:
1. **Context Truncation (`max_seq_len = 128` bytes)**: 128 raw UTF-8 bytes correspond to only ~20–25 English words.
   In dialogue, user prompts typically exceed 150–300 bytes. At 128 bytes, the attention mechanism cannot condition
   on the user query when predicting response tokens, imposing an entropy lower bound near ~2.8–3.2 BPB.
2. **Parameter Saturation (726,304 parameters)**: The Termux-constrained geometry ($d=128, L=4, H=4, d_{ff}=256$)
   has insufficient capacity to simultaneously memorize general English orthography, code structures, and domain
   knowledge across quantum mechanics and sovereign governance.

**Core Hypothesis**: Expanding the receptive field ($128 \rightarrow 512$ bytes) and parameter capacity
($726\text{k} \rightarrow 3.29\text{M}$) will allow contextual conditioning and associative lexical storage,
enabling held-out conversational cross-entropy to cross the **$< 2.0\text{ BPB}$** threshold.

---

## 2. Experimental Arms

Two scaled arms are evaluated under matched parameter parity (~4.08M parameters) and identical 512-byte receptive fields:

| Arm | Description | Hidden Dim ($d$) | Layers ($L$) | Heads ($H$) | Intermediate ($d_{ff}$) | Context ($T$) | Total Parameters | Primary Hypothesis |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`standard_scale512`** | Scaled Standard Transformer | 256 | 6 | 4 | 768 | 512 bytes | **4,077,568** | **Crosses $< 2.000\text{ BPB}$ Speaking Gate** |
| **`crsm_scale512`** | Scaled CRSM Transformer | 256 | 6 | 4 | 512 | 512 bytes | **4,079,152** | Scaled CRSM Comparison Arm |

*Note on Parameter Parity*: Parameter counts are matched within 0.038% (4,077,568 vs 4,079,152). Both arms operate with `max_seq_len = 512` bytes, enabling full conditioning across conversation prompt history.

---

## 3. Data Ingestion and Training Horizon

All arms train on the frozen snapshot established in `~/.osiris/experiments/nclm_arch1/inputs/`:
- **Frozen Archive Pool**: 41,865,933 bytes (4,202 verified workspace and documentation files).
- **Frozen Distillation Pool**: 1,082 mentor lessons + 896 dialogue exchanges (2,606,247 bytes).
- **Sampling Mix**: `0.50` verified docs, `0.30` lessons, `0.20` archive.
- **Seeds**: 3 seeds per arm (Seeds `300`, `301`, `302`).
- **Steps**: 8,000 steps per run with AdamW ($\text{lr} = 3 \times 10^{-4}$, weight decay 0.01, 50-step warmup, cosine decay).

---

## 4. Evaluation and Decision Rules

Evaluations occur every 200 steps on the held-out split (50 held-out documents, 224 held-out exchanges):
1. **Primary Metric**: Minimum held-out conversational cross-entropy (`heldout_chat_bpb`).
2. **Speaking Gate Test**: Mean held-out chat loss over the final evaluation window.
   - **GATE-OPEN**: $\text{Mean Held-Out Chat BPB} \le 2.000$.
   - **GATE-CLOSED**: $\text{Mean Held-Out Chat BPB} > 2.000$.
3. **Statistical Decision Criterion**:
   - **PASS**: `arm_scale3m` achieves $\text{Held-Out Chat BPB} \le 2.000$ on at least 2 of 3 seeds AND demonstrates
     a median gain $\Delta \text{BPB} \ge 0.50$ over `arm_base`.
   - **PARTIAL**: `arm_scale3m` fails $\le 2.000$ but demonstrates statistically significant improvement
     ($\Delta \text{BPB} \ge 0.30$) over both `arm_base` and `arm_ctx512`.
   - **FAIL**: `arm_scale3m` shows no significant improvement ($\Delta \text{BPB} < 0.10$) over `arm_base`.

---

## 5. Non-Interference Invariant

`NCLM-SCALE-1` execution is sequenced to launch strictly after the active `NCLM-ARCH-1` 16-run tournament completes,
ensuring machine load average $\le 3.0$ and zero contention for AVX2 execution units.
