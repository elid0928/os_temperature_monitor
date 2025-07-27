#!/usr/bin/env python3
from flask import Flask, jsonify, render_template_string, request
import sqlite3
from datetime import datetime, timedelta
import json

app = Flask(__name__)
DB_PATH = 'temperature_monitor.db'

def get_friendly_sensor_name(sensor_name):
    """将传感器技术名称转换为用户友好的名称"""
    mapping = {
        # CPU温度
        'k10temp-pci-00c3_Tctl_temp1': 'CPU控制温度',
        'k10temp-pci-00c3_Tccd1_temp3': 'CPU核心温度',
        
        # GPU温度
        'nvidia_gpu_0': 'NVIDIA显卡',
        'nvidia_gpu_1': 'NVIDIA显卡2',
        'amd_gpu': 'AMD显卡',
        
        # 存储设备
        'nvme-pci-0100_Composite_temp1': 'NVMe SSD-1',
        'nvme-pci-0100_Sensor 1_temp2': 'NVMe SSD-1 传感器1',
        'nvme-pci-0100_Sensor 2_temp3': 'NVMe SSD-1 传感器2',
        'nvme-pci-0400_Composite_temp1': 'NVMe SSD-2',
        'nvme-pci-0400_Sensor 1_temp2': 'NVMe SSD-2 传感器1',
        'nvme-pci-0400_Sensor 2_temp3': 'NVMe SSD-2 传感器2',
        
        # 网络设备
        'iwlwifi_1-virtual-0_temp1_temp1': 'WiFi网卡',
        'r8169_0_2a00:00-mdio-0_temp1_temp1': '以太网卡',
        
        # 热区域
        'thermal_thermal_zone0': '系统热区域'
    }
    
    # 如果有精确匹配，返回友好名称
    if sensor_name in mapping:
        return mapping[sensor_name]
    
    # 基于模式的智能匹配
    sensor_lower = sensor_name.lower()
    
    if 'nvidia_gpu' in sensor_lower:
        return f"NVIDIA显卡{sensor_name.split('_')[-1]}"
    elif 'amd_gpu' in sensor_lower:
        return 'AMD显卡'
    elif 'k10temp' in sensor_lower:
        if 'tctl' in sensor_lower:
            return 'CPU控制温度'
        elif 'tccd' in sensor_lower:
            return 'CPU核心温度'
        else:
            return 'CPU温度'
    elif 'nvme' in sensor_lower:
        if 'composite' in sensor_lower:
            # 提取设备编号
            if '0100' in sensor_name:
                return 'NVMe SSD-1'
            elif '0400' in sensor_name:
                return 'NVMe SSD-2'
            else:
                return 'NVMe SSD'
        elif 'sensor' in sensor_lower:
            device_num = '1' if '0100' in sensor_name else '2' if '0400' in sensor_name else ''
            sensor_num = '1' if 'temp2' in sensor_name else '2' if 'temp3' in sensor_name else ''
            return f'NVMe SSD-{device_num} 传感器{sensor_num}' if device_num else 'NVMe传感器'
    elif 'iwlwifi' in sensor_lower or 'wifi' in sensor_lower:
        return 'WiFi网卡'
    elif 'r8169' in sensor_lower or 'ethernet' in sensor_lower:
        return '以太网卡'
    elif 'thermal_zone' in sensor_lower:
        return '系统热区域'
    
    # 如果没有匹配，返回简化的原始名称
    return sensor_name.replace('_', ' ').title()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Temperature Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.3.0/dist/chart.umd.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; margin-bottom: 30px; }
        .chart-container { position: relative; height: 400px; margin: 20px 0; }
        .controls { margin: 20px 0; text-align: center; }
        .controls select, .controls button { margin: 0 10px; padding: 8px 15px; border: 1px solid #ddd; border-radius: 4px; }
        .stats { display: flex; justify-content: space-around; margin: 20px 0; }
        .stat-card { background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; min-width: 120px; }
        .stat-value { font-size: 24px; font-weight: bold; color: #007bff; }
        .stat-label { font-size: 14px; color: #666; margin-top: 5px; }
        .current-temps { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .temp-card { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 15px; 
            border-radius: 8px; 
            text-align: center; 
            cursor: pointer; 
            transition: all 0.3s ease; 
            border: 2px solid transparent;
            user-select: none;
        }
        .temp-card:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 4px 12px rgba(0,0,0,0.2); 
        }
        .temp-card.selected { 
            border: 2px solid #ffd700; 
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%); 
            box-shadow: 0 0 10px rgba(255,215,0,0.5); 
        }
        .temp-name { font-size: 14px; opacity: 0.9; }
        .temp-value { font-size: 28px; font-weight: bold; margin: 5px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌡️ Hardware Temperature Monitor</h1>
        
        <div class="current-temps" id="currentTemps">
            <!-- Current temperatures will be loaded here -->
        </div>
        
        <div class="controls">
            <select id="timeRange">
                <option value="1">Last 1 hour</option>
                <option value="6">Last 6 hours</option>
                <option value="24" selected>Last 24 hours</option>
                <option value="168">Last 7 days</option>
            </select>
            <button onclick="refreshData()">Refresh</button>
            <button onclick="toggleAutoRefresh()">Auto Refresh: <span id="autoStatus">OFF</span></button>
            <button onclick="selectAllSensors()">Select All</button>
            <button onclick="clearSelection()">Clear Selection</button>
        </div>
        
        <div class="chart-container">
            <canvas id="temperatureChart"></canvas>
        </div>
        
        <div class="stats" id="stats">
            <!-- Statistics will be loaded here -->
        </div>
    </div>

    <script>
        let chart;
        let autoRefreshInterval;
        let autoRefreshEnabled = false;
        let selectedSensors = new Set(); // 选中的传感器
        let allTemperatureData = []; // 存储所有温度数据
        let currentTemperatureData = []; // 存储当前温度数据

        function initChart() {
            const ctx = document.getElementById('temperatureChart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    datasets: []
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                displayFormats: {
                                    minute: 'HH:mm',
                                    hour: 'MMM dd HH:mm'
                                }
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Temperature (°C)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                title: function(context) {
                                    // 显示时间
                                    return new Date(context[0].parsed.x).toLocaleString();
                                },
                                label: function(context) {
                                    const dataset = context.dataset;
                                    const originalName = dataset.originalName || dataset.label;
                                    return `${dataset.label}: ${context.parsed.y.toFixed(1)}°C (${originalName})`;
                                }
                            }
                        }
                    },
                    elements: {
                        line: {
                            tension: 0.1
                        },
                        point: {
                            radius: 2
                        }
                    }
                }
            });
        }

        function getRandomColor(index) {
            const colors = [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
            ];
            return colors[index % colors.length];
        }

        async function loadTemperatureData() {
            const timeRange = document.getElementById('timeRange').value;
            try {
                const response = await fetch(`/api/temperatures?hours=${timeRange}`);
                const data = await response.json();
                
                // 存储数据
                allTemperatureData = data.data;
                currentTemperatureData = data.current;
                
                updateChart();
                updateStats(data.stats);
                updateCurrentTemps();
            } catch (error) {
                console.error('Error loading temperature data:', error);
            }
        }

        function updateChart() {
            const datasets = {};
            
            // 只显示选中的传感器数据
            const filteredData = allTemperatureData.filter(reading => {
                const key = reading.friendly_name || reading.sensor_name;
                return selectedSensors.has(key);
            });
            
            filteredData.forEach(reading => {
                const key = reading.friendly_name || reading.sensor_name;
                if (!datasets[key]) {
                    const colorIndex = Object.keys(datasets).length;
                    datasets[key] = {
                        label: key,
                        data: [],
                        borderColor: getRandomColor(colorIndex),
                        backgroundColor: getRandomColor(colorIndex) + '20',
                        fill: false,
                        originalName: reading.sensor_name // 保存原始名称用于tooltip
                    };
                }
                
                datasets[key].data.push({
                    x: new Date(reading.timestamp),
                    y: reading.temperature
                });
            });
            
            chart.data.datasets = Object.values(datasets);
            chart.update();
        }

        function updateStats(stats) {
            const statsContainer = document.getElementById('stats');
            statsContainer.innerHTML = '';
            
            if (stats.total_readings > 0) {
                statsContainer.innerHTML = `
                    <div class="stat-card">
                        <div class="stat-value">${stats.total_readings}</div>
                        <div class="stat-label">Total Readings</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.avg_temp.toFixed(1)}°C</div>
                        <div class="stat-label">Average Temp</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.max_temp.toFixed(1)}°C</div>
                        <div class="stat-label">Max Temp</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.min_temp.toFixed(1)}°C</div>
                        <div class="stat-label">Min Temp</div>
                    </div>
                `;
            }
        }

        function updateCurrentTemps() {
            const container = document.getElementById('currentTemps');
            container.innerHTML = '';
            
            currentTemperatureData.forEach(temp => {
                const sensorKey = temp.friendly_name || temp.sensor_name;
                const tempCard = document.createElement('div');
                
                // 设置基本样式和选中状态
                tempCard.className = selectedSensors.has(sensorKey) ? 'temp-card selected' : 'temp-card';
                tempCard.title = `原始名称: ${temp.sensor_name}\n点击切换图表显示`; // 鼠标悬停显示原始名称
                tempCard.dataset.sensorKey = sensorKey;
                
                tempCard.innerHTML = `
                    <div class="temp-name">${sensorKey}</div>
                    <div class="temp-value">${temp.temperature.toFixed(1)}°C</div>
                    <div class="temp-name">${new Date(temp.timestamp).toLocaleTimeString()}</div>
                `;
                
                // 添加点击事件
                tempCard.addEventListener('click', () => toggleSensor(sensorKey, tempCard));
                
                container.appendChild(tempCard);
            });
        }
        
        function toggleSensor(sensorKey, cardElement) {
            if (selectedSensors.has(sensorKey)) {
                selectedSensors.delete(sensorKey);
                cardElement.classList.remove('selected');
            } else {
                selectedSensors.add(sensorKey);
                cardElement.classList.add('selected');
            }
            
            updateChart(); // 重新渲染图表
        }

        function refreshData() {
            loadTemperatureData();
        }

        function toggleAutoRefresh() {
            const statusSpan = document.getElementById('autoStatus');
            
            if (autoRefreshEnabled) {
                clearInterval(autoRefreshInterval);
                autoRefreshEnabled = false;
                statusSpan.textContent = 'OFF';
            } else {
                autoRefreshInterval = setInterval(loadTemperatureData, 60000); // Refresh every minute
                autoRefreshEnabled = true;
                statusSpan.textContent = 'ON';
            }
        }
        
        function selectAllSensors() {
            selectedSensors.clear();
            currentTemperatureData.forEach(temp => {
                const sensorKey = temp.friendly_name || temp.sensor_name;
                selectedSensors.add(sensorKey);
            });
            updateCurrentTemps(); // 重新渲染卡片状态
            updateChart(); // 重新渲染图表
        }
        
        function clearSelection() {
            selectedSensors.clear();
            updateCurrentTemps(); // 重新渲染卡片状态
            updateChart(); // 重新渲染图表
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            initChart();
            loadTemperatureData();
            
            // Set up event listeners
            document.getElementById('timeRange').addEventListener('change', loadTemperatureData);
        });
    </script>
</body>
</html>
'''

def get_temperature_data(hours=24):
    """获取指定时间范围内的温度数据"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取历史数据
    cursor.execute('''
        SELECT sensor_name, temperature, timestamp
        FROM temperature_readings
        WHERE timestamp >= datetime('now', 'localtime', '-{} hours')
        ORDER BY timestamp ASC
    '''.format(hours))
    
    raw_data = [dict(row) for row in cursor.fetchall()]
    
    # 为每条记录添加友好名称
    data = []
    for row in raw_data:
        row_dict = dict(row)
        row_dict['friendly_name'] = get_friendly_sensor_name(row_dict['sensor_name'])
        data.append(row_dict)
    
    # 获取统计信息
    cursor.execute('''
        SELECT 
            COUNT(*) as total_readings,
            AVG(temperature) as avg_temp,
            MAX(temperature) as max_temp,
            MIN(temperature) as min_temp
        FROM temperature_readings
        WHERE timestamp >= datetime('now', 'localtime', '-{} hours')
    '''.format(hours))
    
    stats = dict(cursor.fetchone())
    
    # 获取最新温度
    cursor.execute('''
        SELECT sensor_name, temperature, timestamp
        FROM temperature_readings t1
        WHERE timestamp = (
            SELECT MAX(timestamp) 
            FROM temperature_readings t2 
            WHERE t2.sensor_name = t1.sensor_name
        )
        ORDER BY sensor_name
    ''')
    
    raw_current = [dict(row) for row in cursor.fetchall()]
    
    # 为当前温度也添加友好名称
    current = []
    for row in raw_current:
        row_dict = dict(row)
        row_dict['friendly_name'] = get_friendly_sensor_name(row_dict['sensor_name'])
        current.append(row_dict)
    
    conn.close()
    
    return {
        'data': data,
        'stats': stats,
        'current': current
    }

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/test')
def test():
    with open('test_web.html', 'r') as f:
        return f.read()

@app.route('/api/temperatures')
def api_temperatures():
    hours = int(request.args.get('hours', 24))
    return jsonify(get_temperature_data(hours))

if __name__ == '__main__':
    print("Starting Temperature Monitor Web Server...")
    print("Open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000, debug=False)