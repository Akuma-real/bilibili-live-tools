"""数据库管理"""
import sqlite3
import os
from contextlib import contextmanager
import datetime

class DatabaseManager:
    def __init__(self, db_path):
        """初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径，例如 'data/database.db'
        """
        # 确保数据目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 让查询结果可以通过列名访问
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def init_db(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建配置表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT
            )
            ''')
            
            # 创建直播记录表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS live_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mid INTEGER NOT NULL,
                room_id INTEGER,
                title TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                status INTEGER DEFAULT 0
            )
            ''')
            
            # 创建截图记录表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                live_id INTEGER NOT NULL,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
    
    def get_config(self, key, default=None):
        """获取配置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM configs WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result['value'] if result else default
    
    def set_config(self, key, value):
        """设置配置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO configs (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?
            ''', (key, value, value))
    
    def add_live_record(self, mid, room_id, title, start_time=None):
        """添加直播记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            start_time = start_time or datetime.datetime.now()
            cursor.execute('''
            INSERT INTO live_records (mid, room_id, title, start_time, status)
            VALUES (?, ?, ?, ?, 1)
            ''', (mid, room_id, title, start_time))
            return cursor.lastrowid
    
    def update_live_status(self, mid, status, end_time=None):
        """更新直播状态"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status == 0:  # 下播
                end_time = end_time or datetime.datetime.now()
                cursor.execute('''
                UPDATE live_records 
                SET status = ?, end_time = ?
                WHERE mid = ? AND status = 1
                ''', (status, end_time, mid))
            else:
                cursor.execute('''
                UPDATE live_records 
                SET status = ?
                WHERE mid = ? AND status = 0
                ''', (status, mid))
    
    def add_screenshot(self, live_id, image_url):
        """添加截图记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO screenshots (live_id, image_url)
            VALUES (?, ?)
            ''', (live_id, image_url))
    
    def get_current_live_id(self, mid):
        """获取当前直播ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT id FROM live_records
            WHERE mid = ? AND status = 1
            ORDER BY start_time DESC LIMIT 1
            ''', (mid,))
            result = cursor.fetchone()
            return result['id'] if result else None
