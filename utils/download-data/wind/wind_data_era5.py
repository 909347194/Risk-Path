import cdsapi
from datetime import datetime
import os

print("=" * 60)
print("ERA5 风场数据下载")
print("=" * 60)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"数据集: reanalysis-era5-single-levels")
print(f"区域: [23.25, 113.25, 23, 113.5]")
print(f"时间范围: 2025年7月全月")
print("=" * 60)

dataset = "reanalysis-era5-single-levels"
request = {
    "product_type": ["reanalysis"],
    "variable": [
        "100m_u_component_of_wind",
        "100m_v_component_of_wind",
        "10m_wind_gust_since_previous_post_processing",
        "instantaneous_10m_wind_gust"
    ],
    "year": ["2025"],
    "month": ["07"],
    "day": [
        "01", "02", "03",
        "04", "05", "06",
        "07", "08", "09",
        "10", "11", "12",
        "13", "14", "15",
        "16", "17", "18",
        "19", "20", "21",
        "22", "23", "24",
        "25", "26", "27",
        "28", "29", "30",
        "31"
    ],
    "time": [
        "00:00", "01:00", "02:00",
        "03:00", "04:00", "05:00",
        "06:00", "07:00", "08:00",
        "09:00", "10:00", "11:00",
        "12:00", "13:00", "14:00",
        "15:00", "16:00", "17:00",
        "18:00", "19:00", "20:00",
        "21:00", "22:00", "23:00"
    ],
    "data_format": "netcdf",
    "download_format": "unarchived",
    "area": [23.25, 113.25, 23, 113.5]
}

print("\n正在提交数据请求...")
# 直接在代码中指定 URL 和 API Key
client = cdsapi.Client(
    url="https://cds.climate.copernicus.eu/api",
    key="5e3dc431-0ea2-48a2-b23b-cf14badeb2fc"
)
result = client.retrieve(dataset, request)

print("数据准备完成，开始下载...")
# 明确指定下载文件名
filename = f"ERA5_wind_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.nc"
result.download(filename)

print(f"\n下载完成! 文件名: {filename}")
print(f"文件位置: {os.path.abspath(filename)}")
print(f"文件大小: {os.path.getsize(filename)/1024/1024:.2f} MB")
print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
