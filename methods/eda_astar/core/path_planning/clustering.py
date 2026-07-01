"""
K-means Clustering Module for EDA-CostA* Algorithm

Implements K-means clustering to identify cluster centroids from open points
as required by Algorithm 2, Line 8 of Pang et al. (2022).

These centroids are used to compute:
- h_Drctn (Eq. 25): Local heuristic direction
- h_Dist (Eq. 24): Global heuristic distance factor
"""

from __future__ import annotations

import numpy as np
from typing import List, Tuple, Optional


class KMeansClusterer:
    """
    K-means clustering for airspace unit positions.
    
    Used in EDA-CostA* Algorithm 2 to cluster open points and extract
    cluster centroids for heuristic computation.
    """
    
    def __init__(
        self,
        n_clusters: int = 5,
        max_iterations: int = 100,
        tolerance: float = 1e-4,
        random_state: Optional[int] = 42,
    ):
        """
        Args:
            n_clusters: Number of cluster centroids to find
            max_iterations: Maximum iterations for convergence
            tolerance: Convergence threshold for centroid movement
            random_state: Random seed for reproducibility
        """
        self.n_clusters = n_clusters
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.random_state = random_state
        
        self.centroids = None
        self.labels = None
        self.inertia = None
    
    def fit(self, points: np.ndarray) -> 'KMeansClusterer':
        """
        Fit K-means to the given points.
        
        Args:
            points: Array of shape (N, 3) with coordinates (layer, row, col)
                   or (x, y, z) in physical space
            
        Returns:
            Self for method chaining
        """
        if len(points) < self.n_clusters:
            raise ValueError(
                f"Number of points ({len(points)}) is less than "
                f"number of clusters ({self.n_clusters})"
            )
        
        # Initialize centroids using k-means++ strategy
        self.centroids = self._initialize_centroids(points)
        
        # Iterative refinement
        for iteration in range(self.max_iterations):
            # Assign points to nearest centroid
            labels = self._assign_clusters(points)
            
            # Update centroids
            new_centroids = self._update_centroids(points, labels)
            
            # Check convergence
            centroid_shift = np.linalg.norm(new_centroids - self.centroids)
            
            self.centroids = new_centroids
            self.labels = labels
            
            if centroid_shift < self.tolerance:
                print(f"  [KMeans] Converged at iteration {iteration + 1}")
                break
        else:
            print(f"  [KMeans] Reached max iterations ({self.max_iterations})")
        
        # Compute inertia (sum of squared distances to centroids)
        self.inertia = self._compute_inertia(points)
        
        return self
    
    def _initialize_centroids(self, points: np.ndarray) -> np.ndarray:
        """
        Initialize centroids using k-means++ algorithm.
        
        This strategy spreads initial centroids across the data space,
        leading to better convergence.
        
        Args:
            points: Data points array
            
        Returns:
            Initial centroid positions
        """
        if self.random_state is not None:
            np.random.seed(self.random_state)
        
        n_samples, n_features = points.shape
        centroids = np.zeros((self.n_clusters, n_features))
        
        # Choose first centroid randomly
        idx = np.random.randint(n_samples)
        centroids[0] = points[idx]
        
        # Choose remaining centroids
        for c in range(1, self.n_clusters):
            # Compute distances to nearest existing centroid
            distances = np.array([
                min(np.linalg.norm(point - centroids[j]) 
                    for j in range(c))
                for point in points
            ])
            
            # Choose next centroid with probability proportional to distance^2
            probabilities = distances ** 2
            probabilities /= probabilities.sum()
            
            cumulative_probs = np.cumsum(probabilities)
            r = np.random.random()
            idx = np.searchsorted(cumulative_probs, r)
            idx = min(idx, n_samples - 1)  # Ensure valid index
            
            centroids[c] = points[idx]
        
        return centroids
    
    def _assign_clusters(self, points: np.ndarray) -> np.ndarray:
        """
        Assign each point to nearest centroid.
        
        Args:
            points: Data points array
            
        Returns:
            Array of cluster labels for each point
        """
        n_samples = len(points)
        labels = np.zeros(n_samples, dtype=int)
        
        for i in range(n_samples):
            distances = [
                np.linalg.norm(points[i] - self.centroids[j])
                for j in range(self.n_clusters)
            ]
            labels[i] = np.argmin(distances)
        
        return labels
    
    def _update_centroids(
        self,
        points: np.ndarray,
        labels: np.ndarray
    ) -> np.ndarray:
        """
        Update centroids as mean of assigned points.
        
        Args:
            points: Data points array
            labels: Cluster assignments
            
        Returns:
            Updated centroid positions
        """
        new_centroids = np.zeros_like(self.centroids)
        
        for c in range(self.n_clusters):
            cluster_points = points[labels == c]
            
            if len(cluster_points) > 0:
                new_centroids[c] = cluster_points.mean(axis=0)
            else:
                # If cluster is empty, keep old centroid
                new_centroids[c] = self.centroids[c]
        
        return new_centroids
    
    def _compute_inertia(self, points: np.ndarray) -> float:
        """
        Compute inertia (within-cluster sum of squares).
        
        Args:
            points: Data points array
            
        Returns:
            Inertia value
        """
        inertia = 0.0
        for i, point in enumerate(points):
            inertia += np.linalg.norm(point - self.centroids[self.labels[i]]) ** 2
        return inertia
    
    def predict(self, points: np.ndarray) -> np.ndarray:
        """
        Predict cluster labels for new points.
        
        Args:
            points: New points to classify
            
        Returns:
            Cluster labels for each point
        """
        if self.centroids is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        labels = np.zeros(len(points), dtype=int)
        for i, point in enumerate(points):
            distances = [
                np.linalg.norm(point - self.centroids[j])
                for j in range(self.n_clusters)
            ]
            labels[i] = np.argmin(distances)
        
        return labels
    
    def get_nearest_centroid(self, point: np.ndarray) -> Tuple[np.ndarray, int]:
        """
        Find nearest centroid to a given point.
        
        Args:
            point: Query point (3D coordinates)
            
        Returns:
            Tuple of (centroid_coordinates, centroid_index)
        """
        if self.centroids is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        distances = [
            np.linalg.norm(point - self.centroids[j])
            for j in range(self.n_clusters)
        ]
        nearest_idx = np.argmin(distances)
        
        return self.centroids[nearest_idx], nearest_idx


def cluster_open_points(
    open_points: List[Tuple[int, int, int]],
    n_clusters: int = 5,
    use_physical_coords: bool = False,
    graph=None,
) -> KMeansClusterer:
    """
    Convenience function to cluster open points from EDA output.
    
    Args:
        open_points: List of (layer, row, col) tuples from best population
        n_clusters: Number of clusters to find
        use_physical_coords: If True, convert to (x, y, z) physical coordinates
        graph: Grid3DPathGraph instance (required if use_physical_coords=True)
        
    Returns:
        Fitted KMeansClusterer instance with centroids
    """
    # Convert to numpy array
    points_array = np.array(open_points, dtype=float)
    
    # Optionally convert to physical coordinates
    if use_physical_coords and graph is not None:
        physical_points = []
        for layer, row, col in open_points:
            coords = graph.centroid(layer, row, col)
            physical_points.append(coords)
        points_array = np.array(physical_points)
    
    # Fit K-means
    clusterer = KMeansClusterer(n_clusters=n_clusters)
    clusterer.fit(points_array)
    
    print(f"  [KMeans] Clustered {len(open_points)} points into {n_clusters} clusters")
    print(f"  [KMeans] Inertia: {clusterer.inertia:.2f}")
    
    return clusterer