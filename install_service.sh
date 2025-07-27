#!/bin/bash

# 温度监控系统 systemd 服务安装脚本

echo "🔧 Installing Temperature Monitor System Service..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="temperature-monitor.service"
SERVICE_FILE="$SCRIPT_DIR/$SERVICE_NAME"

# 检查服务文件是否存在
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Error: $SERVICE_NAME not found in $SCRIPT_DIR"
    exit 1
fi

# 检查当前用户
CURRENT_USER=$(whoami)
if [ "$CURRENT_USER" = "root" ]; then
    echo "⚠️  Warning: Running as root. The service will run as user 'elid'."
fi

# 获取当前用户的UID（用于DBUS）
USER_ID=$(id -u elid 2>/dev/null || id -u $CURRENT_USER)

# 创建临时服务文件，替换用户特定的路径
TEMP_SERVICE="/tmp/$SERVICE_NAME"
sed "s|/home/elid|$HOME|g; s|1000|$USER_ID|g" "$SERVICE_FILE" > "$TEMP_SERVICE"

echo "📁 Installing service file to /etc/systemd/system/..."

# 复制服务文件到系统目录
sudo cp "$TEMP_SERVICE" "/etc/systemd/system/$SERVICE_NAME"

# 清理临时文件
rm "$TEMP_SERVICE"

# 设置权限
sudo chmod 644 "/etc/systemd/system/$SERVICE_NAME"

echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "✅ Enabling temperature-monitor service..."
sudo systemctl enable temperature-monitor.service

echo ""
echo "🎉 Installation completed!"
echo ""
echo "Available commands:"
echo "  sudo systemctl start temperature-monitor    # 启动服务"
echo "  sudo systemctl stop temperature-monitor     # 停止服务"
echo "  sudo systemctl restart temperature-monitor  # 重启服务"
echo "  sudo systemctl status temperature-monitor   # 查看服务状态"
echo "  systemctl --user status temperature-monitor # 查看用户服务状态"
echo ""
echo "💡 Service will automatically start on boot!"
echo "📊 Web interface will be available at: http://localhost:5000"
echo ""
echo "To start the service now, run:"
echo "  sudo systemctl start temperature-monitor"