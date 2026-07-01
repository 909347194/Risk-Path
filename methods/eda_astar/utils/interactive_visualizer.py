"""
Interactive 3D Visualization Utilities using Plotly

Provides interactive 3D visualization for path planning results, cost maps,
and algorithm comparison. Complements Matplotlib static visualizations.

Usage:
    from utils.interactive_visualizer import InteractiveVisualizer
    
    viz = InteractiveVisualizer(output_dir="output/experiment_01")
    fig = viz.plot_path_3d_interactive(path, cost_map)
    fig.show()  # Opens in browser
    fig.write_html("path_3d.html")  # Save as HTML
"""

import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class InteractiveVisualizer:
    """Interactive 3D visualization tools using Plotly."""
    
    def __init__(self, output_dir: str = "output", theme: str = "plotly_white"):
        """
        Initialize interactive visualizer.
        
        Args:
            output_dir: Directory to save HTML files
            theme: Plotly theme ('plotly_white', 'plotly_dark', 'ggplot2', etc.)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.theme = theme
    
    def plot_path_3d_interactive(
        self,
        path: List[Tuple[int, int, int]],
        cost_map: Optional[np.ndarray] = None,
        title: str = "3D Path Visualization (Interactive)",
        show_cost_map: bool = False,
        opacity: float = 0.3
    ) -> go.Figure:
        """
        Create interactive 3D path visualization.
        
        Args:
            path: List of (layer, row, col) tuples
            cost_map: Optional 3D cost array for background
            title: Plot title
            show_cost_map: Whether to show cost map as volume
            opacity: Opacity for cost map volume
            
        Returns:
            Plotly Figure object
        """
        if not path:
            raise ValueError("Path is empty")
        
        fig = go.Figure()
        
        # Extract coordinates
        layers = np.array([p[0] for p in path])
        rows = np.array([p[1] for p in path])
        cols = np.array([p[2] for p in path])
        
        # Add path line
        fig.add_trace(go.Scatter3d(
            x=cols,
            y=rows,
            z=layers,
            mode='lines+markers',
            name='Path',
            line=dict(color='blue', width=4),
            marker=dict(size=5, color='blue', symbol='circle')
        ))
        
        # Mark start and goal
        fig.add_trace(go.Scatter3d(
            x=[cols[0]],
            y=[rows[0]],
            z=[layers[0]],
            mode='markers',
            name='Start',
            marker=dict(size=12, color='green', symbol='triangle-up')
        ))
        
        fig.add_trace(go.Scatter3d(
            x=[cols[-1]],
            y=[rows[-1]],
            z=[layers[-1]],
            mode='markers',
            name='Goal',
            marker=dict(size=12, color='red', symbol='star')
        ))
        
        # Optional: Show cost map as volume
        if show_cost_map and cost_map is not None:
            # Downsample for performance if needed
            if cost_map.shape[0] > 10:
                step = max(1, cost_map.shape[0] // 10)
                cost_map_sampled = cost_map[::step, ::step, ::step]
            else:
                cost_map_sampled = cost_map
            
            # Normalize cost map for visualization
            cost_normalized = (cost_map_sampled - cost_map_sampled.min()) / \
                            (cost_map_sampled.max() - cost_map_sampled.min() + 1e-10)
            
            # Create meshgrid for volume
            z_vals, y_vals, x_vals = np.mgrid[
                0:cost_map_sampled.shape[0],
                0:cost_map_sampled.shape[1],
                0:cost_map_sampled.shape[2]
            ]
            
            fig.add_trace(go.Volume(
                x=x_vals.flatten(),
                y=y_vals.flatten(),
                z=z_vals.flatten(),
                value=cost_normalized.flatten(),
                isomin=0.2,
                isomax=0.8,
                opacity=opacity,
                surface_count=15,
                colorscale='Hot',
                name='Cost Map',
                showscale=True
            ))
        
        # Update layout
        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title='Column',
                yaxis_title='Row',
                zaxis_title='Layer (Altitude)',
                aspectmode='auto'
            ),
            template=self.theme,
            legend=dict(x=0.01, y=0.99),
            margin=dict(l=0, r=0, b=0, t=40)
        )
        
        return fig
    
    def plot_multiple_paths_interactive(
        self,
        paths_dict: Dict[str, List[Tuple[int, int, int]]],
        title: str = "Algorithm Comparison (Interactive)",
        colors: Optional[List[str]] = None
    ) -> go.Figure:
        """
        Plot multiple paths from different algorithms for comparison.
        
        Args:
            paths_dict: Dictionary mapping algorithm names to paths
            title: Plot title
            colors: Optional list of colors for each path
            
        Returns:
            Plotly Figure object
        """
        if not paths_dict:
            raise ValueError("No paths provided")
        
        fig = go.Figure()
        
        # Default colors if not provided
        if colors is None:
            colors = ['blue', 'red', 'green', 'orange', 'purple', 'cyan']
        
        for idx, (algo_name, path) in enumerate(paths_dict.items()):
            if not path:
                continue
            
            layers = np.array([p[0] for p in path])
            rows = np.array([p[1] for p in path])
            cols = np.array([p[2] for p in path])
            
            color = colors[idx % len(colors)]
            
            fig.add_trace(go.Scatter3d(
                x=cols,
                y=rows,
                z=layers,
                mode='lines',
                name=algo_name,
                line=dict(color=color, width=3),
                opacity=0.8
            ))
        
        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title='Column',
                yaxis_title='Row',
                zaxis_title='Layer (Altitude)'
            ),
            template=self.theme,
            legend=dict(x=0.01, y=0.99),
            margin=dict(l=0, r=0, b=0, t=40)
        )
        
        return fig
    
    def plot_cost_map_3d_interactive(
        self,
        cost_map: np.ndarray,
        layer_index: Optional[int] = None,
        title: str = "3D Cost Map Visualization",
        colorscale: str = 'Hot'
    ) -> go.Figure:
        """
        Create interactive 3D visualization of cost map.
        
        Args:
            cost_map: 3D cost array (layers, rows, cols)
            layer_index: Specific layer to highlight (None for all)
            title: Plot title
            colorscale: Plotly colorscale name
            
        Returns:
            Plotly Figure object
        """
        # Normalize cost map
        cost_normalized = (cost_map - cost_map.min()) / \
                        (cost_map.max() - cost_map.min() + 1e-10)
        
        # Create meshgrid
        z_vals, y_vals, x_vals = np.mgrid[
            0:cost_map.shape[0],
            0:cost_map.shape[1],
            0:cost_map.shape[2]
        ]
        
        fig = go.Figure(data=go.Volume(
            x=x_vals.flatten(),
            y=y_vals.flatten(),
            z=z_vals.flatten(),
            value=cost_normalized.flatten(),
            isomin=0.2,
            isomax=0.8,
            opacity=0.3,
            surface_count=20,
            colorscale=colorscale,
            colorbar=dict(title='Normalized Cost')
        ))
        
        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title='Column',
                yaxis_title='Row',
                zaxis_title='Layer'
            ),
            template=self.theme,
            margin=dict(l=0, r=0, b=0, t=40)
        )
        
        return fig
    
    def plot_eda_convergence_interactive(
        self,
        convergence_history: List[Dict],
        title: str = "EDA Convergence History (Interactive)"
    ) -> go.Figure:
        """
        Create interactive plot of EDA convergence history.
        
        Args:
            convergence_history: List of dicts with generation metrics
            title: Plot title
            
        Returns:
            Plotly Figure object
        """
        if not convergence_history:
            raise ValueError("No convergence history provided")
        
        generations = [h['generation'] for h in convergence_history]
        best_fitness = [h['best_fitness'] for h in convergence_history]
        avg_fitness = [h.get('avg_fitness', None) for h in convergence_history]
        
        fig = go.Figure()
        
        # Best fitness
        fig.add_trace(go.Scatter(
            x=generations,
            y=best_fitness,
            mode='lines+markers',
            name='Best Fitness',
            line=dict(color='blue', width=2),
            marker=dict(size=6)
        ))
        
        # Average fitness (if available)
        if any(f is not None for f in avg_fitness):
            fig.add_trace(go.Scatter(
                x=generations,
                y=avg_fitness,
                mode='lines',
                name='Average Fitness',
                line=dict(color='red', width=2, dash='dash')
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title='Generation',
            yaxis_title='Fitness (Cost)',
            template=self.theme,
            hovermode='x unified',
            showlegend=True
        )
        
        return fig
    
    def save_figure(self, fig: go.Figure, filename: str):
        """
        Save Plotly figure to HTML file.
        
        Args:
            fig: Plotly Figure object
            filename: Output filename (will add .html extension)
        """
        if not filename.endswith('.html'):
            filename += '.html'
        
        output_path = self.output_dir / filename
        fig.write_html(str(output_path))
        print(f"  ✓ Saved interactive plot: {output_path}")
    
    def create_dashboard(
        self,
        path: List[Tuple[int, int, int]],
        cost_map: np.ndarray,
        convergence_history: Optional[List[Dict]] = None,
        title: str = "Complete Experiment Dashboard"
    ) -> go.Figure:
        """
        Create comprehensive dashboard with multiple subplots.
        
        Args:
            path: Path coordinates
            cost_map: 3D cost array
            convergence_history: Optional EDA convergence data
            title: Dashboard title
            
        Returns:
            Plotly Figure with subplots
        """
        # Determine number of subplots
        n_plots = 2 if convergence_history else 1
        
        fig = make_subplots(
            rows=1, cols=n_plots,
            specs=[[{'type': 'scene'}, {'type': 'xy'}]] if n_plots == 2 else [[{'type': 'scene'}]],
            subplot_titles=['3D Path', 'Convergence'] if n_plots == 2 else ['3D Path']
        )
        
        # Add 3D path plot
        layers = np.array([p[0] for p in path])
        rows = np.array([p[1] for p in path])
        cols = np.array([p[2] for p in path])
        
        fig.add_trace(go.Scatter3d(
            x=cols, y=rows, z=layers,
            mode='lines+markers',
            name='Path',
            line=dict(color='blue', width=3),
            marker=dict(size=4)
        ), row=1, col=1)
        
        # Add convergence plot if available
        if convergence_history and n_plots == 2:
            generations = [h['generation'] for h in convergence_history]
            best_fitness = [h['best_fitness'] for h in convergence_history]
            
            fig.add_trace(go.Scatter(
                x=generations,
                y=best_fitness,
                mode='lines+markers',
                name='Best Fitness',
                line=dict(color='red', width=2)
            ), row=1, col=2)
        
        fig.update_layout(
            title=title,
            template=self.theme,
            height=600,
            showlegend=False
        )
        
        return fig


# Convenience function for quick use
def quick_plot_path_3d(
    path: List[Tuple[int, int, int]],
    title: str = "3D Path",
    output_file: Optional[str] = None
) -> go.Figure:
    """
    Quick one-liner to create and optionally save 3D path plot.
    
    Args:
        path: List of (layer, row, col) tuples
        title: Plot title
        output_file: Optional filename to save HTML
        
    Returns:
        Plotly Figure object
    """
    viz = InteractiveVisualizer()
    fig = viz.plot_path_3d_interactive(path, title=title)
    
    if output_file:
        viz.save_figure(fig, output_file)
    
    return fig
