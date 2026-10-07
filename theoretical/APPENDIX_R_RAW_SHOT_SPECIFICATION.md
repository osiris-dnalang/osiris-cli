# Appendix R — Raw-Shot Archival Specification
## OSIRIS τ–Φ Dynamical Theory
### Confirmatory Protocol for Quantum Measurement Data

**Author:** Devin Phillip Davis  
**Affiliation:** Agile Defense Systems LLC (CAGE: 9HUP5)  
**Date:** 2026-10-07  
**Version:** 1.0 (Pre-registered and Frozen)  
**Status:** Non-Substitutable (Q-Plane Data Integrity)

---

## R.1 Purpose

This appendix defines the **mandatory archival format and integrity constraints** for raw quantum measurement shots used in the OSIRIS τ–Φ confirmatory experiment.

**Core Principles:**
1. **Raw shots are the authoritative measurement record**
2. **All derived quantities must be reproducible from raw shots**
3. **No filtering, compression, or post-hoc modification is permitted**
4. **Provenance must be preserved at the shot level**

This specification ensures:
- Full reproducibility
- Independent-lab verifiability  
- No hidden preprocessing
- No lossy compression
- No circular variable construction
- No post-hoc endpoint switching

---

## R.2 Minimum Required Fields (FROZEN)

Each circuit-trial record **must** contain the following fields. This schema is **pre-registered and may not be altered**.

### R.2.1 Field Definitions

| Field | Type | Definition | Units | Example |
|-------|------|------------|-------|---------|
| `trial_id` | string | Unique identifier for this trial | - | `"trial_20261007_ibmfez_001"` |
| `circuit_id` | string | Unique identifier for the circuit | - | `"bell_8q_v1"` |
| `backend` | string | Hardware backend identifier | - | `"ibm_fez"` |
| `timestamp` | string | ISO-8601 timestamp of shot acquisition | UTC | `"2026-10-07T10:46:00.123456Z"` |
| `t` | float | Controlled evolution time | μs | `16.0` |
| `T1` | float | Independently measured relaxation time | μs | `45.2` |
| `T2` | float | Independently measured dephasing time | μs | `32.1` |
| `Phi` | float | Coherence coordinate (Appendix Φ) | - | `0.876` |
| `theta` | float | Temporal phase: 2πt/τ₀ | rad | `1.123` |
| `N_q` | integer | Number of qubits in the circuit | - | `127` |
| `D` | integer | Circuit depth (number of layers) | - | `10` |
| `N_g` | integer | Total gate count | - | `45` |
| `epsilon_g` | float | Average gate error rate | - | `0.001` |
| `epsilon_r` | float | Readout error rate | - | `0.02` |
| `raw_shots` | array | Full list of measurement outcomes | - | `["010", "111", "000", ...]` |
| `circuit_hash` | string | SHA-256 hash of circuit definition | - | `"a1b2c3..."` |
| `calibration_hash` | string | SHA-256 hash of calibration data | - | `"d4e5f6..."` |

### R.2.2 Field Constraints

- **`trial_id`**: Must be globally unique within the dataset
- **`circuit_id`**: Must reference a pre-registered circuit definition
- **`timestamp`**: Must be ISO-8601 format with timezone (Z for UTC)
- **`t`**: Must be ≥ 0 (in microseconds)
- **`T1`, `T2`**: Must be > 0 (in microseconds)
- **`Phi`**: Must be in [0, 1] (dimensionless)
- **`theta`**: Must be in [0, 2π) (radians)
- **`N_q`**: Must be ≥ 1
- **`D`**: Must be ≥ 0
- **`N_g`**: Must be ≥ 0
- **`epsilon_g`, `epsilon_r`**: Must be in [0, 1]
- **`raw_shots`**: Must be an array of strings, each of length `N_q`

---

## R.3 Raw-Shot Format (FROZEN)

### R.3.1 Primary Format: JSON Lines (`.jsonl`)

**REQUIRED**: One trial per line, UTF-8 encoding, no compression.

```jsonl
{"trial_id": "trial_001", "circuit_id": "bell_2q", "backend": "ibm_fez", "timestamp": "2026-10-07T10:46:00.000000Z", "t": 16.0, "T1": 45.2, "T2": 32.1, "Phi": 0.876, "theta": 1.123, "N_q": 2, "D": 1, "N_g": 2, "epsilon_g": 0.001, "epsilon_r": 0.02, "raw_shots": ["00", "01", "10", "11", "00", "01", "10", "11", "00", "01"], "circuit_hash": "a1b2c3d4e5f6...", "calibration_hash": "x9y8z7w6v5u4..."}
{"trial_id": "trial_002", "circuit_id": "bell_2q", "backend": "ibm_fez", "timestamp": "2026-10-07T10:46:05.123456Z", "t": 32.0, "T1": 45.2, "T2": 32.1, "Phi": 0.765, "theta": 2.246, "N_q": 2, "D": 1, "N_g": 2, "epsilon_g": 0.001, "epsilon_r": 0.02, "raw_shots": ["00", "11", "01", "10", "00", "11", "01", "10", "00", "11"], "circuit_hash": "a1b2c3d4e5f6...", "calibration_hash": "x9y8z7w6v5u4..."}
```

### R.3.2 Alternative Formats

**Allowed:**
- `.json` (array of trial objects)
- `.csv` (bitstrings only; **must** have separate metadata file)
- `.txt` (plain list of bitstrings, one per line; **must** have separate metadata file)

**Prohibited:**
- ❌ `.pdf` (not machine-readable)
- ❌ `.xlsx` (proprietary format)
- ❌ `.html` (not suitable for archival)
- ❌ `.md` (not structured data)
- ❌ Any compressed format **without** accompanying uncompressed version
- ❌ Any format that obscures raw measurement outcomes

### R.3.3 Format Validation

All files must pass:
1. **UTF-8 encoding check**
2. **Valid JSON/JSONL syntax**
3. **Schema validation** against the required fields
4. **Bitstring validation**: Each shot must be a string of length `N_q` containing only `'0'` and `'1'`
5. **Provenance check**: All hashes must be valid SHA-256

---

## R.4 Fidelity Reconstruction from Raw Shots

### R.4.1 Computational-Basis Targets

For circuits with a **single target bitstring** (e.g., Bell states, GHZ states):

$$F_i = \frac{n_i^*}{N_i}$$

Where:
- $n_i^*$ = Number of shots equal to the target bitstring
- $N_i$ = Total number of shots

**Example:** For a Bell state $|\Phi^+\rangle = \frac{1}{\sqrt{2}}(|00\rangle + |11\rangle)$ with target bitstrings `"00"` and `"11"`:

```python
target_bitstrings = ["00", "11"]
n_star = sum(1 for shot in raw_shots if shot in target_bitstrings)
N = len(raw_shots)
F = n_star / N
```

### R.4.2 Superposition / Entangled Targets

For circuits with **multiple target bitstrings** or **superposition states**:

$$F_i = \langle \psi_i^* | \rho_i | \psi_i^* \rangle$$

**Reconstruction Method:**
1. Use Maximum Likelihood Estimation (MLE) for density matrix reconstruction
2. Requires tomography data (multiple measurement bases)
3. Raw shots must include **all** measurement bases used

**Minimum Requirements:**
- Single-qubit tomography: 3 bases (X, Y, Z)
- Two-qubit tomography: 9 bases
- Shot count per basis: ≥ 1024

### R.4.3 Validation of Reconstruction

Each fidelity value must be validated:
- $0 \leq F \leq 1$
- For computational-basis targets: $F \geq \frac{1}{2^N}$ (random chance)
- For entangled states: $F \geq 0$ (no negative fidelity)

---

## R.5 Integrity Constraints (FROZEN)

### R.5.1 No Post-Hoc Filtering

**PROHIBITED**: Removing shots based on:
- ❌ Fidelity values
- ❌ Φ values
- ❌ θ values
- ❌ Backend performance
- ❌ Calibration state
- ❌ Circuit performance
- ❌ Anomalous values
- ❌ Suspected outliers

**PERMITTED**: Removing shots only for:
- ✅ Documented hardware failures (with justification)
- ✅ Verified readout errors (with calibration proof)

### R.5.2 No Reconstruction from Summaries

Raw shots **must** be:
- ✅ Directly acquired from QPU
- ✅ Stored in full
- ✅ Unprocessed

Raw shots **must NOT** be:
- ❌ Reconstructed from histograms
- ❌ Reconstructed from probability distributions
- ❌ Reconstructed from compressed logs
- ❌ Reconstructed from JSON summaries
- ❌ Reconstructed from fidelity tables

### R.5.3 No Mixing of Sessions

Each raw-shot block must:
- ✅ Correspond to a **single** acquisition session
- ✅ Have a **unique** session identifier
- ✅ Include **all** shots from that session
- ❌ Not mix shots from different sessions
- ❌ Not mix shots from different circuits
- ❌ Not mix shots from different backends

### R.5.4 No Circular Analysis

The analysis must follow this **strict order**:

```
1. Acquire raw shots → Store with hash H₁
2. Compute Φ (Appendix Φ) → Store with hash H₂
3. Compute θ → Store with hash H₃
4. Compute fidelity → Store with hash H₄
5. Begin statistical analysis
```

**PROHIBITED**:
- ❌ Computing Φ after seeing fidelity
- ❌ Computing θ after seeing fidelity
- ❌ Modifying any definition based on outcomes

---

## R.6 Archival Format for Zenodo

### R.6.1 Directory Structure

```
OSIRIS_tauPhi_confirmatory_packet_v5.0/
├── raw_shots/
│   ├── backend_ibm_fez/
│   │   ├── 2026-10-07/
│   │   │   ├── circuit_bell_2q/
│   │   │   │   ├── trial_001.jsonl
│   │   │   │   ├── trial_002.jsonl
│   │   │   │   └── ...
│   │   │   └── circuit_ghz_8q/
│   │   │       ├── trial_001.jsonl
│   │   │       └── ...
│   │   └── 2026-10-08/
│   │       └── ...
│   └── backend_ibm_torino/
│       └── ...
│
├── calibration/
│   ├── 2026-10-07/
│   │   ├── T1_T2_ibm_fez.json
│   │   └── coupling_map_ibm_fez.json
│   └── 2026-10-08/
│       └── ...
│
├── metadata/
│   ├── trial_index.csv
│   ├── circuit_definitions.json
│   └── backend_info.json
│
└── provenance/
    ├── raw_shots.sha256
    ├── calibration.sha256
    └── complete_archive.sha256
```

### R.6.2 File Naming Convention

**Trial Files:**
```
{backend}_{date}_{circuit_id}_{trial_index}.{ext}
```

**Examples:**
- `ibm_fez_20261007_bell_2q_001.jsonl`
- `ibm_torino_20261007_ghz_8q_001.jsonl`

**Calibration Files:**
```
{backend}_{date}_{calibration_type}.json
```

**Examples:**
- `ibm_fez_20261007_T1_T2.json`
- `ibm_fez_20261007_coupling_map.json`

---

## R.7 Trial-Level JSON Schema (FROZEN)

This schema is **pre-registered and may not be altered**.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "OSIRIS τ–Φ Raw Shot Trial",
  "description": "Schema for a single trial in OSIRIS τ–Φ confirmatory experiment",
  "type": "object",
  "required": [
    "trial_id",
    "circuit_id", 
    "backend",
    "timestamp",
    "t",
    "T1",
    "T2",
    "Phi",
    "theta",
    "N_q",
    "D",
    "N_g",
    "epsilon_g",
    "epsilon_r",
    "raw_shots"
  ],
  "additionalProperties": false,
  "properties": {
    "trial_id": {
      "type": "string",
      "pattern": "^[a-zA-Z0-9_-]+$",
      "description": "Unique identifier for this trial"
    },
    "circuit_id": {
      "type": "string",
      "description": "Unique identifier for the circuit"
    },
    "backend": {
      "type": "string",
      "enum": ["ibm_fez", "ibm_torino", "ibm_nazca", "ibm_kyoto", "ibm_osaka", "ibm_brisbane", "ibm_marrakesh"],
      "description": "Hardware backend identifier"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO-8601 timestamp of shot acquisition"
    },
    "t": {
      "type": "number",
      "minimum": 0,
      "description": "Controlled evolution time in microseconds"
    },
    "T1": {
      "type": "number",
      "minimum": 0,
      "exclusiveMinimum": true,
      "description": "Relaxation time in microseconds"
    },
    "T2": {
      "type": "number", 
      "minimum": 0,
      "exclusiveMinimum": true,
      "description": "Dephasing time in microseconds"
    },
    "Phi": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Coherence coordinate (Appendix Φ)"
    },
    "theta": {
      "type": "number",
      "minimum": 0,
      "maximum": 6.28318530718,
      "description": "Temporal phase in radians"
    },
    "N_q": {
      "type": "integer",
      "minimum": 1,
      "description": "Number of qubits"
    },
    "D": {
      "type": "integer",
      "minimum": 0,
      "description": "Circuit depth"
    },
    "N_g": {
      "type": "integer",
      "minimum": 0,
      "description": "Total gate count"
    },
    "epsilon_g": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Average gate error rate"
    },
    "epsilon_r": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Readout error rate"
    },
    "raw_shots": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^[01]+$"
      },
      "minItems": 1,
      "description": "Full list of measurement outcomes (bitstrings)"
    },
    "circuit_hash": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$",
      "description": "SHA-256 hash of circuit definition"
    },
    "calibration_hash": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$",
      "description": "SHA-256 hash of calibration data"
    }
  }
}
```

---

## R.8 Independent-Lab Verification Requirements

An independent laboratory must be able to:

### R.8.1 Recompute Fidelity
```python
# For computational-basis target
def compute_fidelity(raw_shots, target_bitstrings):
    n_star = sum(1 for shot in raw_shots if shot in target_bitstrings)
    N = len(raw_shots)
    return n_star / N
```

### R.8.2 Recompute Φ
- Use Appendix Φ protocols
- Requires calibration data (separate files)

### R.8.3 Recompute θ
```python
import math
def compute_theta(t, tau_0=46.0):
    return 2 * math.pi * t / tau_0
```

### R.8.4 Reproduce All Statistical Tests
- Use Appendix Δ (SAP)
- Requires only raw shots and metadata

### R.8.5 Validate φ-Network Predictions
- Use Appendix Δ procedures
- Requires only observed constants

### R.8.6 Confirm or Falsify τ–Φ Dynamics
- Use Appendix Σ protocols
- Requires only raw shots and independent Φ measurement

---

## R.9 Provenance Requirements

### R.9.1 Per-File Requirements

Each raw-shot file must include in its **metadata** (or accompanying file):

| Field | Type | Description |
|-------|------|-------------|
| `file_hash` | string | SHA-256 hash of the file contents |
| `creation_timestamp` | string | ISO-8601 timestamp of file creation |
| `acquisition_timestamp` | string | ISO-8601 timestamp of data acquisition |
| `session_id` | string | Unique session identifier |
| `backend` | string | Hardware backend |
| `circuit_id` | string | Circuit identifier |
| `n_trials` | integer | Number of trials in file |
| `n_shots_total` | integer | Total shots across all trials |

### R.9.2 Directory-Level Requirements

Each directory must have a `PROVENANCE.md` file containing:

```markdown
# Provenance Record

## Directory: {path}
## Timestamp: {ISO-8601}
## SHA-256 Hash: {hash}

### Contents:
- [ ] File 1: {name} (SHA-256: {hash})
- [ ] File 2: {name} (SHA-256: {hash})
- [ ] ...

### Verification:
```bash
sha256sum -c provenance.sha256
```

### Acquisition Details:
- Backend: {backend}
- Date: {date}
- Session ID: {session_id}
- Operator: {operator}
```

### R.9.3 Complete Archive Requirements

The complete archive must include:

1. **All raw-shot files** (uncompressed)
2. **All calibration files**
3. **All metadata files**
4. **PROVENANCE.md** at each directory level
5. **provenance.sha256** file with hashes of all files
6. **README.md** explaining the structure

---

## R.10 Example Implementation (Python)

```python
import json
import hashlib
from datetime import datetime
from typing import Dict, List

class RawShotTrial:
    """
    Represents a single trial with raw shots.
    Implements Appendix R - Raw-Shot Archival Specification.
    """
    
    # Pre-registered field requirements
    REQUIRED_FIELDS = [
        'trial_id', 'circuit_id', 'backend', 'timestamp',
        't', 'T1', 'T2', 'Phi', 'theta',
        'N_q', 'D', 'N_g', 'epsilon_g', 'epsilon_r',
        'raw_shots'
    ]
    
    def __init__(self, data: Dict):
        """
        Initialize a trial with validation.
        
        Args:
            data: Dictionary containing trial data
        """
        # Validate required fields
        for field in self.REQUIRED_FIELDS:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate field types and constraints
        self._validate(data)
        
        self.data = data
    
    def _validate(self, data: Dict) -> None:
        """Validate all fields against constraints."""
        # String fields
        assert isinstance(data['trial_id'], str), "trial_id must be string"
        assert isinstance(data['circuit_id'], str), "circuit_id must be string"
        assert isinstance(data['backend'], str), "backend must be string"
        
        # Timestamp validation
        try:
            datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("timestamp must be ISO-8601 format")
        
        # Numeric fields
        assert isinstance(data['t'], (int, float)) and data['t'] >= 0, "t must be >= 0"
        assert isinstance(data['T1'], (int, float)) and data['T1'] > 0, "T1 must be > 0"
        assert isinstance(data['T2'], (int, float)) and data['T2'] > 0, "T2 must be > 0"
        assert isinstance(data['Phi'], (int, float)) and 0 <= data['Phi'] <= 1, "Phi must be in [0,1]"
        assert isinstance(data['theta'], (int, float)) and 0 <= data['theta'] < 2*3.14159, "theta must be in [0,2π)"
        
        # Integer fields
        assert isinstance(data['N_q'], int) and data['N_q'] >= 1, "N_q must be >= 1"
        assert isinstance(data['D'], int) and data['D'] >= 0, "D must be >= 0"
        assert isinstance(data['N_g'], int) and data['N_g'] >= 0, "N_g must be >= 0"
        
        # Error rates
        assert 0 <= data['epsilon_g'] <= 1, "epsilon_g must be in [0,1]"
        assert 0 <= data['epsilon_r'] <= 1, "epsilon_r must be in [0,1]"
        
        # Raw shots validation
        assert isinstance(data['raw_shots'], list), "raw_shots must be a list"
        assert len(data['raw_shots']) > 0, "raw_shots must not be empty"
        
        for shot in data['raw_shots']:
            assert isinstance(shot, str), "Each shot must be a string"
            assert all(c in '01' for c in shot), "Shots must contain only 0 and 1"
            assert len(shot) == data['N_q'], f"Shot length must equal N_q ({data['N_q']})"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary with sorted keys for deterministic serialization."""
        return dict(sorted(self.data.items()))
    
    def to_jsonl(self) -> str:
        """Serialize to JSONL format."""
        return json.dumps(self.to_dict(), separators=(',', ':'))
    
    def compute_hash(self) -> str:
        """Compute SHA-256 hash of the trial data."""
        data_str = self.to_jsonl()
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()


class RawShotArchive:
    """
    Collection of raw shot trials with provenance.
    """
    
    def __init__(self):
        self.trials: List[RawShotTrial] = []
        self.metadata: Dict = {
            'archive_created': datetime.now().isoformat() + 'Z',
            'archive_version': '1.0',
            'specification': 'Appendix R - Raw-Shot Archival Specification'
        }
    
    def add_trial(self, trial_data: Dict) -> None:
        """Add a trial with validation."""
        trial = RawShotTrial(trial_data)
        self.trials.append(trial)
    
    def save_to_jsonl(self, filename: str) -> None:
        """Save all trials to a JSONL file."""
        with open(filename, 'w', encoding='utf-8') as f:
            for trial in self.trials:
                f.write(trial.to_jsonl() + '\n')
    
    def compute_archive_hash(self) -> str:
        """Compute SHA-256 hash of the entire archive."""
        archive_str = ''.join(trial.to_jsonl() for trial in sorted(self.trials, key=lambda t: t.data['trial_id']))
        return hashlib.sha256(archive_str.encode('utf-8')).hexdigest()
    
    def save_provenance(self, directory: str) -> None:
        """Save archive with provenance files."""
        import os
        
        # Create directory
        os.makedirs(directory, exist_ok=True)
        
        # Save trials
        trials_file = os.path.join(directory, 'raw_shots.jsonl')
        self.save_to_jsonl(trials_file)
        
        # Compute and save hashes
        archive_hash = self.compute_archive_hash()
        
        provenance = {
            'archive_hash': archive_hash,
            'file_hashes': {},
            'metadata': self.metadata,
            'n_trials': len(self.trials),
            'n_shots_total': sum(len(t.data['raw_shots']) for t in self.trials)
        }
        
        # Compute file hash
        with open(trials_file, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        provenance['file_hashes'][trials_file] = file_hash
        
        # Save provenance
        with open(os.path.join(directory, 'PROVENANCE.md'), 'w') as f:
            f.write(f"# Provenance Record\n\n")
            f.write(f"**Archive Hash:** {archive_hash}\n\n")
            f.write(f"**Created:** {self.metadata['archive_created']}\n\n")
            f.write(f"**Trials:** {len(self.trials)}\n")
            f.write(f"**Total Shots:** {provenance['n_shots_total']}\n\n")
            f.write("## Verification\n")
            f.write(f"```bash\n")
            f.write(f"sha256sum {trials_file}\n")
            f.write(f"# Should output: {file_hash}  {trials_file}\n")
            f.write(f"```\n")
        
        with open(os.path.join(directory, 'provenance.json'), 'w') as f:
            json.dump(provenance, f, indent=2)


# Example usage
if __name__ == "__main__":
    # Create archive
    archive = RawShotArchive()
    
    # Add example trials
    trial_1 = {
        'trial_id': 'trial_20261007_ibmfez_bell_001',
        'circuit_id': 'bell_2q_v1',
        'backend': 'ibm_fez',
        'timestamp': '2026-10-07T10:46:00.000000Z',
        't': 16.0,
        'T1': 45.2,
        'T2': 32.1,
        'Phi': 0.876,
        'theta': 1.123,
        'N_q': 2,
        'D': 1,
        'N_g': 2,
        'epsilon_g': 0.001,
        'epsilon_r': 0.02,
        'raw_shots': ['00', '01', '10', '11', '00', '01', '10', '11', '00', '01']
    }
    
    trial_2 = {
        'trial_id': 'trial_20261007_ibmfez_bell_002',
        'circuit_id': 'bell_2q_v1',
        'backend': 'ibm_fez',
        'timestamp': '2026-10-07T10:46:05.123456Z',
        't': 32.0,
        'T1': 45.2,
        'T2': 32.1,
        'Phi': 0.765,
        'theta': 2.246,
        'N_q': 2,
        'D': 1,
        'N_g': 2,
        'epsilon_g': 0.001,
        'epsilon_r': 0.02,
        'raw_shots': ['00', '11', '01', '10', '00', '11', '01', '10', '00', '11']
    }
    
    archive.add_trial(trial_1)
    archive.add_trial(trial_2)
    
    # Save with provenance
    archive.save_provenance('example_raw_shot_archive')
    
    print(f"Archive created with {len(archive.trials)} trials")
    print(f"Archive hash: {archive.compute_archive_hash()}")
```

---

## R.11 Validation Checklist

### R.11.1 Data Integrity
- [ ] All required fields are present in each trial
- [ ] All field values are within specified ranges
- [ ] All bitstrings have correct length (N_q)
- [ ] All bitstrings contain only '0' and '1'
- [ ] Timestamps are in ISO-8601 format
- [ ] No shots have been filtered or modified

### R.11.2 Provenance
- [ ] Each file has a valid SHA-256 hash
- [ ] Archive has a complete provenance record
- [ ] All metadata is preserved
- [ ] Session information is complete

### R.11.3 Reproducibility
- [ ] Fidelity can be recomputed from raw shots
- [ ] Φ can be recomputed from calibration data
- [ ] θ can be recomputed from t and τ₀
- [ ] All statistical tests can be reproduced

---

## R.12 Common Pitfalls and Mitigations

| Pitfall | Risk | Mitigation |
|---------|------|------------|
| Filtering shots based on fidelity | Circular analysis | Freeze shot acquisition before any analysis |
| Reconstructing shots from histograms | Loss of information | Always store raw shots |
| Mixing sessions | Contamination | Use unique session IDs |
| Not storing calibration data | Cannot recompute Φ | Store all calibration files separately |
| Using lossy compression | Data corruption | Use lossless compression or no compression |
| Modifying timestamps | Provenance violation | Use system time, not manual entry |

---

## R.13 Final Statement

This raw-shot archival specification is **pre-registered and frozen**.

**Key Principles:**
1. Raw shots are the **authoritative measurement record**
2. **No filtering, compression, or modification** is permitted
3. All derived quantities **must** be reproducible from raw shots
4. **Complete provenance** must be preserved
5. **Independent verification** must be possible

**Registration Details:**
- **Registration Date:** 2026-10-07
- **Version:** 1.0 (Frozen)
- **Identity Plane:** Q-Plane (Quantum Data)
- **Non-Substitution:** Raw shots cannot be substituted by any derived quantity

**Contact:**
- **Author:** Devin Phillip Davis
- **Email:** research@dnalang.dev
- **Affiliation:** Agile Defense Systems LLC
- **Location:** Lexington, KY, USA

---

## Appendix R.1: Quick Reference

### Minimum Trial Record
```json
{
  "trial_id": "unique_id",
  "circuit_id": "circuit_name",
  "backend": "ibm_fez",
  "timestamp": "2026-10-07T10:46:00.000000Z",
  "t": 16.0,
  "T1": 45.2,
  "T2": 32.1,
  "Phi": 0.876,
  "theta": 1.123,
  "N_q": 2,
  "D": 1,
  "N_g": 2,
  "epsilon_g": 0.001,
  "epsilon_r": 0.02,
  "raw_shots": ["00", "01", "10", "11", ...]
}
```

### Fidelity Calculation (Computational Basis)
```python
# For Bell state |Φ⁺⟩ = (|00⟩ + |11⟩)/√2
target_bitstrings = ["00", "11"]
n_star = sum(1 for shot in raw_shots if shot in target_bitstrings)
N = len(raw_shots)
F = n_star / N
```

### File Structure
```
archive/
├── raw_shots.jsonl          # All trials
├── calibration.json         # Calibration data
├── PROVENANCE.md           # Provenance record
└── provenance.json         # Machine-readable provenance
```

### Validation Command
```bash
# Verify file integrity
sha256sum -c provenance.sha256

# Validate JSONL
python3 -c "import json; [json.loads(line) for line in open('raw_shots.jsonl')]"
```

---

*This document is part of the OSIRIS τ–Φ Dynamical Theory research program. For updates and errata, see the project repository at github.com/osiris-dnalang/flywheel-2026.*
