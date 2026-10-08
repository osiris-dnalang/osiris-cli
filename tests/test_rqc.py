"""rqc (S0): exact simulation, honest XEB estimators, fair arms, write-ahead ledger; and the old fake-XEB path
recording jobs as not executed."""
import json
import warnings

import numpy as np
import pytest

from rqc import Ledger, collision_probability, linear_xeb, normalized_xeb, perturbed, probabilities, random_circuit
from rqc.circuits import Circuit
from rqc.experiment import run_adaptive, run_random
from rqc.sim import _u, statevector


def depolarizing_sampler(eps, seed=0):
    rng = np.random.default_rng(seed)

    def sample(circuit, shots):
        p = probabilities(circuit)
        q = (1 - eps) * p + eps / len(p)
        return rng.choice(len(p), size=shots, p=q)
    return sample


def _dense_reference(circuit):
    """Full 2^n unitary by Kronecker products: an independent check of the tensordot simulator."""
    n = circuit.n
    U = np.eye(2 ** n, dtype=complex)
    for layer, gates in enumerate(circuit.angles):
        L = np.array([[1]], dtype=complex)
        for theta, phi, lam in gates:
            L = np.kron(L, _u(theta, phi, lam))
        U = L @ U
        for a, b in circuit.cz_pairs(layer):
            d = np.ones(2 ** n)
            for i in range(2 ** n):
                if (i >> (n - 1 - a)) & 1 and (i >> (n - 1 - b)) & 1:
                    d[i] = -1
            U = np.diag(d) @ U
    psi0 = np.zeros(2 ** n); psi0[0] = 1
    return U @ psi0


def test_simulator_matches_dense_unitary():
    for seed in range(3):
        c = random_circuit(4, 5, seed)
        assert np.allclose(statevector(c), _dense_reference(c), atol=1e-10)
    assert abs(probabilities(random_circuit(6, 4, 9)).sum() - 1) < 1e-12


def test_arms_share_structure_and_two_qubit_count():
    a, b = random_circuit(8, 6, 1), random_circuit(8, 6, 2)
    c = perturbed(a, 0.3, 7)
    assert a.structure() == b.structure() == c.structure()
    assert a.two_qubit_gates == c.two_qubit_gates == 3 * 4 + 3 * 3      # 6 layers alternating 4 and 3 pairs on 8 qubits
    assert a.digest() != c.digest()


def test_normalized_xeb_recovers_fidelity_under_depolarizing_noise():
    c = random_circuit(6, 8, 3)
    for eps in (0.0, 0.3, 0.7):
        f = normalized_xeb(probabilities(c), depolarizing_sampler(eps, seed=11)(c, 200_000))
        assert abs(f - (1 - eps)) < 0.03, (eps, f)


def test_concentrated_circuits_inflate_plain_xeb_but_not_normalized():
    c = Circuit(6, 2, tuple(tuple((0.05, 0.0, 0.0) for _ in range(6)) for _ in range(2)))   # output near |000000>
    p = probabilities(c)
    assert collision_probability(p) > 0.9
    samples = depolarizing_sampler(0.5, seed=5)(c, 100_000)
    assert linear_xeb(p, samples) > 20                    # "fidelity" far above 1: the circuit, not the device
    assert abs(normalized_xeb(p, samples) - 0.5) < 0.05


def test_uniform_ideal_distribution_is_refused():
    c = Circuit(2, 1, (((np.pi / 2, 0.0, 0.0), (np.pi / 2, 0.0, 0.0)),))   # H-like on both, no CZ: uniform output
    with pytest.raises(ValueError, match="undefined"):
        normalized_xeb(probabilities(c), [0, 1, 2, 3])


def test_ledger_row_is_written_before_each_sampler_call(tmp_path):
    led = Ledger(str(tmp_path / "rqc.jsonl"))
    inner = depolarizing_sampler(0.2)

    def checking_sampler(circuit, shots):
        last = json.loads(open(led.path).read().splitlines()[-1])
        assert last["kind"] == "RQC_SUBMIT" and last["payload"]["circuit_sha256"] == circuit.digest()
        return inner(circuit, shots)

    run_random(5, 4, 3, 1000, checking_sampler, led, seed=1)
    run_adaptive(5, 4, 3, 1000, checking_sampler, led, seed=1)
    assert led.verify() == (True, "ok")
    lines = open(led.path).read().splitlines()
    row = json.loads(lines[1]); row["payload"]["shots"] = 1; lines[1] = json.dumps(row)
    open(led.path, "w").write("\n".join(lines) + "\n")
    assert not led.verify()[0]


def test_arms_spend_equal_shots_and_calls(tmp_path):
    led = Ledger(str(tmp_path / "l.jsonl"))
    rnd = run_random(5, 4, 4, 500, depolarizing_sampler(0.3), led, seed=2)
    ada = run_adaptive(5, 4, 4, 500, depolarizing_sampler(0.3), led, seed=2)
    assert len(rnd) == len(ada) == 5 and sum(r["shots"] for r in rnd) == sum(r["shots"] for r in ada) == 2500
    for arm in (rnd, ada):
        final = arm[-1]
        assert final["round"] == "final" and final["selected_round"] in range(4)
        chosen = arm[final["selected_round"]]
        assert final["circuit_sha256"] == chosen["circuit_sha256"]                    # same circuit, fresh shots
        assert chosen["xeb_normalized"] == max(r["xeb_normalized"] for r in arm[:-1])
    for r in rnd + ada:
        assert {"xeb_normalized", "xeb_linear", "collision_probability", "circuit_sha256"} <= set(r)


def test_qiskit_circuit_matches_the_simulator():
    pytest.importorskip("qiskit")
    from qiskit.quantum_info import Statevector
    from rqc.circuits import to_qiskit
    c = random_circuit(4, 3, 4)
    qc = to_qiskit(c).remove_final_measurements(inplace=False)
    pq = Statevector(qc).probabilities_dict()
    p = probabilities(c)
    for key, val in pq.items():                         # qiskit keys are 'q3 q2 q1 q0'
        assert abs(p[int(key[::-1], 2)] - val) < 1e-9


def test_old_execution_path_no_longer_fabricates_xeb():
    from osiris_ibm_execution import ExecutionStage, IBMExecutionManager
    m = IBMExecutionManager.__new__(IBMExecutionManager)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        job = IBMExecutionManager._submit_job(m, "h", ExecutionStage.STAGE1_BASELINE, "ibm_x", 8, 6, 2000, "t")
    assert job.status == "not_executed" and job.result_xeb is None and job.job_id.startswith("NOT_EXECUTED_")
    assert any("no hardware path" in str(x.message) for x in w)


def test_counts_to_indices_puts_qubit_zero_first():
    from rqc.samplers import counts_to_indices
    # Qiskit key '01' means q1 = 0, q0 = 1; here qubit 0 is the most significant bit, so index 0b10 = 2
    assert list(counts_to_indices({"01": 3, "10": 1})) == [2, 2, 2, 1]
