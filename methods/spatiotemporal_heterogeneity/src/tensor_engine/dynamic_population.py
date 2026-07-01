# 生成 3D 潮汐人口密度张量 (基于POI激活函数)；致命风险成本；


import numpy as np
from scipy.signal import fftconvolve

class DynamicPopulationBuilder:
    def __init__(self, config):
        """
        加载配置文件中的参数
        """
        self.NX = config['env']['nx']
        self.NY = config['env']['ny']
        self.NT = 96  # 24小时，15分钟一个slice
        
        # 加载 POI 参数
        self.params = config['population']
        
        # 初始化 1D 时间轴 (0.0 到 23.75 小时)
        self.time_hours = np.arange(self.NT) * 0.25

    # ==========================================
    # 第一步：构建 1D 时间激活函数 tau_k(t)
    # ==========================================
    def _build_temporal_profiles(self):
        """生成5个类别的1D时间激活数组，返回字典"""
        t = self.time_hours
        profiles = {}
        
        # 1. 住宅区 (Logistic S型过渡)
        # 夜间为1，白天为0.2，t1=18, t2=7
        k1, k2 = 2.0, 2.0
        p_res = 1.0 - (1 / (1 + np.exp(-k1 * (t - 8)))) + (1 / (1 + np.exp(-k2 * (t - 18))))
        profiles['residential'] = np.clip(p_res, 0.2, 1.0) # 修正波谷并截断
        
        # 2. 办公商业区 (双高斯混合)
        p_office = (0.8 * np.exp(-((t - 8.5)**2)/(2*1.0**2)) + 
                    0.8 * np.exp(-((t - 18.0)**2)/(2*1.5**2)))
        p_office += np.where((t >= 9) & (t <= 17), 0.85, 0.0) # 叠加日间平台
        profiles['office'] = np.clip(p_office, 0.1, 1.0)
        
        # 3. 文教医政 (梯形函数/截断)
        p_inst = np.where((t >= 8) & (t <= 17), 0.9, 0.1)
        profiles['institution'] = p_inst
        
        # 4. 交通枢纽 (尖锐双高斯)
        p_trans = (0.8 * np.exp(-((t - 8.5)**2)/(2*0.5**2)) + 
                   0.8 * np.exp(-((t - 18.5)**2)/(2*0.5**2)) + 0.2)
        profiles['transit'] = np.clip(p_trans, 0.2, 1.0)
        
        # 5. 工业区 (平稳常数 + 微小高斯噪声)
        profiles['industrial'] = np.full(self.NT, 0.35)
        
        return profiles

    # ==========================================
    # 第二步：2D 空间衰减卷积 (FFT Convolve)
    # ==========================================
    def _apply_spatial_gravity(self, poi_grid_2d, sigma_meters):
        """
        生成高斯核，并对离散的 POI 点阵进行卷积，生成空间引力场
        """
        # 将物理距离 sigma(米) 转换为网格数
        grid_resolution = 50.0 
        sigma_grids = sigma_meters / grid_resolution
        
        # 生成高斯核 (核大小取 6 倍 sigma 以保证精度)
        kernel_size = int(sigma_grids * 6)
        if kernel_size % 2 == 0: kernel_size += 1 # 保证是奇数
        
        center = kernel_size // 2
        y, x = np.ogrid[-center:center+1, -center:center+1]
        
        # 计算高斯核公式
        gaussian_kernel = np.exp(-(x**2 + y**2) / (2 * sigma_grids**2))
        
        # 核心魔法：使用 FFT 进行极速二维卷积 (mode='same' 保持输出大小与输入相同)
        gravity_field_2d = fftconvolve(poi_grid_2d, gaussian_kernel, mode='same')
        
        return gravity_field_2d

    # ==========================================
    # 第三步：时空广播与最终张量组装
    # ==========================================
    def build_tensor(self, base_pop_2d, poi_grids_dict):
        """
        主控函数：组装最终的 3D 动态人口张量
        """
        temporal_profiles = self._build_temporal_profiles()
        
        # 初始化一个增益矩阵 (全0)
        total_enhancement_3d = np.zeros((self.NX, self.NY, self.NT), dtype=np.float32)
        
        # 遍历 5 个类别
        for category, poi_2d in poi_grids_dict.items():
            W_k = self.params['poi_weights'][category]
            sigma_k = self.params['sigma_decay'][category]
            
            # 1. 空间：算二维引力场 [NX, NY]
            gravity_2d = self._apply_spatial_gravity(poi_2d, sigma_k)
            
            # 2. 时间：获取一维激活向量 [NT]
            tau_1d = temporal_profiles[category]
            
            # 3. 乘法与广播 (Broadcasting)
            # gravity_2d 变为 [NX, NY, 1]，tau_1d 变为 [NT]
            # Numpy 会自动将它们扩展并相乘为 [NX, NY, NT]
            category_tensor_3d = W_k * gravity_2d[..., np.newaxis] * tau_1d
            
            # 累加到总增益中
            total_enhancement_3d += category_tensor_3d
            
        # 根据你的公式：rho = rho_base * sum(...)
        # 为了防止 base_pop 为 0 导致全部归零，可以加一个小 epsilon，或者修改为加法增强
        # 这里严格按你的乘法公式实现：
        
        final_dynamic_pop_3d = base_pop_2d[..., np.newaxis] * (1.0 + total_enhancement_3d)
        
        # 截断处理极值 (例如最大不允许超过 5万人/km^2 的网格等效人数)
        MAX_POP_PER_GRID = 500  
        final_dynamic_pop_3d = np.clip(final_dynamic_pop_3d, 0, MAX_POP_PER_GRID)
        
        return final_dynamic_pop_3d

# ==========================================
# 本地测试模块 (Mock Data)
# ==========================================
if __name__ == "__main__":
    # 模拟环境配置
    mock_config = {
        'env': {'nx': 200, 'ny': 200},
        'population': {
            'sigma_decay': {
                'residential': 400, 'office': 350, 'institution': 300, 
                'transit': 250, 'industrial': 500
            },
            'poi_weights': {
                'residential': 1.0, 'office': 1.2, 'institution': 1.5, 
                'transit': 1.8, 'industrial': 0.3
            }
        }
    }
    
    # 模拟 data_provision 传来的数据
    mock_base_pop = np.ones((200, 200)) * 10.0 # 每个网格基础有10个人
    
    # 在中心点放一个火车站 (Transit)，在左上角放一个办公楼 (Office)
    mock_poi_grids = {
        'residential': np.zeros((200, 200)),
        'office': np.zeros((200, 200)),
        'institution': np.zeros((200, 200)),
        'transit': np.zeros((200, 200)),
        'industrial': np.zeros((200, 200))
    }
    mock_poi_grids['transit'][100, 100] = 1.0
    mock_poi_grids['office'][50, 50] = 5.0 # 一栋大写字楼
    
    # 运行构建器
    builder = DynamicPopulationBuilder(mock_config)
    pop_tensor_3d = builder.build_tensor(mock_base_pop, mock_poi_grids)
    
    print(f"✅ 生成完毕！张量形状: {pop_tensor_3d.shape}")
    print(f"火车站(100,100) 早上 8:30 (t=34) 的人口: {pop_tensor_3d[100, 100, 34]:.1f}")
    print(f"火车站(100,100) 凌晨 3:00 (t=12) 的人口: {pop_tensor_3d[100, 100, 12]:.1f}")