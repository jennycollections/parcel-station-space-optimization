#!/usr/bin/env python3
"""
性能对比分析工具 - 清晰展示优化效果

这个工具会运行不同配置的系统并直观对比结果，
让您清楚看到每个改进带来的具体提升。
"""

import sys
import os
import time
import random
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any

try:
    # 直接导入当前目录下的模块
    from data_structures import Parcel, Shelf, ParcelStation, ParcelSize, ShelfType
    from optimization_module import create_optimizer
    from learning_module import create_predictor
    import config
    print("✅ 基础模块导入成功")
except ImportError as e:
    print(f"❌ 基础模块导入失败: {e}")
    sys.exit(1)

def create_test_environment():
    """创建标准测试环境"""
    station = ParcelStation()
    
    # 添加货架（使用配置中的标准设置）
    for i in range(config.PREMIUM_SHELF_COUNT):
        pos = config.SHELF_POSITIONS['premium'][i]
        shelf = Shelf(
            f"P{i+1}", 
            ShelfType.PREMIUM, 
            matrix_position=pos,
            capacity_small=config.SHELF_CAPACITY['premium'][ParcelSize.SMALL],
            capacity_medium=config.SHELF_CAPACITY['premium'][ParcelSize.MEDIUM],
            capacity_large=config.SHELF_CAPACITY['premium'][ParcelSize.LARGE],
            distance_to_exit=config.SHELF_DISTANCE_SCORES['premium'][i],
            distance_from_entrance=config.SHELF_DISTANCE_SCORES['premium'][i] * 0.8
        )
        station.add_shelf(shelf)
    
    for i in range(config.STANDARD_SHELF_COUNT):
        pos = config.SHELF_POSITIONS['standard'][i]
        shelf = Shelf(
            f"S{i+1}", 
            ShelfType.STANDARD,
            matrix_position=pos,
            capacity_small=config.SHELF_CAPACITY['standard'][ParcelSize.SMALL],
            capacity_medium=config.SHELF_CAPACITY['standard'][ParcelSize.MEDIUM],
            capacity_large=config.SHELF_CAPACITY['standard'][ParcelSize.LARGE],
            distance_to_exit=config.SHELF_DISTANCE_SCORES['standard'][i],
            distance_from_entrance=config.SHELF_DISTANCE_SCORES['standard'][i] * 0.8
        )
        station.add_shelf(shelf)
    
    return station


def generate_test_scenarios():
    """生成多种测试场景"""
    scenarios = []
    
    # 场景1: 轻负载（10个包裹）
    scenarios.append({
        'name': '轻负载场景',
        'parcel_count': 10,
        'description': '低峰时段，包裹较少'
    })
    
    # 场景2: 中等负载（30个包裹）
    scenarios.append({
        'name': '中等负载场景',
        'parcel_count': 30,
        'description': '正常营业时段'
    })
    
    # 场景3: 高负载（50个包裹）
    scenarios.append({
        'name': '高负载场景',
        'parcel_count': 50,
        'description': '高峰时段，包裹密集'
    })
    
    return scenarios


def generate_parcels(count: int, scenario_name: str = "test") -> List[Parcel]:
    """生成测试包裹"""
    parcels = []
    base_time = datetime.now()
    
    for i in range(count):
        # 模拟不同时间到达
        arrival_time = base_time - timedelta(minutes=random.randint(5, 120))
        
        # 根据场景调整包裹分布
        if "高负载" in scenario_name:
            # 高负载时更多大包裹
            size_weights = [0.4, 0.4, 0.2]  # 更多中大包裹
        elif "轻负载" in scenario_name:
            # 轻负载时更多小包裹
            size_weights = [0.7, 0.2, 0.1]  # 更多小包裹
        else:
            # 正常分布
            size_weights = [0.6, 0.3, 0.1]
        
        size = random.choices(
            [ParcelSize.SMALL, ParcelSize.MEDIUM, ParcelSize.LARGE],
            weights=size_weights
        )[0]
        
        parcel = Parcel(
            parcel_id=f"{scenario_name}_{i:03d}",
            arrival_time=arrival_time,
            size=size
        )
        
        parcels.append(parcel)
    
    return parcels


def run_baseline_system(parcels: List[Parcel], station: ParcelStation) -> Dict[str, Any]:
    """运行基线系统（原有SLAP）"""
    print("   🔧 运行基线SLAP系统...")
    
    # 重置站点状态
    reset_station(station)
    
    # 创建优化器和预测器
    optimizer = create_optimizer("slap")
    predictor = create_predictor("rule_based")
    
    # 记录开始时间
    start_time = time.time()
    
    # 处理每个包裹
    results = []
    for parcel in parcels:
        # 预测取件概率
        prob = predictor.predict_pickup_probability(parcel, datetime.now())
        parcel.predicted_pickup_probability = prob
        
        # 分配货架
        assigned_shelf = optimizer.assign_parcel_to_shelf(parcel, station)
        results.append((parcel, assigned_shelf))
    
    # 记录处理时间
    processing_time = time.time() - start_time
    
    # 计算性能指标
    metrics = calculate_detailed_metrics(results, station, "基线系统")
    metrics['processing_time'] = processing_time
    metrics['predictor_type'] = 'rule_based'
    metrics['optimizer_type'] = 'slap_baseline'
    
    return metrics


def run_enhanced_system(parcels: List[Parcel], station: ParcelStation) -> Dict[str, Any]:
    """运行增强系统（带渐进式改进）"""
    print("   🚀 运行增强系统...")
    
    # 重置站点状态
    reset_station(station)
    
    try:
        from progressive_improvement_system import (
            create_ab_testing_system, 
            TestGroup
        )
        
        # 创建基础组件
        base_optimizer = create_optimizer("slap")
        base_predictor = create_predictor("rule_based")
        
        # 创建A/B测试系统
        ab_system = create_ab_testing_system(base_optimizer, base_predictor)
        
        # 初始化ML预测器
        ab_system.initialize_ml_predictor()
        
        # 🔧 关键修复：训练ML模型
        if ab_system.ml_predictor:
            # 生成训练数据
            training_data = []
            for i in range(100):  # 生成100个训练样本
                train_parcel = generate_parcels(1, "training")[0]
                # 模拟真实的取件结果
                actual_picked_up = random.random() > 0.3  # 70%的包裹会被取件
                training_data.append({
                    'parcel': train_parcel,
                    'picked_up': actual_picked_up,
                    'pickup_time': train_parcel.arrival_time + timedelta(hours=random.randint(1, 48))
                })
            
            # 添加训练数据并训练模型
            for data in training_data:
                ab_system.ml_predictor.add_training_data(
                    data['parcel'], data['pickup_time'], data['picked_up']
                )
            
            # 训练模型
            if len(training_data) >= 10:  # 简化检查
                try:
                    ab_system.ml_predictor.train_model()
                    # 验证训练状态
                    is_trained = ab_system.ml_predictor.is_trained
                    print(f"    ✅ ML模型已训练 (样本数: {len(training_data)}, 状态: {is_trained})")
                    
                    # 测试预测功能
                    test_parcel = training_data[0]['parcel']
                    test_prob = ab_system.ml_predictor.predict_pickup_probability(
                        test_parcel, datetime.now()
                    )
                    print(f"    🧪 测试预测: {test_prob:.3f}")
                    
                except Exception as e:
                    print(f"    ⚠️  ML模型训练失败: {e}")
            else:
                print(f"    ⚠️  训练样本不足: {len(training_data)}")
        
        print("    ✅ A/B测试系统已配置")
        
        # 记录开始时间
        start_time = time.time()
        
        # 处理包裹
        ml_usage_count = 0
        
        # 首先进行预测
        for i, parcel in enumerate(parcels):
            request_id = f"perf_test_{i}"
            
            # 调试：检查ML预测器状态
            if i == 0:  # 只打印第一个包裹的调试信息
                ml_available = ab_system.ml_predictor is not None
                ml_trained = ab_system.ml_predictor.is_trained if ml_available else False
                print(f"    🔍 ML调试: 可用={ml_available}, 已训练={ml_trained}")
            
            # 使用A/B测试系统预测 (强制使用ML预测器测试性能)
            if ab_system.ml_predictor and ab_system.ml_predictor.is_trained:
                prob = ab_system.ml_predictor.predict_pickup_probability(parcel, datetime.now())
                predictor_used = "ml_treatment"
                ml_usage_count += 1
            else:
                # 回退到规则预测
                base_predictor = create_predictor("rule_based")
                prob = base_predictor.predict_pickup_probability(parcel, datetime.now())
                predictor_used = "rule_based_control"
            
            parcel.predicted_pickup_probability = prob
                
            # 调试：记录预测器使用情况
            if i == 0:
                print(f"    🧪 第一个包裹预测: {prob:.3f} (使用: {predictor_used})")
        
        # 使用增强优化器进行批量分配
        base_optimizer = create_optimizer("slap")
        results = base_optimizer.batch_assign_parcels(parcels, station)
        optimizer_used = "slap_ml_enhanced"
        
        # 记录处理时间
        processing_time = time.time() - start_time
        
        # 计算性能指标
        metrics = calculate_detailed_metrics(results, station, "增强系统")
        metrics['processing_time'] = processing_time
        metrics['predictor_type'] = 'ml_enhanced'
        metrics['optimizer_type'] = optimizer_used
        metrics['ml_usage_rate'] = ml_usage_count / len(parcels)
        
        return metrics
        
    except ImportError:
        print("     ⚠️ 增强功能不可用，使用基线系统")
        return run_baseline_system(parcels, station)


def reset_station(station: ParcelStation):
    """重置站点状态"""
    # 清空所有货架
    for shelf in station.shelves:
        shelf.parcels_stored.clear()
        for size in ParcelSize:
            shelf.current_used_volume[size] = 0
    
    # 清空存储记录
    station.stored_parcels.clear()
    station.pending_parcels.clear()


def calculate_detailed_metrics(results: List[tuple], station: ParcelStation, system_name: str) -> Dict[str, Any]:
    """计算详细的性能指标"""
    
    if not results:
        return {}
    
    # 基础指标
    total_parcels = len(results)
    successful_assignments = len([r for r in results if r[1] is not None])
    success_rate = successful_assignments / total_parcels
    
    # 分离成功和失败的分配
    successful_results = [(p, s) for p, s in results if s is not None]
    
    if not successful_results:
        return {
            'system_name': system_name,
            'total_parcels': total_parcels,
            'successful_assignments': 0,
            'success_rate': 0.0,
            'customer_convenience': 0.0,
            'employee_workload': 0.0,
            'system_efficiency': 0.0,
            'future_flexibility': 0.0,
            'overall_score': 0.0
        }
    
    # 1. 客户便利性评分
    customer_convenience = calculate_customer_convenience(successful_results)
    
    # 2. 员工工作量评分
    employee_workload = calculate_employee_workload(station)
    
    # 3. 系统效率评分
    system_efficiency = calculate_system_efficiency(station)
    
    # 4. 未来灵活性评分
    future_flexibility = calculate_future_flexibility(successful_results, station)
    
    # 5. 综合评分（使用SLAP权重）
    weights = config.SLAP_OPTIMIZATION_WEIGHTS
    overall_score = (
        weights['customer_convenience'] * customer_convenience +
        weights['employee_workload'] * employee_workload +
        weights['system_efficiency'] * system_efficiency +
        weights['future_flexibility'] * future_flexibility
    )
    
    return {
        'system_name': system_name,
        'total_parcels': total_parcels,
        'successful_assignments': successful_assignments,
        'success_rate': success_rate,
        'customer_convenience': customer_convenience,
        'employee_workload': employee_workload,
        'system_efficiency': system_efficiency,
        'future_flexibility': future_flexibility,
        'overall_score': overall_score,
        'detailed_breakdown': {
            'high_prob_in_premium': count_high_prob_in_premium(successful_results),
            'utilization_balance': calculate_utilization_balance(station),
            'distance_efficiency': calculate_distance_efficiency(successful_results),
            'capacity_usage': calculate_capacity_usage(station)
        }
    }


def calculate_customer_convenience(results: List[tuple]) -> float:
    """计算客户便利性评分（0-1，越高越好）"""
    if not results:
        return 0.0
    
    total_convenience = 0.0
    for parcel, shelf in results:
        # 距离越短越便利，概率越高权重越大
        distance_score = 1.0 - (shelf.distance_to_exit / 5.0)  # 归一化到0-1
        prob_weight = getattr(parcel, 'predicted_pickup_probability', 0.5)
        
        # 高概率包裹在便利位置得分更高
        convenience = distance_score * (0.5 + 0.5 * prob_weight)
        total_convenience += convenience
    
    return total_convenience / len(results)


def calculate_employee_workload(station: ParcelStation) -> float:
    """计算员工工作负载评分（0-1，越高表示负载越均衡）"""
    if not station.shelves:
        return 0.0
    
    # 计算各货架工作负载
    workload_scores = []
    for shelf in station.shelves:
        # 基于距离和包裹数量计算工作负载
        parcel_count = sum(shelf.current_used_volume.values())
        distance_factor = shelf.distance_from_entrance
        workload = parcel_count * (1.0 + distance_factor * 0.1)
        workload_scores.append(workload)
    
    if not workload_scores:
        return 1.0
    
    # 计算负载均衡度（标准差越小越好）
    import numpy as np
    mean_workload = np.mean(workload_scores)
    std_workload = np.std(workload_scores)
    
    # 归一化：标准差越小，评分越高
    if mean_workload == 0:
        return 1.0
    
    balance_score = 1.0 - min(std_workload / mean_workload, 1.0)
    return balance_score


def calculate_system_efficiency(station: ParcelStation) -> float:
    """计算系统效率评分（0-1，越高越好）"""
    if not station.shelves:
        return 0.0
    
    # 计算总体利用率
    total_capacity = 0
    total_used = 0
    
    for shelf in station.shelves:
        capacity = sum(shelf.capacity_volume.values())
        used = sum(shelf.current_used_volume.values())
        total_capacity += capacity
        total_used += used
    
    if total_capacity == 0:
        return 0.0
    
    overall_utilization = total_used / total_capacity
    
    # 计算利用率均衡度
    utilization_rates = []
    for shelf in station.shelves:
        capacity = sum(shelf.capacity_volume.values())
        used = sum(shelf.current_used_volume.values())
        if capacity > 0:
            utilization_rates.append(used / capacity)
    
    if not utilization_rates:
        return 0.0
    
    import numpy as np
    utilization_std = np.std(utilization_rates)
    balance_factor = 1.0 - min(utilization_std, 1.0)
    
    # 综合评分：利用率 × 平衡度
    efficiency_score = overall_utilization * (0.7 + 0.3 * balance_factor)
    
    return min(efficiency_score, 1.0)


def calculate_future_flexibility(results: List[tuple], station: ParcelStation) -> float:
    """计算未来灵活性评分（0-1，越高越好）"""
    if not results:
        return 0.0
    
    premium_shelves = [s for s in station.shelves if s.location_type == ShelfType.PREMIUM]
    if not premium_shelves:
        return 0.5
    
    # 统计高概率包裹在premium货架的比例
    high_prob_in_premium = 0
    total_high_prob = 0
    
    for parcel, shelf in results:
        prob = getattr(parcel, 'predicted_pickup_probability', 0.5)
        if prob > 0.7:  # 高概率阈值
            total_high_prob += 1
            if shelf in premium_shelves:
                high_prob_in_premium += 1
    
    if total_high_prob == 0:
        return 0.8  # 无高概率包裹时给中等评分
    
    # 高概率包裹在premium货架的比例
    good_allocation_rate = high_prob_in_premium / total_high_prob
    
    # 计算premium货架剩余容量（为未来高概率包裹预留）
    premium_capacity = sum(sum(s.capacity_volume.values()) for s in premium_shelves)
    premium_used = sum(sum(s.current_used_volume.values()) for s in premium_shelves)
    
    if premium_capacity > 0:
        premium_utilization = premium_used / premium_capacity
        # 利用率适中（60-80%）最佳，既充分利用又保留灵活性
        flexibility_factor = 1.0 - abs(premium_utilization - 0.7) / 0.7
    else:
        flexibility_factor = 0.0
    
    # 综合评分
    flexibility_score = 0.6 * good_allocation_rate + 0.4 * flexibility_factor
    
    return min(flexibility_score, 1.0)


def count_high_prob_in_premium(results: List[tuple]) -> Dict[str, int]:
    """统计高概率包裹在premium货架的分布"""
    high_prob_total = 0
    high_prob_in_premium = 0
    
    for parcel, shelf in results:
        prob = getattr(parcel, 'predicted_pickup_probability', 0.5)
        if prob > 0.7:
            high_prob_total += 1
            if shelf.location_type == ShelfType.PREMIUM:
                high_prob_in_premium += 1
    
    return {
        'high_prob_total': high_prob_total,
        'high_prob_in_premium': high_prob_in_premium,
        'allocation_rate': high_prob_in_premium / max(high_prob_total, 1)
    }


def calculate_utilization_balance(station: ParcelStation) -> float:
    """计算利用率平衡度"""
    utilization_rates = []
    
    for shelf in station.shelves:
        capacity = sum(shelf.capacity_volume.values())
        used = sum(shelf.current_used_volume.values())
        if capacity > 0:
            utilization_rates.append(used / capacity)
    
    if not utilization_rates:
        return 1.0
    
    import numpy as np
    return 1.0 - min(np.std(utilization_rates), 1.0)


def calculate_distance_efficiency(results: List[tuple]) -> float:
    """计算距离效率"""
    if not results:
        return 0.0
    
    total_weighted_distance = 0.0
    total_weight = 0.0
    
    for parcel, shelf in results:
        prob = getattr(parcel, 'predicted_pickup_probability', 0.5)
        distance = shelf.distance_to_exit
        
        # 高概率包裹的距离权重更大
        weight = prob
        total_weighted_distance += distance * weight
        total_weight += weight
    
    if total_weight == 0:
        return 0.0
    
    avg_weighted_distance = total_weighted_distance / total_weight
    
    # 距离越短效率越高（最大距离假设为5.0）
    return 1.0 - min(avg_weighted_distance / 5.0, 1.0)


def calculate_capacity_usage(station: ParcelStation) -> float:
    """计算容量使用率"""
    total_capacity = sum(sum(s.capacity_volume.values()) for s in station.shelves)
    total_used = sum(sum(s.current_used_volume.values()) for s in station.shelves)
    
    if total_capacity == 0:
        return 0.0
    
    return total_used / total_capacity


def print_comparison_results(baseline_metrics: Dict, enhanced_metrics: Dict, scenario_name: str):
    """打印对比结果"""
    print(f"\n{'='*60}")
    print(f"📊 {scenario_name} - 性能对比结果")
    print(f"{'='*60}")
    
    print(f"\n📦 基础信息:")
    print(f"   包裹总数: {baseline_metrics['total_parcels']}")
    print(f"   基线成功率: {baseline_metrics['success_rate']:.1%}")
    print(f"   增强成功率: {enhanced_metrics['success_rate']:.1%}")
    
    if 'processing_time' in baseline_metrics and 'processing_time' in enhanced_metrics:
        print(f"   基线处理时间: {baseline_metrics['processing_time']:.3f}秒")
        print(f"   增强处理时间: {enhanced_metrics['processing_time']:.3f}秒")
    
    print(f"\n🎯 核心指标对比:")
    
    metrics_names = [
        ('customer_convenience', '客户便利性'),
        ('employee_workload', '员工工作量'),
        ('system_efficiency', '系统效率'),
        ('future_flexibility', '未来灵活性'),
        ('overall_score', '📊 综合评分')
    ]
    
    improvements = []
    
    for key, name in metrics_names:
        baseline_val = baseline_metrics.get(key, 0)
        enhanced_val = enhanced_metrics.get(key, 0)
        
        if baseline_val > 0:
            improvement = ((enhanced_val - baseline_val) / baseline_val) * 100
        else:
            improvement = 0
        
        improvements.append(improvement)
        
        # 选择合适的图标
        if improvement > 5:
            icon = "🚀"
        elif improvement > 2:
            icon = "📈"
        elif improvement > 0:
            icon = "✅"
        elif improvement > -2:
            icon = "➡️"
        else:
            icon = "📉"
        
        print(f"   {icon} {name:12}: {baseline_val:.3f} → {enhanced_val:.3f} ({improvement:+.1f}%)")
    
    # 总体评估
    overall_improvement = improvements[-1]  # 综合评分的改进
    
    print(f"\n🎯 优化效果评估:")
    if overall_improvement > 10:
        print(f"   🌟 显著优化！性能提升 {overall_improvement:.1f}%")
    elif overall_improvement > 5:
        print(f"   ✨ 明显改进！性能提升 {overall_improvement:.1f}%")
    elif overall_improvement > 2:
        print(f"   📈 轻微提升，性能提升 {overall_improvement:.1f}%")
    elif overall_improvement > -2:
        print(f"   ➡️ 性能基本持平 ({overall_improvement:+.1f}%)")
    else:
        print(f"   ⚠️ 性能有所下降 ({overall_improvement:.1f}%)")
    
    # 详细分析
    if 'detailed_breakdown' in enhanced_metrics:
        breakdown = enhanced_metrics['detailed_breakdown']
        print(f"\n🔍 详细分析:")
        
        high_prob_stats = breakdown.get('high_prob_in_premium', {})
        if high_prob_stats:
            rate = high_prob_stats.get('allocation_rate', 0)
            total = high_prob_stats.get('high_prob_total', 0)
            premium_count = high_prob_stats.get('high_prob_in_premium', 0)
            print(f"   📍 高概率包裹优先分配: {premium_count}/{total} ({rate:.1%})")
        
        balance = breakdown.get('utilization_balance', 0)
        print(f"   ⚖️ 负载均衡度: {balance:.3f}")
        
        distance_eff = breakdown.get('distance_efficiency', 0)
        print(f"   🎯 距离效率: {distance_eff:.3f}")
        
        capacity = breakdown.get('capacity_usage', 0)
        print(f"   📦 容量使用率: {capacity:.1%}")
    
    # ML使用统计
    if 'ml_usage_rate' in enhanced_metrics:
        ml_rate = enhanced_metrics['ml_usage_rate']
        print(f"   🤖 ML预测使用率: {ml_rate:.1%}")


def main():
    """主函数"""
    print("🎯 菜鸟驿站LTO系统 - 性能对比分析")
    print("=" * 60)
    print("📋 本工具将对比基线系统 vs 增强系统的性能差异")
    print("💡 通过实际运行展示每个优化带来的具体提升")
    print("-" * 60)
    
    # 创建测试环境
    print("\n🏗️ 创建测试环境...")
    station = create_test_environment()
    print(f"   ✅ 驿站创建完成: {len(station.shelves)}个货架")
    print(f"      - Premium货架: {len([s for s in station.shelves if s.location_type == ShelfType.PREMIUM])}个")
    print(f"      - Standard货架: {len([s for s in station.shelves if s.location_type == ShelfType.STANDARD])}个")
    
    # 获取测试场景
    scenarios = generate_test_scenarios()
    
    # 汇总结果
    summary_results = []
    
    # 运行每个场景
    for scenario in scenarios:
        print(f"\n🎬 运行场景: {scenario['name']} ({scenario['description']})")
        print("-" * 40)
        
        # 生成测试包裹
        parcels = generate_parcels(scenario['parcel_count'], scenario['name'])
        print(f"   📦 生成测试包裹: {len(parcels)}个")
        
        # 统计包裹分布
        size_counts = {size: 0 for size in ParcelSize}
        for parcel in parcels:
            size_counts[parcel.size] += 1
        
        print(f"      - 小包裹: {size_counts[ParcelSize.SMALL]}个")
        print(f"      - 中包裹: {size_counts[ParcelSize.MEDIUM]}个")  
        print(f"      - 大包裹: {size_counts[ParcelSize.LARGE]}个")
        
        # 运行基线系统
        baseline_metrics = run_baseline_system(parcels.copy(), station)
        
        # 运行增强系统
        enhanced_metrics = run_enhanced_system(parcels.copy(), station)
        
        # 打印对比结果
        print_comparison_results(baseline_metrics, enhanced_metrics, scenario['name'])
        
        # 保存结果用于汇总
        summary_results.append({
            'scenario': scenario,
            'baseline': baseline_metrics,
            'enhanced': enhanced_metrics
        })
    
    # 打印总体汇总
    print_overall_summary(summary_results)
    
    # 保存详细结果
    save_detailed_results(summary_results)


def print_overall_summary(results: List[Dict]):
    """打印总体汇总"""
    print(f"\n{'='*60}")
    print("🏆 总体性能汇总")
    print(f"{'='*60}")
    
    total_improvements = []
    
    print(f"\n📈 各场景综合评分对比:")
    for result in results:
        scenario_name = result['scenario']['name']
        baseline_score = result['baseline'].get('overall_score', 0)
        enhanced_score = result['enhanced'].get('overall_score', 0)
        
        if baseline_score > 0:
            improvement = ((enhanced_score - baseline_score) / baseline_score) * 100
        else:
            improvement = 0
        
        total_improvements.append(improvement)
        
        # 选择图标
        if improvement > 5:
            icon = "🚀"
        elif improvement > 2:
            icon = "📈"
        elif improvement > 0:
            icon = "✅"
        else:
            icon = "➡️"
        
        print(f"   {icon} {scenario_name:12}: {baseline_score:.3f} → {enhanced_score:.3f} ({improvement:+.1f}%)")
    
    # 计算平均改进
    if total_improvements:
        avg_improvement = sum(total_improvements) / len(total_improvements)
        
        print(f"\n🎯 总体评估:")
        print(f"   平均性能提升: {avg_improvement:+.1f}%")
        
        if avg_improvement > 10:
            print("   🌟 系统获得显著优化！建议全面启用增强功能")
        elif avg_improvement > 5:
            print("   ✨ 系统明显改进！建议逐步推广增强功能")
        elif avg_improvement > 2:
            print("   📈 系统轻微提升，可考虑在低风险环境使用")
        elif avg_improvement > -2:
            print("   ➡️ 系统性能基本持平，增强功能可作为备选")
        else:
            print("   ⚠️ 增强功能表现不佳，建议继续使用基线系统")
    
    print(f"\n💡 使用建议:")
    print(f"   🔒 保守方案: python start.py --mode safe    # 使用基线系统")
    print(f"   🧪 测试方案: python start.py --mode test    # 5%流量使用增强功能")
    print(f"   🚀 激进方案: python start.py --mode full    # 全面使用增强功能")


def save_detailed_results(results: List[Dict]):
    """保存详细结果到文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"performance_comparison_{timestamp}.json"
    
    # 准备保存的数据
    save_data = {
        'timestamp': timestamp,
        'test_info': {
            'description': '菜鸟驿站LTO系统性能对比',
            'scenarios_tested': len(results),
            'comparison_type': 'baseline_vs_enhanced'
        },
        'results': results,
        'summary': {
            'avg_improvement': 0.0,
            'best_scenario': '',
            'worst_scenario': ''
        }
    }
    
    # 计算汇总信息
    improvements = []
    for result in results:
        baseline_score = result['baseline'].get('overall_score', 0)
        enhanced_score = result['enhanced'].get('overall_score', 0)
        
        if baseline_score > 0:
            improvement = ((enhanced_score - baseline_score) / baseline_score) * 100
            improvements.append((improvement, result['scenario']['name']))
    
    if improvements:
        save_data['summary']['avg_improvement'] = sum([imp for imp, _ in improvements]) / len(improvements)
        save_data['summary']['best_scenario'] = max(improvements, key=lambda x: x[0])[1]
        save_data['summary']['worst_scenario'] = min(improvements, key=lambda x: x[0])[1]
    
    # 保存文件
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n📁 详细结果已保存到: {filename}")
    except Exception as e:
        print(f"\n⚠️ 保存结果文件失败: {e}")


if __name__ == "__main__":
    try:
        main()
        print(f"\n✅ 性能对比分析完成！")
    except KeyboardInterrupt:
        print(f"\n⚠️ 分析被用户中断")
    except Exception as e:
        print(f"\n❌ 分析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()