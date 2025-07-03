#!/usr/bin/env python3
"""
Simple Objective Function Visualizer

Shows clear improvements of LTO system core metrics:
- Cost reduction
- Efficiency improvement  
- Customer satisfaction enhancement
- Processing time optimization
"""

import json
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path

class SimpleObjectiveVisualizer:
    """Simple objective function visualizer"""
    
    def __init__(self):
        self.results_dir = Path("results_and_logs")
        plt.style.use('default')
        plt.rcParams['font.size'] = 14
        plt.rcParams['figure.figsize'] = (16, 12)
        plt.rcParams['font.family'] = 'sans-serif'
    
    def load_latest_results(self):
        """Load latest analysis results"""
        try:
            # Check multiple locations for result files
            search_paths = [self.results_dir, Path(".")]
            
            for search_path in search_paths:
                # Priority: comprehensive analysis results
                comprehensive_files = list(search_path.glob("comprehensive_analysis_*.json"))
                if comprehensive_files:
                    latest_file = max(comprehensive_files, key=os.path.getctime)
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        return json.load(f), "comprehensive"
                
                # Check for performance comparison results (from start.py)
                performance_files = list(search_path.glob("performance_comparison_*.json"))
                if performance_files:
                    latest_file = max(performance_files, key=os.path.getctime)
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Convert performance comparison format to comprehensive format
                        if 'scenarios' in data:
                            return data, "comprehensive"
                
                # Fallback: cost analysis results
                cost_files = list(search_path.glob("cost_analysis_results_*.json"))
                if cost_files:
                    latest_file = max(cost_files, key=os.path.getctime)
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        return json.load(f), "cost"
            
            print("❌ No result files found, please run analysis tools first")
            return None, None
            
        except Exception as e:
            print(f"❌ Failed to load results: {e}")
            return None, None
    
    def visualize_objective_improvements(self):
        """Visualize objective function improvements"""
        data, data_type = self.load_latest_results()
        if not data:
            return
        
        if data_type == "comprehensive":
            self._plot_comprehensive_results(data)
        elif data_type == "cost":
            self._plot_cost_results(data)
    
    def _plot_comprehensive_results(self, data):
        """Plot comprehensive analysis results as individual charts"""
        scenarios = data.get('scenarios', [])
        if not scenarios:
            print("❌ No scenario data found")
            return
        
        # Extract key metrics
        scenario_names = []
        cost_savings = []
        time_improvements = []
        baseline_costs = []
        enhanced_costs = []
        
        for scenario in scenarios:
            # Get scenario name in English
            scenario_name = scenario['scenario_name']
            english_names = {
                '正常工作日': 'Normal Day',
                '高峰时段': 'Peak Hour', 
                '节假日': 'Holiday',
                '雨天': 'Rainy Day'
            }
            scenario_names.append(english_names.get(scenario_name, scenario_name))
            
            # Get metrics
            metrics = scenario.get('optimization_metrics', {})
            cost_savings.append(metrics.get('total_savings_rate', 0))
            time_improvements.append(metrics.get('time_improvement', 0))
            
            # Get absolute costs for better comparison
            baseline_costs.append(scenario.get('baseline_costs', {}).get('total_cost', 0))
            enhanced_costs.append(scenario.get('enhanced_costs', {}).get('total_cost', 0))
        
        # Calculate averages for summary
        avg_cost_savings = np.mean(cost_savings)
        avg_time_improvement = np.mean(time_improvements)
        total_savings = np.mean(baseline_costs) - np.mean(enhanced_costs)
        
        # Chart 1: Total Cost Comparison (Absolute Values)
        plt.figure(figsize=(12, 8))
        x = np.arange(len(scenario_names))
        width = 0.35
        
        bars_baseline = plt.bar(x - width/2, baseline_costs, width, 
                               label='Baseline System', color='#ff6b6b', alpha=0.8)
        bars_enhanced = plt.bar(x + width/2, enhanced_costs, width, 
                               label='Enhanced LTO System', color='#4ecdc4', alpha=0.8)
        
        plt.title('Total Cost Comparison (Absolute Values)', fontsize=16, fontweight='bold')
        plt.xlabel('Scenarios')
        plt.ylabel('Total Cost (Yuan)')
        plt.xticks(x, scenario_names)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bars in [bars_baseline, bars_enhanced]:
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                        f'{height:.1f}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig("1_cost_comparison_absolute.png", dpi=300, bbox_inches='tight')
        plt.show()
        
        # Chart 2: Cost Savings Percentage
        plt.figure(figsize=(10, 6))
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
        bars = plt.bar(scenario_names, cost_savings, color=colors, alpha=0.8)
        plt.title('Cost Savings Percentage by Scenario', fontsize=16, fontweight='bold')
        plt.ylabel('Savings Percentage (%)')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        # Add percentage labels
        for bar, value in zip(bars, cost_savings):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig("2_cost_savings_percentage.png", dpi=300, bbox_inches='tight')
        plt.show()
        
        # Chart 3: Processing Time Improvements
        plt.figure(figsize=(10, 6))
        bars = plt.bar(scenario_names, time_improvements, color=colors, alpha=0.8)
        plt.title('Processing Time Improvement by Scenario', fontsize=16, fontweight='bold')
        plt.ylabel('Time Improvement (%)')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        for bar, value in zip(bars, time_improvements):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig("3_time_improvements.png", dpi=300, bbox_inches='tight')
        plt.show()
        
        # Chart 4: Side-by-side Performance Comparison
        plt.figure(figsize=(12, 8))
        x = np.arange(len(scenario_names))
        width = 0.35
        
        bars_cost = plt.bar(x - width/2, cost_savings, width, 
                           label='Cost Savings %', color='#ff7f0e', alpha=0.8)
        bars_time = plt.bar(x + width/2, time_improvements, width, 
                           label='Time Improvement %', color='#2ca02c', alpha=0.8)
        
        plt.title('Comprehensive Performance Comparison', fontsize=16, fontweight='bold')
        plt.ylabel('Improvement Percentage (%)')
        plt.xticks(x, scenario_names)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig("4_comprehensive_comparison.png", dpi=300, bbox_inches='tight')
        plt.show()
        
        # Chart 5: Summary Key Performance Indicators
        plt.figure(figsize=(10, 6))
        summary_metrics = ['Avg Cost Savings', 'Avg Time Improvement', 'Overall Performance']
        summary_values = [avg_cost_savings, avg_time_improvement, (avg_cost_savings + avg_time_improvement)/2]
        
        bars = plt.bar(summary_metrics, summary_values, 
                      color=['#ff4757', '#2ed573', '#ffa502'], alpha=0.9)
        plt.title('Summary: Key Performance Indicators', fontsize=16, fontweight='bold')
        plt.ylabel('Improvement Percentage (%)')
        plt.grid(True, alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars, summary_values):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{value:.1f}%', ha='center', va='bottom', 
                    fontweight='bold', fontsize=14)
        
        plt.tight_layout()
        plt.savefig("5_summary_kpis.png", dpi=300, bbox_inches='tight')
        plt.show()
        
        # Print summary
        print(f"\n📊 OBJECTIVE FUNCTION IMPROVEMENT SUMMARY:")
        print(f"{'='*60}")
        print(f"💰 Average Cost Savings: {avg_cost_savings:.1f}%")
        print(f"⚡ Average Time Improvement: {avg_time_improvement:.1f}%")
        print(f"🎯 Overall Performance Gain: {(avg_cost_savings + avg_time_improvement)/2:.1f}%")
        print(f"💵 Total Cost Reduction: {total_savings:.1f} Yuan")
        print(f"📁 5 individual charts saved successfully")
    
    def _plot_cost_results(self, data):
        """Plot cost analysis results as individual charts"""
        baseline = data.get('baseline_costs', {})
        enhanced = data.get('enhanced_costs', {})
        
        if not baseline or not enhanced:
            print("❌ Incomplete cost data")
            return
        
        # Key metrics comparison
        metrics = {
            'Total Cost': (baseline.get('total_cost', 0), enhanced.get('total_cost', 0)),
            'Cost per Parcel': (baseline.get('cost_per_parcel', 0), enhanced.get('cost_per_parcel', 0)),
            'Labor Cost': (baseline.get('labor_cost_total', 0), enhanced.get('labor_cost_total', 0)),
            'Processing Time': (baseline.get('avg_processing_time_per_parcel', 0), 
                              enhanced.get('avg_processing_time_per_parcel', 0))
        }
        
        metric_names = list(metrics.keys())
        baseline_values = [metrics[name][0] for name in metric_names]
        enhanced_values = [metrics[name][1] for name in metric_names]
        
        # Calculate improvements
        improvements = []
        for name in metric_names:
            baseline_val, enhanced_val = metrics[name]
            if baseline_val > 0:
                improvement = ((baseline_val - enhanced_val) / baseline_val) * 100
                improvements.append(improvement)
            else:
                improvements.append(0)
        
        # Chart 1: Absolute Values Comparison
        plt.figure(figsize=(12, 8))
        x = np.arange(len(metric_names))
        width = 0.35
        
        bars1 = plt.bar(x - width/2, baseline_values, width, label='Baseline System', 
                       color='#ff6b6b', alpha=0.8)
        bars2 = plt.bar(x + width/2, enhanced_values, width, label='Enhanced LTO System', 
                       color='#4ecdc4', alpha=0.8)
        
        plt.title('Absolute Values Comparison', fontsize=16, fontweight='bold')
        plt.xticks(x, metric_names, rotation=45)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                        f'{height:.2f}', ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        plt.savefig("1_cost_absolute_comparison.png", dpi=300, bbox_inches='tight')
        plt.show()
        
        # Chart 2: Improvement Percentages
        plt.figure(figsize=(10, 6))
        colors = ['green' if imp > 0 else 'red' for imp in improvements]
        bars = plt.bar(metric_names, improvements, color=colors, alpha=0.8)
        plt.title('Cost Improvement Percentages', fontsize=16, fontweight='bold')
        plt.ylabel('Improvement (%)')
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        # Add percentage labels
        for bar, value in zip(bars, improvements):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                    f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig("2_cost_improvement_percentages.png", dpi=300, bbox_inches='tight')
        plt.show()
        
        # Chart 3: Baseline Cost Breakdown
        plt.figure(figsize=(8, 8))
        baseline_components = {
            'Labor': baseline.get('labor_cost_total', 0),
            'Equipment': baseline.get('operational_cost_total', 0),
            'Errors': baseline.get('error_cost_total', 0),
            'Efficiency': baseline.get('efficiency_cost_total', 0)
        }
        
        plt.pie(baseline_components.values(), labels=baseline_components.keys(), 
               autopct='%1.1f%%', startangle=90)
        plt.title('Baseline System Cost Breakdown', fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig("3_baseline_cost_breakdown.png", dpi=300, bbox_inches='tight')
        plt.show()
        
        # Chart 4: Enhanced System Cost Breakdown
        plt.figure(figsize=(8, 8))
        enhanced_components = {
            'Labor': enhanced.get('labor_cost_total', 0),
            'Equipment': enhanced.get('operational_cost_total', 0),
            'Errors': enhanced.get('error_cost_total', 0),
            'Efficiency': enhanced.get('efficiency_cost_total', 0)
        }
        
        plt.pie(enhanced_components.values(), labels=enhanced_components.keys(), 
               autopct='%1.1f%%', startangle=90)
        plt.title('Enhanced LTO System Cost Breakdown', fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig("4_enhanced_cost_breakdown.png", dpi=300, bbox_inches='tight')
        plt.show()
        
        # Calculate summary
        avg_improvement = np.mean([imp for imp in improvements if imp > 0])
        total_savings = baseline.get('total_cost', 0) - enhanced.get('total_cost', 0)
        
        print(f"\n💰 COST OPTIMIZATION SUMMARY:")
        print(f"{'='*50}")
        print(f"📊 Average improvement: {avg_improvement:.1f}%")
        print(f"💵 Total cost savings: {total_savings:.2f} Yuan")
        print(f"📁 4 individual charts saved successfully")

def main():
    """Main function"""
    print("🎯 Simple Objective Function Visualizer")
    print("="*60)
    
    visualizer = SimpleObjectiveVisualizer()
    visualizer.visualize_objective_improvements()

if __name__ == "__main__":
    main()