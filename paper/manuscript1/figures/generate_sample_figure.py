"""
Generate sample figure - results_visualization.pdf
Demo script for inserting figures in LaTeX papers

Usage:
cd paper/manuscript1/figures
python generate_sample_figure.py
"""

import matplotlib.pyplot as plt
import numpy as np

# Create data
methods = ['Baseline 1', 'Baseline 2', 'Ours']
accuracy = [85.2, 87.5, 92.3]
f1_score = [84.2, 86.5, 91.5]

x = np.arange(len(methods))
width = 0.35

# Create figure
fig, ax = plt.subplots(figsize=(8, 5))

bars1 = ax.bar(x - width/2, accuracy, width, label='Accuracy', color='#2196F3')
bars2 = ax.bar(x + width/2, f1_score, width, label='F1-Score', color='#4CAF50')

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=9)

# Set labels and title
ax.set_ylabel('Score (%)', fontsize=12)
ax.set_title('Performance Comparison', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(methods)
ax.legend(loc='lower right')
ax.set_ylim(0, 100)
ax.grid(axis='y', alpha=0.3, linestyle='--')

# Save
plt.tight_layout()
plt.savefig('results_visualization.pdf', format='pdf', bbox_inches='tight', dpi=300)
print("Sample figure generated: results_visualization.pdf")

# Also save PNG version
plt.savefig('results_visualization.png', format='png', bbox_inches='tight', dpi=300)
print("PNG version generated: results_visualization.png")

plt.show()
