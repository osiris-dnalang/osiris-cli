import numpy as np
from scipy.optimize import curve_fit
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, Operator

# True underlying ZZ interaction on the coupler: zeta = 120 kHz
zeta_true = 2 * np.pi * 120e3  # 120 kHz in rad/s
f_det = 500e3  # 500 kHz artificial detuning

taus = np.linspace(0.0, 2.0e-6, 16) # 16 time points up to 2.0 us

def get_U_zz(tau):
    return Operator(np.diag([
        np.exp(-1j * zeta_true * tau),
        np.exp(+1j * zeta_true * tau),
        np.exp(+1j * zeta_true * tau),
        np.exp(-1j * zeta_true * tau)
    ]))

# Simulation: Ramsey on Q0 conditioned on Q1 state
p0_ctrl0 = []
p0_ctrl1 = []

for t in taus:
    # Circuit A: Q1 in |0>
    qc_A = QuantumCircuit(2)
    qc_A.h(0)
    qc_A.unitary(get_U_zz(t), [0, 1], label="ZZ")
    qc_A.rz(2 * np.pi * f_det * t, 0) # artificial phase advance
    qc_A.h(0)
    sv_A = Statevector.from_instruction(qc_A)
    p0_A = sv_A.probabilities_dict().get('00', 0) + sv_A.probabilities_dict().get('01', 0)
    p0_ctrl0.append(p0_A)

    # Circuit B: Q1 in |1>
    qc_B = QuantumCircuit(2)
    qc_B.x(1) # Flip Q1
    qc_B.h(0)
    qc_B.unitary(get_U_zz(t), [0, 1], label="ZZ")
    qc_B.rz(2 * np.pi * f_det * t, 0)
    qc_B.h(0)
    sv_B = Statevector.from_instruction(qc_B)
    p0_B = sv_B.probabilities_dict().get('00', 0) + sv_B.probabilities_dict().get('01', 0)
    p0_ctrl1.append(p0_B)

# Fit cosine curves to extract frequencies
def cos_fit(t, A, f, phi, C):
    return A * np.cos(2 * np.pi * f * t + phi) + C

popt_0, _ = curve_fit(cos_fit, taus, p0_ctrl0, p0=[0.5, f_det, 0, 0.5])
popt_1, _ = curve_fit(cos_fit, taus, p0_ctrl1, p0=[0.5, f_det, 0, 0.5])

f_0 = abs(popt_0[1])
f_1 = abs(popt_1[1])
zeta_fit_kHz = abs(f_1 - f_0) / 2.0 / 1e3

print(f"True ZZ coupling: {zeta_true / (2*np.pi*1e3):.2f} kHz")
print(f"Measured f(Q1=0): {f_0/1e3:.2f} kHz")
print(f"Measured f(Q1=1): {f_1/1e3:.2f} kHz")
print(f"Extracted ZZ coupling zeta: {zeta_fit_kHz:.2f} kHz")
print(f"Delta* = pi / (2 * zeta) = {np.pi / (2 * (zeta_fit_kHz * 1e3 * 2 * np.pi)) * 1e9:.2f} ns")
