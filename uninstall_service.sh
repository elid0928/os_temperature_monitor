#!/bin/bash

# 温度监控系统 systemd 服务卸载脚本

echo "🗑️  Uninstalling Temperature Monitor System Service..."

SERVICE_NAME="temperature-monitor.service"

# 检查服务是否存在
if ! systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    echo "⚠️  Service $SERVICE_NAME is not installed."
    exit 0
fi

# 停止服务
echo "🛑 Stopping temperature-monitor service..."
sudo systemctl stop temperature-monitor.service 2>/dev/null || true

# 禁用服务
echo "❌ Disabling temperature-monitor service..."
sudo systemctl disable temperature-monitor.service 2>/dev/null || true

# 删除服务文件
echo "📁 Removing service file..."
sudo rm -f "/etc/systemd/system/$SERVICE_NAME"

# 重新加载systemd
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# 重置失败状态
sudo systemctl reset-failed 2>/dev/null || true

echo ""
echo "✅ Temperature Monitor System Service has been uninstalled."
echo "💡 You can still run the system manually using ./start_monitoring.sh"