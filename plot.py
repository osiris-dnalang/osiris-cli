import json
import numpy as np
import matplotlib.pyplot as plt

with open("analysis.json") as f:
    data = json.load(f)

depths = sorted(int(k) for k in data.keys())
matrix = []

for d in depths:
    matrix.append(data[str(d)]["mean"])

matrix = np.array(matrix)

plt.imshow(matrix, aspect='auto')
plt.colorbar(label="Correlation C_0k")
plt.xlabel("Distance k")
plt.ylabel("Depth d")
plt.title("Light-Cone Correlation Map")

plt.savefig("lightcone.png")
plt.show()