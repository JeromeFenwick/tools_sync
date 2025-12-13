# -*- coding: utf-8 -*-
"""
数据库模块 - 使用SQLite存储文件元信息
"""
import sqlite3
import os
import sys
import threading
from datetime import datetime


class Database:
    """文件同步数据库管理类"""
    
    _local = threading.local()
    
    def __init__(self, db_path='sync_data.db'):
        # 确保数据库文件在 exe 同级目录（支持打包后运行）
        if not os.path.isabs(db_path):
            # 如果是相对路径，转为 exe 所在目录的绝对路径
            if getattr(sys, 'frozen', False):
                # 打包后的环境，sys.executable 是 exe 文件路径
                exe_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境，使用当前目录
                exe_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(exe_dir, db_path)
        
        self.db_path = db_path
        self._init_db()
    
    def _get_conn(self):
        """获取线程本地的数据库连接"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 文件信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                relative_path TEXT NOT NULL,
                base_folder TEXT NOT NULL,
                file_size INTEGER,
                modify_time REAL,
                md5_hash TEXT,
                last_sync_time TEXT,
                sync_status TEXT DEFAULT 'unsynced'
            )
        ''')
        
        # 同步历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_time TEXT NOT NULL,
                sync_type TEXT NOT NULL,
                base_folder TEXT NOT NULL,
                file_count INTEGER,
                archive_path TEXT
            )
        ''')
        
        # 冲突记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                conflict_time TEXT NOT NULL,
                source_md5 TEXT,
                target_md5 TEXT,
                resolved INTEGER DEFAULT 0
            )
        ''')
        
        # 配置表 - 存储用户选择的路径
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_time TEXT NOT NULL
            )
        ''')
        
        conn.commit()
    
    def update_file_info(self, file_path, relative_path, base_folder, file_size, modify_time, md5_hash=None):
        """更新或插入文件信息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO file_info 
            (file_path, relative_path, base_folder, file_size, modify_time, md5_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (file_path, relative_path, base_folder, file_size, modify_time, md5_hash))
        
        conn.commit()
    
    def get_file_info(self, file_path):
        """获取文件信息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM file_info WHERE file_path = ?', (file_path,))
        return cursor.fetchone()
    
    def get_files_by_folder(self, base_folder):
        """获取指定文件夹下的所有文件记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM file_info WHERE base_folder = ?', (base_folder,))
        return cursor.fetchall()
    
    def clear_folder_records(self, base_folder):
        """清除指定文件夹的所有记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM file_info WHERE base_folder = ?', (base_folder,))
        conn.commit()
    
    def add_sync_history(self, sync_type, base_folder, file_count, archive_path):
        """添加同步历史记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        sync_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO sync_history 
            (sync_time, sync_type, base_folder, file_count, archive_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (sync_time, sync_type, base_folder, file_count, archive_path))
        
        conn.commit()
    
    def get_sync_history(self, limit=20):
        """获取同步历史记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM sync_history 
            ORDER BY sync_time DESC 
            LIMIT ?
        ''', (limit,))
        
        return cursor.fetchall()
    
    def add_conflict(self, file_path, source_md5, target_md5):
        """添加冲突记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        conflict_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO conflicts 
            (file_path, conflict_time, source_md5, target_md5)
            VALUES (?, ?, ?, ?)
        ''', (file_path, conflict_time, source_md5, target_md5))
        
        conn.commit()
    
    def get_unresolved_conflicts(self):
        """获取未解决的冲突"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM conflicts WHERE resolved = 0')
        return cursor.fetchall()
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            delattr(self._local, 'conn')
    
    # ==================== 配置管理 ====================
    
    def set_config(self, key, value):
        """设置配置项"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        updated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT OR REPLACE INTO config (key, value, updated_time)
            VALUES (?, ?, ?)
        ''', (key, value, updated_time))
        
        conn.commit()
    
    def get_config(self, key, default=None):
        """获取配置项"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
        result = cursor.fetchone()
        
        return result['value'] if result else default
    
    def get_backup_folders(self):
        """获取上次选择的备份文件夹列表"""
        import json
        folders_json = self.get_config('backup_folders', '[]')
        try:
            return json.loads(folders_json)
        except:
            return []
    
    def set_backup_folders(self, folders):
        """保存备份文件夹列表"""
        import json
        self.set_config('backup_folders', json.dumps(folders))
    
    def get_last_sync_target(self):
        """获取上次同步目标文件夹"""
        return self.get_config('last_sync_target', '')
    
    def set_last_sync_target(self, folder):
        """保存同步目标文件夹"""
        self.set_config('last_sync_target', folder)
