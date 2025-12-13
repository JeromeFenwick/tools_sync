#!/bin/bash
# 文件同步工具打包脚本

echo "================================"
echo "文件同步工具 macOS App 打包脚本"
echo "================================"
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 未找到虚拟环境，正在创建..."
    python3 -m venv venv
    echo "✅ 虚拟环境创建完成"
fi

# 激活虚拟环境
echo "📦 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📦 安装依赖..."
pip install --upgrade pip
pip install customtkinter pillow py2app

# 清理旧的打包文件
echo "🧹 清理旧的打包文件..."
rm -rf build dist

# 开始打包
echo "🚀 开始打包 App..."
python setup.py py2app

# 检查打包结果
if [ -d "dist/文件同步工具.app" ]; then
    echo ""
    echo "✅ 打包成功！"
    echo "📦 App 位置: $(pwd)/dist/文件同步工具.app"
    echo ""
    echo "📝 使用说明："
    echo "1. 将 dist/文件同步工具.app 复制到任意位置"
    echo "2. 双击运行即可"
    echo "3. sync_data.db 会自动创建在 App 同目录下"
    echo "4. backups 文件夹会自动创建在 App 同目录下"
    echo ""
    echo "💡 提示：首次运行可能需要在系统偏好设置中允许运行"
else
    echo ""
    echo "❌ 打包失败，请检查错误信息"
fi
