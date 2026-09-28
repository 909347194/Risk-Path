"""研究区网格常量（scripts 间共享；由 build_landuse_map.py 抽出独立成模块）。

坐标/网格约定与 poi_parser.coordinate_to_grid_index(city_bounds) 一致：
  ix = int((lon - minx) / (maxx - minx) * NX)   （经度 -> x）
  iy = int((lat - miny) / (maxy - miny) * NY)   （纬度 -> y）
"""

# 研究区 WGS84 bbox（buildings_max_range）
BBOX = (113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036)
NX = NY = 100
