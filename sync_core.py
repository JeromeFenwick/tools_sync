# -*- coding: utf-8 -*-
"""
同步核心模块 - 文件打包和同步逻辑
"""
import os
import sys
import platform
import shutil
import zipfile
from datetime import datetime
from file_scanner import FileScanner


def get_app_dir():
    """
    获取应用所在目录
    支持 Windows 和 macOS 打包后的路径处理
    """
    if getattr(sys, 'frozen', False):
        # 打包后的环境
        executable_path = sys.executable
        
        # macOS App Bundle 特殊处理
        # sys.executable 在 macOS App 中是 .app/Contents/MacOS/可执行文件
        # 需要获取 .app 的父目录
        if platform.system() == 'Darwin' and '.app/Contents/MacOS' in executable_path:
            # 从可执行文件路径向上找到 .app，再取其父目录
            app_bundle = executable_path.split('.app/Contents/MacOS')[0] + '.app'
            return os.path.dirname(app_bundle)
        else:
            # Windows 或其他系统，直接获取 exe 所在目录
            return os.path.dirname(executable_path)
    else:
        # 开发环境
        return os.path.dirname(os.path.abspath(__file__))


class SyncCore:
    """同步核心逻辑"""
    
    def __init__(self, db):
        self.db = db
    
    def create_backup_package(self, base_folder, files_list, sync_type='diff', output_dir=None):
        """
        创建备份压缩包
        
        Args:
            base_folder: 基础文件夹路径
            files_list: 要打包的文件列表（字典列表）
            sync_type: 同步类型 'diff'=差异同步, 'full'=全量同步
            output_dir: 输出目录，默认为App同目录下的backups文件夹
        
        Returns:
            str: 压缩包路径
        """
        if not files_list:
            return None
        
        # 如果没有指定输出目录，使用App同目录下的backups
        if output_dir is None:
            output_dir = os.path.join(get_app_dir(), 'backups')
        
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 生成压缩包文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder_name = os.path.basename(base_folder)
        archive_name = f"{folder_name}_{sync_type}_{timestamp}.zip"
        archive_path = os.path.join(output_dir, archive_name)
        
        # 创建压缩包
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加清单文件
            manifest_content = self._create_manifest(files_list, base_folder, sync_type)
            zipf.writestr('sync_manifest.txt', manifest_content)
            
            # 添加文件
            for file_info in files_list:
                file_path = file_info['path']
                relative_path = file_info['relative_path']
                
                try:
                    zipf.write(file_path, relative_path)
                except Exception as e:
                    print(f"打包文件失败: {file_path}, 错误: {e}")
        
        # 记录同步历史
        self.db.add_sync_history(sync_type, base_folder, len(files_list), archive_path)
        
        # 打包成功后，更新数据库中的文件信息（记录A端的MD5）
        for file_info in files_list:
            # 如果file_info中有md5_hash，说明是扫描时计算的
            md5_hash = file_info.get('md5_hash')
            if md5_hash:
                self.db.update_file_info(
                    file_info['path'],
                    file_info['relative_path'],
                    base_folder,
                    file_info['size'],
                    file_info['mtime'],
                    md5_hash
                )
        
        return archive_path
    
    def _create_manifest(self, files_list, base_folder, sync_type):
        """创建清单文件内容"""
        lines = [
            f"同步清单",
            f"=" * 60,
            f"同步类型: {sync_type}",
            f"基础路径: {base_folder}",
            f"创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"文件数量: {len(files_list)}",
            f"=" * 60,
            ""
        ]
        
        for idx, file_info in enumerate(files_list, 1):
            size_str = FileScanner.format_size(file_info['size'])
            lines.append(f"{idx}. {file_info['relative_path']} ({size_str})")
        
        return '\n'.join(lines)
    
    def sync_to_folder(self, archive_path, target_folder, callback=None):
        """
        同步到目标文件夹（优化冲突检测逻辑）
        
        Args:
            archive_path: 压缩包路径
            target_folder: 目标文件夹路径
            callback: 回调函数 callback(current, total, filename, status)
        
        Returns:
            dict: 包含成功、冲突文件列表的字典
        
        同步逻辑：
        - A端（压缩包）更新的文件：直接覆盖B端
        - B端（目标文件夹）更新的文件：移至差异文件夹，人工比对
        """
        if not os.path.exists(archive_path):
            return {'success': [], 'conflicts': []}
        
        # 创建临时解压目录
        temp_dir = os.path.join(os.path.dirname(archive_path), 'temp_extract')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        success_files = []
        conflict_files = []
        
        try:
            # 解压文件
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                file_list = [f for f in zipf.namelist() if f != 'sync_manifest.txt']
                total = len(file_list)
                
                for idx, filename in enumerate(file_list):
                    zipf.extract(filename, temp_dir)
                    
                    source_file = os.path.join(temp_dir, filename)
                    target_file = os.path.join(target_folder, filename)
                    
                    # 检查目标文件是否存在且已修改
                    has_conflict = False
                    if os.path.exists(target_file):
                        # 计算MD5检查是否冲突
                        source_md5 = FileScanner.calculate_md5(source_file)
                        target_md5 = FileScanner.calculate_md5(target_file)
                        
                        if source_md5 != target_md5:
                            # MD5不同，需要检查是谁更新了
                            # 查询数据库中的上A端的MD5记录
                            db_record = self.db.get_file_info(target_file)
                            
                            if db_record and db_record['md5_hash']:
                                # 数据库中有记录，判断B端是否修改
                                if db_record['md5_hash'] == source_md5:
                                    # A端没变，B端变了 -> 冲突
                                    has_conflict = True
                                elif db_record['md5_hash'] == target_md5:
                                    # B端没变，A端变了 -> 直接覆盖
                                    has_conflict = False
                                else:
                                    # 双方都变了 -> 冲突
                                    has_conflict = True
                            else:
                                # 数据库没有记录，默认A端更新，直接覆盖
                                has_conflict = False
                            
                            if has_conflict:
                                # B端有修改，移到差异文件夹
                                conflict_dir = os.path.join(target_folder, '差异文件夹', 
                                                           datetime.now().strftime('%Y%m%d_%H%M%S'))
                                if not os.path.exists(conflict_dir):
                                    os.makedirs(conflict_dir)
                                
                                conflict_target = os.path.join(conflict_dir, filename)
                                os.makedirs(os.path.dirname(conflict_target), exist_ok=True)
                                shutil.copy2(source_file, conflict_target)
                                
                                conflict_files.append({
                                    'file': filename,
                                    'source_md5': source_md5,
                                    'target_md5': target_md5,
                                    'conflict_path': conflict_target
                                })
                                
                                # 记录冲突到数据库
                                self.db.add_conflict(target_file, source_md5, target_md5)
                    
                    if not has_conflict:
                        # 没有冲突，直接复制并更新数据库
                        os.makedirs(os.path.dirname(target_file), exist_ok=True)
                        shutil.copy2(source_file, target_file)
                        success_files.append(filename)
                        
                        # 更新数据库记录，记录A端的MD5
                        stat = os.stat(target_file)
                        source_md5 = FileScanner.calculate_md5(source_file)
                        relative_path = os.path.relpath(target_file, target_folder)
                        self.db.update_file_info(
                            target_file,
                            relative_path,
                            target_folder,
                            stat.st_size,
                            stat.st_mtime,
                            source_md5
                        )
                    
                    if callback:
                        status = '冲突' if has_conflict else '成功'
                        callback(idx + 1, total, filename, status)
        
        finally:
            # 清理临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        
        return {
            'success': success_files,
            'conflicts': conflict_files
        }
