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

### 发现的问题与改进方向

#### 问题1: 相同成本货架的处理机制

**问题描述**:
当多个货架的总成本 `total_cost = basic_cost + utilization_penalty` 完全相同时，当前代码采用"先到先得"机制：

```python
if total_cost < best_cost:  # 注意：使用"<"而非"<="
    best_cost = total_cost
    best_shelf = shelf
```

**潜在影响**:

- ❌ **依赖遍历顺序**: 结果取决于`available_shelves`列表的顺序
- ❌ **可能不公平**: 总是偏向列表中靠前的货架
- ❌ **缺乏随机性**: 在完全相同情况下缺乏随机选择

**改进建议**:

```python
# 方案1: 随机选择（推荐）
def _select_best_shelf(self, parcel, available_shelves):
    best_shelves = []  # 存储所有最佳货架
    best_cost = float('inf')
    
    for shelf in available_shelves:
        total_cost = calculate_total_cost(shelf, parcel)
        if total_cost < best_cost:
            best_cost = total_cost
            best_shelves = [shelf]
        elif total_cost == best_cost:
            best_shelves.append(shelf)
    
    return random.choice(best_shelves)  # 随机选择
```

#### 问题2: 相同概率包裹的分配顺序

**问题描述**:
批量分配时，当多个包裹具有相同的预测概率时，当前排序逻辑：

```python
sorted_parcels = sorted(parcels, key=lambda p: p.predicted_pickup_probability or 0, reverse=True)
```

只考虑概率单一维度，相同概率的包裹按原始输入顺序分配。

**潜在影响**:

- ❌ **依赖输入顺序**: 先输入的包裹总是优先获得好位置
- ❌ **缺乏优化考虑**: 未考虑包裹尺寸、到达时间等因素
- ❌ **可能不公平**: 对相同概率包裹处理不够智能

**改进建议**:

```python
# 方案1: 多级排序（推荐）
def batch_assign_parcels(self, parcels, station):
    def sort_key(parcel):
        return (
            -(parcel.predicted_pickup_probability or 0),  # 概率高优先
            parcel.size.value,                           # 小包裹优先
            parcel.arrival_time                          # 早到优先
        )
    
    sorted_parcels = sorted(parcels, key=sort_key)
    # ... 后续分配逻辑
```

**排序优先级逻辑**:

1. **概率**: 高概率包裹优先（主要因素）
2. **尺寸**: 小包裹优先（便于携带，更可能及时取走）
3. **到达时间**: 早到的优先（避免长时间积压）

#### 问题3: 缺乏包裹等待机制 ⚠️ **重要**

**问题描述**:
当所有货架都满了时，系统缺乏完整的包裹等待和重试机制：

**基础版本问题**:

```python
def assign_parcel_to_shelf(self, parcel, station):
    available_shelves = station.get_available_shelves(parcel.size, preferred_type)
    
    if not available_shelves:
        self.logger.warning(f"No available shelves for parcel {parcel.parcel_id}")
        return None  # ❌ 直接失败，包裹丢失
```

**增强版本问题**:

- ✅ 有 `pending_placement_queue`（工人处理队列）
- ❌ 但没有 `shelf_waiting_queue`（货架等待队列）
- ❌ 分配失败的包裹直接消失

**潜在影响**:

- ❌ **包裹丢失**: 分配失败的包裹没有保存
- ❌ **客户体验差**: 包裹到达却无法存储
- ❌ **系统不完整**: 缺乏真实场景的处理能力
- ❌ **无法处理高峰**: 高峰期所有货架满时系统崩溃

**改进建议**:

```python
class EnhancedParcelStation(ParcelStation):
    def __init__(self):
        super().__init__()
        self.shelf_waiting_queue = []  # 等待货架空出的包裹队列
        self.max_waiting_time = timedelta(hours=24)  # 最大等待时间
        
    def add_waiting_parcel(self, parcel: Parcel):
        """将包裹加入等待队列"""
        parcel.waiting_start_time = datetime.now()
        self.shelf_waiting_queue.append(parcel)
        self.logger.info(f"Parcel {parcel.parcel_id} added to waiting queue")
    
    def try_assign_waiting_parcels(self):
        """尝试为等待队列中的包裹分配货架"""
        assigned_count = 0
        remaining_parcels = []
        
        for parcel in self.shelf_waiting_queue:
            # 检查是否超时
            if datetime.now() - parcel.waiting_start_time > self.max_waiting_time:
                self.logger.warning(f"Parcel {parcel.parcel_id} waiting timeout")
                continue
            
            # 尝试分配
            assigned_shelf = self.optimizer.assign_parcel_to_shelf(parcel, self)
            if assigned_shelf:
                assigned_count += 1
                self.logger.info(f"Waiting parcel {parcel.parcel_id} assigned to {assigned_shelf.shelf_id}")
            else:
                remaining_parcels.append(parcel)
        
        self.shelf_waiting_queue = remaining_parcels
        return assigned_count

# 修改优化器
class EnhancedOptimizer(ParcelAssignmentOptimizer):
    def assign_parcel_to_shelf(self, parcel, station):
        # 先尝试正常分配
        result = super().assign_parcel_to_shelf(parcel, station)
        
        if result is None:
            # 分配失败，加入等待队列
            station.add_waiting_parcel(parcel)
            return "WAITING"  # 返回等待状态而非None
        
        return result
```

**等待机制触发时机**:

1. **包裹被取走时**: 货架空出位置，触发等待队列处理
2. **定期检查**: 每隔一定时间检查等待队列
3. **新货架添加时**: 系统扩容时重新分配等待包裹
4. **重优化时**: LSNS重优化可能为等待包裹找到更好方案
5. 结果优化

6. Reference
Barnhart, C., Jacquillat, A., & Schmid, A. (2024). Robotic warehousing operations: a learn-then-optimize approach to large-scale neighborhood search. INFORMS Journal on Optimization.
