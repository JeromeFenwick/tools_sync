# -*- coding: utf-8 -*-
"""
树形图组件（Treemap Widget）
"""
import os
from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, QRectF
from file_scanner import FileScanner


class TreemapWidget(QWidget):
    """树形图可视化组件"""
    
    def __init__(self, data, total, theme='dark', parent=None):
        super().__init__(parent)
        self.data = data
        self.total = total
        self.theme = theme
        self.setMinimumHeight(250)  # 降低最小高度
        self.setMaximumHeight(350)  # 设置最大高度，防止过大
        self.setMouseTracking(True)
        
        # 颜色方案（蓝绿色系低饱和度）
        self.colors = [
            QColor(158, 188, 218),  # 淡蓝
            QColor(145, 191, 219),  # 天蓝
            QColor(166, 206, 227),  # 浅蓝
            QColor(140, 184, 198),  # 蓝灰
            QColor(178, 223, 219),  # 淡青
            QColor(144, 202, 202),  # 青蓝
            QColor(169, 216, 205),  # 青绿
            QColor(184, 225, 215),  # 浅青绿
            QColor(159, 197, 187),  # 柔和青
            QColor(174, 210, 221),  # 淡蓝青
            QColor(189, 215, 228),  # 淡天蓝
            QColor(156, 195, 213),  # 柔蓝
            QColor(171, 210, 199),  # 清新绿
            QColor(162, 196, 201),  # 静谧蓝
            QColor(181, 208, 208),  # 柔和青灰
        ]
        
        self.rectangles = []
        self.hover_index = None
    
    def _calculate_layout(self, width, height):
        """计算树形图布局（Squarified Treemap 算法）"""
        if not self.data or self.total == 0:
            return []
        
        sorted_data = sorted(self.data, key=lambda x: x['total_size'], reverse=True)
        rectangles = []
        
        remaining_data = sorted_data.copy()
        x, y = 0, 0
        w, h = width, height
        horizontal = True
        
        while remaining_data:
            item = remaining_data.pop(0)
            percentage = item['total_size'] / self.total
            
            if horizontal:
                item_width = w * percentage if remaining_data else w
                rectangles.append({
                    'x': x, 'y': y, 'width': item_width, 'height': h, 'data': item
                })
                x += item_width
                w -= item_width
                
                if w < width * 0.3 and remaining_data:
                    horizontal = False
                    x = rectangles[-1]['x']
                    w = rectangles[-1]['width']
                    y = rectangles[-1]['y'] + rectangles[-1]['height'] * 0.3
                    h = rectangles[-1]['height'] * 0.7
            else:
                item_height = h * percentage if remaining_data else h
                rectangles.append({
                    'x': x, 'y': y, 'width': w, 'height': item_height, 'data': item
                })
                y += item_height
                h -= item_height
                
                if h < height * 0.3 and remaining_data:
                    horizontal = True
                    y = rectangles[-1]['y']
                    h = rectangles[-1]['height']
                    x = rectangles[-1]['x'] + rectangles[-1]['width'] * 0.3
                    w = rectangles[-1]['width'] * 0.7
        
        return rectangles
    
    def paintEvent(self, event):
        if not self.data or self.total == 0:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        margin = 10
        width = self.width() - 2 * margin
        height = self.height() - 2 * margin
        self.rectangles = self._calculate_layout(width, height)
        
        # 根据主题选择文字和边框颜色
        if self.theme == 'light':
            text_color = QColor(45, 45, 45)  # 深灰色文字，高对比度
            border_color = QColor(200, 200, 200, 150)  # 浅灰色边框
        else:
            text_color = QColor(255, 255, 255)  # 白色文字
            border_color = QColor(255, 255, 255, 100)  # 半透明白色边框
        
        for i, rect in enumerate(self.rectangles):
            x = margin + rect['x']
            y = margin + rect['y']
            w = rect['width']
            h = rect['height']
            
            color = self.colors[i % len(self.colors)]
            
            if i == self.hover_index:
                if self.theme == 'light':
                    color = color.darker(110)  # 明亮模式下变暗
                else:
                    color = color.lighter(120)  # 暗黑模式下变亮
            
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(border_color, 2))
            painter.drawRect(int(x), int(y), int(w), int(h))
            
            if w > 80 and h > 40:
                folder_name = os.path.basename(rect['data']['folder'])
                size_str = FileScanner.format_size(rect['data']['total_size'])
                percentage = rect['data']['total_size'] / self.total * 100
                
                painter.setPen(QPen(text_color))
                font = painter.font()
                font.setPointSize(10)
                font.setBold(True)
                painter.setFont(font)
                
                text_rect = QRectF(x + 5, y + 5, w - 10, h - 10)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, folder_name)
                
                if h > 60:
                    font.setPointSize(9)
                    font.setBold(False)
                    painter.setFont(font)
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                                   f"{size_str}\n{percentage:.1f}%")
    
    def mouseMoveEvent(self, event):
        pos = event.pos()
        hover_found = False
        margin = 10
        
        for i, rect in enumerate(self.rectangles):
            x = margin + rect['x']
            y = margin + rect['y']
            w = rect['width']
            h = rect['height']
            
            if x <= pos.x() <= x + w and y <= pos.y() <= y + h:
                if self.hover_index != i:
                    self.hover_index = i
                    self.update()
                    
                    folder_name = os.path.basename(rect['data']['folder'])
                    size_str = FileScanner.format_size(rect['data']['total_size'])
                    file_count = rect['data']['file_count']
                    percentage = rect['data']['total_size'] / self.total * 100
                    
                    QToolTip.showText(
                        event.globalPosition().toPoint(),
                        f"{folder_name}\n{file_count} 个文件 | {size_str} ({percentage:.1f}%)",
                        self
                    )
                hover_found = True
                break
        
        if not hover_found and self.hover_index is not None:
            self.hover_index = None
            self.update()
            QToolTip.hideText()
    
    def leaveEvent(self, event):
        if self.hover_index is not None:
            self.hover_index = None
            self.update()
            QToolTip.hideText()
