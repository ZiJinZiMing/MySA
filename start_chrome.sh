#!/bin/bash

# Chrome远程调试启动脚本
# 用于MySA项目的Chrome远程调试环境初始化

echo "🚀 启动Chrome远程调试模式..."

# 检查端口9222是否被占用
if lsof -Pi :9222 -sTCP:LISTEN -t >/dev/null; then
    echo "⚠️  端口9222已被占用，正在尝试关闭现有Chrome进程..."
    pkill -f "chrome.*remote-debugging-port=9222" || true
    sleep 2
fi

# 设置用户数据目录
CHROME_USER_DATA_DIR="$HOME/software/chrome_userdata"

# 创建用户数据目录（如果不存在）
if [ ! -d "$CHROME_USER_DATA_DIR" ]; then
    echo "📁 创建Chrome用户数据目录: $CHROME_USER_DATA_DIR"
    mkdir -p "$CHROME_USER_DATA_DIR"
fi

# 启动Chrome远程调试模式
echo "🌐 启动Chrome（端口9222）..."
google-chrome \
    --remote-debugging-port=9222 \
    --user-data-dir="$CHROME_USER_DATA_DIR" \
    --no-first-run \
    --no-default-browser-check \
    --disable-default-apps \
    &

# 等待Chrome启动
sleep 3

# 检查Chrome是否成功启动
if lsof -Pi :9222 -sTCP:LISTEN -t >/dev/null; then
    echo "✅ Chrome远程调试模式启动成功！"
    echo "📋 配置信息:"
    echo "   - 调试端口: 9222"
    echo "   - 用户数据目录: $CHROME_USER_DATA_DIR"
    echo "   - 进程ID: $(pgrep -f 'chrome.*remote-debugging-port=9222')"
    echo ""
    echo "🔗 下一步操作:"
    echo "   1. 在Chrome中登录SeekingAlpha账户"
    echo "   2. 运行MySA项目中的任意脚本"
    echo "   3. 保持Chrome进程运行期间不要关闭"
    echo ""
    echo "🛑 停止Chrome: pkill -f 'chrome.*remote-debugging-port=9222'"
else
    echo "❌ Chrome启动失败！请检查chrome命令是否可用。"
    exit 1
fi