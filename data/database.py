"""
数据存储模块
SQLite数据库操作
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class Database:
    """SQLite数据库管理"""
    
    def __init__(self, db_path: str = "data/quant.db"):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
    
    def _get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def _init_tables(self):
        """初始化数据表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 行情数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                UNIQUE(symbol, date)
            )
        """)
        
        # 交易记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                commission REAL DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 持仓记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                avg_price REAL NOT NULL,
                entry_date TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 信号记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                strategy TEXT NOT NULL,
                signal INTEGER NOT NULL,
                price REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 绩效记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                equity REAL NOT NULL,
                cash REAL NOT NULL,
                position_value REAL,
                return_pct REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 策略参数表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_params (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                param_name TEXT NOT NULL,
                param_value TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(strategy_name, param_name)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ==================== 行情数据 ====================
    
    def save_price_data(self, symbol: str, df: pd.DataFrame):
        """
        保存行情数据
        
        Args:
            symbol: 股票代码
            df: OHLCV数据
        """
        conn = self._get_connection()
        
        for idx, row in df.iterrows():
            date = idx.strftime('%Y-%m-%d') if isinstance(idx, datetime) else str(idx)
            
            conn.execute("""
                INSERT OR REPLACE INTO price_data 
                (symbol, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (symbol, date, row.get('open'), row.get('high'), 
                  row.get('low'), row.get('close'), row.get('volume')))
        
        conn.commit()
        conn.close()
    
    def get_price_data(self, symbol: str, start_date: str = None, 
                       end_date: str = None) -> pd.DataFrame:
        """
        获取行情数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            行情数据DataFrame
        """
        conn = self._get_connection()
        
        query = "SELECT date, open, high, low, close, volume FROM price_data WHERE symbol = ?"
        params = [symbol]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date"
        
        df = pd.read_sql_query(query, conn, params=params, 
                                parse_dates=['date'], index_col='date')
        conn.close()
        
        return df
    
    # ==================== 交易记录 ====================
    
    def save_trade(self, date: str, symbol: str, action: str, 
                   price: float, quantity: int, commission: float = 0, 
                   notes: str = ""):
        """保存交易记录"""
        conn = self._get_connection()
        
        conn.execute("""
            INSERT INTO trades (date, symbol, action, price, quantity, commission, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (date, symbol, action, price, quantity, commission, notes))
        
        conn.commit()
        conn.close()
    
    def get_trades(self, symbol: str = None, start_date: str = None, 
                   end_date: str = None) -> List[Dict]:
        """获取交易记录"""
        conn = self._get_connection()
        
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date DESC"
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    # ==================== 持仓管理 ====================
    
    def save_position(self, symbol: str, quantity: int, avg_price: float, 
                      entry_date: str):
        """保存或更新持仓"""
        conn = self._get_connection()
        
        conn.execute("""
            INSERT OR REPLACE INTO positions (symbol, quantity, avg_price, entry_date, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (symbol, quantity, avg_price, entry_date))
        
        conn.commit()
        conn.close()
    
    def get_positions(self) -> List[Dict]:
        """获取当前持仓"""
        conn = self._get_connection()
        
        cursor = conn.execute("SELECT * FROM positions WHERE quantity > 0")
        rows = cursor.fetchall()
        
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def clear_positions(self):
        """清空持仓"""
        conn = self._get_connection()
        conn.execute("DELETE FROM positions")
        conn.commit()
        conn.close()
    
    # ==================== 信号记录 ====================
    
    def save_signal(self, date: str, symbol: str, strategy: str, 
                    signal: int, price: float = None):
        """保存信号"""
        conn = self._get_connection()
        
        conn.execute("""
            INSERT INTO signals (date, symbol, strategy, signal, price)
            VALUES (?, ?, ?, ?, ?)
        """, (date, symbol, strategy, signal, price))
        
        conn.commit()
        conn.close()
    
    def get_signals(self, symbol: str = None, strategy: str = None, 
                    limit: int = 100) -> List[Dict]:
        """获取信号记录"""
        conn = self._get_connection()
        
        query = "SELECT * FROM signals WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if strategy:
            query += " AND strategy = ?"
            params.append(strategy)
        
        query += " ORDER BY date DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    # ==================== 绩效记录 ====================
    
    def save_performance(self, date: str, equity: float, cash: float, 
                         position_value: float = 0, return_pct: float = 0):
        """保存绩效记录"""
        conn = self._get_connection()
        
        conn.execute("""
            INSERT INTO performance (date, equity, cash, position_value, return_pct)
            VALUES (?, ?, ?, ?, ?)
        """, (date, equity, cash, position_value, return_pct))
        
        conn.commit()
        conn.close()
    
    def get_performance(self, start_date: str = None, 
                       end_date: str = None) -> pd.DataFrame:
        """获取绩效记录"""
        conn = self._get_connection()
        
        query = "SELECT date, equity, cash, position_value, return_pct FROM performance"
        params = []
        
        if start_date:
            query += " WHERE date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?" if start_date else " WHERE date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date"
        
        df = pd.read_sql_query(query, conn, params=params,
                                parse_dates=['date'], index_col='date')
        conn.close()
        
        return df
    
    # ==================== 策略参数 ====================
    
    def save_strategy_param(self, strategy_name: str, param_name: str, 
                            param_value: str):
        """保存策略参数"""
        conn = self._get_connection()
        
        conn.execute("""
            INSERT OR REPLACE INTO strategy_params (strategy_name, param_name, param_value)
            VALUES (?, ?, ?)
        """, (strategy_name, param_name, param_value))
        
        conn.commit()
        conn.close()
    
    def get_strategy_params(self, strategy_name: str) -> Dict:
        """获取策略参数"""
        conn = self._get_connection()
        
        cursor = conn.execute("""
            SELECT param_name, param_value FROM strategy_params
            WHERE strategy_name = ?
        """, (strategy_name,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return {row[0]: row[1] for row in rows}
    
    # ==================== 工具方法 ====================
    
    def backup(self, backup_path: str = None):
        """备份数据库"""
        if backup_path is None:
            backup_path = self.db_path.replace('.db', f'_backup_{datetime.now().strftime("%Y%m%d")}.db')
        
        conn = self._get_connection()
        backup_conn = sqlite3.connect(backup_path)
        
        conn.backup(backup_conn)
        
        conn.close()
        backup_conn.close()
        
        return backup_path
    
    def clear_old_data(self, days: int = 365):
        """清理旧数据"""
        conn = self._get_connection()
        
        cutoff_date = datetime.now().strftime('%Y-%m-%d')
        
        conn.execute(f"DELETE FROM price_data WHERE date < date('{cutoff_date}', '-{days} days')")
        conn.execute(f"DELETE FROM trades WHERE date < date('{cutoff_date}', '-{days} days')")
        conn.execute(f"DELETE FROM signals WHERE date < date('{cutoff_date}', '-{days} days')")
        conn.execute(f"DELETE FROM performance WHERE date < date('{cutoff_date}', '-{days} days')")
        
        conn.commit()
        conn.close()


# 全局数据库实例
_db = None

def get_db(db_path: str = "data/quant.db") -> Database:
    """获取数据库实例"""
    global _db
    if _db is None:
        _db = Database(db_path)
    return _db
