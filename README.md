# Advanced-analytics-in-planning-automated-warehousing-operations
Learn-then-optimize (LTO) approach is simulated to apply in Cainiao Station in China.

1. Project Overview
这里需要定义问题

2. 算法解释

3. 代码解释

   3.1 config.py: this module contains all configurable parameters for the simulation, including shelf configurations, parcel generation parameters, and simulation settings.
   
   ### SHELF CONFIGURATION
   
   #### Shelf Type (`location_type`)

   定义: 货架的位置类型分类

   数据类型: `ShelfType` 枚举

   取值: `PREMIUM` (优质位置), `STANDARD` (标准位置)

   分布: 3个Premium货架, 5个Standard货架

   | 特征     | Premium | Standard |
   | -------- | ------- | -------- |
   | 距离评分 | 1.0-1.5 | 2.0-4.0  |
   | 容量     | 较小    | 较大     |
   | 便利度   | 高      | 中等     |
   | 竞争度   | 高      | 低       |

   设计理念: 二分类，简化决策复杂度；差异化，明确的便利度和容量差异；稀缺性，Premium货架数量有限，创造竞争。

    #### Distance to Exit (`distance_to_exit`)

   定义: 货架到出口的距离/便利度评分

   数据类型: `float`

   取值: 1.0 - 4.0（数值越小表示位置越便利，取件越容易）

   分布:

   ```python
   SHELF_DISTANCE_SCORES = {
       'premium': [1.0, 1.2, 1.5],           # 最便利位置
       'standard': [2.0, 2.5, 3.0, 3.5, 4.0] # 相对不便利位置
   }
   ```

   设计理念:
   抽象化: 不使用实际物理距离（米），而是便利度的相对评分
   成本导向: 在目标函数中作为成本系数，数值越大"惩罚"越重
   可扩展性: 可根据实际快递站布局调整评分标准

   ### PARCEL GENERATION PARAMETERS

   #### Time Parameters

   时间步长(`TIME_STEP_MINUTES`): 30分钟

   设计理念: 平衡计算效率和时间精度

   模拟时长(`SIMULATION_HOURS`): 12小时

   设计理念: 覆盖一个完整的营业日

   到达率(`PARCEL_ARRIVAL_RATES`): 4-18包裹/小时

   设计理念: 基于中小型快递站的实际业务量

   时间段(`TIME_PERIODS`)

   定义: 一天中的不同时间段分类

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

   设计理念:
   用户行为: 反映中国用户的取件时间偏好
   业务逻辑: (上班前)、午休、下班后是取件高峰
   预测基础: 为概率预测提供时间特征

   #### Parcel Size

   定义: 包裹的尺寸分类

   数据类型: `ParcelSize` 枚举

   取值: `SMALL`, `MEDIUM`, `LARGE`

   分布: 60% 小件, 30% 中件, 10% 大件

   容量影响:

   ```python
   SHELF_CAPACITY = {
       'premium': {SMALL: 8, MEDIUM: 4, LARGE: 2},
       'standard': {SMALL: 12, MEDIUM: 6, LARGE: 3}
   }
   ```

   设计理念:
   简化分类: 避免连续尺寸的复杂性
   容量约束: 不同尺寸占用不同货架空间
   现实分布: 基于电商包裹的典型尺寸分布

   ### LEARNING MODULE PARAMETERS
   
   #### Pickup Probability (`predicted_pickup_probability`) ?

   定义: 包裹在未来特定时间内被取走的概率

   数据类型: `float`

   范围: 0.0 - 1.0（1.0表示肯定会被取走，0.0表示不太可能被取走）

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

   影响因素:
   时间段: 高峰期概率更高
   包裹大小: 大包裹概率略低（需要规划取件）
   随机噪声: ±0.1的随机变化模拟不确定性

   设计理念:
   时间相关性: 反映用户取件的时间偏好
   现实性: 基于对中国快递站用户行为的观察
   可替换性: 未来可用ML模型替换规则

   ### OPTIMIZATION MODULE PARAMETERS

   ### VALIDATION PARAMETERS

   定义：？

   取值：HIGH_PROBABILITY_THRESHOLD >= 0.7

   验证范围:
   ```python
   MIN_PROBABILITY = 0.0
   MAX_PROBABILITY = 1.0
   MIN_DISTANCE_SCORE = 0.1
   MAX_DISTANCE_SCORE = 10.0
   ```

   设计理念: 模拟真实的空间约束
   
   #### 我没找到assignment cost
   #### 这个部分的设置应该基于一定的现实考察，所以需要更多的数据支持

   3.2 data_structures.py: this module defines the fundamental classes used throughout the simulation, including Parcel, Shelf, and ParcelStation.

   3.3 learning_module.py: this module currently uses rule-based prediction model to predict pickup probability (p_hat_i) for each parcel,
based on features like arrival time, parcel size, and time period.
   #### 这个部分未来会进一步使用machine learning model

   3.4 optimization_module.py: it uses the predicted pickup probabilities from the learning module to make intelligent parcel-to-shelf assignment decisions.

   #### 这里我忽然想到一个问题就是国内的货架摆放好像是基于产品种类（可能和运输过程的货物摆放有关系），如果我们现在按照产品被取走的概率摆放货物，可能给快递员带来更多的工作量。所以，我觉着应该进一步弄清楚原来的快递摆放规则。

   3.5 simulation_engine.py: this module is to collect data by generating parcel arrivals over time, using the learning module to predict pickup probabilities, using the optimization module to assign parcels to shelves.

   3.6 main.py: this module utilized the data collected from the simulation_engine.py to demonstrate the "Learn-then-Optimize" workflow for parcel station management.
  
4. 结果解释
### Key Metrics

- **LTO Alignment Score**: How well the system assigns high-probability parcels to premium shelves
- **Average Assignment Cost**: Overall cost based on the objective function
- **Shelf Utilization**: How efficiently different shelf types are used
- **Premium Assignment Ration**: Percentage of parcels assigned to premium shelves

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

5. 结果优化

6. Reference
Barnhart, C., Jacquillat, A., & Schmid, A. (2024). Robotic warehousing operations: a learn-then-optimize approach to large-scale neighborhood search. INFORMS Journal on Optimization.
