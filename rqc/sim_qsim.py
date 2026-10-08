"""Ideal output probabilities with qsim (Google's C++ statevector simulator, via qsimcirq): an optional fast path for
circuits larger than rqc.sim handles comfortably (about 20+ qubits). Same index convention as rqc.sim: qubit 0 is
the most significant bit. rqc.sim stays the reference used by the frozen S2 code; this module is used only when
called explicitly."""
import numpy as np


def probabilities(circuit, threads=None):
    import cirq
    import qsimcirq
    from .circuits import to_cirq
    qubits = cirq.LineQubit.range(circuit.n)
    c = to_cirq(circuit, qubits)[:-1]                            # drop the measurement moment
    opts = qsimcirq.QSimOptions(cpu_threads=threads) if threads else qsimcirq.QSimOptions()
    sv = qsimcirq.QSimSimulator(qsim_options=opts).simulate(c, qubit_order=qubits).final_state_vector
    p = np.abs(np.asarray(sv, dtype=np.complex128)) ** 2
    return p / p.sum()
