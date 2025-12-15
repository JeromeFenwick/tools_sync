# -*- coding: utf-8 -*-
"""
py2app setup script for 文件同步工具 (PyQt6 版本)
"""
from setuptools import setup
import os
import sys
from PyQt6 import QtCore

# 获取 PyQt6 的路径
qt_plugins_path = os.path.join(os.path.dirname(QtCore.__file__), 'Qt6', 'plugins')

APP = ['gui_qt6.py']
DATA_FILES = []

# 如果 Qt plugins 目录存在，添加到 DATA_FILES
if os.path.exists(qt_plugins_path):
    DATA_FILES.append((os.path.join('Contents', 'PlugIns'), [qt_plugins_path]))

OPTIONS = {
    'argv_emulation': False,
    'packages': ['PyQt6'],
    'includes': [
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'PyQt6.sip',
    ],
    'iconfile': 'icon.ico',
    'plist': {
        'CFBundleName': '文件同步工具',
        'CFBundleDisplayName': '文件同步工具',
        'CFBundleGetInfoString': "文件同步工具 - 智能备份与同步 (PyQt6 Edition)",
        'CFBundleIdentifier': "com.fenwick.filesync",
        'CFBundleVersion': "2.2.0",
        'CFBundleShortVersionString': "2.2.0",
        'NSHumanReadableCopyright': "Copyright © 2026 Fenwick All Rights Reserved",
        'NSHighResolutionCapable': True,
    },
    'excludes': ['matplotlib', 'numpy', 'scipy', 'customtkinter', 'tkinter'],
    'frameworks': [],
    'qt_plugins': ['platforms', 'styles'],
    'optimize': 2,
}

setup(
    name='文件同步工具',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
