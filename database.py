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
    
    def get_sync_folders(self):
        """获取上次选择的同步文件夹列表"""
        import json
        folders_json = self.get_config('sync_folders', '[]')
        try:
            return json.loads(folders_json)
        except:
            return []
    
    def set_sync_folders(self, folders):
        """保存同步文件夹列表"""
        import json
        self.set_config('sync_folders', json.dumps(folders))
    
    # ==================== 统计数据 ====================
    
    def get_backup_statistics(self, days=30, dimension='backup_date'):
        """
        获取备份统计数据
        
        Args:
            days: 统计最近多少天的数据
            dimension: 统计维度，可选值:
                - 'backup_date': 按备份日期统计
                - 'file_create_date': 按文件创建日期统计
                - 'file_modify_date': 按文件修改日期统计
        
        Returns:
            dict: 包含日期、文件数量、备份次数的统计数据
        """
        from datetime import datetime, timedelta
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if dimension == 'backup_date':
            # 按备份日期统计
            cursor.execute('''
                SELECT 
                    DATE(sync_time) as date,
                    COUNT(*) as backup_count,
                    SUM(file_count) as total_files
                FROM sync_history
                WHERE sync_time >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(sync_time)
                ORDER BY date ASC
            ''', (days,))
        elif dimension == 'file_modify_date':
            # 按文件修改日期统计
            cursor.execute('''
                SELECT 
                    DATE(modify_time, 'unixepoch') as date,
                    0 as backup_count,
                    COUNT(*) as total_files
                FROM file_info
                WHERE modify_time >= strftime('%s', datetime('now', '-' || ? || ' days'))
                GROUP BY DATE(modify_time, 'unixepoch')
                ORDER BY date ASC
            ''', (days,))
        else:  # file_create_date - 暂时使用modify_time作为替代
            # 注意: SQLite 没有内置的创建时间，这里使用修改时间作为示例
            cursor.execute('''
                SELECT 
                    DATE(modify_time, 'unixepoch') as date,
                    0 as backup_count,
                    COUNT(*) as total_files
                FROM file_info
                WHERE modify_time >= strftime('%s', datetime('now', '-' || ? || ' days'))
                GROUP BY DATE(modify_time, 'unixepoch')
                ORDER BY date ASC
            ''', (days,))
        
        results = cursor.fetchall()
        
        # 构建完整的日期范围（包括没有备份的日期）
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)
        
        # 创建日期到数据的映射
        date_map = {}
        for row in results:
            date_str = row['date']
            date_map[date_str] = {
                'backup_count': row['backup_count'],
                'file_count': row['total_files'] or 0
            }
        
        # 生成完整的日期序列和数据
        all_dates = []
        all_backup_counts = []
        all_file_counts = []
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            all_dates.append(date_str)
            
            if date_str in date_map:
                all_backup_counts.append(date_map[date_str]['backup_count'])
                all_file_counts.append(date_map[date_str]['file_count'])
            else:
                all_backup_counts.append(0)
                all_file_counts.append(0)
            
            current_date += timedelta(days=1)
        
        return {
            'dates': all_dates,
            'backup_counts': all_backup_counts,
            'file_counts': all_file_counts
        }
    
    def get_storage_statistics(self):
        """
        获取存储空间统计数据
        
        Returns:
            dict: 包含各文件夹的存储统计
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                base_folder,
                COUNT(*) as file_count,
                SUM(file_size) as total_size
            FROM file_info
            GROUP BY base_folder
        ''')
        
        results = cursor.fetchall()
        
        return [
            {
                'folder': row['base_folder'],
                'file_count': row['file_count'],
                'total_size': row['total_size'] or 0
            }
            for row in results
        ]
