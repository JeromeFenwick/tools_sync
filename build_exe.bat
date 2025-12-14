@echo off
chcp 65001 >nul
REM 文件同步工具 Windows 打包脚本 (PyQt6 版本)

echo ================================
echo 文件同步工具 Windows EXE 打包脚本
echo PyQt6 Edition
echo ================================
echo.

REM 检查虚拟环境
if not exist "venv" (
    echo ❌ 未找到虚拟环境，正在创建...
    python -m venv venv
    echo ✅ 虚拟环境创建完成
)

REM 激活虚拟环境
echo 📦 激活虚拟环境...
call venv\Scripts\activate.bat

REM 安装依赖
echo 📦 安装依赖...
pip install --upgrade pip
pip install PyQt6 pillow pyinstaller

REM 清理旧的打包文件
echo 🧹 清理旧的打包文件...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM 开始打包
echo 🚀 开始打包 EXE...
pyinstaller build_exe.spec

REM 检查打包结果
if exist "dist\文件同步工具.exe" (
    echo.
    echo ✅ 打包成功！
    echo 📦 EXE 位置: %CD%\dist\文件同步工具.exe
    echo.
    echo 📝 使用说明：
    echo 1. 将 dist\文件同步工具.exe 复制到任意位置
    echo 2. 双击运行即可
    echo 3. sync_data.db 会自动创建在 EXE 同目录下
    echo 4. backups 文件夹会自动创建在 EXE 同目录下
    echo.
) else (
    echo.
    echo ❌ 打包失败，请检查错误信息
)

pause