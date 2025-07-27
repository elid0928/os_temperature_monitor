#!/bin/bash

# 温度监控系统启动脚本
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Temperature Monitoring System..."

# 初始化数据库（如果还没有初始化）
if [ ! -f "temperature_monitor.db" ]; then
    echo "Initializing database..."
    python3 init_db.py
fi

# 设置权限
chmod +x temperature_collector.py
chmod +x web_server.py

# 先收集一次数据
echo "Collecting initial temperature data..."
python3 temperature_collector.py

# 启动定时采集（后台运行）
echo "Starting temperature collection service (every 60 seconds)..."
{
    while true; do
        sleep 60
        python3 temperature_collector.py
    done
} &

COLLECTOR_PID=$!
echo "Temperature collector started with PID: $COLLECTOR_PID"

# 启动Web服务器
echo "Starting web server on http://localhost:5000..."
python3 web_server.py &

WEB_PID=$!
echo "Web server started with PID: $WEB_PID"

# 保存PID用于停止服务
echo $COLLECTOR_PID > collector.pid
echo $WEB_PID > web.pid

# 为systemd创建主PID文件
echo $$ > temperature-monitor.pid

echo ""
echo "✅ Temperature monitoring system is now running!"
echo "📊 Web interface: http://localhost:5000"
echo "🔄 Data collection: every 60 seconds"
echo ""

# 检查是否由systemd启动
if [ "$1" = "--systemd" ]; then
    echo "Running as systemd service..."
    # 作为守护进程运行，不等待用户输入
    exit 0
else
    echo "To stop the monitoring system, run: ./stop_monitoring.sh"
    # 等待用户输入或信号
    wait
fi