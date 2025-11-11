"""
统一数据源接口层
用于隔离不同数据源的实现细节，主程序通过统一接口调用
"""
import requests
import json
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class DataSource:
    """数据源基类"""
    
    def __init__(self):
        self.cache_dir = "data_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_stock_data(self, stock_code: str, market: str, frequency: str, 
                      start_date: str, end_date: str) -> pd.DataFrame:
        """获取股票数据"""
        raise NotImplementedError("子类必须实现此方法")
    
    def _save_to_cache(self, stock_code: str, market: str, frequency: str, 
                      data: pd.DataFrame):
        """保存数据到本地缓存"""
        cache_file = f"{self.cache_dir}/{stock_code}_{market}_{frequency}.csv"
        data.to_csv(cache_file, index=False)
    
    def _load_from_cache(self, stock_code: str, market: str, frequency: str, 
                        start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从缓存加载数据"""
        cache_file = f"{self.cache_dir}/{stock_code}_{market}_{frequency}.csv"
        
        if os.path.exists(cache_file):
            data = pd.read_csv(cache_file)
            if len(data) > 0:
                # 过滤日期范围
                data['datetime'] = pd.to_datetime(data['datetime'])
                mask = (data['datetime'] >= pd.to_datetime(start_date)) & \
                       (data['datetime'] <= pd.to_datetime(end_date))
                return data[mask]
        return None


class ZhituDataSource(DataSource):
    """智图API数据源实现"""
    
    def __init__(self, token: str = "你的api 去zhituapi.com免费领取"):
        super().__init__()
        self.token = token
        self.base_url = "https://api.zhituapi.com/hs/history"
        
        # 分时级别映射
        self.frequency_map = {
            '5分钟': '5',
            '15分钟': '15', 
            '30分钟': '30',
            '60分钟': '60',
            '日线': 'd',
            '周线': 'w',
            '月线': 'm',
            '年线': 'y'
        }
        
        # 除权方式映射
        self.adjust_map = {
            '不复权': 'n',
            '前复权': 'f', 
            '后复权': 'b',
            '等比前复权': 'fr',
            '等比后复权': 'br'
        }
    
    def get_stock_data(self, stock_code: str, market: str = "SZ", frequency: str = "日线",
                      adjust: str = "不复权", start_date: str = "20240101", 
                      end_date: str = None) -> pd.DataFrame:
        """
        获取股票历史数据
        
        Args:
            stock_code: 股票代码，如000001
            market: 市场代码，如SZ/SH
            frequency: 分时级别，如'日线','5分钟'等
            adjust: 除权方式，如'不复权','前复权'等
            start_date: 开始日期，格式YYYYMMDD
            end_date: 结束日期，格式YYYYMMDD，默认为当前日期
        """
        
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        
        # 检查缓存
        cached_data = self._load_from_cache(stock_code, market, frequency, start_date, end_date)
        if cached_data is not None:
            return cached_data
        
        # 构建API请求参数
        freq_code = self.frequency_map.get(frequency, 'd')
        adjust_code = self.adjust_map.get(adjust, 'n')
        
        # 分钟数据只能使用不复权
        if freq_code in ['5', '15', '30', '60']:
            adjust_code = 'n'
        
        url = f"{self.base_url}/{stock_code}.{market}/{freq_code}/{adjust_code}"
        params = {
            'token': self.token,
            'st': start_date,
            'et': end_date
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                df = self._parse_response_data(data)
                # 保存到缓存
                self._save_to_cache(stock_code, market, frequency, df)
                
                # 过滤日期范围
                mask = (df['datetime'] >= pd.to_datetime(start_date)) & \
                       (df['datetime'] <= pd.to_datetime(end_date))
                return df[mask]
            else:
                print(f"未获取到数据: {stock_code}.{market}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"API请求失败: {e}")
            return pd.DataFrame()
    
    def _parse_response_data(self, data: List[Dict]) -> pd.DataFrame:
        """解析API返回数据"""
        df = pd.DataFrame(data)
        
        # 重命名列
        column_mapping = {
            't': 'datetime',
            'o': 'open',
            'h': 'high', 
            'l': 'low',
            'c': 'close',
            'v': 'volume',
            'a': 'amount',
            'pc': 'prev_close',
            'sf': 'suspended'
        }
        
        df = df.rename(columns=column_mapping)
        
        # 转换时间格式
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # 确保数据类型正确
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount', 'prev_close']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if 'suspended' in df.columns:
            df['suspended'] = df['suspended'].astype(int)
        
        return df


class DataSourceManager:
    """数据源管理器"""
    
    def __init__(self, source_type: str = "zhitu", **kwargs):
        """
        Args:
            source_type: 数据源类型，目前支持'zhitu'
            **kwargs: 数据源初始化参数
        """
        self.source_type = source_type
        
        if source_type == "zhitu":
            self.data_source = ZhituDataSource(**kwargs)
        else:
            raise ValueError(f"不支持的数据源类型: {source_type}")
    
    def get_stock_data(self, stock_code: str, **kwargs) -> pd.DataFrame:
        """统一接口获取股票数据"""
        return self.data_source.get_stock_data(stock_code, **kwargs)
    
    def get_available_stocks(self) -> List[str]:
        """获取已缓存的股票列表"""
        cache_dir = self.data_source.cache_dir
        if os.path.exists(cache_dir):
            files = os.listdir(cache_dir)
            return [f.replace('.csv', '') for f in files if f.endswith('.csv')]
        return []


# 默认数据源实例
_default_manager = DataSourceManager()


def get_stock_data(stock_code: str, **kwargs) -> pd.DataFrame:
    """
    获取股票数据的快捷函数
    
    Args:
        stock_code: 股票代码，如'000001'
        **kwargs: 其他参数，参考DataSourceManager.get_stock_data
    """
    return _default_manager.get_stock_data(stock_code, **kwargs)


def set_data_source(source_type: str, **kwargs):
    """设置默认数据源"""
    global _default_manager
    _default_manager = DataSourceManager(source_type, **kwargs)


if __name__ == "__main__":
    # 测试代码
    df = get_stock_data("000001", market="SZ", frequency="日线", 
                       start_date="20240101", end_date="20241231")
    print(f"获取数据条数: {len(df)}")
    if len(df) > 0:
        print(df.head())
