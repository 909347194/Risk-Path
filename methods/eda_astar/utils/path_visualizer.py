"""
Path Visualization Utilities

Provides tools for visualizing 3D paths, cost maps, and EDA convergence.
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
import seaborn as sns


class PathVisualizer:
    """Visualization tools for single algorithm experiments."""
    
    def __init__(self, output_dir: str = "output", dpi: int = 300):
        """
        Initialize visualizer.
        
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
    
    def plot_path_3d(self, path, cost_map, title="3D Path Visualization"):
        """
        Plot 3D path on cost map background.
        
        Args:
            path: List of (layer, row, col) tuples
            cost_map: 3D numpy array (layers, rows, cols)
            title: Plot title
        """
        if not path:
            print("  ⚠ No path to visualize")
            return
        
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # Extract path coordinates
        layers = [p[0] for p in path]
        rows = [p[1] for p in path]
        cols = [p[2] for p in path]
        
        # Plot path
        ax.plot(cols, rows, layers, 'b-o', markersize=4, linewidth=2, label='Path')
        
        # Mark start and goal
        ax.scatter([cols[0]], [rows[0]], [layers[0]], c='green', s=200, marker='^', label='Start')
        ax.scatter([cols[-1]], [rows[-1]], [layers[-1]], c='red', s=200, marker='*', label='Goal')
        
        ax.set_xlabel('Column')
        ax.set_ylabel('Row')
        ax.set_zlabel('Layer (Altitude)')
        ax.set_title(title)
        ax.legend()
        
        plt.tight_layout()
        save_path = self.output_dir / "path_3d.png"
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ Saved: {save_path}")
    
    def plot_cost_map_slices(self, cost_map, slice_indices=None):
        """
        Plot horizontal slices of the 3D cost map.
        
        Args:
            cost_map: 3D numpy array (layers, rows, cols)
            slice_indices: List of layer indices to plot (default: all)
        """
        if slice_indices is None:
            slice_indices = list(range(cost_map.shape[0]))
        
        n_slices = len(slice_indices)
        fig, axes = plt.subplots(1, n_slices, figsize=(4*n_slices, 4))
        
        if n_slices == 1:
            axes = [axes]
        
        for idx, layer_idx in enumerate(slice_indices):
            im = axes[idx].imshow(cost_map[layer_idx], cmap='hot', interpolation='nearest')
            axes[idx].set_title(f'Layer {layer_idx}')
            axes[idx].axis('off')
            plt.colorbar(im, ax=axes[idx])
        
        plt.suptitle('Cost Map Slices by Altitude', fontsize=14, y=1.02)
        plt.tight_layout()
        
        save_path = self.output_dir / "cost_map_slices.png"
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ Saved: {save_path}")
    
    def plot_eda_convergence(self, convergence_history):
        """
        Plot EDA convergence history.
        
        Args:
            convergence_history: List of dicts with 'generation', 'best_fitness', etc.
        """
        if not convergence_history:
            print("  ⚠ No convergence history to plot")
            return
        
        generations = [h['generation'] for h in convergence_history]
        best_fitness = [h['best_fitness'] for h in convergence_history]
        avg_fitness = [h.get('avg_fitness', 0) for h in convergence_history]
        
        plt.figure(figsize=(10, 6))
        plt.plot(generations, best_fitness, 'b-o', label='Best Fitness', markersize=4)
        if any(avg_fitness):
            plt.plot(generations, avg_fitness, 'r--', label='Average Fitness')
        
        plt.xlabel('Generation')
        plt.ylabel('Fitness (Cost)')
        plt.title('EDA Convergence History')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        save_path = self.output_dir / "eda_convergence.png"
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ Saved: {save_path}")
    
    def plot_clustering_results(self, open_points, centroids, labels):
        """
        Plot K-means clustering results.
        
        Args:
            open_points: List of (layer, row, col) tuples
            centroids: List of centroid coordinates
            labels: Cluster labels for each point
        """
        if not open_points or not centroids:
            print("  ⚠ No clustering data to plot")
            return
        
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        points = np.array(open_points)
        centroids_arr = np.array(centroids)
        
        # Scatter plot with cluster colors
        scatter = ax.scatter(points[:, 2], points[:, 1], points[:, 0], 
                           c=labels, cmap='viridis', alpha=0.6, s=20)
        
        # Plot centroids
        ax.scatter(centroids_arr[:, 2], centroids_arr[:, 1], centroids_arr[:, 0],
                  c='red', marker='*', s=300, edgecolors='black', linewidths=2, label='Centroids')
        
        ax.set_xlabel('Column')
        ax.set_ylabel('Row')
        ax.set_zlabel('Layer')
        ax.set_title('K-means Clustering Results')
        ax.legend()
        
        plt.colorbar(scatter, label='Cluster')
        plt.tight_layout()
        
        save_path = self.output_dir / "clustering_results.png"
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ Saved: {save_path}")
