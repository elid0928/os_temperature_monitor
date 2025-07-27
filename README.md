# 硬件温度监控系统

这是一个适用于Ubuntu 24.04的硬件温度监控系统，可以实时收集系统温度数据并通过Web界面展示。

## 功能特性

- 🌡️ 自动检测并采集硬件温度（CPU、GPU、NVMe SSD、网卡等）
- 📊 每60秒采集一次数据并存储到SQLite数据库
- 🌐 提供Web界面展示实时温度图表
- 📈 支持多时间范围查看（1小时、6小时、24小时、7天）
- 🔄 自动刷新功能
- 📉 显示温度统计信息（平均值、最大值、最小值）
- 🚨 智能温度告警：超过安全阈值时发送系统通知
- 🎯 点击式图表展示：点击温度卡片选择要查看的指标
- 🏷️ 友好的传感器名称显示

## 系统要求

- Ubuntu 24.04
- Python 3
- lm-sensors工具
- Flask（会自动安装）

## 文件说明

- `init_db.py` - 初始化SQLite数据库
- `temperature_collector.py` - 温度数据采集脚本
- `web_server.py` - Web服务器
- `start_monitoring.sh` - 启动监控系统
- `stop_monitoring.sh` - 停止监控系统
- `temperature_monitor.db` - SQLite数据库文件（运行后自动创建）

## 快速开始

### 1. 启动监控系统

```bash
./start_monitoring.sh
```

系统会自动：
- 初始化数据库
- 开始每60秒采集一次温度数据
- 启动Web服务器在 http://localhost:5000

### 2. 查看监控界面

打开浏览器访问：http://localhost:5000

### 3. 停止监控系统

```bash
./stop_monitoring.sh
```

## 手动操作

### 单次采集温度数据
```bash
python3 temperature_collector.py
```

### 只启动Web服务器
```bash
python3 web_server.py
```

### 初始化数据库
```bash
python3 init_db.py
```

## 数据库结构

温度数据存储在SQLite数据库中，表结构如下：

```sql
CREATE TABLE temperature_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    sensor_name TEXT NOT NULL,
    temperature REAL NOT NULL,
    unit TEXT DEFAULT 'C'
);
```

## Web界面功能

- **实时温度卡片**：显示所有传感器的当前温度，点击卡片可切换图表显示
- **历史图表**：可选择不同时间范围查看温度变化趋势
- **统计信息**：显示所选时间范围内的温度统计
- **自动刷新**：可开启自动刷新功能
- **友好名称**：显示用户友好的传感器名称，鼠标悬停可查看原始名称

## 温度告警功能

系统会自动监控硬件温度，当超过安全阈值时发送系统通知：

### 告警阈值设置
- **CPU控制温度**: 85°C
- **CPU核心温度**: 90°C  
- **NVIDIA显卡**: 83°C
- **AMD显卡**: 90°C
- **NVMe SSD**: 75°C
- **WiFi网卡**: 75°C
- **以太网卡**: 80°C
- **系统热区域**: 70°C

### 告警特性
- 🔔 使用Linux系统通知（notify-send）
- ⏰ 5分钟冷却时间，避免频繁告警
- 📝 自动记录告警历史
- 🎨 温度越高，通知紧急程度越高

## 故障排除

1. **如果没有检测到温度传感器**：
   ```bash
   sudo sensors-detect
   ```

2. **如果sensors命令不存在**：
   ```bash
   sudo apt update
   sudo apt install lm-sensors
   ```

3. **如果Flask未安装**：
   ```bash
   pip3 install flask
   ```

4. **查看日志**：
   温度采集脚本会输出详细的日志信息，包括检测到的传感器和温度值。

## 开机自启动（推荐）

### 自动安装systemd服务

使用提供的安装脚本一键安装：

```bash
./install_service.sh
```

安装完成后，服务会在开机时自动启动。

### 手动管理服务

```bash
# 查看服务状态
sudo systemctl status temperature-monitor

# 启动服务
sudo systemctl start temperature-monitor

# 停止服务  
sudo systemctl stop temperature-monitor

# 重启服务
sudo systemctl restart temperature-monitor

# 查看服务日志
sudo journalctl -u temperature-monitor -f
```

### 卸载服务

如果需要卸载systemd服务：

```bash
./uninstall_service.sh
```

## 注意事项

- 系统需要读取 `/sys/class/thermal/` 和 `/sys/class/hwmon/` 目录下的温度传感器
- Web服务器默认运行在5000端口，确保端口未被占用
- 数据库文件会在当前目录创建，确保有写入权限