import numpy as np

a = "2.342 2.112 1.234"
b = "Unknown"

a = np.array(a.split(), dtype=float)
print a[1]