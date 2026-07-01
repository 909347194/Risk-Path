"""
Comparison Visualization Utilities

Provides tools for comparing multiple algorithms and generating comparative plots.
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
import seaborn as sns


class ComparisonVisualizer:
    """Visualization tools for algorithm comparison experiments."""
    
    def __init__(self, output_dir: str = "output", dpi: int = 300):
        """
        Initialize comparison visualizer.
        
        Args:
            output_dir: Directory to save visualizations
            dpi: Resolution for saved figures
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = dpi
        
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.dpi'] = dpi
        plt.rcParams['savefig.dpi'] = dpi
    
    def plot_path_comparison(self, paths_dict, costs_dict, title="Algorithm Path Comparison"):
        """
        Plot multiple algorithm paths on the same 3D plot for comparison.
        
        Args:
            paths_dict: Dict mapping algorithm names to paths
            costs_dict: Dict mapping algorithm names to costs
            title: Plot title
        """
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        colors = ['blue', 'red', 'green', 'orange', 'purple']
        markers = ['o', 's', '^', 'D', 'v']
        
        for idx, (algo_name, path) in enumerate(paths_dict.items()):
            if not path:
                continue
            
            color = colors[idx % len(colors)]
            marker = markers[idx % len(markers)]
            
            layers = [p[0] for p in path]
            rows = [p[1] for p in path]
            cols = [p[2] for p in path]
            
            cost = costs_dict.get(algo_name, 0)
            label = f"{algo_name} (Cost: {cost:.2f})"
            
            ax.plot(cols, rows, layers, color=color, marker=marker, 
                   markersize=3, linewidth=1.5, label=label, alpha=0.7)
        
        ax.set_xlabel('Column')
        ax.set_ylabel('Row')
        ax.set_zlabel('Layer (Altitude)')
        ax.set_title(title)
        ax.legend(loc='best')
        
        plt.tight_layout()
        save_path = self.output_dir / "path_comparison.png"
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ Saved: {save_path}")
    
    def plot_performance_comparison(self, results_dict, metrics=['cost', 'time', 'waypoints']):
        """
        Plot bar charts comparing algorithm performance across multiple metrics.
        
        Args:
            results_dict: Dict mapping algorithm names to result dicts
            metrics: List of metrics to compare ('cost', 'time', 'waypoints')
        """
        algo_names = list(results_dict.keys())
        n_metrics = len(metrics)
        
        fig, axes = plt.subplots(1, n_metrics, figsize=(5*n_metrics, 5))
        
        if n_metrics == 1:
            axes = [axes]
        
        colors = ['#2196F3', '#F44336', '#4CAF50', '#FF9800']
        
        for idx, metric in enumerate(metrics):
            values = [results_dict[algo][metric] for algo in algo_names]
            
            bars = axes[idx].bar(range(len(algo_names)), values, color=colors[:len(algo_names)])
            axes[idx].set_xticks(range(len(algo_names)))
            axes[idx].set_xticklabels(algo_names, rotation=45, ha='right')
            axes[idx].set_title(f'{metric.upper()} Comparison')
            axes[idx].grid(axis='y', alpha=0.3)
            
            # Add value labels on bars
            for bar, value in zip(bars, values):
                height = bar.get_height()
                axes[idx].text(bar.get_x() + bar.get_width()/2., height,
                             f'{value:.2f}',
                             ha='center', va='bottom', fontsize=9)
        
        plt.suptitle('Algorithm Performance Comparison', fontsize=14, y=1.02)
        plt.tight_layout()
        
        save_path = self.output_dir / "performance_comparison.png"
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ Saved: {save_path}")
