"""
配置管理器 (Configuration Manager)

支持三个配置文件的加载和管理：
1. common.yaml - 公共配置（风险模型、噪声敏感度等）
2. micro_experiment.yaml - 微观实验配置
3. macro_case_study.yaml - 宏观案例研究配置

使用示例：
    from tensor_engine.config_manager import ConfigManager

    # 加载微观实验配置
    config = ConfigManager(mode='micro')
    
    # 访问公共配置
    print(config.common.crash_probability.wind.k_w)
    
    # 访问实验配置
    print(config.experiment.spatial_grid.resolution_xy)
    
    # 获取成本权重
    weights = config.get_cost_weights('default')
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Literal, Optional, Union

import yaml

from .load_config import EasyDict, _convert_to_easy_dict


# 配置模式类型
ConfigMode = Literal['micro', 'macro']

# 配置目录路径
CONFIGS_DIR = Path(__file__).parent.parent.parent / "configs"


class ConfigManager:
    """
    配置管理器，支持微观/宏观实验配置的统一加载。
    
    Attributes:
        common: 公共配置 (common.yaml)
        experiment: 实验配置 (micro_experiment.yaml 或 macro_case_study.yaml)
        mode: 当前配置模式 ('micro' 或 'macro')
    """
    
    def __init__(self, mode: ConfigMode = 'micro', config_dir: Optional[Path] = None):
        """
        初始化配置管理器。
        
        Args:
            mode: 配置模式，'micro' 或 'macro'
            config_dir: 配置目录路径，默认为 configs/
        """
        self.mode = mode
        self.config_dir = config_dir or CONFIGS_DIR
        
        # 加载配置文件
        self.common = self._load_common_config()
        self.experiment = self._load_experiment_config()
    
    def _load_common_config(self) -> EasyDict:
        """加载公共配置文件。"""
        config_path = self.config_dir / "common.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"公共配置文件不存在: {config_path}")
        return _load_yaml(config_path)
    
    def _load_experiment_config(self) -> EasyDict:
        """加载实验配置文件。"""
        if self.mode == 'micro':
            config_path = self.config_dir / "micro_experiment.yaml"
        elif self.mode == 'macro':
            config_path = self.config_dir / "macro_case_study.yaml"
        else:
            raise ValueError(f"不支持的配置模式: {self.mode}，必须是 'micro' 或 'macro'")
        
        if not config_path.exists():
            raise FileNotFoundError(f"实验配置文件不存在: {config_path}")
        return _load_yaml(config_path)
    
    def get_cost_weights(self, preset: str = 'default') -> Dict[str, float]:
        """
        获取成本权重预设。
        
        Args:
            preset: 预设名称，可选值: 'default', 'emergency', 'quiet_night', 'strict_safety'
        
        Returns:
            包含 w_ops, w_fatal, w_prop, w_noise 的字典
        """
        presets = self.common.cost_weight_presets
        if preset not in presets:
            available = list(presets.keys())
            raise ValueError(f"未知的权重预设: {preset}，可选值: {available}")
        
        return dict(presets[preset])
    
    def get_grid_config(self) -> Dict:
        """
        获取网格配置。
        
        Returns:
            包含空间网格和时间配置的字典
        """
        exp = self.experiment
        return {
            'nx': exp.grid_dims.nx,
            'ny': exp.grid_dims.ny,
            'nz': exp.grid_dims.nz,
            'nt': exp.temporal.nt,
            'dx': exp.spatial_grid.resolution_xy,
            'dy': exp.spatial_grid.resolution_xy,
            'dz': exp.spatial_grid.resolution_z,
            'dt_minutes': exp.temporal.dt_minutes,
        }
    
    def get_sigma_decay(self) -> float:
        """
        获取POI空间衰减参数。
        
        Returns:
            sigma_decay值（米）
        """
        if self.mode == 'micro':
            return self.common.population_tidal.sigma_decay.micro
        else:
            return self.common.population_tidal.sigma_decay.macro
    
    def get_noise_coefficients(self) -> Dict[str, float]:
        """
        获取噪声敏感度系数。
        
        Returns:
            土地利用类型到敏感度系数的映射
        """
        return dict(self.common.noise_sensitivity.landuse_coefficients)
    
    def get_time_penalty(self) -> Dict[str, float]:
        """
        获取时间惩罚系数。
        
        Returns:
            包含 daytime 和 nighttime 系数的字典
        """
        return dict(self.common.noise_sensitivity.time_penalty)
    
    def get_od_pairs(self) -> list:
        """
        获取OD对列表。
        
        Returns:
            OD对列表，每个元素为 {'origin': [x, y], 'destination': [x, y]}
        """
        exp = self.experiment
        
        if self.mode == 'micro':
            # 微观实验：返回主OD和备选OD
            pairs = []
            if 'primary' in exp.od_pairs:
                pairs.append(exp.od_pairs.primary)
            if 'alternatives' in exp.od_pairs:
                pairs.extend(exp.od_pairs.alternatives)
            return pairs
        else:
            # 宏观实验：返回所有OD
            pairs = []
            for category in exp.od_pairs.values():
                if isinstance(category, list):
                    pairs.extend(category)
            return pairs
    
    def get_time_slots(self, experiment_type: str = 'algorithm_comparison') -> list:
        """
        获取实验时间槽。
        
        Args:
            experiment_type: 实验类型
        
        Returns:
            时间槽列表
        """
        exp = self.experiment
        if hasattr(exp.experiments, experiment_type):
            return list(exp.experiments[experiment_type].time_slots)
        return []
    
    def summary(self) -> str:
        """
        生成配置摘要。
        
        Returns:
            格式化的配置摘要字符串
        """
        lines = [
            "=" * 60,
            f"配置管理器摘要 (模式: {self.mode})",
            "=" * 60,
            "",
            "网格配置:",
            f"  nx={self.experiment.grid_dims.nx}, "
            f"ny={self.experiment.grid_dims.ny}, "
            f"nz={self.experiment.grid_dims.nz}, "
            f"nt={self.experiment.temporal.nt}",
            f"  分辨率: {self.experiment.spatial_grid.resolution_xy}m x "
            f"{self.experiment.spatial_grid.resolution_xy}m x "
            f"{self.experiment.spatial_grid.resolution_z}m",
            "",
            "POI衰减参数:",
            f"  sigma_decay = {self.get_sigma_decay()}m",
            "",
            "噪声敏感度:",
        ]
        
        for lu_type, coeff in self.get_noise_coefficients().items():
            lines.append(f"  {lu_type}: {coeff}")
        
        lines.extend([
            "",
            "时间惩罚:",
            f"  daytime: {self.get_time_penalty()['daytime']}",
            f"  nighttime: {self.get_time_penalty()['nighttime']}",
            "",
            "OD对数量: {}".format(len(self.get_od_pairs())),
            "=" * 60,
        ])
        
        return "\n".join(lines)


def _load_yaml(path: Path) -> EasyDict:
    """加载YAML文件并返回EasyDict。"""
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return _convert_to_easy_dict(data)


def _easydict_to_dict(obj) -> dict:
    """将EasyDict递归转换为纯dict。"""
    if isinstance(obj, EasyDict):
        return {key: _easydict_to_dict(value) for key, value in obj.items()}
    elif isinstance(obj, dict):
        return {key: _easydict_to_dict(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_easydict_to_dict(item) for item in obj]
    else:
        return obj


def _deep_merge(base: dict, override: dict) -> dict:
    """
    深度合并两个纯字典。
    
    override 中的值会覆盖 base 中的值。
    对于嵌套字典，会递归合并。
    """
    result = base.copy()
    
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


# ============================================================================
# 便捷函数
# ============================================================================

def get_config_manager(mode: ConfigMode = 'micro') -> ConfigManager:
    """
    获取配置管理器实例。
    
    Args:
        mode: 'micro' 或 'macro'
    
    Returns:
        ConfigManager实例
    """
    return ConfigManager(mode=mode)


def load_micro_config() -> EasyDict:
    """
    快速加载微观实验配置。
    
    Returns:
        EasyDict，包含微观实验配置
    """
    return ConfigManager(mode='micro').experiment


def load_macro_config() -> EasyDict:
    """
    快速加载宏观案例研究配置。
    
    Returns:
        EasyDict，包含宏观案例研究配置
    """
    return ConfigManager(mode='macro').experiment


# ============================================================================
# 向后兼容：保留旧的接口
# ============================================================================

def load_config(config_path: Optional[Union[str, Path]] = None) -> EasyDict:
    """
    加载配置文件（向后兼容接口）。
    
    如果指定路径，直接加载该文件。
    如果未指定路径，加载公共配置。
    """
    if config_path is not None:
        return _load_yaml(Path(config_path))
    
    # 默认返回公共配置
    return _load_yaml(CONFIGS_DIR / "common.yaml")


def load_all_configs(config_dir: Optional[Union[str, Path]] = None) -> Dict[str, EasyDict]:
    """
    加载目录下所有配置文件（向后兼容接口）。
    """
    config_dir = Path(config_dir) if config_dir else CONFIGS_DIR
    
    configs = {}
    for yaml_file in config_dir.glob("*.yaml"):
        config_name = yaml_file.stem
        configs[config_name] = _load_yaml(yaml_file)
    
    return configs


def get_risk_config() -> EasyDict:
    """
    快速获取风险参数配置（向后兼容接口）。
    """
    return load_config()


if __name__ == "__main__":
    # 测试配置管理器
    print("=" * 60)
    print("配置管理器测试")
    print("=" * 60)
    
    # 测试微观配置
    print("\n[微观实验配置]")
    micro_config = ConfigManager(mode='micro')
    print(micro_config.summary())
    
    # 测试宏观配置
    print("\n[宏观案例研究配置]")
    macro_config = ConfigManager(mode='macro')
    print(macro_config.summary())
    
    # 测试成本权重
    print("\n[成本权重预设]")
    for preset in ['default', 'emergency', 'quiet_night', 'strict_safety']:
        weights = micro_config.get_cost_weights(preset)
        print(f"  {preset}: {weights}")
