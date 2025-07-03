# Cainiao Parcel Station LTO System

A **Learn-then-Optimize (LTO)** system for optimizing parcel placement in Chinese parcel stations (e.g., Cainiao stations). This project demonstrates how LTO algorithms can be applied to real-world logistics problems.

## 🎯 Project Overview

This system implements a simplified LTO framework that:

1. **LEARNS**: Predicts the pickup probability of each parcel based on arrival time, size, and other features
2. **OPTIMIZES**: Assigns parcels to shelf locations to minimize total cost while prioritizing high-probability parcels for convenient locations
3. **ANALYZES**: Evaluates the effectiveness of the LTO strategy

### Key Features

- **Modular Design**: Separate learning and optimization components that can be easily extended
- **Realistic Simulation**: Time-based parcel arrivals with configurable patterns
- **Cost-based Optimization**: Implements the objective function `D_j * (1 - p̂_i)` where `D_j` is shelf distance and `p̂_i` is predicted pickup probability
- **Performance Metrics**: Comprehensive analysis of LTO effectiveness and system performance

## 📁 Project Structure

```
project/
├── data_structures.py          # Core classes (Parcel, Shelf, ParcelStation)
├── config.py                  # Configuration parameters
├── learning_module.py         # Learning component (pickup probability prediction)
├── optimization_module.py     # Basic optimization component (greedy algorithm)
├── advanced_optimization.py   # Advanced LTO-LSNS optimization algorithms
├── simulation_engine.py       # Basic simulation orchestrator
├── enhanced_simulation.py     # Enhanced simulation with batch processing
├── main.py                   # Entry point for basic simulations
├── test_system.py            # Basic system tests
├── test_advanced_optimization.py # Advanced optimization tests
├── stress_test.py            # Stress testing for algorithm comparison
├── README.md                 # This file (project documentation)
├── simulation_results.json   # Basic simulation results
└── enhanced_simulation_results_*.json # Enhanced simulation results
```

### 🔗 文件关系与协调机制

为了帮助理解这个看似复杂的系统，让我们用简单的方式解释每个文件的作用以及它们如何协调工作：

#### 🏗️ 基础层 (Foundation Layer)

**1. `data_structures.py` - 数据基础**
- **作用**: 定义系统中的基本"物品"
- **包含**: 
  - `Parcel` (包裹) - 就像现实中的快递包裹
  - `Shelf` (货架) - 就像快递站的储物架
  - `ParcelStation` (快递站) - 管理所有货架的地方
- **比喻**: 这就像搭积木前先准备好各种形状的积木块

**2. `config.py` - 配置中心**
- **作用**: 存放所有的"设置参数"
- **包含**: 货架数量、距离评分、时间设置等
- **比喻**: 就像游戏的设置菜单，可以调整难度、时间等参数
- **关系**: 所有其他文件都会来这里"查看设置"

#### 🧠 核心逻辑层 (Core Logic Layer)

**3. `learning_module.py` - 学习大脑**
- **作用**: 预测包裹被取走的概率
- **输入**: 包裹信息（大小、到达时间等）
- **输出**: 概率数字（0-1之间）
- **比喻**: 就像一个经验丰富的快递员，能猜测哪些包裹会很快被取走
- **依赖**: 使用 `data_structures.py` 中的包裹信息，读取 `config.py` 中的时间设置

**4. `optimization_module.py` - 决策大脑**
- **作用**: 决定把包裹放在哪个货架上
- **输入**: 包裹 + 预测概率 + 可用货架
- **输出**: 最佳货架选择
- **比喻**: 就像一个聪明的仓库管理员，知道怎么摆放物品最合理
- **依赖**: 使用 `learning_module.py` 的预测结果，操作 `data_structures.py` 中的货架

#### 🎮 控制层 (Control Layer)

**5. `simulation_engine.py` - 总指挥**
- **作用**: 协调整个系统运行
- **功能**: 
  - 生成包裹到达
  - 调用学习模块预测
  - 调用优化模块分配
  - 记录结果
- **比喻**: 就像乐队指挥，让各个部分按节拍协调演奏
- **依赖**: 调用上面所有模块，是系统的"大脑中枢"

**6. `main.py` - 程序入口**
- **作用**: 程序的启动按钮
- **功能**: 创建模拟引擎并运行
- **比喻**: 就像电视遥控器的开机键
- **依赖**: 主要调用 `simulation_engine.py`

#### 🧪 测试层 (Testing Layer)

**7. `test_system.py` - 基础测试**
- **作用**: 检查各个模块是否正常工作
- **比喻**: 就像汽车出厂前的质量检测
- **依赖**: 测试所有核心模块

### 🔄 工作流程 (简化版)

让我们看看一个包裹从到达到分配的完整流程：

```
1. main.py 启动程序
   ↓
2. simulation_engine.py 开始模拟
   ↓
3. 生成新包裹 (使用 data_structures.py 中的 Parcel 类)
   ↓
4. learning_module.py 预测取件概率
   ↓
5. optimization_module.py 选择最佳货架
   ↓
6. 更新货架状态 (使用 data_structures.py 中的 Shelf 类)
   ↓
7. 记录结果并继续下一个包裹
```

### 🎯 关键依赖关系

**数据流向**:
```
config.py → 为所有模块提供参数
data_structures.py → 为所有模块提供数据结构
learning_module.py → 为 optimization_module.py 提供预测
optimization_module.py → 为 simulation_engine.py 提供决策
simulation_engine.py → 协调所有模块
main.py → 启动整个系统
```

**模块调用关系**:
- `main.py` 调用 `simulation_engine.py`
- `simulation_engine.py` 调用 `learning_module.py` 和 `optimization_module.py`
- 所有模块都使用 `data_structures.py` 和 `config.py`
- `test_system.py` 测试所有模块

### 💡 为什么需要这么多文件？

1. **模块化设计**: 每个文件负责一个特定功能，就像工厂的不同车间
2. **易于维护**: 如果要修改学习算法，只需要改 `learning_module.py`
3. **可扩展性**: 可以轻松添加新的优化算法或学习方法
4. **代码复用**: 不同的测试文件可以重复使用相同的核心模块
5. **团队协作**: 不同的人可以同时开发不同的模块

### 🚀 如何开始理解代码？

**建议阅读顺序**:
1. 先看 `config.py` - 了解系统参数
2. 再看 `data_structures.py` - 理解基本数据结构
3. 然后看 `learning_module.py` - 理解预测逻辑
4. 接着看 `optimization_module.py` - 理解决策逻辑
5. 最后看 `simulation_engine.py` - 理解整体协调
6. 运行 `main.py` - 看实际效果

**调试技巧**:
- 从 `main.py` 开始，逐步跟踪代码执行
- 使用 `test_system.py` 单独测试各个模块
- 查看生成的 `simulation_results.json` 了解输出格式

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- No external dependencies required (uses only standard library)

### Running the System

1. **Quick Demo** (recommended for first run):
   ```bash
   python main.py --demo
   ```

2. **Full Simulation** (12 hours by default):
   ```bash
   python main.py
   ```

3. **Custom Duration**:
   ```bash
   python main.py --hours 6
   ```

4. **Quiet Mode** (minimal output):
   ```bash
   python main.py --quiet
   ```

### Advanced Features

5. **Advanced LTO-LSNS Optimization**:
   ```bash
   python test_advanced_optimization.py
   ```

6. **Enhanced Simulation with Batch Processing**:
   ```bash
   python enhanced_simulation.py
   ```

7. **Stress Testing** (algorithm comparison under challenging conditions):
   ```bash
   python stress_test.py
   ```

8. **System Integration Tests**:
   ```bash
   python test_system.py
   ```

### Testing Individual Modules

```bash
# Test learning module
python learning_module.py

# Test optimization module  
python optimization_module.py

# Test simulation engine
python simulation_engine.py
```

## 🏗️ System Architecture

### LTO Workflow

```
Parcel Arrival → [LEARNING] → Pickup Probability → [OPTIMIZATION] → Shelf Assignment
                     ↓                                    ↓
              Feature Extraction                   Cost Minimization
              Rule-based Logic                    Greedy Heuristic
```

### Core Components

#### 1. Learning Module (`learning_module.py`)
- **Purpose**: Predict pickup probability `p̂_i` for each parcel
- **Current Implementation**: Rule-based predictor using time periods and parcel size
- **Future Extension**: Can be replaced with ML models (Logistic Regression, etc.)

#### 2. Optimization Module (`optimization_module.py`)
- **Purpose**: Assign parcels to shelves to minimize cost
- **Objective**: `min Σ D_j * (1 - p̂_i) * x_ij`
- **Strategy**: High-probability parcels prefer premium (convenient) shelves

#### 3. Simulation Engine (`simulation_engine.py`)
- **Purpose**: Orchestrate the complete LTO process over time
- **Features**: Realistic parcel generation, time-step simulation, performance analysis

## ⚙️ Configuration

Key parameters in `config.py`:

```python
# Simulation settings
SIMULATION_HOURS = 12
TIME_STEP_MINUTES = 30

# Shelf configuration
PREMIUM_SHELF_COUNT = 3
STANDARD_SHELF_COUNT = 5

# LTO parameters
HIGH_PROBABILITY_THRESHOLD = 0.7
SHELF_DISTANCE_SCORES = {
    'premium': [1.0, 1.2, 1.5],
    'standard': [2.0, 2.5, 3.0, 3.5, 4.0]
}
```

## 📊 Understanding Results

### Key Metrics

- **LTO Alignment Score**: How well the system assigns high-probability parcels to premium shelves
- **Average Assignment Cost**: Overall cost based on the objective function
- **Shelf Utilization**: How efficiently different shelf types are used
- **Premium Assignment Ratio**: Percentage of parcels assigned to premium shelves

### Sample Output

```
CAINIAO PARCEL STATION LTO SIMULATION SUMMARY
============================================================
Simulation Duration: 12 hours
Total Parcels Processed: 156
Average Assignment Cost: 0.847
Premium Shelf Usage: 45.5%

LTO Effectiveness Metrics:
------------------------------
High-prob → Premium Rate: 89.2%
Low-prob → Standard Rate: 78.4%
Overall LTO Alignment: 83.8%
```

## 📋 变量假设与定义

本节详细说明系统中每个关键变量的定义、假设和设计理念。

### 🏷️ 核心变量定义

#### 1. Distance to Exit (`distance_to_exit`)

**定义**: 货架到出口的距离/便利度评分
- **数据类型**: `float`
- **单位**: 抽象的便利度评分（无量纲）
- **范围**: 1.0 - 4.0
- **解释**: 数值越小表示位置越便利，取件越容易

**具体配置**:
```python
SHELF_DISTANCE_SCORES = {
    'premium': [1.0, 1.2, 1.5],           # 最便利位置
    'standard': [2.0, 2.5, 3.0, 3.5, 4.0] # 相对不便利位置
}
```

**设计理念**:
- **抽象化**: 不使用实际物理距离（米），而是便利度的相对评分
- **成本导向**: 在目标函数中作为成本系数，数值越大"惩罚"越重
- **可扩展性**: 可根据实际快递站布局调整评分标准

**为什么这样定义**:
1. **简化建模**: 避免复杂的空间几何计算
2. **灵活适配**: 不同快递站可以有不同的便利度标准
3. **LTO逻辑**: 支持"高概率包裹优先便利位置"的核心思想

#### 2. Pickup Probability (`predicted_pickup_probability`)

**定义**: 包裹在未来特定时间内被取走的概率
- **数据类型**: `float`
- **范围**: 0.0 - 1.0
- **解释**: 1.0表示肯定会被取走，0.0表示不太可能被取走

**当前实现** (基于规则):
```python
BASE_PICKUP_PROBABILITIES = {
    'peak_morning': 0.85,    # 早高峰：高概率
    'normal_morning': 0.65,  # 普通上午：中高概率
    'peak_afternoon': 0.75,  # 午高峰：高概率
    'normal_afternoon': 0.55, # 普通下午：中等概率
    'peak_evening': 0.90,    # 晚高峰：很高概率
    'low_evening': 0.40      # 晚间：较低概率
}
```

**影响因素**:
- **时间段**: 高峰期概率更高
- **包裹大小**: 大包裹概率略低（需要规划取件）
- **随机噪声**: ±0.1的随机变化模拟不确定性

**设计理念**:
- **时间相关性**: 反映用户取件的时间偏好
- **现实性**: 基于对中国快递站用户行为的观察
- **可替换性**: 未来可用ML模型替换规则

#### 3. Parcel Size (`size`)

**定义**: 包裹的尺寸分类
- **数据类型**: `ParcelSize` 枚举
- **取值**: `SMALL`, `MEDIUM`, `LARGE`
- **分布**: 60% 小件, 30% 中件, 10% 大件

**容量影响**:
```python
SHELF_CAPACITY = {
    'premium': {SMALL: 8, MEDIUM: 4, LARGE: 2},
    'standard': {SMALL: 12, MEDIUM: 6, LARGE: 3}
}
```

**设计理念**:
- **简化分类**: 避免连续尺寸的复杂性
- **容量约束**: 不同尺寸占用不同货架空间
- **现实分布**: 基于电商包裹的典型尺寸分布

#### 4. Shelf Type (`location_type`)

**定义**: 货架的位置类型分类
- **数据类型**: `ShelfType` 枚举
- **取值**: `PREMIUM` (优质位置), `STANDARD` (标准位置)
- **配置**: 3个Premium货架, 5个Standard货架

**特征对比**:
| 特征 | Premium | Standard |
|------|---------|----------|
| 距离评分 | 1.0-1.5 | 2.0-4.0 |
| 容量 | 较小 | 较大 |
| 便利度 | 高 | 中等 |
| 竞争度 | 高 | 低 |

**设计理念**:
- **二分类**: 简化决策复杂度
- **差异化**: 明确的便利度和容量差异
- **稀缺性**: Premium货架数量有限，创造竞争

#### 5. Assignment Cost (`assignment_cost`)

**定义**: 将包裹分配到特定货架的成本
- **计算公式**: `cost = distance_to_exit × (1 - predicted_pickup_probability)`
- **数据类型**: `float`
- **范围**: 0.0 - 4.0 (理论上)

**成本逻辑**:
- **高概率包裹**: `(1 - 0.9) × distance = 0.1 × distance` → 低成本偏好低距离
- **低概率包裹**: `(1 - 0.3) × distance = 0.7 × distance` → 成本对距离不太敏感

**设计理念**:
- **LTO核心**: 体现"学习指导优化"的思想
- **权衡机制**: 平衡概率预测和位置便利度
- **可解释性**: 成本计算逻辑清晰直观

### 🎯 时间相关变量

#### 6. Time Periods (`TIME_PERIODS`)

**定义**: 一天中的不同时间段分类
```python
TIME_PERIODS = {
    'peak_morning': (8, 10),    # 早高峰
    'normal_morning': (10, 12), # 普通上午
    'peak_afternoon': (12, 14), # 午高峰
    'normal_afternoon': (14, 16), # 普通下午
    'peak_evening': (16, 18),   # 晚高峰
    'low_evening': (18, 20)     # 晚间
}
```

**设计理念**:
- **用户行为**: 反映中国用户的取件时间偏好
- **业务逻辑**: 上班前、午休、下班后是取件高峰
- **预测基础**: 为概率预测提供时间特征

#### 7. Simulation Parameters

**时间步长** (`TIME_STEP_MINUTES`): 30分钟
- **理念**: 平衡计算效率和时间精度

**模拟时长** (`SIMULATION_HOURS`): 12小时
- **理念**: 覆盖一个完整的营业日

**到达率** (`PARCEL_ARRIVAL_RATES`): 4-18包裹/小时
- **理念**: 基于中小型快递站的实际业务量

### 🔧 系统参数

#### 8. Thresholds and Limits

**高概率阈值** (`HIGH_PROBABILITY_THRESHOLD`): 0.7
- **用途**: 区分高/低概率包裹的分界线
- **影响**: LTO效果评估的关键参数

**容量限制**: 每个货架按尺寸分别限制
- **理念**: 模拟真实的空间约束

**验证范围**:
```python
MIN_PROBABILITY = 0.0
MAX_PROBABILITY = 1.0
MIN_DISTANCE_SCORE = 0.1
MAX_DISTANCE_SCORE = 10.0
```

### 💡 假设说明

#### 核心假设

1. **简化假设**:
   - 包裹尺寸离散化（小/中/大）
   - 货架位置二分类（优质/标准）
   - 时间段固定划分

2. **业务假设**:
   - 用户取件行为有时间规律性
   - 包裹大小影响取件概率
   - 位置便利度可以量化

3. **技术假设**:
   - 预测概率在短期内稳定
   - 成本函数线性可加
   - 贪心算法能找到合理解

#### 局限性

1. **现实简化**: 实际快递站更复杂
2. **数据模拟**: 缺乏真实历史数据
3. **静态模型**: 未考虑动态调整

#### 扩展方向

1. **更精细建模**: 连续变量、多维特征
2. **机器学习**: 基于历史数据的预测模型
3. **动态优化**: 实时调整和重新分配

## 🔧 Technical Details

### Mathematical Formulation

The system implements a simplified version of the LTO framework:

**Learning Component:**
- Input features: arrival time, parcel size, time period
- Output: pickup probability `p̂_i ∈ [0,1]`

**Optimization Component:**
- Decision variables: `x_ij ∈ {0,1}` (1 if parcel i assigned to shelf j)
- Objective: `minimize Σ_i Σ_j D_j * (1 - p̂_i) * x_ij`
- Constraints: capacity limits, one assignment per parcel

### Design Patterns

- **Factory Pattern**: `create_predictor()`, `create_optimizer()`
- **Strategy Pattern**: Interchangeable learning and optimization algorithms
- **Observer Pattern**: Logging and result collection

## 🚀 Advanced Algorithms

### LTO-LSNS (Learn-then-Optimize Large-Scale Neighborhood Search)

本项目实现了基于锚点论文的高级LTO-LSNS算法，相比基础贪心算法具有以下特性：

#### 核心特性

1. **机器学习指导的子问题选择**:
   - 使用ML模型预测子问题的优化潜力
   - 基于历史优化结果动态学习
   - 特征包括：成本分布、容量利用率、分配不匹配度等

2. **多种邻域搜索策略**:
   - **Recent Arrivals**: 重新优化最近到达的包裹
   - **High Cost**: 针对高成本分配进行改进
   - **Misaligned**: 修正不符合LTO逻辑的分配
   - **Random**: 随机选择进行探索

3. **批处理优化**:
   - 将包裹分批处理，每批进行迭代改进
   - 支持精确枚举（小规模）和启发式算法（大规模）
   - 禁忌搜索防止循环

4. **自适应学习**:
   - 根据优化结果调整特征权重
   - 动态适应不同的包裹分布模式
   - 持续改进预测准确性

#### 性能对比

通过压力测试，高级算法在以下场景中表现更优：
- **高竞争场景**: Premium货架容量有限，多个高概率包裹竞争
- **容量压力**: 大包裹较多，需要精细的容量管理
- **复杂分布**: 包裹概率分布不均匀的情况

#### 算法复杂度

- **基础贪心**: O(n×m) 其中 n=包裹数, m=货架数
- **LTO-LSNS**: O(k×n×m) 其中 k=迭代次数（通常k=3-5）
- **内存使用**: 额外存储ML模型和历史数据

## 🛠️ Extending the System

### Adding ML-based Learning

1. Implement `MLPickupPredictor` class in `learning_module.py`
2. Train model using historical data
3. Replace rule-based predictor in simulation

### Advanced Optimization

1. Implement exact optimization using mathematical programming (PuLP, Gurobi)
2. Add Large Neighborhood Search (LNS) for iterative improvement
3. Consider multi-objective optimization

### Real-world Integration

1. Connect to actual parcel station data
2. Add real-time prediction updates
3. Implement parcel pickup simulation

## 📈 Performance Considerations

- **Scalability**: Current implementation handles hundreds of parcels efficiently
- **Memory Usage**: Results are stored in memory; consider streaming for large simulations
- **Computation Time**: Greedy optimization is O(n*m) where n=parcels, m=shelves

## 🤝 Contributing

This is an academic project demonstrating LTO concepts. Key areas for improvement:

1. **Machine Learning**: Implement real ML models for pickup prediction
2. **Optimization**: Add more sophisticated assignment algorithms
3. **Validation**: Compare with baseline strategies (FIFO, random assignment)
4. **Visualization**: Add plots and charts for result analysis

## 📚 References

### Academic Sources
- **Anchor Paper**: "Learn-then-Optimize approaches for robotic warehousing" - 本项目的核心理论基础
- **LTO Framework**: Learn-then-Optimize两阶段决策框架的理论与应用
- **Assignment Problem**: 经典分配问题的数学建模方法
- **Large Neighborhood Search**: 大规模邻域搜索算法在组合优化中的应用

### Industry Context
- **Cainiao Network**: 菜鸟网络智慧物流体系
- **Chinese E-commerce Logistics**: 中国电商物流末端配送模式研究
- **Parcel Station Operations**: 快递驿站运营管理最佳实践

### Technical References
- **Optimization Algorithms**: 贪心算法、禁忌搜索、机器学习指导优化
- **Simulation Modeling**: 离散事件仿真在物流系统中的应用
- **Performance Metrics**: LTO系统效果评估指标体系

### Related Work
- **Warehouse Management**: 仓储管理系统中的智能分配算法
- **Last-mile Delivery**: 末端配送优化问题研究
- **Predictive Analytics**: 预测分析在物流中的应用

## 📄 License

This project is for educational and research purposes. See individual file headers for specific licensing information.

---

**For questions or issues, please refer to the project documentation or contact the development team.** 