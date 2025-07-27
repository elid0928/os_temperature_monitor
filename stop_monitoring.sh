#!/bin/bash

# 温度监控系统停止脚本
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Stopping Temperature Monitoring System..."

# 停止温度采集进程
if [ -f "collector.pid" ]; then
    COLLECTOR_PID=$(cat collector.pid)
    if kill -0 $COLLECTOR_PID 2>/dev/null; then
        echo "Stopping temperature collector (PID: $COLLECTOR_PID)..."
        kill $COLLECTOR_PID
        rm collector.pid
    fi
fi

# 停止Web服务器
if [ -f "web.pid" ]; then
    WEB_PID=$(cat web.pid)
    if kill -0 $WEB_PID 2>/dev/null; then
        echo "Stopping web server (PID: $WEB_PID)..."
        kill $WEB_PID
        rm web.pid
    fi
fi

# 清理其他可能的进程
pkill -f "temperature_collector.py"
pkill -f "web_server.py"

echo "✅ Temperature monitoring system stopped."