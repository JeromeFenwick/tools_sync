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
    QGridLayout, QSizePolicy, QProgressBar, QGraphicsView, QGraphicsScene, QToolTip,
    QGraphicsBlurEffect
)
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer, QParallelAnimationGroup, QRectF
from PyQt6.QtGui import QPalette, QColor, QPainter, QPainterPath, QRegion, QFont, QIcon, QPen, QBrush
from database import Database
from file_scanner import FileScanner
from sync_core import SyncCore
from treemap_widget import TreemapWidget
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


class FloatingBubble(QWidget):
    """浮动气泡提示框"""
    
    def __init__(self, text, theme='dark', parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.theme = theme
        
        # 根据主题设置颜色
        if theme == 'light':
            # 明亮模式：中饱和度蓝绿渐变
            bg_start = "rgba(200, 235, 225, 0.95)"
            bg_end = "rgba(210, 235, 250, 0.95)"
            text_color = "#2B2B2B"
            border_color = "rgba(150, 200, 185, 0.7)"
        else:
            # 暗黑模式：中饱和度深色渐变
            bg_start = "rgba(28, 52, 58, 0.95)"
            bg_end = "rgba(20, 45, 60, 0.95)"
            text_color = "#E8E8E8"
            border_color = "rgba(80, 150, 125, 0.7)"
        
        # 设置内容
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setOpenExternalLinks(True)  # 启用超链接功能
        self.label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {bg_start},
                    stop:1 {bg_end}
                );
                color: {text_color};
                padding: 25px;
                border-radius: 15px;
                border: 2px solid {border_color};
                font-size: 13px;
                font-family: "Microsoft YaHei";
                line-height: 1.8;
            }}
        """)
        layout.addWidget(self.label)
        
        # 设置最大宽度
        self.setMaximumWidth(450)
        
        # 添加渐隐动画
        self.opacity_effect = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_effect.setDuration(200)
        self.opacity_effect.setStartValue(0.0)
        self.opacity_effect.setEndValue(1.0)
        self.opacity_effect.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def showEvent(self, event):
        """显示时播放渐显动画"""
        super().showEvent(event)
        self.opacity_effect.start()
    
    def paintEvent(self, event):
        """绘制阴影和背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制柔和阴影
        shadow_rect = self.rect().adjusted(10, 10, -10, -10)
        
        # 多层阴影效果
        for i in range(8, 0, -1):
            alpha = int(30 - i * 3)
            shadow_color = QColor(0, 0, 0, alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(shadow_color))
            painter.drawRoundedRect(
                shadow_rect.adjusted(-i, -i, i, i),
                15 + i, 15 + i
            )


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
        """绘制圆角背景和渐变效果"""
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
            
            # 根据主题创建渐变背景
            from PyQt6.QtGui import QLinearGradient
            gradient = QLinearGradient(rect.x(), rect.y(), rect.x(), rect.y() + rect.height())
            
            # 检查当前主题
            current_theme = getattr(self, 'current_theme', 'dark') if hasattr(self, 'current_theme') else 'dark'
            
            if current_theme == 'light':
                # 明亮模式：中饱和度蓝绿渐变
                gradient.setColorAt(0, QColor(200, 235, 225))  # 薄荷绿
                gradient.setColorAt(1, QColor(210, 235, 250))  # 天空蓝
            else:
                # 暗黑模式：中饱和度深色渐变
                gradient.setColorAt(0, QColor(28, 52, 58))    # 深青灰
                gradient.setColorAt(1, QColor(20, 45, 60))    # 深蓝灰
            
            painter.fillPath(path, gradient)
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
        
        # 设置窗口图标
        self._set_window_icon()
        
        # 启用拖拽功能
        self.setAcceptDrops(True)
        
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 确保所有线程都已结束
            event.accept()
        except Exception as e:
            print(f"关闭错误: {e}")
            event.accept()
    
    def _set_window_icon(self):
        """设置窗口图标"""
        try:
            icon_path = os.path.join(get_app_dir(), 'icon.ico')
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            else:
                print(f"图标文件不存在: {icon_path}")
        except Exception as e:
            print(f"设置窗口图标失败: {e}")
    
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
    
    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """放下事件 - 添加拖拽的文件夹"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                folder_path = url.toLocalFile()
                if os.path.isdir(folder_path):
                    # 在备份模式下添加到备份文件夹列表
                    if self.current_mode == 'backup':
                        if folder_path not in self.selected_paths:
                            self.selected_paths.append(folder_path)
                            if hasattr(self, 'folder_list_layout'):
                                self._add_folder_item(folder_path)
                            self._log_message(f"✓ 拖拽添加文件夹: {folder_path}")
                            self.db.set_backup_folders(self.selected_paths)
                    # 在同步模式下也可以添加
                    elif self.current_mode == 'sync':
                        if folder_path not in self.selected_paths:
                            self.selected_paths.append(folder_path)
                            if hasattr(self, 'folder_list_layout'):
                                self._add_folder_item(folder_path)
                            self._log_message(f"✓ 拖拽添加文件夹: {folder_path}")
                            self.db.set_sync_folders(self.selected_paths)
            event.acceptProposedAction()
            
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
        self._add_button_animation(backup_btn)  # 添加动画
        btn_layout.addWidget(backup_btn)
        
        # 同步模式按钮
        sync_btn = QPushButton("🔄 同步模式")
        sync_btn.setObjectName("modeBtn")
        sync_btn.setProperty("mode", "sync")
        sync_btn.setFixedSize(220, 100)
        sync_btn.clicked.connect(lambda: self._switch_mode('sync'))
        self._add_button_animation(sync_btn)  # 添加动画
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
        coming_info = QLabel(
            "🚀 更多功能\n"
            "拖拽添加 · 动画效果 · 数据统计"
        )
        coming_info.setObjectName("infoText")
        info_layout.addWidget(coming_info)
        
        layout.addWidget(info_frame)
        
        layout.addStretch()
        
        # 版本信息
        version = QLabel("v2.2 Enhanced Edition\n\nCopyright © 2026 Fenwick All Rights Reserved")
        version.setObjectName("version")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        
        self.content_layout.addWidget(container)
        
    def _switch_mode(self, mode):
        """切换工作模式（带动画）"""
        self.current_mode = mode
        
        # 添加渐隐动画
        self._fade_out_content()
        
        # 延迟切换界面
        QTimer.singleShot(200, lambda: self._switch_mode_delayed(mode))
    
    def _switch_mode_delayed(self, mode):
        """延迟切换模式（动画后）"""
        if mode == 'backup':
            self._create_backup_interface()
        else:
            self._create_sync_interface()
        
        # 添加渐显动画
        self._fade_in_content()
    
    def _fade_out_content(self):
        """内容区域渐隐动画"""
        if hasattr(self, 'content_widget') and self.content_widget:
            animation = QPropertyAnimation(self.content_widget, b"windowOpacity")
            animation.setDuration(150)
            animation.setStartValue(1.0)
            animation.setEndValue(0.0)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.start()
            # 保存引用防止被垃圾回收
            self._fade_animation = animation
    
    def _fade_in_content(self):
        """内容区域渐显动画"""
        if hasattr(self, 'content_widget') and self.content_widget:
            self.content_widget.setWindowOpacity(0.0)
            animation = QPropertyAnimation(self.content_widget, b"windowOpacity")
            animation.setDuration(200)
            animation.setStartValue(0.0)
            animation.setEndValue(1.0)
            animation.setEasingCurve(QEasingCurve.Type.InCubic)
            animation.start()
            # 保存引用防止被垃圾回收
            self._fade_animation = animation
    
    def _add_button_animation(self, button):
        """为按钮添加点击动画效果"""
        original_press = button.mousePressEvent
        original_release = button.mouseReleaseEvent
        
        def animated_press(event):
            # 按下时缩小
            animation = QPropertyAnimation(button, b"geometry")
            animation.setDuration(100)
            start_geo = button.geometry()
            end_geo = start_geo.adjusted(2, 2, -2, -2)
            animation.setStartValue(start_geo)
            animation.setEndValue(end_geo)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.start()
            button._press_animation = animation
            original_press(event)
        
        def animated_release(event):
            # 释放时恢复
            animation = QPropertyAnimation(button, b"geometry")
            animation.setDuration(100)
            start_geo = button.geometry()
            end_geo = start_geo.adjusted(-2, -2, 2, 2)
            animation.setStartValue(start_geo)
            animation.setEndValue(end_geo)
            animation.setEasingCurve(QEasingCurve.Type.InCubic)
            animation.start()
            button._release_animation = animation
            original_release(event)
        
        button.mousePressEvent = animated_press
        button.mouseReleaseEvent = animated_release
            
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
        
        # 日志标签和导出按钮
        log_header = QWidget()
        log_header_layout = QHBoxLayout(log_header)
        log_header_layout.setContentsMargins(0, 0, 0, 0)
        log_header_layout.setSpacing(10)
        
        log_label = QLabel("📋 操作日志")
        log_label.setObjectName("sectionTitle")
        log_header_layout.addWidget(log_label)
        
        log_header_layout.addStretch()
        
        # 导出按钮
        export_btn = QPushButton("💾 导出")
        export_btn.setObjectName("iconBtn")
        export_btn.setFixedSize(80, 30)
        export_btn.setToolTip("导出日志为TXT/CSV")
        export_btn.clicked.connect(lambda: self._export_log('backup'))
        log_header_layout.addWidget(export_btn)
        
        layout.addWidget(log_header)
        
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
        
        # 日志标签和导出按钮
        log_header = QWidget()
        log_header_layout = QHBoxLayout(log_header)
        log_header_layout.setContentsMargins(0, 0, 0, 0)
        log_header_layout.setSpacing(10)
        
        log_label = QLabel("📋 操作日志")
        log_label.setObjectName("sectionTitle")
        log_header_layout.addWidget(log_label)
        
        log_header_layout.addStretch()
        
        # 导出按钮
        export_btn = QPushButton("💾 导出")
        export_btn.setObjectName("iconBtn")
        export_btn.setFixedSize(80, 30)
        export_btn.setToolTip("导出日志为TXT/CSV")
        export_btn.clicked.connect(lambda: self._export_log('sync'))
        log_header_layout.addWidget(export_btn)
        
        layout.addWidget(log_header)
        
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
                'panel': 'rgba(255, 255, 255, 0.5)',  # 50%透明度，透出渐变背景
                'titlebar': '#E8E8E8',
                'text': '#1A1A1A',
                'text_secondary': '#505050',
                'separator': '#D0D0D0',
                'input_bg': '#FAFAFA',
                'input_border': '#D0D0D0',
                'hover': 'rgba(224, 224, 224, 0.6)'  # 60%透明度
            }
        else:  # dark
            colors = {
                'bg': '#1A1A1A',
                'panel': 'rgba(43, 43, 43, 0.3)',  # 50%透明度，透出渐变背景
                'titlebar': '#2B2B2B',
                'text': '#E0E0E0',
                'text_secondary': '#A0A0A0',
                'separator': '#404040',
                'input_bg': '#1F1F1F',
                'input_border': '#404040',
                'hover': 'rgba(58, 58, 58, 0.6)'  # 60%透明度
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
            
            /* 页面标题（设置页等）*/
            #pageTitle {{
                color: {colors['text']};
                font-size: 24px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
                padding: 0px;  /* 移除内边距，避免影响布局 */
                margin: 0px;  /* 移除外边距 */
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
                background-color: rgba(47, 165, 114, 0.85);  /* 85%不透明度 */
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-family: "Microsoft YaHei";
                padding: 10px;
            }}
            
            #primaryBtn:hover {{
                background-color: rgba(38, 143, 95, 0.9);  /* 悬停时更不透明 */
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
                background-color: rgba(31, 106, 165, 0.85);
            }}
            
            #actionBtn[action="scan"]:hover {{
                background-color: rgba(23, 90, 138, 0.9);
            }}
            
            #actionBtn[action="diff"] {{
                background-color: rgba(204, 119, 0, 0.85);
            }}
            
            #actionBtn[action="diff"]:hover {{
                background-color: rgba(179, 102, 0, 0.9);
            }}
            
            #actionBtn[action="full"] {{
                background-color: rgba(204, 47, 38, 0.85);
            }}
            
            #actionBtn[action="full"]:hover {{
                background-color: rgba(179, 41, 35, 0.9);
            }}
            
            /* 大操作按钮 */
            #bigActionBtn {{
                background-color: rgba(47, 165, 114, 0.85);
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 18px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
            }}
            
            #bigActionBtn:hover {{
                background-color: rgba(38, 143, 95, 0.9);
            }}
            
            /* 次要按钮 */
            #secondaryBtn {{
                background-color: rgba(31, 106, 165, 0.85);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-family: "Microsoft YaHei";
                padding: 10px;
            }}
            
            #secondaryBtn:hover {{
                background-color: rgba(23, 90, 138, 0.9);
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
                background-color: rgba(47, 165, 114, 0.85);
                color: white;
                border-color: rgba(47, 165, 114, 0.9);
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
                background-color: rgba(47, 165, 114, 0.85);
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
                
            result = self.sync_core.sync_to_folder_parallel(
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
    
    def _export_log(self, mode='backup'):
        """导出日志为TXT或CSV文件"""
        # 获取日志内容
        if mode == 'backup':
            if not hasattr(self, 'backup_log'):
                return
            log_content = self.backup_log.toPlainText()
            default_name = f"备份日志_{QTimer().remainingTime()}.txt"
        else:
            if not hasattr(self, 'sync_log'):
                return
            log_content = self.sync_log.toPlainText()
            default_name = f"同步日志_{QTimer().remainingTime()}.txt"
        
        if not log_content.strip():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "提示", "日志为空，无法导出")
            return
        
        # 选择保存文件
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{mode}_log_{timestamp}.txt"
        
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出日志",
            default_name,
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # 根据文件类型导出
            if file_path.endswith('.csv'):
                # CSV格式：将日志按行分割
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['时间戳', '日志内容'])
                    for line in log_content.split('\n'):
                        if line.strip():
                            writer.writerow([timestamp, line.strip()])
            else:
                # TXT格式：直接保存
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"====== {mode.upper()} 日志 ======\n")
                    f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(log_content)
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "成功", f"日志已导出到:\n{file_path}")
            
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"导出日志失败:\n{str(e)}")
    
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
        title.setObjectName("pageTitle")
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
        
        dark_btn = QPushButton("🌙 暗黑模式")
        dark_btn.setObjectName("themeBtn")
        dark_btn.setProperty("selected", self.current_theme == 'dark')
        dark_btn.setFixedHeight(50)
        dark_btn.clicked.connect(lambda: self._switch_theme('dark'))
        theme_btn_layout.addWidget(dark_btn)
        
        light_btn = QPushButton("☀️ 明亮模式")
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
        
        # 统计图表区域
        stats_section = QWidget()
        stats_layout = QVBoxLayout(stats_section)
        stats_layout.setSpacing(15)
        
        stats_label = QLabel("📊 数据统计")
        stats_label.setObjectName("sectionTitle")
        stats_layout.addWidget(stats_label)
        
        # 统计按钮布局
        stats_btn_layout = QHBoxLayout()
        stats_btn_layout.setSpacing(15)
        
        # 备份趋势图
        trend_btn = QPushButton("📈 备份趋势")
        trend_btn.setObjectName("themeBtn")
        trend_btn.setFixedHeight(50)
        trend_btn.clicked.connect(self._show_backup_trend)
        stats_btn_layout.addWidget(trend_btn)
        
        # 空间分析
        storage_btn = QPushButton("💾 空间分析")
        storage_btn.setObjectName("themeBtn")
        storage_btn.setFixedHeight(50)
        storage_btn.clicked.connect(self._show_storage_analysis)
        stats_btn_layout.addWidget(storage_btn)
        
        stats_layout.addLayout(stats_btn_layout)
        panel_layout.addWidget(stats_section)
        
        # 分隔线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setObjectName("separator")
        panel_layout.addWidget(separator2)
        
        # 关于信息 - 浮动气泡式
        about_section = QWidget()
        about_layout = QVBoxLayout(about_section)
        about_layout.setSpacing(10)
        
        about_label = QLabel("ℹ️ 关于")
        about_label.setObjectName("sectionTitle")
        about_layout.addWidget(about_label)
        
        # 简要信息（默认显示）
        self.about_brief = QLabel(
            "文件同步工具 v2.2 Enhanced | PyQt6 Edition\n"
            "👆 悬停查看详细信息"
        )
        self.about_brief.setObjectName("infoText")
        self.about_brief.setWordWrap(True)
        self.about_brief.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.about_brief.setStyleSheet("""
            padding: 15px;
            background-color: rgba(47, 165, 114, 0.1);
            border: 2px solid rgba(80, 150, 125, 0.6);
            border-radius: 10px;
        """)
        about_layout.addWidget(self.about_brief)
        
        # 绑定鼠标事件
        self.about_brief.enterEvent = lambda e: self._start_bubble_timer()
        self.about_brief.leaveEvent = lambda e: self._cancel_bubble_timer()
        self.about_brief.mousePressEvent = lambda e: self._show_about_bubble_immediately()
        
        # 气泡提示框和蒙版
        self.about_bubble = None
        self.bubble_overlay = None
        self._bubble_hide_timer = None
        self._bubble_show_timer = None  # 延迟显示定时器
        
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
    
    def _start_bubble_timer(self):
        """开始气泡显示延迟定时器（3秒）"""
        # 取消任何现有的定时器
        self._cancel_bubble_timer()
        
        # 创建1.5秒延迟定时器
        self._bubble_show_timer = QTimer()
        self._bubble_show_timer.setSingleShot(True)
        self._bubble_show_timer.timeout.connect(self._show_about_bubble_delayed)
        self._bubble_show_timer.start(1500)  # 1.5秒
    
    def _cancel_bubble_timer(self):
        """取消气泡显示延迟定时器"""
        if self._bubble_show_timer:
            self._bubble_show_timer.stop()
            self._bubble_show_timer = None
        
        # 鼠标离开时，如果气泡已显示，延迟隐藏
        if self.about_bubble and self.about_bubble.isVisible():
            self._hide_about_bubble_delayed()
    
    def _show_about_bubble_immediately(self):
        """立即显示气泡（点击触发）"""
        self._cancel_bubble_timer()
        self._show_about_bubble_delayed()
    
    def _show_about_bubble_delayed(self):
        """延迟显示气泡（由定时器或点击触发）"""
        # 取消延迟隐藏
        if self._bubble_hide_timer:
            self._bubble_hide_timer.stop()
            self._bubble_hide_timer = None
        
        # 创建蒙版层（如果不存在）
        if not hasattr(self, 'bubble_overlay') or self.bubble_overlay is None:
            self.bubble_overlay = QWidget(self)
            self.bubble_overlay.setGeometry(0, 0, self.width(), self.height())
            self.bubble_overlay.setStyleSheet("""
                background-color: rgba(0, 0, 0, 0.5);
            """)
            self.bubble_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.bubble_overlay.lower()  # 确保在最底层
        
        # 显示蒙版
        self.bubble_overlay.show()
        self.bubble_overlay.raise_()
        
        # 根据主题设置颜色
        if self.current_theme == 'light':
            card_bg = "rgba(185, 225, 210, 0.55)"  # 提高饱和度
            title_color_1 = "#28A068"  # 更鲜艳的绿色
            title_color_2 = "#1A5F95"  # 更鲜艳的蓝色
            text_color = "#2B2B2B"
            subtitle_color = "#707070"
        else:
            card_bg = "rgba(30, 55, 60, 0.55)"  # 提高饱和度
            title_color_1 = "#55D095"  # 更鲜艳的绿色
            title_color_2 = "#45BBEF"  # 更鲜艳的蓝色
            text_color = "#E0E0E0"
            subtitle_color = "#B0B0B0"
        
        # 创建气泡内容
        bubble_text = (
            "<div style='text-align: center; margin-bottom: 15px;'>"
            f"<span style='font-size: 16px; font-weight: bold; color: {title_color_1};'>"
            "📦 文件同步工具 v2.2 Enhanced</span><br>"
            f"<span style='font-size: 12px; color: {subtitle_color};'>PyQt6 Edition</span>"
            "</div>"
            
            f"<div style='margin: 12px 0; padding: 10px; background: {card_bg}; border-radius: 8px; border-left: 3px solid {title_color_1};'>"
            f"<span style='color: {title_color_1}; font-weight: bold;'>✨ 核心功能</span><br>"
            f"<span style='font-size: 12px; color: {text_color};'>"
            "• 智能备份 &nbsp; • MD5校验 &nbsp; • 冲突处理<br>"
            "• 拖拽添加 &nbsp; • 动画效果 &nbsp; • 数据统计"
            "</span>"
            "</div>"
            
            f"<div style='margin: 12px 0; padding: 10px; background: {card_bg}; border-radius: 8px; border-left: 3px solid {title_color_2};'>"
            f"<span style='color: {title_color_2}; font-weight: bold;'>🚀 增强特性</span><br>"
            f"<span style='font-size: 12px; color: {text_color};'>"
            "• 日志导出(TXT/CSV)<br>"
            "• 多线程并发优化<br>"
            "• 存储空间可视化"
            "</span>"
            "</div>"
            
            f"<div style='text-align: center; margin-top: 15px; padding-top: 10px; border-top: 1px solid rgba(47, 165, 114, 0.4);'>"
            "<span style='font-size: 11px; color: #A0A0A0;'>"
            "👨‍💻 作者: Fenwick &nbsp;|&nbsp; "
            f"<a href='https://github.com/JeromeFenwick/tools_sync' style='color: {title_color_1}; text-decoration: none;'>🔗 GitHub</a><br>"
            "© 2026 Fenwick. All Rights Reserved."
            "</span>"
            "</div>"
        )
        
        # 如果气泡已存在，关闭它
        if self.about_bubble:
            self.about_bubble.close()
            self.about_bubble = None
        
        # 创建新气泡（传递主题）
        self.about_bubble = FloatingBubble(bubble_text, self.current_theme, self)
        
        # 计算气泡位置（在简要信息上方居中）
        if hasattr(self, 'about_brief'):
            brief_global_pos = self.about_brief.mapToGlobal(QPoint(0, 0))
            bubble_width = 420
            bubble_x = brief_global_pos.x() + (self.about_brief.width() - bubble_width) // 2
            bubble_y = brief_global_pos.y() - self.about_bubble.sizeHint().height() - 15
            
            self.about_bubble.move(bubble_x, bubble_y)
        
        # 显示气泡
        self.about_bubble.show()
        self.about_bubble.raise_()  # 确保在蒙版之上
        
        # 绑定气泡的鼠标事件
        self.about_bubble.enterEvent = lambda e: self._cancel_bubble_hide()
        self.about_bubble.leaveEvent = lambda e: self._hide_about_bubble_delayed()
    
    def _hide_about_bubble_delayed(self):
        """延迟隐藏气泡"""
        if self._bubble_hide_timer:
            self._bubble_hide_timer.stop()
        
        self._bubble_hide_timer = QTimer()
        self._bubble_hide_timer.setSingleShot(True)
        self._bubble_hide_timer.timeout.connect(self._hide_about_bubble)
        self._bubble_hide_timer.start(300)
    
    def _cancel_bubble_hide(self):
        """取消延迟隐藏"""
        if self._bubble_hide_timer:
            self._bubble_hide_timer.stop()
            self._bubble_hide_timer = None
    
    def _hide_about_bubble(self):
        """隐藏气泡"""
        if self.about_bubble:
            self.about_bubble.close()
            self.about_bubble = None
        
        # 隐藏蒙版
        if hasattr(self, 'bubble_overlay') and self.bubble_overlay:
            self.bubble_overlay.hide()
    
    def _show_backup_trend(self):
        """显示备份趋势图表"""
        self._clear_content()
        
        # 主容器
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        # 标题（固定在顶部，不参与居中）
        title = QLabel("📈 备份趋势分析")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)
        
        # Tab页签和热力图的容器（用于垂直居中）
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        
        # Tab页签容器
        tab_container = QWidget()
        tab_layout = QHBoxLayout(tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)
        
        # 创建三个Tab选项卡
        self.dimension_tabs = {}
        tab_items = [
            ("📅 备份日期", "backup_date"),
            ("📝 文件修改日期", "file_modify_date"),
            ("✨ 文件创建日期", "file_create_date")
        ]
        
        for i, (label, dimension) in enumerate(tab_items):
            tab_btn = QPushButton(label)
            tab_btn.setFixedHeight(40)
            tab_btn.setMinimumWidth(140)
            tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # 设置Tab选项卡样式
            if self.current_theme == 'light':
                tab_btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        border-bottom: 3px solid transparent;
                        padding: 8px 20px;
                        font-size: 13px;
                        font-weight: bold;
                        color: #888888;
                        border-radius: 0px;
                    }
                    QPushButton:hover {
                        color: #3B8ED0;
                        background-color: rgba(59, 142, 208, 0.05);
                        border-top-left-radius: 8px;
                        border-top-right-radius: 8px;
                        border-bottom-left-radius: 0px;
                        border-bottom-right-radius: 0px;
                    }
                    QPushButton[selected="true"] {
                        color: #3B8ED0;
                        border-bottom: 3px solid #3B8ED0;
                        background-color: rgba(59, 142, 208, 0.1);
                        border-top-left-radius: 8px;
                        border-top-right-radius: 8px;
                        border-bottom-left-radius: 0px;
                        border-bottom-right-radius: 0px;
                    }
                """)
            else:
                tab_btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        border-bottom: 3px solid transparent;
                        padding: 8px 20px;
                        font-size: 13px;
                        font-weight: bold;
                        color: #888888;
                        border-radius: 0px;
                    }
                    QPushButton:hover {
                        color: #3B8ED0;
                        background-color: rgba(59, 142, 208, 0.1);
                        border-top-left-radius: 8px;
                        border-top-right-radius: 8px;
                        border-bottom-left-radius: 0px;
                        border-bottom-right-radius: 0px;
                    }
                    QPushButton[selected="true"] {
                        color: #3B8ED0;
                        border-bottom: 3px solid #3B8ED0;
                        background-color: rgba(59, 142, 208, 0.15);
                        border-top-left-radius: 8px;
                        border-top-right-radius: 8px;
                        border-bottom-left-radius: 0px;
                        border-bottom-right-radius: 0px;
                    }
                """)
            
            # 绑定点击事件
            tab_btn.clicked.connect(lambda checked, d=dimension: self._on_tab_clicked(d))
            tab_layout.addWidget(tab_btn)
            self.dimension_tabs[dimension] = tab_btn
        
        # 添加弹性空间
        tab_layout.addStretch()
        
        # 添加底部分隔线
        separator = QFrame()
        separator.setFixedHeight(1)
        if self.current_theme == 'light':
            separator.setStyleSheet("background-color: #E0E0E0;")
        else:
            separator.setStyleSheet("background-color: #404040;")
        
        # 将Tab和分隔线添加到垂直布局
        tab_wrapper = QWidget()
        tab_wrapper_layout = QVBoxLayout(tab_wrapper)
        tab_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        tab_wrapper_layout.setSpacing(0)
        tab_wrapper_layout.addWidget(tab_container)
        tab_wrapper_layout.addWidget(separator)
        
        center_layout.addWidget(tab_wrapper)
        
        # 创建图表容器（用于动态更新）
        self.chart_container = QWidget()
        self.chart_container_layout = QVBoxLayout(self.chart_container)
        self.chart_container_layout.setContentsMargins(0, 0, 0, 0)  # 取消所有边距
        self.chart_container_layout.setSpacing(0)
        
        # 将图表添加到center_container
        center_layout.addWidget(self.chart_container)
        
        # 添加上方弹性空间，使Tab+热力图垂直居中
        layout.addStretch()
        
        # 添加center_container（包含Tab、热力图）
        layout.addWidget(center_container)
        
        # 加载默认统计数据，并设置默认Tab选中状态
        self._set_active_tab('backup_date')
        self._load_chart_data('backup_date')
        
        # 添加下方弹性空间，使Tab+热力图垂直居中
        layout.addStretch()
        
        # 返回按钮（固定在底部）
        back_btn = QPushButton("← 返回设置")
        back_btn.setObjectName("primaryBtn")
        back_btn.setFixedHeight(50)
        back_btn.clicked.connect(self._show_settings)
        layout.addWidget(back_btn)
        
        self.content_layout.addWidget(container)
    
    def _on_tab_clicked(self, dimension):
        """Tab页签点击回调"""
        self._set_active_tab(dimension)
        self._load_chart_data(dimension)
    
    def _set_active_tab(self, active_dimension):
        """设置Tab选中状态"""
        for dimension, tab_btn in self.dimension_tabs.items():
            if dimension == active_dimension:
                tab_btn.setProperty("selected", "true")
            else:
                tab_btn.setProperty("selected", "false")
            # 刷新样式
            tab_btn.style().unpolish(tab_btn)
            tab_btn.style().polish(tab_btn)
            tab_btn.update()
    
    def _on_dimension_changed(self, index):
        """统计维度变更回调（保留兼容）"""
        dimension = self.dimension_combo.currentData()
        self._load_chart_data(dimension)
    
    def _load_chart_data(self, dimension='backup_date'):
        """加载图表数据"""
        # 清空当前图表
        for i in reversed(range(self.chart_container_layout.count())):
            widget = self.chart_container_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        
        # 获取统计数据（近一年）
        stats = self.db.get_backup_statistics(365, dimension)
        
        # 创建图表面板
        chart_panel = QFrame()
        chart_panel.setObjectName("panel")
        chart_layout = QVBoxLayout(chart_panel)
        chart_layout.setContentsMargins(30, 15, 30, 30)  # 减小上边距
        
        if stats['dates']:
            # 统计信息（左对齐）
            total_backups = sum(stats['backup_counts'])
            total_files = sum(stats['file_counts'])
            
            # 根据维度调整显示文本
            if dimension == 'backup_date':
                info_text = QLabel(
                    f"最近一年统计\n"
                    f"备份总次数: {total_backups} 次\n"
                    f"文件总数: {total_files} 个\n"
                )
            elif dimension == 'file_modify_date':
                info_text = QLabel(
                    f"最近一年统计\n"
                    f"修改文件总数: {total_files} 个\n"
                    f"最近有修改的日子: {len([c for c in stats['file_counts'] if c > 0])} 天\n"
                )
            else:  # file_create_date
                info_text = QLabel(
                    f"最近一年统计\n"
                    f"创建文件总数: {total_files} 个\n"
                    f"最近有创建的日子: {len([c for c in stats['file_counts'] if c > 0])} 天\n"
                )
            
            info_text.setObjectName("sectionTitle")
            info_text.setAlignment(Qt.AlignmentFlag.AlignLeft)  # 文本居左
            chart_layout.addWidget(info_text)
            
            # GitHub风格热力图
            chart_widget = self._create_bar_chart(stats)
            chart_layout.addWidget(chart_widget)
            
            # 添加图例说明（居中）
            legend_container = QWidget()
            legend_layout = QHBoxLayout(legend_container)
            legend_layout.setContentsMargins(0, 10, 0, 0)
            legend_layout.setSpacing(10)
            
            # 添加左侧弹性空间使图例居中
            legend_layout.addStretch()
            
            legend_label = QLabel("活跃度:")
            legend_label.setObjectName("sectionTitle")
            # 根据主题设置字体样式和颜色
            if self.current_theme == 'light':
                legend_label.setStyleSheet("font-size: 11px; color: #586069; font-weight: bold;")
            else:
                legend_label.setStyleSheet("font-size: 11px; color: #C9D1D9; font-weight: bold;")
            legend_layout.addWidget(legend_label)
            
            # 根据主题选择颜色
            if self.current_theme == 'light':
                legend_colors = ["#EBEDF0", "#9BE9A8", "#40C463", "#30A14E", "#216E39"]
                text_color = "#586069"
            else:
                legend_colors = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]
                text_color = "#C9D1D9"  # 提升暗黑模式下的文字亮度
            
            # 绘制图例色块
            for i, color in enumerate(legend_colors):
                color_box = QLabel()
                color_box.setFixedSize(12, 12)
                color_box.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
                legend_layout.addWidget(color_box)
                if i == 0:
                    low_label = QLabel("低")
                    low_label.setStyleSheet(f"font-size: 11px; color: {text_color}; font-weight: normal;")
                    legend_layout.addWidget(low_label)
                elif i == len(legend_colors) - 1:
                    high_label = QLabel("高")
                    high_label.setStyleSheet(f"font-size: 11px; color: {text_color}; font-weight: normal;")
                    legend_layout.addWidget(high_label)
            
            # 添加右侧弹性空间使图例居中
            legend_layout.addStretch()
            chart_layout.addWidget(legend_container)
        else:
            no_data = QLabel("⚠️ 暂无数据")
            no_data.setObjectName("sectionTitle")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chart_layout.addWidget(no_data)
        
        self.chart_container_layout.addWidget(chart_panel)
    
    def _create_bar_chart(self, stats):
        """创建GitHub风格热力图"""
        chart_widget = QFrame()
        chart_widget.setObjectName("chartFrame")
        chart_widget.setMinimumHeight(180)
        
        # 自定义热力图绘图
        class HeatmapWidget(QWidget):
            def __init__(self, data, theme='dark', parent=None):
                super().__init__(parent)
                self.dates = data['dates']
                self.file_counts = data['file_counts']
                self.theme = theme
                self.setMinimumHeight(160)
                self.setMouseTracking(True)  # 启用鼠标跟踪
                
                # 计算热力图数据：按周组织
                self.weeks_data = self._organize_by_weeks()
                self.hover_cell = None  # 当前悬停的单元格
            
            def _organize_by_weeks(self):
                """将日期数据按周组织成7行（周日到周六）"""
                from datetime import datetime
                
                weeks = []
                current_week = [None] * 7  # 一周7天
                
                for i, date_str in enumerate(self.dates):
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    weekday = date_obj.weekday()  # 0=周一, 6=周日
                    # 转换为周日=0, 周一=1, ..., 周六=6
                    day_index = (weekday + 1) % 7
                    
                    # 如果是周日（新的一周开始）并且当前周不为空
                    if day_index == 0 and any(cell is not None for cell in current_week):
                        weeks.append(current_week)
                        current_week = [None] * 7
                    
                    current_week[day_index] = {
                        'date': date_str,
                        'count': self.file_counts[i],
                        'display_date': date_obj.strftime('%m月%d日')
                    }
                
                # 添加最后一周
                if any(cell is not None for cell in current_week):
                    weeks.append(current_week)
                
                return weeks
            
            def _get_color_for_count(self, count, max_count):
                """根据文件数量返回热力图颜色（GitHub风格）"""
                if count == 0:
                    # 无活动
                    if self.theme == 'light':
                        return QColor("#EBEDF0")
                    else:
                        return QColor("#161B22")
                
                # 计算强度等级（0-4）
                if max_count == 0:
                    level = 0
                else:
                    ratio = count / max_count
                    if ratio < 0.25:
                        level = 1
                    elif ratio < 0.5:
                        level = 2
                    elif ratio < 0.75:
                        level = 3
                    else:
                        level = 4
                
                # GitHub绿色配色方案
                if self.theme == 'light':
                    colors = [
                        "#EBEDF0",  # 0: 无
                        "#9BE9A8",  # 1: 低
                        "#40C463",  # 2: 中低
                        "#30A14E",  # 3: 中高
                        "#216E39"   # 4: 高
                    ]
                else:
                    colors = [
                        "#161B22",  # 0: 无
                        "#0E4429",  # 1: 低
                        "#006D32",  # 2: 中低
                        "#26A641",  # 3: 中高
                        "#39D353"   # 4: 高
                    ]
                
                return QColor(colors[level])
            
            def paintEvent(self, event):
                if not self.weeks_data:
                    return
                
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # 计算绘图区域
                width = self.width()
                height = self.height()
                
                # 单元格大小（根据周数动态调整）
                num_weeks = len(self.weeks_data)
                margin_left = 60
                margin_top = 20
                margin_right = 20
                
                # 计算可用宽度和最佳单元格大小
                available_width = width - margin_left - margin_right
                cell_spacing = 2
                # 根据周数计算单元格大小，最大6，最多12
                cell_size = max(6, min(12, (available_width - (num_weeks - 1) * cell_spacing) // num_weeks))
                
                # 根据主题设置颜色
                if self.theme == 'light':
                    text_color = QColor("#2B2B2B")
                    label_color = QColor("#586069")
                else:
                    text_color = QColor("#E0E0E0")
                    label_color = QColor("#8B949E")
                
                # 绘制星期标签（只在单元格足够大时显示）
                if cell_size >= 10:
                    painter.setPen(label_color)
                    painter.setFont(QFont("Microsoft YaHei", 8))
                    weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
                    for i, day in enumerate(weekdays):
                        if i % 2 == 1:  # 只显示奇数行标签，避免拥挤
                            y = margin_top + i * (cell_size + cell_spacing) + cell_size // 2
                            painter.drawText(5, y - 5, margin_left - 10, cell_size + 10,
                                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, day)
                
                # 计算最大值用于颜色映射
                max_count = max(self.file_counts) if self.file_counts else 1
                
                # 绘制热力图格子
                for week_idx, week in enumerate(self.weeks_data):
                    for day_idx, cell_data in enumerate(week):
                        if cell_data is None:
                            continue
                        
                        x = margin_left + week_idx * (cell_size + cell_spacing)
                        y = margin_top + day_idx * (cell_size + cell_spacing)
                        
                        # 获取颜色
                        color = self._get_color_for_count(cell_data['count'], max_count)
                        
                        # 绘制圆角矩形
                        painter.setBrush(color)
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawRoundedRect(x, y, cell_size, cell_size, 2, 2)
                        
                        # 如果鼠标悬停在此单元格上，绘制边框
                        if self.hover_cell and self.hover_cell == (week_idx, day_idx):
                            painter.setPen(QPen(text_color, 2))
                            painter.setBrush(Qt.BrushStyle.NoBrush)
                            painter.drawRoundedRect(x-1, y-1, cell_size+2, cell_size+2, 2, 2)
                
                # 绘制月份标签（仅在每个月的第一周显示）
                painter.setPen(label_color)
                painter.setFont(QFont("Microsoft YaHei", 8))
                drawn_months = set()
                last_month = None
                for week_idx, week in enumerate(self.weeks_data):
                    # 找到这一周的第一个有效日期
                    for cell_data in week:
                        if cell_data:
                            from datetime import datetime
                            date_obj = datetime.strptime(cell_data['date'], '%Y-%m-%d')
                            month = date_obj.strftime('%Y-%m')
                            month_label = date_obj.strftime('%m月')
                            
                            # 只在月份变化时显示
                            if month != last_month:
                                x = margin_left + week_idx * (cell_size + cell_spacing)
                                painter.drawText(x, 5, 50, 15, Qt.AlignmentFlag.AlignLeft, month_label)
                                last_month = month
                            break
            
            def mouseMoveEvent(self, event):
                """鼠标移动事件 - 检测悬停的单元格"""
                pos = event.pos()
                
                # 使用与paintEvent相同的计算逻辑
                width = self.width()
                num_weeks = len(self.weeks_data)
                margin_left = 60
                margin_top = 20
                margin_right = 20
                
                available_width = width - margin_left - margin_right
                cell_spacing = 2
                cell_size = max(6, min(12, (available_width - (num_weeks - 1) * cell_spacing) // num_weeks))
                
                # 查找鼠标所在的单元格
                hover_found = False
                for week_idx, week in enumerate(self.weeks_data):
                    for day_idx, cell_data in enumerate(week):
                        if cell_data is None:
                            continue
                        
                        x = margin_left + week_idx * (cell_size + cell_spacing)
                        y = margin_top + day_idx * (cell_size + cell_spacing)
                        
                        # 检查鼠标是否在单元格内
                        if (x <= pos.x() <= x + cell_size and 
                            y <= pos.y() <= y + cell_size):
                            if self.hover_cell != (week_idx, day_idx):
                                self.hover_cell = (week_idx, day_idx)
                                self.update()  # 触发重绘
                                
                                # 显示tooltip
                                tooltip_text = f"{cell_data['display_date']}\n文件数: {cell_data['count']}"
                                QToolTip.setFont(QFont("Microsoft YaHei", 10))
                                QToolTip.showText(event.globalPosition().toPoint(), tooltip_text, self)
                            hover_found = True
                            break
                    if hover_found:
                        break
                
                # 如果鼠标不在任何单元格上
                if not hover_found and self.hover_cell is not None:
                    self.hover_cell = None
                    self.update()
                    QToolTip.hideText()
            
            def leaveEvent(self, event):
                """鼠标离开控件"""
                if self.hover_cell is not None:
                    self.hover_cell = None
                    self.update()
                    QToolTip.hideText()
        
        chart = HeatmapWidget(stats, self.current_theme, chart_widget)
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.addWidget(chart)
        
        return chart_widget
    
    def _show_storage_analysis(self):
        """显示存储空间分析"""
        self._clear_content()
        
        # 主容器
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        # 标题和详细列表按钮容器（固定在顶部）
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title = QLabel("💾 存储空间分析")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)
        
        # 添加弹性空间
        header_layout.addStretch()
        
        # 详细列表按钮（右上角）
        self.storage_stats_data = None  # 存储数据供弹窗使用
        details_btn = QPushButton("📋 详细列表")
        details_btn.setObjectName("secondaryBtn")
        details_btn.setFixedHeight(40)
        details_btn.setFixedWidth(120)
        details_btn.clicked.connect(self._show_storage_details_dialog)
        header_layout.addWidget(details_btn)
        
        layout.addWidget(header_container)
        
        # 获取存储统计
        storage_stats = self.db.get_storage_statistics()
        
        # 创建图表面板
        chart_panel = QFrame()
        chart_panel.setObjectName("panel")
        chart_layout = QVBoxLayout(chart_panel)
        chart_layout.setContentsMargins(30, 30, 30, 30)
        chart_layout.setSpacing(20)
        
        if storage_stats:
            # 保存数据供弹窗使用
            self.storage_stats_data = storage_stats
            
            # 计算总大小
            total_size = sum(item['total_size'] for item in storage_stats)
            total_files = sum(item['file_count'] for item in storage_stats)
            
            # 显示总统计（左对齐）
            info_text = QLabel(
                f"存储总览\n"
                f"文件夹数: {len(storage_stats)} 个\n"
                f"文件总数: {total_files} 个\n"
                f"占用空间: {FileScanner.format_size(total_size)}"
            )
            info_text.setObjectName("sectionTitle")
            info_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
            chart_layout.addWidget(info_text)
            
            # 上方弹性空间，使树形图垂直居中
            chart_layout.addStretch()
            
            # 树形图（Treemap）
            treemap_chart = self._create_treemap_chart(storage_stats, total_size)
            chart_layout.addWidget(treemap_chart)
            
            # 下方弹性空间，使树形图垂直居中
            chart_layout.addStretch()
        else:
            # 无数据时居中显示
            chart_layout.addStretch()
            no_data = QLabel("⚠️ 暂无存储数据")
            no_data.setObjectName("sectionTitle")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chart_layout.addWidget(no_data)
            chart_layout.addStretch()
        
        layout.addWidget(chart_panel)
        
        # 返回按钮
        back_btn = QPushButton("← 返回设置")
        back_btn.setObjectName("primaryBtn")
        back_btn.setFixedHeight(50)
        back_btn.clicked.connect(self._show_settings)
        layout.addWidget(back_btn)
        
        self.content_layout.addWidget(container)
    
    def _show_storage_details_dialog(self):
        """显示存储详细列表气泡"""
        if not self.storage_stats_data:
            return
        
        from PyQt6.QtWidgets import QDialog
        from PyQt6.QtCore import Qt, QPoint
        
        # 创建无边框气泡对话框
        bubble = QDialog(self)
        bubble.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        bubble.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 根据主题选择颜色
        if self.current_theme == 'light':
            bg_color = "rgba(255, 255, 255, 1.0)"  # 完全不透明白色
            border_color = "rgba(0, 0, 0, 0.15)"
            title_color = "#2B2B2B"
            separator_color = "rgba(0, 0, 0, 0.1)"
            item_bg = "rgba(0, 0, 0, 0.03)"
            item_hover_bg = "rgba(0, 0, 0, 0.08)"
            name_color = "#2B2B2B"
            label_color = "#606060"
            value_color = "#404040"
            percentage_color = "#1F6AA5"
            scrollbar_bg = "rgba(0, 0, 0, 0.05)"
            scrollbar_handle = "rgba(0, 0, 0, 0.2)"
        else:
            bg_color = "rgba(43, 43, 43, 1.0)"  # 完全不透明深灰色
            border_color = "rgba(255, 255, 255, 0.15)"
            title_color = "#E0E0E0"
            separator_color = "rgba(255, 255, 255, 0.1)"
            item_bg = "rgba(255, 255, 255, 0.05)"
            item_hover_bg = "rgba(255, 255, 255, 0.1)"
            name_color = "#E0E0E0"
            label_color = "#A0A0A0"
            value_color = "#C0C0C0"
            percentage_color = "#3B8ED0"
            scrollbar_bg = "rgba(255, 255, 255, 0.05)"
            scrollbar_handle = "rgba(255, 255, 255, 0.2)"
        
        # 主容器
        main_container = QFrame(bubble)
        main_container.setObjectName("bubble")
        main_container.setStyleSheet(f"""
            QFrame#bubble {{
                background-color: {bg_color};
                border-radius: 12px;
                border: 1px solid {border_color};
            }}
        """)
        
        # 布局
        container_layout = QVBoxLayout(bubble)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(main_container)
        
        layout = QVBoxLayout(main_container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("📁 存储详情")
        title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {title_color};
            padding-bottom: 5px;
        """)
        layout.addWidget(title_label)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {separator_color}; max-height: 1px;")
        layout.addWidget(separator)
        
        # 滚动区域
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 禁用水平滚动条
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)  # 垂直滚动条按需显示
        scroll.setMaximumHeight(400)
        scroll.setMinimumWidth(380)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: {scrollbar_bg};
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {scrollbar_handle};
                border-radius: 4px;
                margin: 0px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        # 内容容器
        content = QWidget()
        content.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
            QFrame {
                border: none;
            }
        """)
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(5, 5, 5, 5)
        
        # 计算总大小
        total_size = sum(item['total_size'] for item in self.storage_stats_data)
        
        # 显示每个文件夹
        for item in self.storage_stats_data:
            folder_name = os.path.basename(item['folder'])
            size_str = FileScanner.format_size(item['total_size'])
            percentage = (item['total_size'] / total_size * 100) if total_size > 0 else 0
            
            # 文件夹项
            item_frame = QFrame()
            item_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {item_bg};
                    border-radius: 8px;
                    padding: 8px;
                }}
                QFrame:hover {{
                    background-color: {item_hover_bg};
                }}
            """)
            item_layout = QVBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 8, 10, 8)
            item_layout.setSpacing(4)
            
            # 文件夹名称
            name_label = QLabel(f"📁 {folder_name}")
            name_label.setStyleSheet(f"""
                font-size: 13px;
                font-weight: bold;
                color: {name_color};
            """)
            item_layout.addWidget(name_label)
            
            # 详细信息
            detail_label = QLabel(
                f"<span style='color: {label_color};'>文件数:</span> <span style='color: {value_color};'>{item['file_count']} 个</span><br>"
                f"<span style='color: {label_color};'>大小:</span> <span style='color: {value_color};'>{size_str}</span><br>"
                f"<span style='color: {label_color};'>占比:</span> <span style='color: {percentage_color};'>{percentage:.1f}%</span>"
            )
            detail_label.setStyleSheet("font-size: 11px; line-height: 1.4;")
            item_layout.addWidget(detail_label)
            
            content_layout.addWidget(item_frame)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # 计算气泡位置（在主窗口中心）
        # 获取气泡的尺寸
        bubble.adjustSize()
        bubble_width = 400  # 气泡宽度
        bubble_height = min(450, bubble.sizeHint().height())  # 气泡高度，最大450
        
        # 获取主窗口的全局位置和尺寸
        main_window = self.window()
        main_global_pos = main_window.mapToGlobal(QPoint(0, 0))
        main_width = main_window.width()
        main_height = main_window.height()
        
        # 计算居中位置
        bubble_x = main_global_pos.x() + (main_width - bubble_width) // 2
        bubble_y = main_global_pos.y() + (main_height - bubble_height) // 2
        
        bubble.move(bubble_x, bubble_y)
        
        # 显示气泡
        bubble.exec()
    
    def _create_pie_chart(self, storage_stats, total_size):
        """创建饼图"""
        chart_widget = QFrame()
        chart_widget.setObjectName("chartFrame")
        chart_widget.setMinimumHeight(350)
        
        class PieChartWidget(QWidget):
            def __init__(self, data, total, theme='dark', parent=None):
                super().__init__(parent)
                self.data = data
                self.total = total
                self.theme = theme
                self.setMinimumHeight(300)
                
                # 颜色方案
                self.colors = [
                    QColor(47, 165, 114),   # #2FA572 - 绿色
                    QColor(31, 106, 165),   # #1F6AA5 - 蓝色
                    QColor(232, 17, 35),    # #E81123 - 红色
                    QColor(255, 185, 0),    # #FFB900 - 黄色
                    QColor(142, 68, 173),   # #8E44AD - 紫色
                ]
            
            def paintEvent(self, event):
                if not self.data or self.total == 0:
                    return
                
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # 根据主题设置边框颜色
                if self.theme == 'light':
                    border_color = QColor("#FFFFFF")  # 白色边框
                else:
                    border_color = QColor("#1A1A1A")  # 深色边框
                
                # 计算中心和半径
                width = self.width()
                height = self.height()
                center_x = width // 2
                center_y = height // 2
                radius = min(width, height) // 3
                
                # 绘制饼图
                start_angle = 0
                for i, item in enumerate(self.data):
                    percentage = item['total_size'] / self.total
                    span_angle = int(percentage * 360 * 16)  # Qt 使用 1/16 度
                    
                    color = self.colors[i % len(self.colors)]
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(border_color, 2))
                    
                    # 绘制扇形
                    rect = QRectF(center_x - radius, center_y - radius, 
                                 radius * 2, radius * 2)
                    painter.drawPie(rect, start_angle, span_angle)
                    
                    start_angle += span_angle
        
        chart = PieChartWidget(storage_stats, total_size, self.current_theme, chart_widget)
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.addWidget(chart)
        
        return chart_widget
    
    def _create_treemap_chart(self, storage_stats, total_size):
        """创建树形图（Treemap）"""
        chart_widget = QFrame()
        chart_widget.setObjectName("chartFrame")
        chart_widget.setMinimumHeight(250)  # 降低最小高度
        chart_widget.setMaximumHeight(350)  # 限制最大高度
        
        chart = TreemapWidget(storage_stats, total_size, self.current_theme, chart_widget)
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.addWidget(chart)
        
        return chart_widget


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
