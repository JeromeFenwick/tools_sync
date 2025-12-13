# -*- coding: utf-8 -*-
"""
文件扫描模块 - 扫描文件夹并计算MD5
"""
import os
import hashlib
from datetime import datetime


class FileScanner:
    """文件扫描器"""
    
    @staticmethod
    def calculate_md5(file_path, block_size=65536):
        """计算文件MD5值"""
        md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(block_size)
                    if not data:
                        break
                    md5.update(data)
            return md5.hexdigest()
        except Exception as e:
            print(f"计算MD5失败: {file_path}, 错误: {e}")
            return None
    
    @staticmethod
    def scan_folder(base_folder, callback=None):
        """
        扫描文件夹，返回文件信息列表
        
        Args:
            base_folder: 要扫描的基础文件夹路径
            callback: 回调函数，用于更新进度 callback(current, total, filename)
        
        Returns:
            list: 文件信息列表，每项包含 {path, relative_path, size, mtime}
        """
        files_info = []
        
        if not os.path.exists(base_folder):
            return files_info
        
        # 先统计总文件数
        total_files = sum([len(files) for _, _, files in os.walk(base_folder)])
        current = 0
        
        for root, dirs, files in os.walk(base_folder):
            for filename in files:
                file_path = os.path.join(root, filename)
                
                try:
                    stat = os.stat(file_path)
                    relative_path = os.path.relpath(file_path, base_folder)
                    
                    files_info.append({
                        'path': file_path,
                        'relative_path': relative_path,
                        'size': stat.st_size,
                        'mtime': stat.st_mtime
                    })
                    
                    current += 1
                    if callback:
                        callback(current, total_files, filename)
                        
                except Exception as e:
                    print(f"扫描文件失败: {file_path}, 错误: {e}")
                    continue
        
        return files_info
    
    @staticmethod
    def compare_files(db, base_folder, files_info, callback=None):
        """
        比对文件变化，返回有差异的文件列表
        
        Args:
            db: 数据库对象
            base_folder: 基础文件夹路径
            files_info: 扫描得到的文件信息列表
            callback: 回调函数
        
        Returns:
            list: 有差异的文件路径列表，每项包含MD5信息
        
        注意：此函数不会更新数据库，仅识别差异文件
        """
        changed_files = []
        total = len(files_info)
        
        for idx, file_info in enumerate(files_info):
            file_path = file_info['path']
            db_record = db.get_file_info(file_path)
            
            # 判断是否有差异（新文件 或 大小/时间不同）
            has_diff = False
            if db_record is None:
                has_diff = True
            elif (db_record['file_size'] != file_info['size'] or 
                  abs(db_record['modify_time'] - file_info['mtime']) > 1):
                has_diff = True
            
            if has_diff:
                # 计算MD5确认差异
                md5_hash = FileScanner.calculate_md5(file_path)
                if db_record is None or db_record['md5_hash'] != md5_hash:
                    # 添加MD5信息到file_info
                    file_info_with_md5 = file_info.copy()
                    file_info_with_md5['md5_hash'] = md5_hash
                    changed_files.append(file_info_with_md5)
                    # 注意：不再在这里更新数据库
            
            if callback:
                callback(idx + 1, total, os.path.basename(file_path))
        
        return changed_files
    
    @staticmethod
    def format_size(size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
