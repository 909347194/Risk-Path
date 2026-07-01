import json

def extract_region_bounds(geojson_path):
    """
    从 GeoJSON 文件中提取区域的经纬度边界
    
    参数:
        geojson_path: GeoJSON 文件路径
    
    返回:
        dict: 包含 North, West, East, South 的字典
    """
    # 读取 GeoJSON 文件
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 初始化边界值
    min_lon = float('inf')
    max_lon = float('-inf')
    min_lat = float('inf')
    max_lat = float('-inf')
    
    # 遍历所有 features
    for feature in data['features']:
        geometry = feature['geometry']
        coords = geometry['coordinates']
        
        # 处理 MultiPolygon 或 Polygon 类型
        def extract_coords_from_geometry(coords_list):
            nonlocal min_lon, max_lon, min_lat, max_lat
            
            if isinstance(coords_list[0][0], list):
                # MultiPolygon: [[[lon, lat], ...], [[lon, lat], ...]]
                for polygon in coords_list:
                    for ring in polygon:
                        for point in ring:
                            lon, lat = point[0], point[1]
                            min_lon = min(min_lon, lon)
                            max_lon = max(max_lon, lon)
                            min_lat = min(min_lat, lat)
                            max_lat = max(max_lat, lat)
            else:
                # Polygon: [[lon, lat], ...]
                for ring in coords_list:
                    for point in ring:
                        lon, lat = point[0], point[1]
                        min_lon = min(min_lon, lon)
                        max_lon = max(max_lon, lon)
                        min_lat = min(min_lat, lat)
                        max_lat = max(max_lat, lat)
        
        extract_coords_from_geometry(coords)
    
    # 返回结果
    bounds = {
        'North': max_lat,
        'West': min_lon,
        'East': max_lon,
        'South': min_lat
    }
    
    return bounds


if __name__ == '__main__':
    # GeoJSON 文件路径
    geojson_path = r'e:\01Reproduction\Risk-Path\data\1test-data\buildings_max_range\buildings_max_range.geojson'
    
    # 提取边界
    bounds = extract_region_bounds(geojson_path)
    
    # 输出结果
    print("=" * 50)
    print("Sub-region extraction from buildings_max_range.geojson")
    print("=" * 50)
    print(f"North: {bounds['North']}")
    print(f"West:  {bounds['West']}")
    print(f"East:  {bounds['East']}")
    print(f"South: {bounds['South']}")
    print("=" * 50)
    
    # 也可以直接复制使用的格式
    print("\n可直接复制的格式:")
    print(f"North: {bounds['North']}")
    print(f"West: {bounds['West']}")
    print(f"East: {bounds['East']}")
    print(f"South: {bounds['South']}")
