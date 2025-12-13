# -*- coding: utf-8 -*-
"""
py2app setup script for 文件同步工具 (PyQt6 版本)
"""
from setuptools import setup

APP = ['gui_qt6.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets'],
    'includes': ['PIL'],
    'iconfile': 'icon.ico',  # 如果有图标文件，可以指定路径
    'plist': {
        'CFBundleName': '文件同步工具',
        'CFBundleDisplayName': '文件同步工具',
        'CFBundleGetInfoString': "文件同步工具 - 智能备份与同步 (PyQt6 Edition)",
        'CFBundleIdentifier': "com.yourname.filesync",
        'CFBundleVersion': "2.0.0",
        'CFBundleShortVersionString': "2.0.0",
        'NSHumanReadableCopyright': "Copyright © 2026 Fenwick All Rights Reserved",
        'NSHighResolutionCapable': True,
    },
    'excludes': ['matplotlib', 'numpy', 'scipy', 'customtkinter', 'tkinter'],  # 排除不需要的大型库
    'optimize': 2,
}

setup(
    name='文件同步工具',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
