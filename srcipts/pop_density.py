""" 
Population Density Index Calculation
重力模型：
    P(r) = exp(1 - r^2)
论文：UAV path optimization with an integrated cost assessment model considering third-party risks in metropolitan environments
"""

import numpy as np
import matplotlib.pyplot as plt

# 归一化影响半径 r ∈ [0,1]
r = np.linspace(0, 1, 200)
# 密度指数函数
y = np.exp(1 - r**2)

plt.figure(figsize=(6,4))
plt.plot(r, y, 'r-', linewidth=2)
plt.xlabel('Normalized influence radius r')
plt.ylabel('Population density index')
plt.grid(True, alpha=0.3)
plt.show()