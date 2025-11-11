"""
HTML图表可视化模块
用于生成网格策略结果的交互式图表
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
import json
import os
from typing import Dict, List
from grid_strategy import GridStrategyCalculator, StrategyResult


class ChartVisualizer:
    """图表可视化器"""
    
    def __init__(self):
        self.template = "plotly_white"
        self.color_scheme = {
            'strategy': '#1f77b4',
            'stock': '#ff7f0e', 
            'buy': '#2ca02c',
            'sell': '#d62728',
            'cash': '#9467bd',
            'grid': '#8c564b'
        }
    
    def create_comprehensive_dashboard(self, calculator: GridStrategyCalculator,
                                     optimization_results: Dict,
                                     stock_code: str) -> str:
        """创建综合仪表板"""
        
        # 创建子图布局
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                '价格走势与交易点', '网格策略收益曲线',
                '参数优化热力图', '收益分布对比',
                '交易统计', '风险指标对比'
            ),
            specs=[[{"secondary_y": True}, {}],
                   [{}, {}],
                   [{}, {}]],
            vertical_spacing=0.08,
            horizontal_spacing=0.08
        )
        
        # 1. 价格走势与交易点
        self._add_price_chart(fig, calculator, optimization_results, row=1, col=1)
        
        # 2. 网格策略收益曲线
        self._add_return_chart(fig, calculator, optimization_results, row=1, col=2)
        
        # 3. 参数优化热力图
        self._add_heatmap(fig, optimization_results, row=2, col=1)
        
        # 4. 收益分布对比
        self._add_return_distribution(fig, optimization_results, row=2, col=2)
        
        # 5. 交易统计
        self._add_trade_statistics(fig, optimization_results, row=3, col=1)
        
        # 6. 风险指标对比
        self._add_risk_metrics(fig, optimization_results, row=3, col=2)
        
        # 更新布局
        fig.update_layout(
            height=1200,
            title_text=f"{stock_code} 网格策略优化分析仪表板",
            template=self.template,
            showlegend=True
        )
        
        return self._save_chart(fig, f"{stock_code}_dashboard")
    
    def _add_price_chart(self, fig, calculator, optimization_results, row, col):
        """添加价格走势图"""
        best_result = optimization_results.get('best_result')
        
        if best_result:
            # 获取价格数据
            prices = best_result.daily_values.set_index('date')['price']
            
            # 添加价格线
            fig.add_trace(
                go.Scatter(
                    x=prices.index,
                    y=prices.values,
                    name='股票价格',
                    line=dict(color=self.color_scheme['stock'], width=2)
                ),
                row=row, col=col, secondary_y=False
            )
            
            # 添加交易点
            buy_points = [t for t in best_result.trade_records if t.direction.value == 'buy']
            sell_points = [t for t in best_result.trade_records if t.direction.value == 'sell']
            
            if buy_points:
                fig.add_trace(
                    go.Scatter(
                        x=[t.datetime for t in buy_points],
                        y=[t.price for t in buy_points],
                        mode='markers',
                        name='买入点',
                        marker=dict(
                            color=self.color_scheme['buy'],
                            size=8,
                            symbol='triangle-up'
                        )
                    ),
                    row=row, col=col, secondary_y=False
                )
            
            if sell_points:
                fig.add_trace(
                    go.Scatter(
                        x=[t.datetime for t in sell_points],
                        y=[t.price for t in sell_points],
                        mode='markers',
                        name='卖出点',
                        marker=dict(
                            color=self.color_scheme['sell'],
                            size=8,
                            symbol='triangle-down'
                        )
                    ),
                    row=row, col=col, secondary_y=False
                )
    
    def _add_return_chart(self, fig, calculator, optimization_results, row, col):
        """添加收益曲线图"""
        best_result = optimization_results.get('best_result')
        
        if best_result:
            daily_values = best_result.daily_values
            
            # 计算累计收益
            daily_values['strategy_return'] = (
                daily_values['total_value'] / daily_values['total_value'].iloc[0] - 1
            )
            daily_values['stock_return'] = (
                daily_values['price'] / daily_values['price'].iloc[0] - 1
            )
            
            # 添加策略收益曲线
            fig.add_trace(
                go.Scatter(
                    x=daily_values['date'],
                    y=daily_values['strategy_return'],
                    name='策略收益',
                    line=dict(color=self.color_scheme['strategy'], width=3)
                ),
                row=row, col=col
            )
            
            # 添加股票收益曲线
            fig.add_trace(
                go.Scatter(
                    x=daily_values['date'],
                    y=daily_values['stock_return'],
                    name='股票收益',
                    line=dict(color=self.color_scheme['stock'], width=2, dash='dash')
                ),
                row=row, col=col
            )
    
    def _add_heatmap(self, fig, optimization_results, row, col):
        """添加参数优化热力图"""
        all_results = optimization_results.get('all_results', pd.DataFrame())
        
        if not all_results.empty:
            # 创建热力图数据
            heatmap_data = all_results.pivot_table(
                index='up_ratio', 
                columns='down_ratio', 
                values='excess_return', 
                aggfunc='mean'
            )
            
            fig.add_trace(
                go.Heatmap(
                    z=heatmap_data.values,
                    x=heatmap_data.columns,
                    y=heatmap_data.index,
                    colorscale='Viridis',
                    colorbar=dict(title="超额收益")
                ),
                row=row, col=col
            )
    
    def _add_return_distribution(self, fig, optimization_results, row, col):
        """添加收益分布对比图"""
        all_results = optimization_results.get('all_results', pd.DataFrame())
        
        if not all_results.empty:
            fig.add_trace(
                go.Histogram(
                    x=all_results['excess_return'],
                    name='超额收益分布',
                    nbinsx=30,
                    marker_color=self.color_scheme['strategy'],
                    opacity=0.7
                ),
                row=row, col=col
            )
    
    def _add_trade_statistics(self, fig, optimization_results, row, col):
        """添加交易统计图"""
        best_result = optimization_results.get('best_result')
        
        if best_result:
            trade_stats = {
                '买入次数': best_result.buy_trades,
                '卖出次数': best_result.sell_trades,
                '总交易次数': best_result.total_trades
            }
            
            fig.add_trace(
                go.Bar(
                    x=list(trade_stats.keys()),
                    y=list(trade_stats.values()),
                    marker_color=[self.color_scheme['buy'], 
                                 self.color_scheme['sell'], 
                                 self.color_scheme['strategy']]
                ),
                row=row, col=col
            )
    
    def _add_risk_metrics(self, fig, optimization_results, row, col):
        """添加风险指标对比图"""
        best_result = optimization_results.get('best_result')
        
        if best_result:
            risk_metrics = {
                '年化收益': best_result.annual_return,
                '最大回撤': best_result.max_drawdown,
                '夏普比率': best_result.sharpe_ratio
            }
            
            fig.add_trace(
                go.Bar(
                    x=list(risk_metrics.keys()),
                    y=list(risk_metrics.values()),
                    marker_color=['#1f77b4', '#ff7f0e', '#2ca02c']
                ),
                row=row, col=col
            )
    
    def create_simple_comparison_chart(self, calculator: GridStrategyCalculator,
                                     optimization_results: Dict,
                                     stock_code: str) -> str:
        """创建简单对比图表"""
        
        best_result = optimization_results.get('best_result')
        
        if not best_result:
            return ""
        
        # 创建收益对比图
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('收益曲线对比', '持仓价值变化'),
            vertical_spacing=0.1
        )
        
        # 收益曲线对比
        daily_values = best_result.daily_values
        daily_values['strategy_cum_return'] = (
            daily_values['total_value'] / daily_values['total_value'].iloc[0]
        )
        daily_values['stock_cum_return'] = (
            daily_values['price'] / daily_values['price'].iloc[0]
        )
        
        fig.add_trace(
            go.Scatter(
                x=daily_values['date'],
                y=daily_values['strategy_cum_return'],
                name='网格策略',
                line=dict(color=self.color_scheme['strategy'], width=3)
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=daily_values['date'],
                y=daily_values['stock_cum_return'],
                name='买入持有',
                line=dict(color=self.color_scheme['stock'], width=2, dash='dash')
            ),
            row=1, col=1
        )
        
        # 持仓价值变化
        fig.add_trace(
            go.Scatter(
                x=daily_values['date'],
                y=daily_values['cash'],
                name='现金',
                stackgroup='one',
                line=dict(color=self.color_scheme['cash'])
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=daily_values['date'],
                y=daily_values['stock_value'],
                name='股票价值',
                stackgroup='one',
                line=dict(color=self.color_scheme['stock'])
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            height=800,
            title_text=f"{stock_code} 网格策略 vs 买入持有策略对比",
            template=self.template
        )
        
        return self._save_chart(fig, f"{stock_code}_comparison")
    
    def _save_chart(self, fig, filename: str) -> str:
        """保存图表为HTML文件"""
        os.makedirs('reports', exist_ok=True)
        filepath = f"reports/{filename}.html"
        
        # 保存为交互式HTML
        fig.write_html(filepath, include_plotlyjs='cdn')
        
        return filepath


def generate_report(stock_code: str, optimization_results: Dict) -> str:
    """生成策略报告"""
    
    best_result = optimization_results.get('best_result')
    best_params = optimization_results.get('best_parameters', {})
    
    if not best_result:
        return ""
    
    # 创建报告HTML
    report_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{stock_code} 网格策略分析报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }}
        .metric-card {{ background: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
        .positive {{ color: #2ca02c; }}
        .negative {{ color: #d62728; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{stock_code} 网格策略优化分析报告</h1>
        <p>生成时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <h2>策略摘要</h2>
        <div class="metrics">
            <div class="metric-card">
                <div>最优参数</div>
                <div class="metric-value">上涨{best_params.get('up_ratio', 0):.1%}/下跌{best_params.get('down_ratio', 0):.1%}</div>
            </div>
            <div class="metric-card">
                <div>策略收益</div>
                <div class="metric-value {'positive' if best_result.total_return >= 0 else 'negative'}">{best_result.total_return:+.2%}</div>
            </div>
            <div class="metric-card">
                <div>股票收益</div>
                <div class="metric-value {'positive' if best_result.stock_return >= 0 else 'negative'}">{best_result.stock_return:+.2%}</div>
            </div>
            <div class="metric-card">
                <div>超额收益</div>
                <div class="metric-value {'positive' if best_result.excess_return >= 0 else 'negative'}">{best_result.excess_return:+.2%}</div>
            </div>
            <div class="metric-card">
                <div>最大回撤</div>
                <div class="metric-value negative">{best_result.max_drawdown:.2%}</div>
            </div>
            <div class="metric-card">
                <div>夏普比率</div>
                <div class="metric-value {'positive' if best_result.sharpe_ratio >= 0 else 'negative'}">{best_result.sharpe_ratio:.2f}</div>
            </div>
        </div>
    </div>
    
    <div>
        <h2>详细分析</h2>
        <p>总交易次数：{best_result.total_trades} (买入：{best_result.buy_trades}, 卖出：{best_result.sell_trades})</p>
        <p>年化收益率：{best_result.annual_return:.2%}</p>
        <p>网格数量：{best_result.grid_count}</p>
    </div>
    
    <div>
        <h2>图表分析</h2>
        <p>请查看生成的交互式图表文件：</p>
        <ul>
            <li><a href="{stock_code}_dashboard.html">综合仪表板</a></li>
            <li><a href="{stock_code}_comparison.html">策略对比图</a></li>
        </ul>
    </div>
</body>
</html>
    """
    
    # 保存报告
    os.makedirs('reports', exist_ok=True)
    report_file = f"reports/{stock_code}_report.html"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_html)
    
    return report_file


if __name__ == "__main__":
    # 测试代码
    from data_source import get_stock_data
    from grid_strategy import GridStrategyCalculator
    
    # 获取测试数据
    df = get_stock_data("000001", market="SZ", frequency="日线", 
                       start_date="20230101", end_date="20231231")
    
    if len(df) > 0:
        calculator = GridStrategyCalculator(df)
        
        # 运行优化
        optimization = calculator.optimize_grid_parameters(
            min_up_ratio=0.02, max_up_ratio=0.08,
            min_down_ratio=0.02, max_down_ratio=0.08,
            step_size=0.01
        )
        
        # 生成图表
        visualizer = ChartVisualizer()
        
        # 创建综合仪表板
        dashboard_file = visualizer.create_comprehensive_dashboard(
            calculator, optimization, "000001"
        )
        print(f"仪表板已保存: {dashboard_file}")
        
        # 创建简单对比图
        comparison_file = visualizer.create_simple_comparison_chart(
            calculator, optimization, "000001"
        )
        print(f"对比图已保存: {comparison_file}")
        
        # 生成报告
        report_file = generate_report("000001", optimization)
        print(f"报告已保存: {report_file}")
    else:
        print("未获取到测试数据")