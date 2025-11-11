"""
网格策略分析主程序
用户输入股票代码，自动获取数据、优化策略参数、生成图表和报告
"""
import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import Optional

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_source import get_stock_data, DataSourceManager
from grid_strategy import GridStrategyCalculator, save_optimization_results
from chart_visualizer import ChartVisualizer, generate_report


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='网格策略分析工具')
    
    parser.add_argument('stock_code', type=str, help='股票代码，如000001')
    parser.add_argument('--market', type=str, default='SZ', choices=['SZ', 'SH'], 
                       help='市场代码，SZ(深市)或SH(沪市)')
    parser.add_argument('--frequency', type=str, default='日线', 
                       choices=['日线', '5分钟', '15分钟', '30分钟', '60分钟', '周线', '月线', '年线'],
                       help='数据频率')
    parser.add_argument('--start_date', type=str, default=None,
                       help='开始日期，格式YYYYMMDD，默认为一年前')
    parser.add_argument('--end_date', type=str, default=None,
                       help='结束日期，格式YYYYMMDD，默认为今天')
    parser.add_argument('--initial_cash', type=float, default=100000,
                       help='初始资金，默认100000')
    parser.add_argument('--min_up_ratio', type=float, default=0.01,
                       help='最小上涨比例，默认0.01')
    parser.add_argument('--max_up_ratio', type=float, default=0.1,
                       help='最大上涨比例，默认0.1')
    parser.add_argument('--min_down_ratio', type=float, default=0.01,
                       help='最小下跌比例，默认0.01')
    parser.add_argument('--max_down_ratio', type=float, default=0.1,
                       help='最大下跌比例，默认0.1')
    parser.add_argument('--step_size', type=float, default=0.001,
                       help='优化步长，默认0.001(0.1%)')
    parser.add_argument('--adjust', type=str, default='不复权',
                       choices=['不复权', '前复权', '后复权', '等比前复权', '等比后复权'],
                       help='除权方式')
    
    return parser.parse_args()


def setup_default_dates():
    """设置默认日期范围"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # 默认一年数据
    
    return start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")


def get_stock_data_with_retry(stock_code: str, market: str, frequency: str, 
                             adjust: str, start_date: str, end_date: str, 
                             max_retries: int = 3) -> Optional[dict]:
    """带重试机制的数据获取"""
    for attempt in range(max_retries):
        try:
            print(f"📡 第{attempt + 1}次尝试获取数据...")
            
            df = get_stock_data(
                stock_code=stock_code,
                market=market,
                frequency=frequency,
                adjust=adjust,
                start_date=start_date,
                end_date=end_date
            )
            
            if len(df) > 0:
                print(f"✅ 成功获取 {len(df):,} 条数据")
                return df
            else:
                print("⚠️ 未获取到数据，检查股票代码是否正确")
                
        except Exception as e:
            print(f"❌ 获取数据失败: {e}")
            
        if attempt < max_retries - 1:
            print("⏳ 等待2秒后重试...")
            import time
            time.sleep(2)
    
    return None


def run_analysis(args):
    """运行完整分析流程"""
    print("🎯" + "=" * 58 + "🎯")
    print(f"📈 开始分析股票: {args.stock_code}.{args.market}")
    print(f"📊 数据频率: {args.frequency}")
    print("🎯" + "=" * 58 + "🎯")
    
    # 设置日期范围
    if not args.start_date or not args.end_date:
        default_start, default_end = setup_default_dates()
        start_date = args.start_date or default_start
        end_date = args.end_date or default_end
    else:
        start_date = args.start_date
        end_date = args.end_date
    
    print(f"📅 分析期间: {start_date} 到 {end_date}")
    print(f"💰 初始资金: {args.initial_cash:,.0f}")
    
    # 获取股票数据
    df = get_stock_data_with_retry(
        stock_code=args.stock_code,
        market=args.market,
        frequency=args.frequency,
        adjust=args.adjust,
        start_date=start_date,
        end_date=end_date
    )
    
    if df is None or len(df) == 0:
        print("❌ 无法获取股票数据，请检查网络连接和股票代码")
        return False
    
    # 创建网格策略计算器
    calculator = GridStrategyCalculator(df)
    
    # 计算正股收益
    stock_return = calculator.calculate_stock_return(start_date, end_date)
    print(f"📈 正股收益: {stock_return:.2%}")
    
    # 优化网格策略参数
    print(f"\n🎯 参数范围: 上涨[{args.min_up_ratio:.1%}-{args.max_up_ratio:.1%}] "
          f"下跌[{args.min_down_ratio:.1%}-{args.max_down_ratio:.1%}] "
          f"步长{args.step_size:.1%}")
    
    optimization_results = calculator.optimize_grid_parameters(
        initial_cash=args.initial_cash,
        min_up_ratio=args.min_up_ratio,
        max_up_ratio=args.max_up_ratio,
        min_down_ratio=args.min_down_ratio,
        max_down_ratio=args.max_down_ratio,
        step_size=args.step_size,
        start_date=start_date,
        end_date=end_date
    )
    
    best_result = optimization_results.get('best_result')
    
    if not best_result:
        print("❌ 未找到有效的优化结果")
        return False
    
    # 输出优化结果
    print("\n" + "📊" + "=" * 38 + "📊")
    print("✨ 优化结果汇总")
    print("📊" + "=" * 38 + "📊")
    print(f"🎯 最优参数: 上涨{best_result.up_ratio:.1%}, 下跌{best_result.down_ratio:.1%}")
    print(f"💰 策略收益: {best_result.total_return:.2%}")
    print(f"📈 正股收益: {best_result.stock_return:.2%}")
    print(f"🚀 超额收益: {best_result.excess_return:.2%}")
    print(f"📅 年化收益: {best_result.annual_return:.2%}")
    print(f"📉 最大回撤: {best_result.max_drawdown:.2%}")
    print(f"⚖️ 夏普比率: {best_result.sharpe_ratio:.2f}")
    print(f"🔄 交易次数: {best_result.total_trades:,}")
    print(f"🔢 网格数量: {best_result.grid_count:,}")
    
    # 保存优化结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = save_optimization_results(
        optimization_results, 
        f"{args.stock_code}_{timestamp}"
    )
    print(f"\n💾 优化结果已保存: {results_file}")
    
    # 生成图表
    print("\n📊 生成可视化图表...")
    visualizer = ChartVisualizer()
    
    # 创建综合仪表板
    dashboard_file = visualizer.create_comprehensive_dashboard(
        calculator, optimization_results, args.stock_code
    )
    print(f"📈 综合仪表板: {dashboard_file}")
    
    # 创建简单对比图
    comparison_file = visualizer.create_simple_comparison_chart(
        calculator, optimization_results, args.stock_code
    )
    print(f"📊 策略对比图: {comparison_file}")
    
    # 生成报告
    report_file = generate_report(args.stock_code, optimization_results)
    print(f"📋 分析报告: {report_file}")
    
    print("\n" + "🎉" + "=" * 56 + "🎉")
    print("✨ 分析完成!")
    print("🎉" + "=" * 56 + "🎉")
    print("\n📁 生成的资源文件:")
    print(f"1. 📂 数据缓存: data_cache/")
    print(f"2. 📊 优化结果: results/")
    print(f"3. 📈 图表文件: charts/")
    print(f"4. 📋 分析报告: reports/")
    
    return True


def main():
    """主函数"""
    try:
        args = parse_arguments()
        
        success = run_analysis(args)
        
        if success:
            print("\n🎉 分析成功完成！")
            print("📂 可以打开 reports/ 目录下的HTML文件查看详细分析报告")
        else:
            print("\n❌ 分析失败，请检查输入参数")
            
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
    except Exception as e:
        print(f"\n程序执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()