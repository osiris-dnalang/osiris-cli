from qiskit_ibm_runtime import QiskitRuntimeService
import networkx as nx

s = QiskitRuntimeService()
b = s.backend('ibm_fez')
g = nx.Graph()
for u, v in b.coupling_map:
    g.add_edge(u, v)

cycles = nx.cycle_basis(g)
hex_cycles = [c for c in cycles if len(c) == 6]
print(f"Total 6-cycles on ibm_fez: {len(hex_cycles)}")
for i, c in enumerate(hex_cycles[:5]):
    print(f"Cycle {i+1}: {c}")
