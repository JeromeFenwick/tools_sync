# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件 (PyQt6 版本)
用于将文件同步工具打包成单个 exe 可执行文件

使用方法：
    pyinstaller build_exe.spec

要求：
    - 数据库文件(sync_data.db)不打包，放在exe同级目录
    - 如果数据库不存在，程序会自动创建
    - 所有依赖打包进exe
"""

block_cipher = None

a = Analysis(
    ['gui_qt6.py'],  # 入口文件 (修改为 PyQt6 版本)
    pathex=[],
    binaries=[],
    datas=[],  # 不打包数据库文件
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'sqlite3',
        'hashlib',
        'zipfile',
        'threading',
        'datetime',
        'json',
        'platform',
        'ctypes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['customtkinter', 'tkinter'],  # 排除 CustomTkinter 相关
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='文件同步工具',  # exe文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 使用UPX压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # 可以添加图标文件路径，如 'icon.ico'
)
