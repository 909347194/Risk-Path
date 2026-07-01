```python
# 方式1: 从 YAML 文件加载配置
model = DynamicCrashProbability(
    config_path='methods/spatiotemporal_heterogeneity/configs/risk_params.yaml'
)

# 方式2: 先加载配置再传入
config = CrashProbConfig.from_yaml('methods/spatiotemporal_heterogeneity/configs/risk_params.yaml')
model = DynamicCrashProbability(config=config)

# 方式3: 使用默认配置（向后兼容）
model = DynamicCrashProbability()
```



```python
from tensor_engine.config_loader import ConfigLoader

# 加载配置
config = ConfigLoader()

# 打印配置摘要
config.print_summary()

# 获取特定场景
micro_scenario = config.get_scenario('micro_validation')
macro_scenario = config.get_scenario('macro_city')

# 访问网格信息
print(f"Micro grid: {micro_scenario.spatial_grid.nx} × "
      f"{micro_scenario.spatial_grid.ny} × {micro_scenario.spatial_grid.nz}")
# 输出: Micro grid: 40 × 40 × 12

print(f"Macro grid: {macro_scenario.spatial_grid.nx} × "
      f"{macro_scenario.spatial_grid.ny} × {macro_scenario.spatial_grid.nz}")
# 输出: Macro grid: 100 × 100 × 12

# 获取其他配置
flight_params = config.get_flight_parameters()
env_data = config.get_environmental_data_config()
comp_settings = config.get_computational_settings()
```
