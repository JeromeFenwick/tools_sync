# -*- coding: utf-8 -*-
""" 
现代化GUI界面 - 使用 CustomTkinter
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import sys
import platform
from PIL import Image, ImageDraw
from database import Database
from file_scanner import FileScanner
from sync_core import SyncCore


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


# 设置外观模式和默认颜色主题
ctk.set_appearance_mode("dark")  # 模式: "dark", "light", "system"
ctk.set_default_color_theme("blue")  # 主题: "blue", "green", "dark-blue"


class ModernSyncGUI(ctk.CTk):
    """现代化文件同步工具GUI"""
    
    def __init__(self):
        super().__init__()
        
        # 窗口配置
        self.title("文件同步工具")
        self.geometry("1100x750")
        
        # 使用 overrideredirect 实现无边框
        self.overrideredirect(True)
        
        # 设置窗口透明色键
        self.attributes('-transparentcolor', '#010101')
        
        # 设置圆角半径
        self.corner_radius = 20
        
        # 设置窗口圆角（跨平台）
        if platform.system() == 'Windows':
            self.after(10, self._setup_taskbar_icon)
            # 设置圆角窗口
            self.after(20, self._apply_rounded_corners)
        elif platform.system() == 'Darwin':  # macOS
            # macOS 圆角窗口设置
            self.after(20, self._apply_rounded_corners)
        
        # 窗口拖动变量
        self._drag_start_x = 0
        self._drag_start_y = 0
        
        # 初始化数据库和核心模块
        app_dir = get_app_dir()
        db_path = os.path.join(app_dir, 'sync_data.db')
        self.db = Database(db_path)
        self.sync_core = SyncCore(self.db)
        
        # 当前模式
        self.current_mode = None
        
        # 数据存储
        self.selected_paths = []
        self.backup_folder = None
        self.sync_target_folder = None
        self.scan_results = []
        self.changed_files = []
        
        # 创建圆角背景容器
        self._create_rounded_container()
        
        # 创建自定义标题栏
        self._create_titlebar()
        
        # 创建模式选择界面
        self._create_mode_selection()
        
        # 绑定窗口大小变化事件以更新圆角
        self.bind('<Configure>', self._on_window_configure)
    
    def _create_rounded_container(self):
        """
        创建圆角背景容器
        """
        # 创建主背景框架,使用透明色作为背景
        self.configure(bg='#010101')
        
        # 创建实际内容容器,带圆角
        self.content_frame = ctk.CTkFrame(
            self,
            corner_radius=self.corner_radius,
            fg_color=("#F0F0F0", "#1A1A1A"),
            border_width=0
        )
        # 留出一些边距让圆角更明显
        self.content_frame.pack(fill="both", expand=True, padx=2, pady=2)
    
    def _on_window_configure(self, event=None):
        """
        窗口大小变化时更新圆角遮罩
        """
        pass  # content_frame 使用 pack 布局自动调整
    
    def _apply_rounded_corners(self):
        """
        应用圆角窗口（跨平台支持）
        """
        if platform.system() == 'Windows':
            self._apply_windows_rounded_corners()
        elif platform.system() == 'Darwin':  # macOS
            self._apply_macos_rounded_corners()
    
    def _apply_windows_rounded_corners(self):
        """
        应用 Windows 11 风格的圆角窗口
        """
        try:
            import ctypes
            from ctypes import wintypes
            
            # 获取窗口句柄
            hwnd = ctypes.windll.user32.FindWindowW(None, self.title())
            if not hwnd:
                return
            
            # Windows 11 DWM 圆角 API
            # DWM_WINDOW_CORNER_PREFERENCE
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2  # 圆角 (1=小圆角, 2=标准圆角, 3=大圆角)
            
            # 设置圆角属性
            preference = ctypes.c_int(DWMWCP_ROUND)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(preference),
                ctypes.sizeof(preference)
            )
            
            # 额外: 设置窗口阴影
            DWMWA_NCRENDERING_POLICY = 2
            DWMNCRP_ENABLED = 2
            rendering = ctypes.c_int(DWMNCRP_ENABLED)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_NCRENDERING_POLICY,
                ctypes.byref(rendering),
                ctypes.sizeof(rendering)
            )
            
        except Exception as e:
            print(f"Windows 设置圆角窗口失败: {e}")
    
    def _apply_macos_rounded_corners(self):
        """
        应用 macOS 风格的圆角窗口
        """
        try:
            # macOS 的窗口默认就有圆角，但我们可以增强效果
            # 对于 overrideredirect 窗口，需要特殊处理
            
            # 获取 Tk 窗口的 NSWindow 对象
            from tkinter import _tkinter
            
            # 设置窗口样式为圆角
            # macOS 上 overrideredirect 窗口默认已经是圆角的
            # 我们主要确保窗口有阴影效果
            
            # 设置窗口阴影
            try:
                # 使用 tkinter 的 wm 命令设置阴影
                # 对于 overrideredirect 窗口，macOS 会自动应用圆角
                self.update_idletasks()
                
                # macOS 的圆角和阴影是系统默认行为
                # 只要确保 content_frame 的圆角设置正确即可
                print("macOS: 圆角窗口已启用")
                
            except Exception as inner_e:
                print(f"macOS 阴影设置失败: {inner_e}")
                
        except Exception as e:
            print(f"macOS 设置圆角窗口失败: {e}")
    
    def _setup_taskbar_icon(self):
        """
        设置任务栏图标显示
        使用 Windows API 设置窗口扩展样式，让 overrideredirect 窗口也能在任务栏显示
        """
        try:
            import ctypes
            from ctypes import wintypes
            
            # 获取窗口句柄
            hwnd = ctypes.windll.user32.FindWindowW(None, self.title())
            if hwnd:
                # 设置窗口图标
                try:
                    # 获取图标文件路径
                    icon_path = os.path.join(get_app_dir(), 'icon.ico')
                    if os.path.exists(icon_path):
                        # 加载图标
                        IMAGE_ICON = 1
                        LR_LOADFROMFILE = 0x00000010
                        LR_DEFAULTSIZE = 0x00000040
                        
                        # 加载大图标和小图标
                        hicon_big = ctypes.windll.user32.LoadImageW(
                            None, icon_path, IMAGE_ICON, 
                            0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE
                        )
                        hicon_small = ctypes.windll.user32.LoadImageW(
                            None, icon_path, IMAGE_ICON,
                            16, 16, LR_LOADFROMFILE
                        )
                        
                        # 设置窗口图标
                        WM_SETICON = 0x0080
                        ICON_BIG = 1
                        ICON_SMALL = 0
                        if hicon_big:
                            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
                        if hicon_small:
                            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
                except Exception as icon_error:
                    print(f"设置窗口图标失败: {icon_error}")
                
                # 获取当前扩展样式
                GWL_EXSTYLE = -20
                ex_style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
                # 添加 WS_EX_APPWINDOW 样式（在任务栏显示）
                # 移除 WS_EX_TOOLWINDOW 样式（避免隐藏）
                WS_EX_APPWINDOW = 0x00040000
                WS_EX_TOOLWINDOW = 0x00000080
                ex_style |= WS_EX_APPWINDOW
                ex_style &= ~WS_EX_TOOLWINDOW
                ctypes.windll.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex_style)
                
                # 强制刷新任务栏
                # SW_HIDE = 0, SW_SHOW = 5
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # 隐藏
                ctypes.windll.user32.ShowWindow(hwnd, 5)  # 显示
        except Exception as e:
            print(f"设置任务栏图标失败: {e}")
    
    def _create_titlebar(self):
        """创建自定义标题栏"""
        self.titlebar = ctk.CTkFrame(
            self.content_frame,
            height=45,
            corner_radius=0,
            fg_color=("#E0E0E0", "#1E1E1E")
        )
        self.titlebar.pack(fill="x", side="top")
        self.titlebar.pack_propagate(False)
        
        # 标题文字
        self.title_label = ctk.CTkLabel(
            self.titlebar,
            text="📦 文件同步工具",
            font=ctk.CTkFont(family="微软雅黑", size=13, weight="bold")
        )
        self.title_label.pack(side="left", padx=15)
        
        # 绑定拖动事件
        self.titlebar.bind("<Button-1>", self._start_drag)
        self.titlebar.bind("<B1-Motion>", self._on_drag)
        self.title_label.bind("<Button-1>", self._start_drag)
        self.title_label.bind("<B1-Motion>", self._on_drag)
        
        # 按钮容器
        button_frame = ctk.CTkFrame(self.titlebar, fg_color="transparent")
        button_frame.pack(side="right", padx=5)
        
        # 最小化按钮
        self.minimize_btn = ctk.CTkButton(
            button_frame,
            text="—",
            width=40,
            height=30,
            corner_radius=8,
            fg_color="transparent",
            text_color=("#2B2B2B", "#E0E0E0"),  # 浅色模式用深色，深色模式用浅色
            hover_color=("#D0D0D0", "#2A2A2A"),
            command=self._minimize_window
        )
        self.minimize_btn.pack(side="left", padx=2)
        
        # 最大化按钮
        self.maximize_btn = ctk.CTkButton(
            button_frame,
            text="□",
            width=40,
            height=30,
            corner_radius=8,
            fg_color="transparent",
            text_color=("#2B2B2B", "#E0E0E0"),  # 浅色模式用深色，深色模式用浅色
            hover_color=("#D0D0D0", "#2A2A2A"),
            command=self._toggle_maximize
        )
        self.maximize_btn.pack(side="left", padx=2)
        
        # 关闭按钮
        self.close_btn = ctk.CTkButton(
            button_frame,
            text="✕",
            width=40,
            height=30,
            corner_radius=8,
            fg_color="transparent",
            text_color=("#2B2B2B", "#E0E0E0"),  # 浅色模式用深色，深色模式用浅色
            hover_color=("#E81123", "#C42B1C"),
            command=self._close_window
        )
        self.close_btn.pack(side="left", padx=2)
    
    def _start_drag(self, event):
        """开始拖动窗口"""
        self._drag_start_x = event.x
        self._drag_start_y = event.y
    
    def _on_drag(self, event):
        """拖动窗口"""
        x = self.winfo_x() + event.x - self._drag_start_x
        y = self.winfo_y() + event.y - self._drag_start_y
        self.geometry(f"+{x}+{y}")
    
    def _minimize_window(self):
        """最小化窗口"""
        self.iconify()
    
    def _toggle_maximize(self):
        """切换最大化状态"""
        if self.state() == 'zoomed':
            self.state('normal')
        else:
            self.state('zoomed')
    
    def _close_window(self):
        """关闭窗口"""
        self.quit()
        self.destroy()
    
    def _create_mode_selection(self):
        """创建模式选择界面"""
        # 清空窗口（保留标题栏和背景容器）
        for widget in self.content_frame.winfo_children():
            if widget != self.titlebar:
                widget.destroy()
        
        # 更新标题栏文字
        self.title_label.configure(text="📦 文件同步工具")
        
        # 主容器
        main_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=40, pady=(20, 40))
        
        # 标题
        title_label = ctk.CTkLabel(
            main_container,
            text="文件同步工具",
            font=ctk.CTkFont(family="微软雅黑", size=42, weight="bold")
        )
        title_label.pack(pady=(60, 20))
        
        # 副标题
        subtitle_label = ctk.CTkLabel(
            main_container,
            text="智能变更检测 · MD5校验 · 冲突处理",
            font=ctk.CTkFont(family="微软雅黑", size=16),
            text_color=("gray60", "gray50")
        )
        subtitle_label.pack(pady=(0, 80))
        
        # 按钮容器
        button_container = ctk.CTkFrame(main_container, fg_color="transparent")
        button_container.pack(pady=40)
        
        # 备份模式按钮
        backup_btn = ctk.CTkButton(
            button_container,
            text="📦 备份模式",
            font=ctk.CTkFont(family="微软雅黑", size=20, weight="bold"),
            width=220,
            height=100,
            corner_radius=20,
            fg_color=("#2CC985", "#2FA572"),
            hover_color=("#28B573", "#268F5F"),
            command=lambda: self._switch_mode('backup')
        )
        backup_btn.grid(row=0, column=0, padx=25)
        
        # 同步模式按钮
        sync_btn = ctk.CTkButton(
            button_container,
            text="🔄 同步模式",
            font=ctk.CTkFont(family="微软雅黑", size=20, weight="bold"),
            width=220,
            height=100,
            corner_radius=20,
            fg_color=("#3B8ED0", "#1F6AA5"),
            hover_color=("#2E7AB8", "#175A8A"),
            command=lambda: self._switch_mode('sync')
        )
        sync_btn.grid(row=0, column=1, padx=25)
        
        # 说明卡片
        info_frame = ctk.CTkFrame(main_container, corner_radius=20)
        info_frame.pack(pady=40, padx=100, fill="x")
        
        # 备份模式说明
        backup_info = ctk.CTkLabel(
            info_frame,
            text="📦 备份模式\n扫描文件夹变化，生成压缩包备份",
            font=ctk.CTkFont(family="微软雅黑", size=13),
            justify="left"
        )
        backup_info.grid(row=0, column=0, padx=30, pady=20, sticky="w")
        
        # 分隔线1
        separator1 = ctk.CTkFrame(info_frame, width=2, height=40, fg_color=("gray70", "gray30"))
        separator1.grid(row=0, column=1, padx=20)
        
        # 同步模式说明
        sync_info = ctk.CTkLabel(
            info_frame,
            text="🔄 同步模式\n智能冲突检测，安全同步文件",
            font=ctk.CTkFont(family="微软雅黑", size=13),
            justify="left"
        )
        sync_info.grid(row=0, column=2, padx=30, pady=20, sticky="w")
        
        # 分隔线2
        separator2 = ctk.CTkFrame(info_frame, width=2, height=40, fg_color=("gray70", "gray30"))
        separator2.grid(row=0, column=3, padx=20)
        
        # 待开发功能说明
        coming_soon_info = ctk.CTkLabel(
            info_frame,
            text="🚀 更多功能\n敬请期待...",
            font=ctk.CTkFont(family="微软雅黑", size=13),
            justify="left",
            text_color=("gray50", "gray60")  # 使用灰色表示待开发
        )
        coming_soon_info.grid(row=0, column=4, padx=30, pady=20, sticky="w")
        
        # 底部版本信息
        version_label = ctk.CTkLabel(
            self.content_frame,
            text="v2.0 Modern Edition\nCopyright © 2026 Fenwick All Rights Reserved",
            font=ctk.CTkFont(family="微软雅黑", size=11),
            text_color=("gray60", "gray40")
        )
        version_label.pack(side="bottom", pady=10)
    
    def _switch_mode(self, mode):
        """切换工作模式"""
        self.current_mode = mode
        if mode == 'backup':
            self._create_backup_interface()
        else:
            self._create_sync_interface()
    
    def _create_backup_interface(self):
        """创建备份模式界面"""
        # 清空窗口（保留标题栏和背景容器）
        for widget in self.content_frame.winfo_children():
            if widget != self.titlebar:
                widget.destroy()
        
        # 更新标题栏文字
        self.title_label.configure(text="📦 备份模式")
        
        # 清空并重新加载备份文件夹列表
        self.selected_paths = []
        
        # 顶部导航栏
        self._create_navbar()
        
        # 主容器 - 使用grid布局
        main_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        main_frame.grid_columnconfigure(0, weight=1, minsize=350)  # 左侧面板固定最小宽度
        main_frame.grid_columnconfigure(1, weight=2)  # 右侧面板更宽
        main_frame.grid_rowconfigure(0, weight=1)
        
        # 左侧面板 - 文件夹选择
        left_panel = ctk.CTkFrame(main_frame, corner_radius=15)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        left_title = ctk.CTkLabel(
            left_panel,
            text="📁 备份文件夹",
            font=ctk.CTkFont(family="微软雅黑", size=18, weight="bold")
        )
        left_title.pack(pady=(20, 15), padx=20)
        
        # 按钮容器
        button_container = ctk.CTkFrame(left_panel, fg_color="transparent")
        button_container.pack(fill="x", padx=20, pady=(0, 15))
        button_container.grid_columnconfigure(0, weight=1)
        button_container.grid_columnconfigure(1, weight=0)
        
        # 添加文件夹按钮
        add_folder_btn = ctk.CTkButton(
            button_container,
            text="➕ 添加文件夹",
            font=ctk.CTkFont(family="微软雅黑", size=14),
            height=45,
            corner_radius=10,
            fg_color=("#2CC985", "#2FA572"),
            hover_color=("#28B573", "#268F5F"),
            command=self._add_backup_folder
        )
        add_folder_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        
        # 刷新按钮
        refresh_btn = ctk.CTkButton(
            button_container,
            text="🔄",
            font=ctk.CTkFont(size=16),
            width=45,
            height=45,
            corner_radius=10,
            fg_color=("#757575", "#4A4A4A"),
            hover_color=("#616161", "#3A3A3A"),
            command=self._refresh_backup_folders
        )
        refresh_btn.grid(row=0, column=1, sticky="e")
        
        # 文件夹列表框架
        list_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # 使用 CTkScrollableFrame
        self.folder_scroll = ctk.CTkScrollableFrame(
            list_frame,
            corner_radius=10,
            fg_color=("gray90", "gray20")
        )
        self.folder_scroll.pack(fill="both", expand=True)
        
        # 加载上次选择的文件夹
        self._load_backup_folders()
        
        # 右侧面板 - 操作区域
        right_panel = ctk.CTkFrame(main_frame, corner_radius=15)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right_panel.grid_rowconfigure(1, weight=1)
        
        right_title = ctk.CTkLabel(
            right_panel,
            text="⚙️ 备份操作",
            font=ctk.CTkFont(family="微软雅黑", size=18, weight="bold")
        )
        right_title.pack(pady=(20, 15), padx=20)
        
        # 操作按钮容器
        btn_container = ctk.CTkFrame(right_panel, fg_color="transparent")
        btn_container.pack(fill="x", padx=20)
        
        # 扫描按钮
        scan_btn = ctk.CTkButton(
            btn_container,
            text="🔍 扫描变更",
            font=ctk.CTkFont(family="微软雅黑", size=15, weight="bold"),
            height=50,
            corner_radius=10,
            fg_color=("#3B8ED0", "#1F6AA5"),
            hover_color=("#2E7AB8", "#175A8A"),
            command=self._scan_changes
        )
        scan_btn.pack(fill="x", pady=(0, 12))
        
        # 差异同步按钮
        diff_btn = ctk.CTkButton(
            btn_container,
            text="📦 差异同步",
            font=ctk.CTkFont(family="微软雅黑", size=15, weight="bold"),
            height=50,
            corner_radius=10,
            fg_color=("#FF9500", "#CC7700"),
            hover_color=("#E68600", "#B36600"),
            command=lambda: self._create_backup('diff')
        )
        diff_btn.pack(fill="x", pady=(0, 12))
        
        # 全量同步按钮
        full_btn = ctk.CTkButton(
            btn_container,
            text="📦 全量同步",
            font=ctk.CTkFont(family="微软雅黑", size=15, weight="bold"),
            height=50,
            corner_radius=10,
            fg_color=("#FF3B30", "#CC2F26"),
            hover_color=("#E63530", "#B32923"),
            command=lambda: self._create_backup('full')
        )
        full_btn.pack(fill="x", pady=(0, 12))
        
        # 日志区域
        log_label = ctk.CTkLabel(
            right_panel,
            text="📋 操作日志",
            font=ctk.CTkFont(family="微软雅黑", size=14, weight="bold"),
            anchor="w"
        )
        log_label.pack(fill="x", padx=20, pady=(20, 10))
        
        self.backup_log = ctk.CTkTextbox(
            right_panel,
            corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("gray90", "gray15")
        )
        self.backup_log.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.backup_log.configure(state="disabled")
    
    def _create_sync_interface(self):
        """创建同步模式界面"""
        # 清空窗口（保留标题栏和背景容器）
        for widget in self.content_frame.winfo_children():
            if widget != self.titlebar:
                widget.destroy()
        
        # 更新标题栏文字
        self.title_label.configure(text="🔄 同步模式")
        
        # 顶部导航栏
        self._create_navbar()
        
        # 主容器
        main_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        main_frame.grid_columnconfigure(0, weight=1, minsize=350)  # 左侧面板固定最小宽度
        main_frame.grid_columnconfigure(1, weight=2)  # 右侧面板更宽
        main_frame.grid_rowconfigure(0, weight=1)
        
        # 左侧面板 - 文件选择
        left_panel = ctk.CTkFrame(main_frame, corner_radius=15)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        left_title = ctk.CTkLabel(
            left_panel,
            text="🎯 同步配置",
            font=ctk.CTkFont(family="微软雅黑", size=18, weight="bold")
        )
        left_title.pack(pady=(20, 20), padx=20)
        
        # 目标文件夹选择
        target_label = ctk.CTkLabel(
            left_panel,
            text="目标文件夹",
            font=ctk.CTkFont(family="微软雅黑", size=13, weight="bold"),
            anchor="w"
        )
        target_label.pack(fill="x", padx=20, pady=(10, 5))
        
        select_target_btn = ctk.CTkButton(
            left_panel,
            text="📁 选择目标文件夹",
            font=ctk.CTkFont(family="微软雅黑", size=14),
            height=45,
            corner_radius=10,
            fg_color=("#2CC985", "#2FA572"),
            hover_color=("#28B573", "#268F5F"),
            command=self._select_sync_target
        )
        select_target_btn.pack(fill="x", padx=20, pady=(0, 10))
        
        # 显示目标路径
        self.target_display = ctk.CTkTextbox(
            left_panel,
            height=70,
            corner_radius=10,
            font=ctk.CTkFont(family="微软雅黑", size=11),
            fg_color=("gray90", "gray20")
        )
        self.target_display.pack(fill="x", padx=20, pady=(0, 20))
        
        # 加载上次选择的目标文件夹
        last_target = self.db.get_last_sync_target()
        if last_target and os.path.exists(last_target):
            self.sync_target_folder = last_target
            self.target_display.insert("1.0", last_target)
        else:
            self.target_display.insert("1.0", "未选择目标文件夹")
        self.target_display.configure(state="disabled")
        
        # 分隔线
        separator1 = ctk.CTkFrame(left_panel, height=2, fg_color=("gray70", "gray30"))
        separator1.pack(fill="x", padx=20, pady=15)
        
        # 压缩包选择
        archive_label = ctk.CTkLabel(
            left_panel,
            text="备份压缩包",
            font=ctk.CTkFont(family="微软雅黑", size=13, weight="bold"),
            anchor="w"
        )
        archive_label.pack(fill="x", padx=20, pady=(10, 5))
        
        select_archive_btn = ctk.CTkButton(
            left_panel,
            text="📦 选择压缩包",
            font=ctk.CTkFont(family="微软雅黑", size=14),
            height=45,
            corner_radius=10,
            fg_color=("#3B8ED0", "#1F6AA5"),
            hover_color=("#2E7AB8", "#175A8A"),
            command=self._select_archive
        )
        select_archive_btn.pack(fill="x", padx=20, pady=(0, 10))
        
        # 显示压缩包路径
        self.archive_display = ctk.CTkTextbox(
            left_panel,
            height=70,
            corner_radius=10,
            font=ctk.CTkFont(family="微软雅黑", size=11),
            fg_color=("gray90", "gray20")
        )
        self.archive_display.pack(fill="x", padx=20, pady=(0, 20))
        self.archive_display.insert("1.0", "未选择压缩包")
        self.archive_display.configure(state="disabled")
        
        # 右侧面板 - 同步操作
        right_panel = ctk.CTkFrame(main_frame, corner_radius=15)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right_panel.grid_rowconfigure(1, weight=1)
        
        right_title = ctk.CTkLabel(
            right_panel,
            text="🚀 执行同步",
            font=ctk.CTkFont(family="微软雅黑", size=18, weight="bold")
        )
        right_title.pack(pady=(20, 15), padx=20)
        
        # 同步按钮
        sync_btn = ctk.CTkButton(
            right_panel,
            text="🔄 开始同步",
            font=ctk.CTkFont(family="微软雅黑", size=18, weight="bold"),
            height=80,
            corner_radius=20,
            fg_color=("#2CC985", "#2FA572"),
            hover_color=("#28B573", "#268F5F"),
            command=self._perform_sync
        )
        sync_btn.pack(fill="x", padx=20, pady=(0, 20))
        
        # 说明卡片
        info_card = ctk.CTkFrame(right_panel, corner_radius=15, fg_color=("#E8F4FD", "#1A3A52"))
        info_card.pack(fill="x", padx=20, pady=(0, 20))
        
        info_title = ctk.CTkLabel(
            info_card,
            text="ℹ️ 同步说明",
            font=ctk.CTkFont(family="微软雅黑", size=13, weight="bold"),
            anchor="w"
        )
        info_title.pack(fill="x", padx=15, pady=(15, 5))
        
        info_text = ctk.CTkLabel(
            info_card,
            text="• 自动检测文件MD5冲突\n• 冲突文件移至差异文件夹\n• 未冲突文件直接同步到目标位置\n• 安全可靠，不会丢失数据",
            font=ctk.CTkFont(family="微软雅黑", size=12),
            justify="left",
            anchor="w"
        )
        info_text.pack(fill="x", padx=15, pady=(0, 15))
        
        # 日志区域
        log_label = ctk.CTkLabel(
            right_panel,
            text="📋 操作日志",
            font=ctk.CTkFont(family="微软雅黑", size=14, weight="bold"),
            anchor="w"
        )
        log_label.pack(fill="x", padx=20, pady=(10, 10))
        
        self.sync_log = ctk.CTkTextbox(
            right_panel,
            corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("gray90", "gray15")
        )
        self.sync_log.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.sync_log.configure(state="disabled")
    
    def _create_navbar(self):
        """创建顶部导航栏"""
        navbar = ctk.CTkFrame(self.content_frame, height=60, corner_radius=0, fg_color=("#DBDBDB", "#2B2B2B"))
        navbar.pack(fill="x", padx=0, pady=(0, 15))  # 添加下边距
        navbar.pack_propagate(False)
        
        # 当前模式标签
        mode_text = "📦 备份模式" if self.current_mode == 'backup' else "🔄 同步模式"
        mode_label = ctk.CTkLabel(
            navbar,
            text=mode_text,
            font=ctk.CTkFont(family="微软雅黑", size=16, weight="bold")
        )
        mode_label.pack(side="left", padx=25)
        
        # 切换模式按钮
        switch_text = "切换到同步模式" if self.current_mode == 'backup' else "切换到备份模式"
        switch_mode = 'sync' if self.current_mode == 'backup' else 'backup'
        
        switch_btn = ctk.CTkButton(
            navbar,
            text=f"↔️ {switch_text}",
            font=ctk.CTkFont(family="微软雅黑", size=13),
            width=150,
            height=36,
            corner_radius=8,
            fg_color=("#757575", "#4A4A4A"),
            hover_color=("#616161", "#3A3A3A"),
            command=lambda: self._switch_mode(switch_mode)
        )
        switch_btn.pack(side="right", padx=25)
        
        # 主题切换按钮
        theme_btn = ctk.CTkButton(
            navbar,
            text="🌓",
            font=ctk.CTkFont(size=16),
            width=40,
            height=36,
            corner_radius=8,
            fg_color=("#757575", "#4A4A4A"),
            hover_color=("#616161", "#3A3A3A"),
            command=self._toggle_theme
        )
        theme_btn.pack(side="right", padx=(0, 10))
    
    def _toggle_theme(self):
        """切换主题"""
        current = ctk.get_appearance_mode()
        new_mode = "light" if current == "Dark" else "dark"
        ctk.set_appearance_mode(new_mode)
    
    def _add_backup_folder(self):
        """添加备份文件夹"""
        folder = filedialog.askdirectory(title="选择要备份的文件夹")
        if folder and folder not in self.selected_paths:
            self.selected_paths.append(folder)
            self._add_folder_item(folder)
            self._log_message(f"✓ 已添加文件夹: {folder}", self.backup_log)
            
            # 保存到数据库
            self.db.set_backup_folders(self.selected_paths)
    
    def _add_folder_item(self, folder):
        """添加文件夹项到列表"""
        item_frame = ctk.CTkFrame(self.folder_scroll, corner_radius=8, fg_color=("white", "gray25"))
        item_frame.pack(fill="x", pady=5, padx=5)
        
        # 文件夹信息容器
        info_container = ctk.CTkFrame(item_frame, fg_color="transparent")
        info_container.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        
        # 文件夹图标和名称
        folder_name = os.path.basename(folder)
        path_label = ctk.CTkLabel(
            info_container,
            text=f"📁 {folder_name}",
            font=ctk.CTkFont(family="微软雅黑", size=12, weight="bold"),
            anchor="w"
        )
        path_label.pack(anchor="w")
        
        # 完整路径提示
        full_path_label = ctk.CTkLabel(
            info_container,
            text=folder,
            font=ctk.CTkFont(family="微软雅黑", size=9),
            text_color=("gray50", "gray60"),
            anchor="w"
        )
        full_path_label.pack(anchor="w")
        
        # 删除按钮
        delete_btn = ctk.CTkButton(
            item_frame,
            text="✕",
            font=ctk.CTkFont(size=14),
            width=30,
            height=30,
            corner_radius=6,
            fg_color="transparent",
            hover_color=("#E81123", "#C42B1C"),
            command=lambda: self._remove_backup_folder(folder, item_frame)
        )
        delete_btn.pack(side="right", padx=10)
    
    def _load_backup_folders(self):
        """加载上次选择的备份文件夹"""
        saved_folders = self.db.get_backup_folders()
        for folder in saved_folders:
            if os.path.exists(folder) and folder not in self.selected_paths:
                self.selected_paths.append(folder)
                self._add_folder_item(folder)
    
    def _remove_backup_folder(self, folder, item_frame):
        """删除备份文件夹"""
        if folder in self.selected_paths:
            self.selected_paths.remove(folder)
            item_frame.destroy()
            
            # 更新数据库
            self.db.set_backup_folders(self.selected_paths)
            self._log_message(f"✖️ 已删除文件夹: {folder}", self.backup_log)
    
    def _refresh_backup_folders(self):
        """刷新备份文件夹列表"""
        # 清空列表
        for widget in self.folder_scroll.winfo_children():
            widget.destroy()
        
        # 清空选中列表
        self.selected_paths.clear()
        
        # 重新加载
        self._load_backup_folders()
        self._log_message("🔄 已刷新文件夹列表", self.backup_log)
    
    def _scan_changes(self):
        """扫描文件夹变更"""
        if not self.selected_paths:
            messagebox.showwarning("提示", "请先添加要备份的文件夹")
            return
        
        # 默认扫描第一个文件夹
        folder = self.selected_paths[0]
        self._log_message(f"\n🔍 开始扫描文件夹: {folder}", self.backup_log)
        
        def scan_thread():
            def scan_callback(current, total, filename):
                self._log_message(f"扫描中: {current}/{total} - {filename}", self.backup_log, replace_last=True)
            
            # 扫描文件
            files_info = FileScanner.scan_folder(folder, scan_callback)
            self._log_message(f"\n✓ 扫描完成，共找到 {len(files_info)} 个文件", self.backup_log)
            
            # 比对变化
            self._log_message("🔍 正在比对文件差异...", self.backup_log)
            
            def compare_callback(current, total, filename):
                self._log_message(f"比对中: {current}/{total} - {filename}", self.backup_log, replace_last=True)
            
            self.changed_files = FileScanner.compare_files(
                self.db, folder, files_info, compare_callback
            )
            self.scan_results = files_info
            
            self._log_message(f"\n✓ 比对完成，发现 {len(self.changed_files)} 个文件有变化", self.backup_log)
        
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def _create_backup(self, sync_type):
        """创建备份包"""
        if not self.selected_paths:
            messagebox.showwarning("提示", "请先添加要备份的文件夹")
            return
        
        folder = self.selected_paths[0]
        
        if sync_type == 'diff' and not self.changed_files:
            messagebox.showwarning("提示", "请先扫描变更，或选择全量同步")
            return
        
        type_name = "差异" if sync_type == 'diff' else "全量"
        self._log_message(f"\n📦 开始创建{type_name}备份包...", self.backup_log)
        
        def backup_thread():
            files_to_backup = self.changed_files if sync_type == 'diff' else self.scan_results
            
            if not files_to_backup and sync_type == 'full':
                # 如果没有扫描结果，先扫描
                files_to_backup = FileScanner.scan_folder(folder)
                # 全量同步需要计算所有文件的MD5
                for file_info in files_to_backup:
                    md5_hash = FileScanner.calculate_md5(file_info['path'])
                    file_info['md5_hash'] = md5_hash
            
            if not files_to_backup:
                self._log_message("⚠️ 没有需要备份的文件", self.backup_log)
                return
            
            archive_path = self.sync_core.create_backup_package(
                folder, files_to_backup, sync_type
            )
            
            if archive_path:
                self._log_message(f"\n✓ 备份包创建成功！", self.backup_log)
                self._log_message(f"  路径: {archive_path}", self.backup_log)
                self._log_message(f"  文件数: {len(files_to_backup)}", self.backup_log)
                messagebox.showinfo("成功", f"备份包已创建！\n\n文件数: {len(files_to_backup)}\n路径: {archive_path}")
            else:
                self._log_message("✗ 备份包创建失败", self.backup_log)
        
        threading.Thread(target=backup_thread, daemon=True).start()
    
    def _select_sync_target(self):
        """选择同步目标文件夹"""
        folder = filedialog.askdirectory(title="选择同步目标文件夹")
        if folder:
            self.sync_target_folder = folder
            self.target_display.configure(state="normal")
            self.target_display.delete("1.0", "end")
            self.target_display.insert("1.0", folder)
            self.target_display.configure(state="disabled")
            self._log_message(f"✓ 已选择目标文件夹: {folder}", self.sync_log)
            
            # 保存到数据库
            self.db.set_last_sync_target(folder)
    
    def _select_archive(self):
        """选择压缩包"""
        archive = filedialog.askopenfilename(
            title="选择压缩包",
            filetypes=[("压缩包", "*.zip"), ("所有文件", "*.*")]
        )
        if archive:
            self.selected_archive = archive
            self.archive_display.configure(state="normal")
            self.archive_display.delete("1.0", "end")
            self.archive_display.insert("1.0", archive)
            self.archive_display.configure(state="disabled")
            self._log_message(f"✓ 已选择压缩包: {os.path.basename(archive)}", self.sync_log)
    
    def _perform_sync(self):
        """执行同步"""
        if not hasattr(self, 'sync_target_folder') or not self.sync_target_folder:
            messagebox.showwarning("提示", "请先选择目标文件夹")
            return
        
        if not hasattr(self, 'selected_archive') or not self.selected_archive:
            messagebox.showwarning("提示", "请先选择压缩包")
            return
        
        self._log_message(f"\n🔄 开始同步到: {self.sync_target_folder}", self.sync_log)
        
        def sync_thread():
            def sync_callback(current, total, filename, status):
                icon = "✓" if status == "成功" else "⚠️"
                self._log_message(
                    f"{icon} 同步中: {current}/{total} - {filename} [{status}]",
                    self.sync_log,
                    replace_last=True
                )
            
            result = self.sync_core.sync_to_folder(
                self.selected_archive,
                self.sync_target_folder,
                sync_callback
            )
            
            self._log_message(f"\n✓ 同步完成！", self.sync_log)
            self._log_message(f"  成功: {len(result['success'])} 个文件", self.sync_log)
            self._log_message(f"  冲突: {len(result['conflicts'])} 个文件", self.sync_log)
            
            if result['conflicts']:
                self._log_message("\n⚠️ 冲突文件已移至差异文件夹:", self.sync_log)
                for conflict in result['conflicts'][:5]:  # 最多显示5个
                    self._log_message(f"  • {conflict['file']}", self.sync_log)
                if len(result['conflicts']) > 5:
                    self._log_message(f"  • ... 还有 {len(result['conflicts']) - 5} 个", self.sync_log)
            
            msg = f"同步完成！\n\n✓ 成功: {len(result['success'])} 个文件\n"
            if result['conflicts']:
                msg += f"⚠️ 冲突: {len(result['conflicts'])} 个文件\n\n冲突文件已移至差异文件夹，请人工比对"
            
            messagebox.showinfo("同步完成", msg)
        
        threading.Thread(target=sync_thread, daemon=True).start()
    
    def _log_message(self, message, log_widget, replace_last=False):
        """添加日志消息"""
        def update_log():
            log_widget.configure(state="normal")
            if replace_last:
                # 删除最后一行
                log_widget.delete("end-2l", "end-1l")
            log_widget.insert("end", message + "\n")
            log_widget.see("end")
            log_widget.configure(state="disabled")
        
        self.after(0, update_log)


def main():
    app = ModernSyncGUI()
    app.mainloop()


if __name__ == '__main__':
    main()
