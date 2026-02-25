#!/usr/bin/env python3
"""
下载100只股票10年日线数据
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import random
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.fetcher import DataFetcher

# 100只股票池 (A股为主)
STOCKS = [
    # 蓝筹股
    ('600519.SS', '贵州茅台'), ('601318.SS', '中国平安'), ('600036.SS', '招商银行'),
    ('600887.SS', '伊利股份'), ('600309.SS', '万华化学'), ('601888.SS', '中国中铁'),
    ('600028.SS', '中国石化'), ('600000.SS', '浦发银行'), ('600030.SS', '中信证券'),
    ('600016.SS', '民生银行'), ('600585.SS', '海螺水泥'), ('601166.SS', '兴业银行'),
    ('600050.SS', '中国联通'), ('600900.SS', '长江电力'), ('600276.SS', '恒瑞医药'),
    ('601398.SS', '工商银行'), ('601988.SS', '中国银行'), ('601288.SS', '农业银行'),
    ('600031.SS', '三六零'), ('600030.SS', '中信证券'),
    
    # 创业板
    ('300033.SZ', '同花顺'), ('300015.SZ', '爱尔眼科'), ('300003.SZ', '乐普医疗'),
    ('300122.SZ', '智飞生物'), ('300014.SZ', '亿纬锂能'), ('300759.SZ', '惠伦高科'),
    ('300001.SZ', '睿创微纳'), ('300012.SZ', '华测检测'), ('300456.SZ', '华测'),
    ('300015.SZ', '普瑞眼科'), ('300122.SZ', '智飞'), ('300014.SZ', '亿纬'),
    
    # 科技股
    ('002475.SZ', '立讯精密'), ('002415.SZ', '海康威视'), ('002594.SZ', '比亚迪'),
    ('002230.SZ', '科大讯飞'), ('002410.SZ', '广联达'), ('002444.SZ', '巨星科技'),
    ('002371.SZ', '北方华创'), ('002475.SZ', '立讯'), ('002415.SZ', '海康'),
    ('002594.SZ', '比亚迪股份'),
    
    # 更多蓝筹
    ('600031.SS', '三木集团'), ('600033.SS', '福建高速'), ('600036.SS', '招商银行'),
    ('600048.SS', '保利发展'), ('600050.SS', '中国联通'), ('600104.SS', '上汽集团'),
    ('600176.SS', '中国巨石'), ('600177.SS', '雅戈尔'), ('600183.SS', '生亚泰'),
    ('600195.SS', '中牧股份'), ('600276.SS', '恒瑞医药'), ('600309.SS', '万华化学'),
    ('600406.SS', '国电南瑞'), ('600436.SS', '片仔癀'), ('600519.SS', '贵州茅台'),
    ('600547.SS', '山东黄金'), ('600585.SS', '海螺水泥'), ('600690.SS', '青岛海尔'),
    ('600703.SS', '三安光电'), ('600745.SS', '闻泰科技'), ('600809.SS', '山西汾酒'),
    ('600837.SS', '海康威视'), ('600887.SS', '伊利股份'), ('600900.SS', '长江电力'),
    ('600036.SS', '招商银行'), ('601012.SS', '隆基绿能'), ('601166.SS', '兴业银行'),
    ('601318.SS', '中国平安'), ('601328.SS', '交通银行'), ('601398.SS', '工商银行'),
    ('601857.SS', '中国石油'), ('601888.SS', '中国中铁'), ('601988.SS', '中国银行'),
    
    # 补充
    ('000001.SS', '上证指数'), ('000300.SS', '沪深300'), ('000016.SS', '深证成指'),
    ('000852.SS', '中小板指'), ('000688.SS', '科创50'), ('399001.SZ', '深证成指'),
    ('399006.SZ', '创业板指'),
]

# 去重
seen = set()
unique_stocks = []
for s in STOCKS:
    if s[0] not in seen:
        seen.add(s[0])
        unique_stocks.append(s)

# 取100只
STOCKS_100 = unique_stocks[:100]

OUTPUT_DIR = Path(__file__).parent / 'data' / 'stocks_10y'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def download_stock(code, name):
    """下载单只股票"""
    fetcher = DataFetcher()
    
    print(f"下载: {code} {name} ...", end=" ", flush=True)
    
    try:
        df = fetcher.download(code, period="10y")
        
        if df is not None and len(df) > 1000:
            # 统一列名
            df.columns = df.columns.str.lower()
            
            # 保存
            filename = f"{code.replace('.', '_')}.csv"
            filepath = OUTPUT_DIR / filename
            df.to_csv(filepath)
            
            print(f"✓ {len(df)} 条")
            return True
        else:
            print(f"✗ 数据不足")
            return False
            
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False

def main():
    print("="*60)
    print(f"下载100只股票10年数据")
    print(f"保存位置: {OUTPUT_DIR}")
    print("="*60)
    
    success = 0
    failed = []
    
    for i, (code, name) in enumerate(STOCKS_100, 1):
        print(f"[{i}/100]", end=" ")
        if download_stock(code, name):
            success += 1
        else:
            failed.append((code, name))
        
        # 避免请求过快
        if i % 10 == 0:
            time.sleep(2)
    
    print("\n" + "="*60)
    print(f"完成! 成功: {success}/100")
    print(f"失败: {len(failed)}")
    
    if failed:
        print("\n失败列表:")
        for code, name in failed:
            print(f"  {code} {name}")

if __name__ == "__main__":
    main()
