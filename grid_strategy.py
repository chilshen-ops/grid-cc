"""
网格策略计算模块
用于计算不同上涨下跌幅度下的网格策略收益，并与正股收益对比
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import json
import os
from dataclasses import dataclass
from enum import Enum


class TradeDirection(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class TradeRecord:
    """交易记录"""
    datetime: pd.Timestamp
    price: float
    direction: TradeDirection
    quantity: float
    cash_after: float
    stock_after: float
    total_value: float


@dataclass
class StrategyResult:
    """策略结果"""
    # 策略参数
    up_ratio: float
    down_ratio: float
    initial_cash: float
    grid_count: int
    
    # 收益指标
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    
    # 交易统计
    total_trades: int
    buy_trades: int
    sell_trades: int
    
    # 对比数据
    stock_return: float
    excess_return: float
    
    # 详细数据
    trade_records: List[TradeRecord]
    daily_values: pd.DataFrame


class GridStrategyCalculator:
    """网格策略计算器"""
    
    def __init__(self, price_data: pd.DataFrame):
        """
        Args:
            price_data: 包含收盘价的数据框，需要'datetime'和'close'列
        """
        self.price_data = price_data.copy()
        self.price_data['date'] = pd.to_datetime(self.price_data['datetime']).dt.date
        
        # 按日期分组，取最后一条记录作为当日收盘价
        daily_data = self.price_data.groupby('date').agg({
            'close': 'last',
            'datetime': 'last'
        }).reset_index()
        
        self.daily_prices = daily_data.set_index('date')['close']
        self.daily_dates = daily_data['date']
    
    def calculate_stock_return(self, start_date: Optional[str] = None, 
                              end_date: Optional[str] = None) -> float:
        """计算正股收益"""
        prices = self._get_price_range(start_date, end_date)
        if len(prices) < 2:
            return 0.0
        
        start_price = prices.iloc[0]
        end_price = prices.iloc[-1]
        
        return (end_price - start_price) / start_price
    
    def optimize_grid_parameters(self, initial_cash: float = 100000,
                                min_up_ratio: float = 0.01,
                                max_up_ratio: float = 0.1,
                                min_down_ratio: float = 0.01,
                                max_down_ratio: float = 0.1,
                                step_size: float = 0.001,
                                start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> Dict:
        """
        优化网格策略参数
        
        Args:
            initial_cash: 初始资金
            min_up_ratio: 最小上涨比例
            max_up_ratio: 最大上涨比例
            min_down_ratio: 最小下跌比例
            max_down_ratio: 最大下跌比例
            step_size: 步长
            start_date: 开始日期
            end_date: 结束日期
        """
        best_result = None
        best_excess_return = -float('inf')
        all_results = []
        
        # 生成所有可能的参数组合
        up_ratios = np.arange(min_up_ratio, max_up_ratio + step_size, step_size)
        down_ratios = np.arange(min_down_ratio, max_down_ratio + step_size, step_size)
        
        # 计算总任务数
        total_tasks = len(up_ratios) * len(down_ratios)
        completed_tasks = 0
        
        # 设置进度条
        print("🚀 开始优化网格策略参数...")
        print(f"📊 总参数组合: {total_tasks:,}")
        print()
        
        for up_ratio in up_ratios:
            for down_ratio in down_ratios:
                # 跳过无效组合
                if up_ratio <= 0 or down_ratio <= 0:
                    completed_tasks += 1
                    continue
                
                result = self.run_grid_strategy(
                    up_ratio=up_ratio,
                    down_ratio=down_ratio,
                    initial_cash=initial_cash,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if result is not None:
                    all_results.append({
                        'up_ratio': up_ratio,
                        'down_ratio': down_ratio,
                        'excess_return': result.excess_return,
                        'total_return': result.total_return,
                        'stock_return': result.stock_return,
                        'max_drawdown': result.max_drawdown,
                        'sharpe_ratio': result.sharpe_ratio,
                        'total_trades': result.total_trades
                    })
                    
                    if result.excess_return > best_excess_return:
                        best_excess_return = result.excess_return
                        best_result = result
                
                # 更新进度
                completed_tasks += 1
                progress = completed_tasks / total_tasks * 100
                
                # 显示美观的进度条
                bar_length = 30
                filled_length = int(bar_length * completed_tasks // total_tasks)
                
                # 使用彩色进度条
                bar = '█' * filled_length + '░' * (bar_length - filled_length)
                
                # 添加进度指示器
                if progress < 25:
                    indicator = '🟡'
                elif progress < 50:
                    indicator = '🟠'
                elif progress < 75:
                    indicator = '🔵'
                else:
                    indicator = '🟢'
                
                # 格式化显示
                eta = "计算中..." if completed_tasks < total_tasks else "即将完成"
                
                print(f'\r{indicator} 进度: [{bar}] {progress:5.1f}% | {completed_tasks:,}/{total_tasks:,} | ETA: {eta}', end='', flush=True)
        
        # 进度条完成
        print("\n\n🎉 参数优化完成!")
        print("✨ 所有参数组合已计算完毕")
        
        return {
            'best_result': best_result,
            'all_results': pd.DataFrame(all_results),
            'best_parameters': {
                'up_ratio': best_result.up_ratio if best_result else None,
                'down_ratio': best_result.down_ratio if best_result else None
            }
        }
    
    def run_grid_strategy(self, up_ratio: float, down_ratio: float,
                         initial_cash: float = 100000,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> Optional[StrategyResult]:
        """
        运行网格策略
        
        Args:
            up_ratio: 上涨触发比例
            down_ratio: 下跌触发比例
            initial_cash: 初始资金
            start_date: 开始日期
            end_date: 结束日期
        """
        prices = self._get_price_range(start_date, end_date)
        
        if len(prices) < 2:
            return None
        
        # 初始化变量
        cash = initial_cash
        stock_value = 0.0
        current_price = prices.iloc[0]
        
        # 计算网格数量（基于价格波动范围）
        price_range = prices.max() - prices.min()
        grid_count = max(5, int(price_range / (current_price * min(up_ratio, down_ratio))))
        
        # 计算每个网格的资金量
        grid_cash = initial_cash / grid_count
        
        # 初始化交易记录
        trade_records = []
        daily_values = []
        
        # 初始化网格基准价格
        base_price = current_price
        
        for date, price in prices.items():
            # 检查是否需要交易
            trade_made = False
            
            # 上涨触发卖出
            if price >= base_price * (1 + up_ratio):
                if stock_value > 0:
                    # 卖出部分股票
                    sell_amount = grid_cash
                    sell_quantity = sell_amount / price
                    
                    if stock_value >= sell_amount:
                        cash += sell_amount
                        stock_value -= sell_amount
                        
                        trade_records.append(TradeRecord(
                            datetime=pd.Timestamp(date),
                            price=price,
                            direction=TradeDirection.SELL,
                            quantity=sell_quantity,
                            cash_after=cash,
                            stock_after=stock_value,
                            total_value=cash + stock_value
                        ))
                        trade_made = True
                        
                        # 更新基准价格
                        base_price = price
            
            # 下跌触发买入
            elif price <= base_price * (1 - down_ratio):
                if cash >= grid_cash:
                    # 买入股票
                    buy_amount = min(grid_cash, cash)
                    buy_quantity = buy_amount / price
                    
                    cash -= buy_amount
                    stock_value += buy_amount
                    
                    trade_records.append(TradeRecord(
                        datetime=pd.Timestamp(date),
                        price=price,
                        direction=TradeDirection.BUY,
                        quantity=buy_quantity,
                        cash_after=cash,
                        stock_after=stock_value,
                        total_value=cash + stock_value
                    ))
                    trade_made = True
                    
                    # 更新基准价格
                    base_price = price
            
            # 记录每日价值
            total_value = cash + stock_value
            daily_values.append({
                'date': date,
                'total_value': total_value,
                'cash': cash,
                'stock_value': stock_value,
                'price': price
            })
        
        # 计算最终结果
        daily_df = pd.DataFrame(daily_values)
        daily_df['return'] = daily_df['total_value'].pct_change()
        
        # 计算各种指标
        start_value = daily_df['total_value'].iloc[0]
        end_value = daily_df['total_value'].iloc[-1]
        total_return = (end_value - start_value) / start_value
        
        # 年化收益率
        days = len(daily_df)
        annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0
        
        # 最大回撤
        rolling_max = daily_df['total_value'].expanding().max()
        drawdowns = (daily_df['total_value'] - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()
        
        # 夏普比率
        daily_returns = daily_df['return'].dropna()
        sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if len(daily_returns) > 1 else 0
        
        # 交易统计
        buy_trades = len([t for t in trade_records if t.direction == TradeDirection.BUY])
        sell_trades = len([t for t in trade_records if t.direction == TradeDirection.SELL])
        
        # 正股收益
        stock_return = self.calculate_stock_return(start_date, end_date)
        excess_return = total_return - stock_return
        
        return StrategyResult(
            up_ratio=up_ratio,
            down_ratio=down_ratio,
            initial_cash=initial_cash,
            grid_count=grid_count,
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            total_trades=len(trade_records),
            buy_trades=buy_trades,
            sell_trades=sell_trades,
            stock_return=stock_return,
            excess_return=excess_return,
            trade_records=trade_records,
            daily_values=daily_df
        )
    
    def _get_price_range(self, start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> pd.Series:
        """获取指定日期范围内的价格数据"""
        prices = self.daily_prices.copy()
        
        if start_date:
            start_date = pd.to_datetime(start_date).date()
            prices = prices[prices.index >= start_date]
        
        if end_date:
            end_date = pd.to_datetime(end_date).date()
            prices = prices[prices.index <= end_date]
        
        return prices


def save_optimization_results(results: Dict, filename: str):
    """保存优化结果到文件"""
    # 创建报告目录
    os.makedirs('reports', exist_ok=True)
    
    # 保存详细结果
    filepath = f"reports/{filename}_results.json"
    
    # 转换为可序列化的格式
    serializable_results = {
        'best_parameters': results.get('best_parameters', {}),
        'all_results': results.get('all_results', pd.DataFrame()).to_dict('records')
    }
    
    if 'best_result' in results and results['best_result']:
        best_result = results['best_result']
        serializable_results['best_result'] = {
            'up_ratio': best_result.up_ratio,
            'down_ratio': best_result.down_ratio,
            'total_return': best_result.total_return,
            'annual_return': best_result.annual_return,
            'max_drawdown': best_result.max_drawdown,
            'sharpe_ratio': best_result.sharpe_ratio,
            'total_trades': best_result.total_trades,
            'stock_return': best_result.stock_return,
            'excess_return': best_result.excess_return
        }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(serializable_results, f, indent=2, ensure_ascii=False)
    
    return filepath


if __name__ == "__main__":
    # 测试代码
    from data_source import get_stock_data
    
    # 获取测试数据
    df = get_stock_data("000001", market="SZ", frequency="日线", 
                       start_date="20230101", end_date="20231231")
    
    if len(df) > 0:
        calculator = GridStrategyCalculator(df)
        
        # 测试单次策略
        result = calculator.run_grid_strategy(up_ratio=0.05, down_ratio=0.03)
        
        if result:
            print(f"策略收益: {result.total_return:.2%}")
            print(f"正股收益: {result.stock_return:.2%}")
            print(f"超额收益: {result.excess_return:.2%}")
            print(f"交易次数: {result.total_trades}")
        
        # 测试参数优化
        optimization = calculator.optimize_grid_parameters(
            min_up_ratio=0.02, max_up_ratio=0.08,
            min_down_ratio=0.02, max_down_ratio=0.08,
            step_size=0.01
        )
        
        if optimization['best_result']:
            best = optimization['best_result']
            print(f"\n最优参数: 上涨{best.up_ratio:.1%}, 下跌{best.down_ratio:.1%}")
            print(f"最优超额收益: {best.excess_return:.2%}")
    else:
        print("未获取到测试数据")