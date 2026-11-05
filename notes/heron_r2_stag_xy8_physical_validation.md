# IBM Heron r2 STAG-XY8 Physical QPU Validation Campaign

- **Target Hardware:** IBM Quantum Heron r2 (`ibm_marrakesh`, 156 transmon qubits)
- **Lead Operator:** Devin Phillip Davis / Enki
- **Permanent DOI:** [10.5281/zenodo.23967473](https://doi.org/10.5281/zenodo.23967473)
- **Governance Standard:** Gate 0 / SYS-021 Immutable Cryptographic Ledger (`evidence_ledger.db` Sequences #1–#5)

## Key Findings
1. **Physical Scale:** 4 independent jobs (`dblrpnt8ft8s738tlgcg`, `dblsnal8mdtc73d6pkmg`, `dblt471kbkrc73coc33g`, `dbltkdd8ft8s738toef0`), 648 ISA circuits, 663,552 physical shots, 192 s QPU compute.
2. **Decisive Protection Against Decoherence:** Decoupling decisively outperformed bare idle decay across all seven physical heavy-hex edges ($\Delta \langle XX \rangle$ up to $+0.4360$ under $4.0\,\mu\mathrm{s}$ evolution).
3. **Statistically Significant Gain:** On benchmark edge (14, 15), STAG-XY8 achieved a statistically significant correlation gain over synchronous XY8: $\Delta \langle XX \rangle = +0.0186$ ($95\%$ bootstrap CI $[+0.0107, +0.0264]$, $p < 0.001$).
4. **Forensic Resolution of Prior Artifacts:** Empirical audit of historical job `dblr6lhkbkrc73co9h30` proved unspaced DD pulses collapsed algebraically during transpilation to identity ($0\text{ ns}$), producing artificial suppression signatures. All current circuits enforce explicit $4.0\text{ ns}$ $dt$ delay scheduling.
