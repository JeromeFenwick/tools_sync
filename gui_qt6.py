# -*- coding: utf-8 -*-
""" 
现代化GUI界面 - 使用 PyQt6
"""
import sys
import os
import platform
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QTextEdit, QFileDialog,
    QGridLayout, QSizePolicy, QProgressBar
)
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer
from PyQt6.QtGui import QPalette, QColor, QPainter, QPainterPath, QRegion, QFont
from database import Database
from file_scanner import FileScanner
from sync_core import SyncCore
import threading


def get_app_dir():
    """
    获取应用所在目录
    支持 Windows 和 macOS 打包后的路径处理
    """
    if getattr(sys, 'frozen', False):
        executable_path = sys.executable
        
        if platform.system() == 'Darwin' and '.app/Contents/MacOS' in executable_path:
            app_bundle = executable_path.split('.app/Contents/MacOS')[0] + '.app'
            return os.path.dirname(app_bundle)
        else:
            return os.path.dirname(executable_path)
    else:
        return os.path.dirname(os.path.abspath(__file__))


class RoundedWindow(QMainWindow):
    """支持圆角的主窗口"""
    
    def __init__(self):
        super().__init__()
        self.corner_radius = 20
        self.bg_color = QColor("#1A1A1A")  # 默认背景色
        self._setup_window()
    
    def set_background_color(self, color):
        """设置背景颜色"""
        self.bg_color = QColor(color)
        self.update()  # 触发重绘
        
    def _setup_window(self):
        """设置窗口属性"""
        # 无边框窗口
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 窗口大小
        self.resize(1100, 750)
        
        # 拖动相关
        self._drag_pos = QPoint()
        
    def paintEvent(self, event):
        """绘制圆角背景"""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 绘制阴影和圆角背景
            path = QPainterPath()
            rect = self.rect().adjusted(5, 5, -5, -5)
            path.addRoundedRect(
                rect.x(), rect.y(), rect.width(), rect.height(),
                self.corner_radius, self.corner_radius
            )
            
            # 背景色
            painter.fillPath(path, self.bg_color)
        except Exception as e:
            print(f"绘制错误: {e}")
        finally:
            super().paintEvent(event)


class ModernSyncGUI(RoundedWindow):
    """现代化文件同步工具GUI - Qt6版本"""
    
    # 定义信号（线程安全）
    backup_log_signal = pyqtSignal(str)
    sync_log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        # 连接信号（必须在最先）
        self.backup_log_signal.connect(self._append_backup_log)
        self.sync_log_signal.connect(self._append_sync_log)
        
        # 初始化数据库和核心模块
        app_dir = get_app_dir()
        db_path = os.path.join(app_dir, 'sync_data.db')
        self.db = Database(db_path)
        self.sync_core = SyncCore(self.db)
        
        # 当前模式
        self.current_mode = None
        self.current_theme = 'dark'  # 默认暗色主题
        
        # 数据存储
        self.selected_paths = []
        self.backup_folder = None
        self.sync_target_folder = None
        self.scan_results = []
        self.changed_files = []
        
        # 创建UI
        self._create_ui()
        
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 确保所有线程都已结束
            event.accept()
        except Exception as e:
            print(f"关闭错误: {e}")
            event.accept()
    
    def _create_ui(self):
        """创建主UI"""
        # 主容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)
        
        # 创建标题栏
        self._create_titlebar(main_layout)
        
        # 创建内容区域
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.content_widget)
        
        # 显示模式选择界面
        self._create_mode_selection()
        
        # 应用样式表
        self._apply_stylesheet()
        
    def _create_titlebar(self, parent_layout):
        """创建自定义标题栏"""
        titlebar = QFrame()
        titlebar.setObjectName("titlebar")
        titlebar.setFixedHeight(45)
        
        layout = QHBoxLayout(titlebar)
        layout.setContentsMargins(15, 0, 5, 0)
        layout.setSpacing(10)
        
        # 标题
        self.title_label = QLabel("📦 文件同步工具")
        self.title_label.setObjectName("titleLabel")
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # 设置按钮
        settings_btn = QPushButton("⚙️")
        settings_btn.setObjectName("settingsBtn")
        settings_btn.setFixedSize(45, 35)
        settings_btn.setToolTip("设置")
        settings_btn.clicked.connect(self._show_settings)
        layout.addWidget(settings_btn)
        
        # 最小化按钮
        min_btn = QPushButton("—")
        min_btn.setObjectName("minBtn")
        min_btn.setFixedSize(45, 35)
        min_btn.setToolTip("最小化")
        min_btn.clicked.connect(self.showMinimized)
        layout.addWidget(min_btn)
        
        # 最大化按钮
        max_btn = QPushButton("❏")
        max_btn.setObjectName("maxBtn")
        max_btn.setFixedSize(45, 35)
        max_btn.setToolTip("最大化")
        max_btn.clicked.connect(self._toggle_maximize)
        layout.addWidget(max_btn)
        
        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(45, 35)
        close_btn.setToolTip("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        parent_layout.addWidget(titlebar)
        
        # 使标题栏可拖动
        titlebar.mousePressEvent = self._title_mouse_press
        titlebar.mouseMoveEvent = self._title_mouse_move
        self.title_label.mousePressEvent = self._title_mouse_press
        self.title_label.mouseMoveEvent = self._title_mouse_move
        
    def _title_mouse_press(self, event):
        """标题栏鼠标按下"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            
    def _title_mouse_move(self, event):
        """标题栏鼠标移动"""
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            
    def _toggle_maximize(self):
        """切换最大化状态"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
            
    def _create_mode_selection(self):
        """创建模式选择界面"""
        # 清空内容区域
        self._clear_content()
        
        # 更新标题
        self.title_label.setText("🔧  文件同步工具")
        
        # 主容器
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 60, 40, 40)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel("文件同步工具")
        title.setObjectName("mainTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 副标题
        subtitle = QLabel("智能变更检测 · MD5校验 · 冲突处理")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(60)
        
        # 按钮容器
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setSpacing(50)
        
        # 备份模式按钮
        backup_btn = QPushButton("📦 备份模式")
        backup_btn.setObjectName("modeBtn")
        backup_btn.setProperty("mode", "backup")
        backup_btn.setFixedSize(220, 100)
        backup_btn.clicked.connect(lambda: self._switch_mode('backup'))
        btn_layout.addWidget(backup_btn)
        
        # 同步模式按钮
        sync_btn = QPushButton("🔄 同步模式")
        sync_btn.setObjectName("modeBtn")
        sync_btn.setProperty("mode", "sync")
        sync_btn.setFixedSize(220, 100)
        sync_btn.clicked.connect(lambda: self._switch_mode('sync'))
        btn_layout.addWidget(sync_btn)
        
        layout.addWidget(btn_container, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addSpacing(40)
        
        # 说明卡片
        info_frame = QFrame()
        info_frame.setObjectName("infoCard")
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(30, 20, 30, 20)
        
        # 备份模式说明
        backup_info = QLabel("📦 备份模式\n扫描文件夹变化，生成压缩包备份")
        backup_info.setObjectName("infoText")
        info_layout.addWidget(backup_info)
        
        # 分隔线
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setObjectName("separator")
        info_layout.addWidget(sep1)
        
        # 同步模式说明
        sync_info = QLabel("🔄 同步模式\n智能冲突检测，安全同步文件")
        sync_info.setObjectName("infoText")
        info_layout.addWidget(sync_info)
        
        # 分隔线
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setObjectName("separator")
        info_layout.addWidget(sep2)
        
        # 更多功能说明
        coming_info = QLabel("🚀 更多功能\n敬请期待 . . .")
        coming_info.setObjectName("infoText")
        info_layout.addWidget(coming_info)
        
        layout.addWidget(info_frame)
        
        layout.addStretch()
        
        # 版本信息
        version = QLabel("v2.0 Modern Edition\nCopyright © 2026 Fenwick All Rights Reserved")
        version.setObjectName("version")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        
        self.content_layout.addWidget(container)
        
    def _switch_mode(self, mode):
        """切换工作模式"""
        self.current_mode = mode
        if mode == 'backup':
            self._create_backup_interface()
        else:
            self._create_sync_interface()
            
    def _create_backup_interface(self):
        """创建备份模式界面"""
        # 清空内容
        self._clear_content()
        
        # 清空选择
        self.selected_paths = []
        
        # 创建导航栏
        self._create_navbar()
        
        # 主容器
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 0, 20, 20)
        main_layout.setSpacing(20)
        
        # 左侧面板（固定宽度）
        left_panel = self._create_left_panel_backup()
        left_panel.setFixedWidth(380)  # 固定宽度
        main_layout.addWidget(left_panel)
        
        # 右侧面板
        right_panel = self._create_right_panel_backup()
        main_layout.addWidget(right_panel, 1)  # 使用stretch占据剩余空间
        
        self.content_layout.addWidget(main_widget)
        
    def _create_left_panel_backup(self):
        """创建备份模式左侧面板"""
        panel = QFrame()
        panel.setObjectName("panel")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("📁 备份文件夹")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        
        # 按钮容器
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setSpacing(8)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加文件夹按钮
        add_btn = QPushButton("➕ 添加文件夹")
        add_btn.setObjectName("primaryBtn")
        add_btn.setFixedHeight(45)
        add_btn.clicked.connect(self._add_backup_folder)
        btn_layout.addWidget(add_btn, 1)
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄")
        refresh_btn.setObjectName("iconBtn")
        refresh_btn.setFixedSize(45, 45)
        refresh_btn.clicked.connect(self._refresh_backup_folders)
        btn_layout.addWidget(refresh_btn)
        
        layout.addWidget(btn_container)
        
        # 文件夹列表（无滚动条）
        self.folder_list_widget = QWidget()
        self.folder_list_layout = QVBoxLayout(self.folder_list_widget)
        self.folder_list_layout.setContentsMargins(0, 0, 0, 0)
        self.folder_list_layout.setSpacing(8)
        self.folder_list_layout.addStretch()
        
        # 直接添加到面板，不使用滚动区域
        layout.addWidget(self.folder_list_widget, 1)
        
        # 加载保存的文件夹
        self._load_backup_folders()
        
        return panel
        
    def _create_right_panel_backup(self):
        """创建备份模式右侧面板"""
        panel = QFrame()
        panel.setObjectName("panel")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("⚙️ 备份操作")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        
        # 操作按钮
        scan_btn = QPushButton("🔍 扫描变更")
        scan_btn.setObjectName("actionBtn")
        scan_btn.setProperty("action", "scan")
        scan_btn.setFixedHeight(50)
        scan_btn.clicked.connect(self._scan_changes)
        layout.addWidget(scan_btn)
        
        diff_btn = QPushButton("📦 差异同步")
        diff_btn.setObjectName("actionBtn")
        diff_btn.setProperty("action", "diff")
        diff_btn.setFixedHeight(50)
        diff_btn.clicked.connect(lambda: self._create_backup('diff'))
        layout.addWidget(diff_btn)
        
        full_btn = QPushButton("📦 全量同步")
        full_btn.setObjectName("actionBtn")
        full_btn.setProperty("action", "full")
        full_btn.setFixedHeight(50)
        full_btn.clicked.connect(lambda: self._create_backup('full'))
        layout.addWidget(full_btn)
        
        # 日志标签
        log_label = QLabel("📋 操作日志")
        log_label.setObjectName("sectionTitle")
        layout.addWidget(log_label)
        
        # 进度条
        self.backup_progress = QProgressBar()
        self.backup_progress.setVisible(False)
        self.backup_progress.setTextVisible(True)
        layout.addWidget(self.backup_progress)
        
        # 日志文本框
        self.backup_log = QTextEdit()
        self.backup_log.setObjectName("logText")
        self.backup_log.setReadOnly(True)
        layout.addWidget(self.backup_log, 1)
        
        return panel
        
    def _create_sync_interface(self):
        """创建同步模式界面"""
        # 清空内容
        self._clear_content()
        
        # 创建导航栏
        self._create_navbar()
        
        # 主容器
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 0, 20, 20)
        main_layout.setSpacing(20)
        
        # 左侧面板（固定宽度）
        left_panel = self._create_left_panel_sync()
        left_panel.setFixedWidth(380)  # 固定宽度，与备份模式一致
        main_layout.addWidget(left_panel)
        
        # 右侧面板
        right_panel = self._create_right_panel_sync()
        main_layout.addWidget(right_panel, 1)  # 使用stretch占据剩余空间
        
        self.content_layout.addWidget(main_widget)
        
    def _create_left_panel_sync(self):
        """创建同步模式左侧面板"""
        panel = QFrame()
        panel.setObjectName("panel")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("🎯 同步配置")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        
        # 目标文件夹标签
        target_label = QLabel("目标文件夹")
        target_label.setObjectName("sectionLabel")
        layout.addWidget(target_label)
        
        # 选择目标文件夹按钮
        select_target_btn = QPushButton("📁 选择目标文件夹")
        select_target_btn.setObjectName("primaryBtn")
        select_target_btn.setFixedHeight(45)
        select_target_btn.clicked.connect(self._select_sync_target)
        layout.addWidget(select_target_btn)
        
        # 显示目标路径
        self.target_display = QTextEdit()
        self.target_display.setObjectName("pathDisplay")
        self.target_display.setFixedHeight(70)
        self.target_display.setReadOnly(True)
        
        # 加载上次选择的目标文件夹
        last_target = self.db.get_last_sync_target()
        if last_target and os.path.exists(last_target):
            self.sync_target_folder = last_target
            self.target_display.setText(last_target)
        else:
            self.target_display.setText("未选择目标文件夹")
        
        layout.addWidget(self.target_display)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        layout.addWidget(separator)
        
        # 压缩包标签
        archive_label = QLabel("备份压缩包")
        archive_label.setObjectName("sectionLabel")
        layout.addWidget(archive_label)
        
        # 选择压缩包按钮
        select_archive_btn = QPushButton("📦 选择压缩包")
        select_archive_btn.setObjectName("secondaryBtn")
        select_archive_btn.setFixedHeight(45)
        select_archive_btn.clicked.connect(self._select_archive)
        layout.addWidget(select_archive_btn)
        
        # 显示压缩包路径
        self.archive_display = QTextEdit()
        self.archive_display.setObjectName("pathDisplay")
        self.archive_display.setFixedHeight(70)
        self.archive_display.setReadOnly(True)
        self.archive_display.setText("未选择压缩包")
        layout.addWidget(self.archive_display)
        
        layout.addStretch()
        
        return panel
        
    def _create_right_panel_sync(self):
        """创建同步模式右侧面板"""
        panel = QFrame()
        panel.setObjectName("panel")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("🚀 执行同步")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        
        # 同步按钮
        sync_btn = QPushButton("🔄 开始同步")
        sync_btn.setObjectName("bigActionBtn")
        sync_btn.setFixedHeight(80)
        sync_btn.clicked.connect(self._perform_sync)
        layout.addWidget(sync_btn)
        
        # 说明卡片
        info_card = QFrame()
        info_card.setObjectName("infoCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(15, 15, 15, 15)
        
        info_title = QLabel("ℹ️ 同步说明")
        info_title.setObjectName("sectionTitle")
        info_layout.addWidget(info_title)
        
        info_text = QLabel(
            "• 自动检测文件MD5冲突\n"
            "• 冲突文件移至差异文件夹\n"
            "• 未冲突文件直接同步到目标位置\n"
            "• 安全可靠，不会丢失数据"
        )
        info_text.setObjectName("infoText")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_card)
        
        # 日志标签
        log_label = QLabel("📋 操作日志")
        log_label.setObjectName("sectionTitle")
        layout.addWidget(log_label)
        
        # 进度条
        self.sync_progress = QProgressBar()
        self.sync_progress.setVisible(False)
        self.sync_progress.setTextVisible(True)
        layout.addWidget(self.sync_progress)
        
        # 日志文本框
        self.sync_log = QTextEdit()
        self.sync_log.setObjectName("logText")
        self.sync_log.setReadOnly(True)
        layout.addWidget(self.sync_log, 1)
        
        return panel
        
    def _create_navbar(self):
        """创建导航栏"""
        navbar = QFrame()
        navbar.setObjectName("navbar")
        navbar.setFixedHeight(60)
        
        layout = QHBoxLayout(navbar)
        layout.setContentsMargins(25, 0, 25, 0)
        
        # 模式标签
        mode_text = "📦 备份模式" if self.current_mode == 'backup' else "🔄 同步模式"
        mode_label = QLabel(mode_text)
        mode_label.setObjectName("modeLabel")
        layout.addWidget(mode_label)
        
        layout.addStretch()
        
        # 主题切换按钮（根据当前主题显示不同图标）
        theme_icon = "☀️" if self.current_theme == 'dark' else "🌙"
        self.theme_btn = QPushButton(theme_icon)
        self.theme_btn.setObjectName("navBtn")
        self.theme_btn.setFixedSize(50, 36)
        self.theme_btn.setToolTip("切换主题")
        self.theme_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_btn)
        
        # 切换模式按钮
        switch_text = "切换到同步模式" if self.current_mode == 'backup' else "切换到备份模式"
        switch_mode = 'sync' if self.current_mode == 'backup' else 'backup'
        switch_btn = QPushButton(f"↔️ {switch_text}")
        switch_btn.setObjectName("navBtn")
        switch_btn.setFixedHeight(36)
        switch_btn.clicked.connect(lambda: self._switch_mode(switch_mode))
        layout.addWidget(switch_btn)
        
        self.content_layout.addWidget(navbar)
        
    def _toggle_theme(self):
        """快速切换主题"""
        new_theme = 'light' if self.current_theme == 'dark' else 'dark'
        
        # 切换主题
        self.current_theme = new_theme
        
        # 设置窗口背景色
        if new_theme == 'light':
            self.set_background_color('#F5F5F5')
        else:
            self.set_background_color('#1A1A1A')
        
        # 重新应用样式表
        self._apply_stylesheet()
        
        # 更新主题按钮图标
        if hasattr(self, 'theme_btn'):
            theme_icon = "☀️" if new_theme == 'dark' else "🌙"
            self.theme_btn.setText(theme_icon)
        
        # 刷新当前界面
        if self.current_mode == 'backup':
            self._create_backup_interface()
        elif self.current_mode == 'sync':
            self._create_sync_interface()
        else:
            self._create_mode_selection()
        
    def _clear_content(self):
        """清空内容区域"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
    def _apply_stylesheet(self):
        """应用样式表"""
        # 根据当前主题选择颜色
        if self.current_theme == 'light':
            colors = {
                'bg': '#F5F5F5',
                'panel': '#FFFFFF',
                'titlebar': '#E8E8E8',
                'text': '#1A1A1A',
                'text_secondary': '#505050',
                'separator': '#D0D0D0',
                'input_bg': '#FAFAFA',
                'input_border': '#D0D0D0',
                'hover': '#E0E0E0'
            }
        else:  # dark
            colors = {
                'bg': '#1A1A1A',
                'panel': '#2B2B2B',
                'titlebar': '#2B2B2B',
                'text': '#E0E0E0',
                'text_secondary': '#A0A0A0',
                'separator': '#404040',
                'input_bg': '#1F1F1F',
                'input_border': '#404040',
                'hover': '#3A3A3A'
            }
        
        self.setStyleSheet(f"""
            /* 主窗口 */
            QMainWindow {{
                background-color: {colors['bg']};
            }}
            
            /* 标题栏 */
            #titlebar {{
                background-color: {colors['titlebar']};
                border-top-left-radius: 15px;
                border-top-right-radius: 15px;
            }}
            
            #titleLabel {{
                color: {colors['text']};
                font-size: 16px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
            }}
            
            /* 设置按钮 */
            #settingsBtn {{
                background-color: transparent;
                color: {colors['text']};
                border: none;
                border-radius: 8px;
                font-size: 16px;
            }}
            
            #settingsBtn:hover {{
                background-color: {colors['hover']};
            }}
            
            /* 标题栏按钮 */
            #minBtn, #maxBtn, #closeBtn {{
                background-color: transparent;
                color: {colors['text']};
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }}
            
            #minBtn:hover, #maxBtn:hover {{
                background-color: {colors['hover']};
            }}
            
            #closeBtn:hover {{
                background-color: #C42B1C;
            }}
            
            /* 主标题 */
            #mainTitle {{
                color: {colors['text']};
                font-size: 42px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
            }}
            
            #subtitle {{
                color: {colors['text_secondary']};
                font-size: 16px;
                font-family: "Microsoft YaHei";
            }}
            
            /* 模式按钮 */
            QPushButton#modeBtn {{
                color: white;
                font-size: 20px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
                border: none;
                border-radius: 20px;
            }}
            
            QPushButton#modeBtn[mode="backup"] {{
                background-color: #2FA572;
            }}
            
            QPushButton#modeBtn[mode="backup"]:hover {{
                background-color: #268F5F;
            }}
            
            QPushButton#modeBtn[mode="sync"] {{
                background-color: #1F6AA5;
            }}
            
            QPushButton#modeBtn[mode="sync"]:hover {{
                background-color: #175A8A;
            }}
            
            /* 信息卡片 */
            #infoCard {{
                background-color: {colors['panel']};
                border: 1px solid {colors['separator']};
                border-radius: 15px;
            }}
            
            #infoText {{
                color: {colors['text']};
                font-size: 14px;
                font-weight: 500;
                font-family: "Microsoft YaHei";
                line-height: 1.6;
            }}
            
            #separator {{
                background-color: {colors['separator']};
            }}
            
            /* 版本信息 */
            #version {{
                color: {colors['text_secondary']};
                font-size: 11px;
                font-family: "Microsoft YaHei";
            }}
            
            /* 导航栏 */
            #navbar {{
                background-color: {colors['panel']};
                border-bottom: 1px solid {colors['separator']};
            }}
            
            #modeLabel {{
                color: {colors['text']};
                font-size: 16px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
            }}
            
            #navBtn {{
                background-color: {colors['hover']};
                color: {colors['text']};
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-family: "Microsoft YaHei";
                padding: 5px 15px;
            }}
            
            #navBtn:hover {{
                background-color: {colors['separator']};
            }}
            
            /* 面板 */
            #panel {{
                background-color: {colors['panel']};
                border-radius: 15px;
            }}
            
            #panelTitle {{
                color: {colors['text']};
                font-size: 18px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
            }}
            
            #sectionTitle {{
                color: {colors['text']};
                font-size: 14px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
            }}
            
            /* 按钮 */
            #primaryBtn {{
                background-color: #2FA572;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-family: "Microsoft YaHei";
                padding: 10px;
            }}
            
            #primaryBtn:hover {{
                background-color: #268F5F;
            }}
            
            #iconBtn {{
                background-color: {colors['hover']};
                color: {colors['text']};
                border: none;
                border-radius: 10px;
                font-size: 16px;
            }}
            
            #iconBtn:hover {{
                background-color: {colors['separator']};
            }}
            
            #actionBtn {{
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
            }}
            
            #actionBtn[action="scan"] {{
                background-color: #1F6AA5;
            }}
            
            #actionBtn[action="scan"]:hover {{
                background-color: #175A8A;
            }}
            
            #actionBtn[action="diff"] {{
                background-color: #CC7700;
            }}
            
            #actionBtn[action="diff"]:hover {{
                background-color: #B36600;
            }}
            
            #actionBtn[action="full"] {{
                background-color: #CC2F26;
            }}
            
            #actionBtn[action="full"]:hover {{
                background-color: #B32923;
            }}
            
            /* 大操作按钮 */
            #bigActionBtn {{
                background-color: #2FA572;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 18px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
            }}
            
            #bigActionBtn:hover {{
                background-color: #268F5F;
            }}
            
            /* 次要按钮 */
            #secondaryBtn {{
                background-color: #1F6AA5;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-family: "Microsoft YaHei";
                padding: 10px;
            }}
            
            #secondaryBtn:hover {{
                background-color: #175A8A;
            }}
            
            /* 路径显示框 */
            #pathDisplay {{
                background-color: {colors['input_bg']};
                color: {colors['text']};
                border: 1px solid {colors['input_border']};
                border-radius: 10px;
                font-family: "Microsoft YaHei";
                font-size: 11px;
                padding: 10px;
            }}
            
            /* 章节标签 */
            #sectionLabel {{
                color: {colors['text_secondary']};
                font-size: 13px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
            }}
            
            /* 主题按钮 */
            #themeBtn {{
                background-color: {colors['panel']};
                color: {colors['text']};
                border: 2px solid {colors['separator']};
                border-radius: 10px;
                font-size: 14px;
                font-family: "Microsoft YaHei";
                padding: 10px;
            }}
            
            #themeBtn:hover {{
                background-color: {colors['hover']};
                border-color: #2FA572;
            }}
            
            #themeBtn[selected="true"] {{
                background-color: #2FA572;
                color: white;
                border-color: #2FA572;
            }}
            
            /* 进度条 */
            QProgressBar {{
                background-color: {colors['input_bg']};
                border: none;
                border-radius: 10px;
                text-align: center;
                color: {colors['text']};
                font-family: "Microsoft YaHei";
                font-size: 12px;
                height: 25px;
            }}
            
            QProgressBar::chunk {{
                background-color: #2FA572;
                border-radius: 10px;
            }}
            
            /* 文件夹项 */
            #folderItem {{
                background-color: {colors['input_bg']};
                border: 1px solid {colors['input_border']};
                border-radius: 10px;
                padding: 10px;
            }}
            
            #folderName {{
                color: {colors['text']};
                font-size: 14px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
            }}
            
            #folderPath {{
                color: {colors['text_secondary']};
                font-size: 11px;
                font-family: "Microsoft YaHei";
            }}
            
            /* 路径省略显示 */
            #folderPathElided {{
                color: {colors['text_secondary']};
                font-size: 11px;
                font-family: "Consolas", "Microsoft YaHei";
            }}
            
            #deleteBtn {{
                background-color: transparent;
                color: #CC2F26;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }}
            
            #deleteBtn:hover {{
                background-color: #3A2A2A;
            }}
            
            /* 日志文本框 */
            #logText {{
                background-color: {colors['input_bg']};
                color: {colors['text']};
                border: 1px solid {colors['input_border']};
                border-radius: 10px;
                font-family: "Consolas", "Courier New";
                font-size: 11px;
                padding: 10px;
            }}
        """)

    # ========== 业务逻辑方法 ==========
    
    def _add_backup_folder(self):
        """添加备份文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择要备份的文件夹")
        if folder and folder not in self.selected_paths:
            self.selected_paths.append(folder)
            self._add_folder_item(folder)
            self._log_message(f"✓ 已添加文件夹: {folder}")
            self.db.set_backup_folders(self.selected_paths)
            
    def _add_folder_item(self, folder):
        """添加文件夹项到列表"""
        item = QFrame()
        item.setObjectName("folderItem")
        item.setFixedHeight(70)  # 固定高度，保持一致性
        
        layout = QHBoxLayout(item)
        layout.setContentsMargins(15, 10, 10, 10)
        
        # 信息容器
        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(5)
        
        # 文件夹名
        folder_name = os.path.basename(folder)
        name = QLabel(f"📁 {folder_name}")
        name.setObjectName("folderName")
        name.setToolTip(folder_name)  # 悬停显示完整名称
        
        # 设置文本省略
        from PyQt6.QtCore import Qt
        name.setTextFormat(Qt.TextFormat.PlainText)
        name.setWordWrap(False)
        name.setMaximumWidth(300)  # 限制最大宽度
        
        # 使用QFontMetrics实现省略号
        font_metrics = name.fontMetrics()
        elided_text = font_metrics.elidedText(
            f"📁 {folder_name}", 
            Qt.TextElideMode.ElideRight, 
            300
        )
        name.setText(elided_text)
        
        info_layout.addWidget(name)
        
        # 路径显示（省略中间部分）
        path = QLabel()
        path.setObjectName("folderPathElided")
        path.setToolTip(folder)  # 鼠标悬停显示完整路径
        
        # 智能省略路径
        elided_path = self._elide_path(folder, 35)  # 最多35个字符
        path.setText(elided_path)
        
        info_layout.addWidget(path)
        
        layout.addWidget(info, 1)
        
        # 删除按钮
        del_btn = QPushButton("✕")
        del_btn.setObjectName("deleteBtn")
        del_btn.setFixedSize(30, 30)
        del_btn.setToolTip("删除文件夹")
        del_btn.clicked.connect(lambda: self._remove_folder_item(folder, item))
        layout.addWidget(del_btn)
        
        # 插入到列表（在 stretch 之前）
        self.folder_list_layout.insertWidget(
            self.folder_list_layout.count() - 1, item
        )
    
    def _elide_path(self, path, max_length=35):
        """智能省略路径，保留开头和结尾"""
        if len(path) <= max_length:
            return path
        
        # 分离盘符和路径
        if ':' in path:
            drive, rest = path.split(':', 1)
            drive += ':'
        else:
            drive = ''
            rest = path
        
        # 分离文件名
        parts = rest.replace('\\', '/').split('/')
        filename = parts[-1] if parts else ''
        
        # 计算可用长度
        available = max_length - len(drive) - len(filename) - 5  # 5 for "/.../"
        
        if available > 0 and len(parts) > 2:
            # 保留第一层目录
            first_dir = parts[1] if len(parts) > 1 else ''
            if len(first_dir) > available:
                first_dir = first_dir[:available]
            return f"{drive}/{first_dir}/.../{filename}"
        else:
            # 路径太短，直接省略中间
            start_len = max_length // 2
            end_len = max_length - start_len - 3
            return f"{path[:start_len]}...{path[-end_len:]}"
        
    def _remove_folder_item(self, folder, item):
        """删除文件夹项"""
        if folder in self.selected_paths:
            self.selected_paths.remove(folder)
            item.deleteLater()
            self.db.set_backup_folders(self.selected_paths)
            self._log_message(f"✖️ 已删除文件夹: {folder}")
            
    def _load_backup_folders(self):
        """加载保存的文件夹"""
        saved_folders = self.db.get_backup_folders()
        for folder in saved_folders:
            if os.path.exists(folder) and folder not in self.selected_paths:
                self.selected_paths.append(folder)
                self._add_folder_item(folder)
                
    def _refresh_backup_folders(self):
        """刷新文件夹列表"""
        # 清空列表
        for i in range(self.folder_list_layout.count() - 1):  # 保留最后的 stretch
            item = self.folder_list_layout.itemAt(0)
            if item.widget():
                item.widget().deleteLater()
                self.folder_list_layout.removeItem(item)
        
        self.selected_paths.clear()
        self._load_backup_folders()
        self._log_message("🔄 已刷新文件夹列表")
        
    def _scan_changes(self):
        """扫描文件变更"""
        if not self.selected_paths:
            self._log_message("⚠️ 请先添加要备份的文件夹")
            return
            
        folder = self.selected_paths[0]
        self._log_message(f"\n🔍 开始扫描文件夹: {folder}")
        
        def scan_thread():
            def scan_callback(current, total, filename):
                self._log_message(f"扫描中: {current}/{total} - {filename}")
                
            files_info = FileScanner.scan_folder(folder, scan_callback)
            self._log_message(f"\n✓ 扫描完成，共找到 {len(files_info)} 个文件")
            
            self._log_message("🔍 正在比对文件差异...")
            
            def compare_callback(current, total, filename):
                self._log_message(f"比对中: {current}/{total} - {filename}")
                
            self.changed_files = FileScanner.compare_files(
                self.db, folder, files_info, compare_callback
            )
            self.scan_results = files_info
            
            self._log_message(f"\n✓ 比对完成，发现 {len(self.changed_files)} 个文件有变化")
            
        threading.Thread(target=scan_thread, daemon=True).start()
        
    def _create_backup(self, sync_type):
        """创建备份包"""
        if not self.selected_paths:
            self._log_message("⚠️ 请先添加要备份的文件夹")
            return
            
        folder = self.selected_paths[0]
        
        if sync_type == 'diff' and not self.changed_files:
            self._log_message("⚠️ 请先扫描变更，或选择全量同步")
            return
            
        type_name = "差异" if sync_type == 'diff' else "全量"
        self._log_message(f"\n📦 开始创建{type_name}备份包...")
        
        def backup_thread():
            files_to_backup = self.changed_files if sync_type == 'diff' else self.scan_results
            
            if not files_to_backup and sync_type == 'full':
                files_to_backup = FileScanner.scan_folder(folder)
                for file_info in files_to_backup:
                    md5_hash = FileScanner.calculate_md5(file_info['path'])
                    file_info['md5_hash'] = md5_hash
                    
            if not files_to_backup:
                self._log_message("⚠️ 没有需要备份的文件")
                return
                
            archive_path = self.sync_core.create_backup_package(
                folder, files_to_backup, sync_type
            )
            
            if archive_path:
                self._log_message(f"\n✓ 备份包创建成功！")
                self._log_message(f"  路径: {archive_path}")
                self._log_message(f"  文件数: {len(files_to_backup)}")
            else:
                self._log_message("✗ 备份包创建失败")
                
        threading.Thread(target=backup_thread, daemon=True).start()
        
    def _log_message(self, message):
        """添加日志消息（线程安全）"""
        # 发出信号，由主线程处理
        self.backup_log_signal.emit(message)
    
    def _append_backup_log(self, message):
        """在主线程中添加备份日志"""
        if hasattr(self, 'backup_log'):
            self.backup_log.append(message)
            
    def _select_sync_target(self):
        """选择同步目标文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择同步目标文件夹")
        if folder:
            self.sync_target_folder = folder
            self.target_display.setText(folder)
            self.db.set_last_sync_target(folder)
            self._log_sync_message(f"✓ 已选择目标文件夹: {folder}")
            
    def _select_archive(self):
        """选择压缩包"""
        archive, _ = QFileDialog.getOpenFileName(
            self, 
            "选择压缩包",
            "",
            "压缩包 (*.zip);;所有文件 (*.*)"
        )
        if archive:
            self.selected_archive = archive
            self.archive_display.setText(archive)
            self._log_sync_message(f"✓ 已选择压缩包: {os.path.basename(archive)}")
            
    def _perform_sync(self):
        """执行同步"""
        if not hasattr(self, 'sync_target_folder') or not self.sync_target_folder:
            self._log_sync_message("⚠️ 请先选择目标文件夹")
            return
            
        if not hasattr(self, 'selected_archive') or not self.selected_archive:
            self._log_sync_message("⚠️ 请先选择压缩包")
            return
            
        self._log_sync_message(f"\n🔄 开始同步到: {self.sync_target_folder}")
        
        def sync_thread():
            def sync_callback(current, total, filename, status):
                icon = "✓" if status == "成功" else "⚠️"
                self._log_sync_message(
                    f"{icon} 同步中: {current}/{total} - {filename} [{status}]"
                )
                
            result = self.sync_core.sync_to_folder(
                self.selected_archive,
                self.sync_target_folder,
                sync_callback
            )
            
            self._log_sync_message(f"\n✓ 同步完成！")
            self._log_sync_message(f"  成功: {len(result['success'])} 个文件")
            self._log_sync_message(f"  冲突: {len(result['conflicts'])} 个文件")
            
            if result['conflicts']:
                self._log_sync_message("\n⚠️ 冲突文件已移至差异文件夹:")
                for conflict in result['conflicts'][:5]:
                    self._log_sync_message(f"  • {conflict['file']}")
                if len(result['conflicts']) > 5:
                    self._log_sync_message(f"  • ... 还有 {len(result['conflicts']) - 5} 个")
                    
        threading.Thread(target=sync_thread, daemon=True).start()
        
    def _log_sync_message(self, message):
        """添加同步日志消息（线程安全）"""
        # 发出信号，由主线程处理
        self.sync_log_signal.emit(message)
    
    def _append_sync_log(self, message):
        """在主线程中添加同步日志"""
        if hasattr(self, 'sync_log'):
            self.sync_log.append(message)
    
    def _show_settings(self):
        """显示设置页面"""
        # 清空内容
        self._clear_content()
        
        # 主容器
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel("设置")
        title.setObjectName("mainTitle")
        layout.addWidget(title)
        
        # 设置面板
        settings_panel = QFrame()
        settings_panel.setObjectName("panel")
        panel_layout = QVBoxLayout(settings_panel)
        panel_layout.setContentsMargins(30, 30, 30, 30)
        panel_layout.setSpacing(25)
        
        # 主题设置
        theme_section = QWidget()
        theme_layout = QVBoxLayout(theme_section)
        theme_layout.setSpacing(15)
        
        theme_label = QLabel("🎨 主题设置")
        theme_label.setObjectName("sectionTitle")
        theme_layout.addWidget(theme_label)
        
        # 主题按钮
        theme_btn_layout = QHBoxLayout()
        theme_btn_layout.setSpacing(15)
        
        dark_btn = QPushButton("🌙 暗色模式")
        dark_btn.setObjectName("themeBtn")
        dark_btn.setProperty("selected", self.current_theme == 'dark')
        dark_btn.setFixedHeight(50)
        dark_btn.clicked.connect(lambda: self._switch_theme('dark'))
        theme_btn_layout.addWidget(dark_btn)
        
        light_btn = QPushButton("☀️ 亮色模式")
        light_btn.setObjectName("themeBtn")
        light_btn.setProperty("selected", self.current_theme == 'light')
        light_btn.setFixedHeight(50)
        light_btn.clicked.connect(lambda: self._switch_theme('light'))
        theme_btn_layout.addWidget(light_btn)
        
        theme_layout.addLayout(theme_btn_layout)
        panel_layout.addWidget(theme_section)
        
        # 分隔线
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setObjectName("separator")
        panel_layout.addWidget(separator1)
        
        # 关于信息
        about_section = QWidget()
        about_layout = QVBoxLayout(about_section)
        about_layout.setSpacing(10)
        
        about_label = QLabel("ℹ️ 关于")
        about_label.setObjectName("sectionTitle")
        about_layout.addWidget(about_label)
        
        info_text = QLabel(
            "文件同步工具 v2.0\n"
            "PyQt6 Edition\n\n"
            "功能：智能备份、MD5校验、冲突处理\n"
            "框架：PyQt6 + Python 3.9+\n\n"
            "作者：Fenwick\n"
            "链接：https://github.com/JeromeFenwick/tools_sync\n\n"
            "版权所有 © 2026 Fenwick. 版权所有。"
        )
        info_text.setObjectName("infoText")
        info_text.setWordWrap(True)
        about_layout.addWidget(info_text)
        
        panel_layout.addWidget(about_section)
        panel_layout.addStretch()
        
        layout.addWidget(settings_panel)
        
        # 返回按钮
        back_btn = QPushButton("← 返回主页")
        back_btn.setObjectName("primaryBtn")
        back_btn.setFixedHeight(50)
        back_btn.clicked.connect(self._create_mode_selection)
        layout.addWidget(back_btn)
        
        self.content_layout.addWidget(container)
    
    def _switch_theme(self, theme):
        """切换主题"""
        if self.current_theme == theme:
            return
            
        self.current_theme = theme
        
        # 创建淡入淡出动画
        self.setWindowOpacity(0.0)
        QTimer.singleShot(100, lambda: self._apply_theme_and_fade_in(theme))
    
    def _apply_theme_and_fade_in(self, theme):
        """应用主题并淡入"""
        # 设置窗口背景色
        if theme == 'light':
            self.set_background_color('#F5F5F5')
        else:
            self.set_background_color('#1A1A1A')
        
        # 重新应用样式表
        self._apply_stylesheet()
        
        # 淡入动画
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.start()
        
        # 重新显示设置页面
        QTimer.singleShot(100, self._show_settings)


def main():
    app = QApplication(sys.argv)
    
    # 设置应用字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = ModernSyncGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
