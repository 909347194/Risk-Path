# 组装/归一化 各项成本，输出最终的Cost_total Tensor;数据出口；

"""
Tensor Builder for Spatiotemporal Heterogeneity Model

Assembles and normalizes various cost components to produce the final
Cost_total 4D tensor. This module serves as the data export interface.

Uses GridSystem for consistent dimensional management across all modules.
"""

import numpy as np
from typing import Dict, Optional
from .grid_system import GridSystem


class TensorBuilder:
    """
    Builds and combines multiple risk/cost tensors into a unified cost field.
    
    Components may include:
    - P_crash (dynamic crash probability)
    - Population density (spatiotemporal)
    - Noise sensitivity (landuse × time)
    - Property damage risk
    - Obstacle avoidance cost
    """
    
    def __init__(self, grid: Optional[GridSystem] = None):
        """
        Initialize tensor builder with grid system.
        
        Args:
            grid: GridSystem instance defining dimensions. Uses default if None.
        """
        self.grid = grid or GridSystem()
        self.components: Dict[str, np.ndarray] = {}
        self.weights: Dict[str, float] = {}
    
    def add_component(self, name: str, tensor: np.ndarray, weight: float = 1.0):
        """
        Add a cost component with optional weight.
        
        Args:
            name: Component identifier
            tensor: 4D numpy array matching grid shape
            weight: Weight for this component in final cost
        """
        if tensor.shape != self.grid.shape:
            raise ValueError(
                f"Tensor shape {tensor.shape} does not match grid shape {self.grid.shape}"
            )
        
        self.components[name] = tensor
        self.weights[name] = weight
    
    def normalize_component(self, name: str, method: str = 'minmax') -> np.ndarray:
        """
        Normalize a component tensor.
        
        Args:
            name: Component identifier
            method: Normalization method ('minmax', 'zscore', 'log')
            
        Returns:
            Normalized tensor
        """
        if name not in self.components:
            raise KeyError(f"Component '{name}' not found")
        
        tensor = self.components[name].copy()
        
        if method == 'minmax':
            min_val = np.min(tensor)
            max_val = np.max(tensor)
            if max_val > min_val:
                tensor = (tensor - min_val) / (max_val - min_val)
            else:
                tensor = np.zeros_like(tensor)
        
        elif method == 'zscore':
            mean = np.mean(tensor)
            std = np.std(tensor)
            if std > 0:
                tensor = (tensor - mean) / std
            else:
                tensor = np.zeros_like(tensor)
        
        elif method == 'log':
            tensor = np.log1p(tensor)
            max_val = np.max(tensor)
            if max_val > 0:
                tensor = tensor / max_val
        
        self.components[name] = tensor
        return tensor
    
    def build_total_cost(self, normalize: bool = True) -> np.ndarray:
        """
        Build the total cost tensor by combining all components.
        
        Cost_total = Σ (weight_i × component_i)
        
        Args:
            normalize: Whether to normalize the final result to [0, 1]
            
        Returns:
            4D total cost tensor
        """
        if not self.components:
            raise ValueError("No components added. Use add_component() first.")
        
        # Initialize with zeros
        total_cost = np.zeros(self.grid.shape, dtype=np.float64)
        
        # Weighted sum
        for name, tensor in self.components.items():
            weight = self.weights.get(name, 1.0)
            total_cost += weight * tensor
        
        # Normalize if requested
        if normalize:
            min_val = np.min(total_cost)
            max_val = np.max(total_cost)
            if max_val > min_val:
                total_cost = (total_cost - min_val) / (max_val - min_val)
            else:
                total_cost = np.zeros_like(total_cost)
        
        return total_cost.astype(np.float32)
    
    def reset(self):
        """Clear all components and weights."""
        self.components.clear()
        self.weights.clear()
    
    def get_component_summary(self) -> str:
        """Generate summary of current components."""
        if not self.components:
            return "No components added."
        
        lines = [
            "=" * 60,
            "Tensor Components Summary",
            "=" * 60,
        ]
        
        for name, tensor in self.components.items():
            weight = self.weights.get(name, 1.0)
            lines.append(f"{name:20s} | Weight: {weight:6.2f} | "
                        f"Range: [{np.min(tensor):.4f}, {np.max(tensor):.4f}] | "
                        f"Mean: {np.mean(tensor):.4f}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


if __name__ == "__main__":
    # Test tensor builder
    print("Testing Tensor Builder")
    print("=" * 60)
    
    # Create grid and builder
    from .grid_system import get_macro_grid
    grid = get_macro_grid()
    builder = TensorBuilder(grid)
    
    # Add sample components
    print("\nAdding sample components...")
    
    # Component 1: Crash probability (random for testing)
    p_crash = np.random.rand(*grid.shape).astype(np.float32) * 0.01
    builder.add_component('p_crash', p_crash, weight=2.0)
    
    # Component 2: Population density
    population = np.random.rand(*grid.shape).astype(np.float32) * 100
    builder.add_component('population', population, weight=1.5)
    
    # Component 3: Noise sensitivity
    noise = np.random.rand(*grid.shape).astype(np.float32)
    builder.add_component('noise', noise, weight=1.0)
    
    # Print summary
    print(builder.get_component_summary())
    
    # Normalize one component
    print("\nNormalizing 'population' component...")
    builder.normalize_component('population', method='minmax')
    
    # Build total cost
    print("\nBuilding total cost tensor...")
    total_cost = builder.build_total_cost(normalize=True)
    
    print(f"Total cost shape: {total_cost.shape}")
    print(f"Total cost range: [{np.min(total_cost):.4f}, {np.max(total_cost):.4f}]")
    print(f"Total cost mean: {np.mean(total_cost):.4f}")
    print(f"Memory usage: {total_cost.nbytes / (1024**2):.2f} MB")