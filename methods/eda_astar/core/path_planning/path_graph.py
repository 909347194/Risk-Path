"""
DEPRECATED: This file has been split into modular components.

Please use:
- from .graph import Grid3DPathGraph
- from .astar import CostAStarSearcher
- from .eda_costastar import EDACostAStarSearcher

This file is kept for backward compatibility only.
"""

# Backward compatibility imports
from .graph import Grid3DPathGraph
from .astar import CostAStarSearcher
from .eda_costastar import EDACostAStarSearcher

__all__ = ["Grid3DPathGraph", "CostAStarSearcher", "EDACostAStarSearcher"]
