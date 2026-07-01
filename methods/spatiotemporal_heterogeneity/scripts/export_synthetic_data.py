"""
合成数据导出脚本 - 修复版

此脚本会自动处理模块导入和 GIS 环境冲突问题。
"""

import os
import sys

def fix_proj_environment():
    """修复 PROJ 环境变量冲突"""
    # 保存原始 PROJ_LIB 值
    original_proj_lib = os.environ.get('PROJ_LIB')
    
    # 清除可能冲突的 PROJ_LIB 环境变量
    if 'PROJ_LIB' in os.environ:
        del os.environ['PROJ_LIB']
    
    try:
        # 测试 PROJ 是否正常工作
        import rasterio
        from rasterio.crs import CRS
        crs = CRS.from_epsg(4326)
        print("✅ PROJ 配置正常")
        return True, original_proj_lib
    except Exception as e:
        print(f"⚠️ PROJ 配置有问题: {e}")
        print("ℹ️ 将禁用原生 GIS 格式导出")
        return False, original_proj_lib
    finally:
        # 恢复原始环境变量（稍后在主函数中处理）
        pass

def restore_proj_environment(original_proj_lib):
    """恢复原始 PROJ 环境变量"""
    if original_proj_lib is not None:
        os.environ['PROJ_LIB'] = original_proj_lib
    elif 'PROJ_LIB' in os.environ:
        del os.environ['PROJ_LIB']

def main():
    # 修复 PROJ 环境
    gis_supported, original_proj_lib = fix_proj_environment()
    
    try:
        # 从 methods.spatiotemporal_heterogeneity.utils.synthetic_data_factory 导入函数
        from methods.spatiotemporal_heterogeneity.utils.synthetic_data_factory import export_synthetic_data, generate_synthetic_city
        
        # 生成数据
        print("🔄 生成合成城市数据...")
        city_data = generate_synthetic_city(60, 60, 12, 96, seed=42)
        
        # 导出数据
        print("💾 导出合成数据...")
        export_synthetic_data(
            city_data, 
            seed=42, 
            export_raw_gis=gis_supported, 
            export_tensors=True
        )
        
        print("✅ 合成数据导出完成！")
        
    finally:
        # 恢复原始 PROJ 环境变量
        restore_proj_environment(original_proj_lib)

if __name__ == "__main__":
    main()