# 网格策略分析工具

基于智图API的股票网格策略优化分析工具，支持自动获取历史数据、参数优化、可视化图表和报告生成。

## 功能特性

- ✅ **统一数据源接口**：隔离不同数据源实现细节，支持灵活切换
- ✅ **本地数据缓存**：自动保存获取的数据，避免重复请求
- ✅ **网格策略优化**：自动寻找最优的上涨/下跌触发比例
- ✅ **多维度分析**：收益对比、风险指标、交易统计等
- ✅ **交互式图表**：基于Plotly的交互式可视化图表
- ✅ **HTML报告**：自动生成详细的分析报告

## 项目结构

```
ssq/
├── data_source.py          # 统一数据源接口
├── grid_strategy.py        # 网格策略计算模块
├── chart_visualizer.py     # 图表可视化模块
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖包列表
├── README.md              # 说明文档
└── zhitu api              # API说明文件
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 基本用法

```bash
python main.py 000001
```

### 完整参数示例

```bash
python main.py 000001 \
  --market SZ \
  --frequency 日线 \
  --start_date 20230101 \
  --end_date 20231231 \
  --initial_cash 100000 \
  --min_up_ratio 0.02 \
  --max_up_ratio 0.08 \
  --min_down_ratio 0.02 \
  --max_down_ratio 0.08 \
  --step_size 0.01
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `stock_code` | 股票代码（必需） | - |
| `--market` | 市场代码（SZ/SH） | SZ |
| `--frequency` | 数据频率 | 日线 |
| `--start_date` | 开始日期（YYYYMMDD） | 一年前 |
| `--end_date` | 结束日期（YYYYMMDD） | 今天 |
| `--initial_cash` | 初始资金 | 100000 |
| `--min_up_ratio` | 最小上涨比例 | 0.01 |
| `--max_up_ratio` | 最大上涨比例 | 0.10 |
| `--min_down_ratio` | 最小下跌比例 | 0.01 |
| `--max_down_ratio` | 最大下跌比例 | 0.10 |
| `--step_size` | 优化步长 | 0.01 |

## 输出文件

程序运行后会生成以下目录和文件：

- `data_cache/`：股票数据缓存
- `reports/`：分析报告HTML文件

## 核心模块说明

### 1. 数据源模块 (`data_source.py`)

提供统一的数据获取接口，支持：
- 智图API数据获取
- 本地数据缓存管理
- 灵活的日期范围设置
- 多频率数据支持

### 2. 网格策略模块 (`grid_strategy.py`)

实现网格策略的核心算法：
- 策略参数优化
- 收益指标计算
- 风险指标分析
- 交易记录管理

### 3. 图表可视化模块 (`chart_visualizer.py`)

生成交互式可视化图表：
- 价格走势与交易点
- 收益曲线对比
- 参数优化热力图
- 风险指标分析

## 示例输出

### 控制台输出示例
```
============================================================
开始分析股票: 000001.SZ
数据频率: 日线
============================================================
分析期间: 20230101 到 20231231
初始资金: 100,000

开始优化网格策略参数...
参数范围: 上涨[2.0%-8.0%] 下跌[2.0%-8.0%] 步长1.0%

========================================
优化结果汇总
========================================
最优参数: 上涨5.0%, 下跌3.0%
策略收益: +15.23%
正股收益: +12.45%
超额收益: +2.78%
年化收益: +14.89%
最大回撤: -8.34%
夏普比率: 1.23
交易次数: 28
网格数量: 12
```

### 生成的图表 分析报告
- `reports/000001_dashboard.html`：综合仪表板
- `reports/000001_comparison.html`：策略对比图
- `reports/000001_report.html`：详细分析报告

## 高级用法

### 自定义数据源

```python
from data_source import DataSourceManager

# 创建自定义数据源
manager = DataSourceManager(source_type="zhitu")
df = manager.get_stock_data("000001", market="SZ", frequency="日线")
```

### 直接调用策略模块

```python
from grid_strategy import GridStrategyCalculator

# 创建计算器
calculator = GridStrategyCalculator(price_data)

# 运行单次策略
result = calculator.run_grid_strategy(up_ratio=0.05, down_ratio=0.03)

# 参数优化
optimization = calculator.optimize_grid_parameters(
    min_up_ratio=0.02, max_up_ratio=0.08,
    min_down_ratio=0.02, max_down_ratio=0.08
)
```

## 注意事项

1. **API限制**：智图API有请求频率限制，请合理使用
2. **数据质量**：确保股票代码和市场代码正确
3. **参数设置**：根据股票波动性调整参数范围
4. **缓存管理**：`data_cache/`目录可定期清理

## 技术支持

如有问题或建议，请检查：
1. 网络连接是否正常
2. 股票代码和市场代码是否正确
3. 日期范围是否合理
4. 依赖包是否安装完整

## 许可证

本项目仅供学习和研究使用。
