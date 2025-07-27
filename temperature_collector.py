#!/usr/bin/env python3
import sqlite3
import subprocess
import re
import json
from datetime import datetime, timedelta
import logging
import os
import time

DB_PATH = 'temperature_monitor.db'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 温度告警阈值配置（摄氏度）
TEMPERATURE_THRESHOLDS = {
    # CPU温度阈值
    'cpu_control': 85,    # CPU控制温度 (Tctl)
    'cpu_core': 90,       # CPU核心温度 (Tccd)
    'cpu_general': 85,    # 通用CPU温度
    
    # GPU温度阈值
    'gpu_nvidia': 83,     # NVIDIA GPU
    'gpu_amd': 90,        # AMD GPU
    
    # 存储设备温度阈值
    'nvme_ssd': 75,       # NVMe SSD
    'ssd_general': 70,    # 通用SSD
    
    # 网络设备温度阈值
    'network_wifi': 75,   # WiFi网卡
    'network_ethernet': 80, # 以太网卡
    
    # 系统温度阈值
    'system_thermal': 70, # 系统热区域
    
    # 默认阈值
    'default': 75
}

# 告警冷却时间（秒），避免频繁通知
ALERT_COOLDOWN = 300  # 5分钟

def get_temperature_threshold(sensor_name):
    """根据传感器名称获取对应的温度阈值"""
    sensor_lower = sensor_name.lower()
    
    # CPU温度
    if 'k10temp' in sensor_lower or 'cpu' in sensor_lower:
        if 'tctl' in sensor_lower:
            return TEMPERATURE_THRESHOLDS['cpu_control']
        elif 'tccd' in sensor_lower or 'core' in sensor_lower:
            return TEMPERATURE_THRESHOLDS['cpu_core']
        else:
            return TEMPERATURE_THRESHOLDS['cpu_general']
    
    # GPU温度
    elif 'nvidia' in sensor_lower:
        return TEMPERATURE_THRESHOLDS['gpu_nvidia']
    elif 'amd' in sensor_lower and 'gpu' in sensor_lower:
        return TEMPERATURE_THRESHOLDS['gpu_amd']
    
    # 存储设备
    elif 'nvme' in sensor_lower:
        return TEMPERATURE_THRESHOLDS['nvme_ssd']
    elif 'ssd' in sensor_lower:
        return TEMPERATURE_THRESHOLDS['ssd_general']
    
    # 网络设备
    elif 'wifi' in sensor_lower or 'iwlwifi' in sensor_lower:
        return TEMPERATURE_THRESHOLDS['network_wifi']
    elif 'ethernet' in sensor_lower or 'r8169' in sensor_lower:
        return TEMPERATURE_THRESHOLDS['network_ethernet']
    
    # 系统热区域
    elif 'thermal' in sensor_lower:
        return TEMPERATURE_THRESHOLDS['system_thermal']
    
    # 默认阈值
    return TEMPERATURE_THRESHOLDS['default']

def send_system_notification(title, message, urgency='normal'):
    """发送Linux系统通知"""
    try:
        # 检查是否有notify-send命令
        subprocess.run(['which', 'notify-send'], check=True, capture_output=True)
        
        # 发送通知
        cmd = [
            'notify-send',
            '--urgency', urgency,
            '--icon', 'dialog-warning' if urgency == 'critical' else 'dialog-information',
            '--app-name', 'Temperature Monitor',
            title,
            message
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"System notification sent: {title}")
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        # 如果notify-send不可用，尝试使用zenity
        try:
            subprocess.run(['which', 'zenity'], check=True, capture_output=True)
            
            cmd = [
                'zenity', 
                '--warning' if urgency == 'critical' else '--info',
                '--text', f"{title}\n\n{message}",
                '--title', 'Temperature Monitor',
                '--no-wrap'
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Zenity notification sent: {title}")
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            # 如果都不可用，输出到日志
            logger.warning(f"System notification not available. Alert: {title} - {message}")

def get_friendly_sensor_name_for_alert(sensor_name):
    """为告警获取友好的传感器名称"""
    sensor_lower = sensor_name.lower()
    
    if 'k10temp' in sensor_lower:
        if 'tctl' in sensor_lower:
            return 'CPU控制温度'
        elif 'tccd' in sensor_lower:
            return 'CPU核心温度'
        else:
            return 'CPU温度'
    elif 'nvidia_gpu' in sensor_lower:
        return 'NVIDIA显卡'
    elif 'amd_gpu' in sensor_lower:
        return 'AMD显卡'
    elif 'nvme' in sensor_lower:
        if '0100' in sensor_name:
            return 'NVMe SSD-1'
        elif '0400' in sensor_name:
            return 'NVMe SSD-2'
        else:
            return 'NVMe SSD'
    elif 'iwlwifi' in sensor_lower:
        return 'WiFi网卡'
    elif 'r8169' in sensor_lower:
        return '以太网卡'
    elif 'thermal' in sensor_lower:
        return '系统热区域'
    
    return sensor_name.replace('_', ' ').title()

def check_temperature_alerts(temperatures):
    """检查温度告警并发送通知"""
    current_time = datetime.now()
    alert_file = 'temperature_alerts.json'
    
    # 读取上次告警记录
    last_alerts = {}
    if os.path.exists(alert_file):
        try:
            with open(alert_file, 'r') as f:
                last_alerts = json.load(f)
        except:
            last_alerts = {}
    
    new_alerts = {}
    
    for temp_data in temperatures:
        sensor_name = temp_data['sensor_name']
        temperature = temp_data['temperature']
        threshold = get_temperature_threshold(sensor_name)
        
        if temperature > threshold:
            # 温度超过阈值
            last_alert_time_str = last_alerts.get(sensor_name)
            
            # 检查是否需要发送告警（冷却时间）
            should_alert = True
            if last_alert_time_str:
                try:
                    last_alert_time = datetime.fromisoformat(last_alert_time_str)
                    time_diff = (current_time - last_alert_time).total_seconds()
                    if time_diff < ALERT_COOLDOWN:
                        should_alert = False
                except:
                    pass
            
            if should_alert:
                # 发送告警通知
                friendly_name = get_friendly_sensor_name_for_alert(sensor_name)
                title = f"🔥 温度告警 - {friendly_name}"
                message = f"当前温度: {temperature:.1f}°C\n告警阈值: {threshold}°C\n超出阈值: {temperature - threshold:.1f}°C"
                
                urgency = 'critical' if temperature > threshold + 10 else 'normal'
                send_system_notification(title, message, urgency)
                
                logger.warning(f"Temperature alert: {friendly_name} = {temperature:.1f}°C (threshold: {threshold}°C)")
                
                # 记录告警时间
                new_alerts[sensor_name] = current_time.isoformat()
            else:
                # 保持原有的告警时间
                new_alerts[sensor_name] = last_alert_time_str
        else:
            # 温度正常，移除告警记录
            if sensor_name in last_alerts:
                friendly_name = get_friendly_sensor_name_for_alert(sensor_name)
                logger.info(f"Temperature normalized: {friendly_name} = {temperature:.1f}°C")
    
    # 保存告警记录
    try:
        with open(alert_file, 'w') as f:
            json.dump(new_alerts, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save alert records: {e}")

def get_sensors_data():
    """使用sensors命令获取温度数据"""
    try:
        result = subprocess.run(['sensors', '-A', '-j'], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logger.error(f"Failed to get sensors data: {e}")
        return None

def parse_temperature_data(sensors_data):
    """解析sensors输出的温度数据"""
    temperatures = []
    
    if not sensors_data:
        return temperatures
    
    for chip_name, chip_data in sensors_data.items():
        if not isinstance(chip_data, dict):
            continue
            
        for sensor_name, sensor_data in chip_data.items():
            # 跳过适配器信息
            if sensor_name == "Adapter":
                continue
                
            if isinstance(sensor_data, dict):
                # 查找所有以_input结尾的温度值
                for key, value in sensor_data.items():
                    if key.endswith('_input') and isinstance(value, (int, float)):
                        # 使用更清晰的命名
                        if 'temp' in key or 'temp' in sensor_name.lower() or any(x in sensor_name.lower() for x in ['tctl', 'tccd', 'composite']):
                            full_sensor_name = f"{chip_name}_{sensor_name}_{key.replace('_input', '')}"
                            temperatures.append({
                                'sensor_name': full_sensor_name,
                                'temperature': value,
                                'unit': 'C'
                            })
    
    return temperatures

def get_thermal_zone_data():
    """从/sys/class/thermal获取温度数据"""
    temperatures = []
    
    try:
        result = subprocess.run(['find', '/sys/class/thermal', '-name', 'temp', '-type', 'f'], 
                              capture_output=True, text=True, check=True)
        
        for temp_file in result.stdout.strip().split('\n'):
            if temp_file:
                try:
                    with open(temp_file, 'r') as f:
                        temp_millicelsius = int(f.read().strip())
                        temp_celsius = temp_millicelsius / 1000.0
                        
                    zone_name = temp_file.split('/')[-2]  # thermal_zone0, etc.
                    temperatures.append({
                        'sensor_name': f"thermal_{zone_name}",
                        'temperature': temp_celsius,
                        'unit': 'C'
                    })
                except (IOError, ValueError) as e:
                    logger.warning(f"Could not read {temp_file}: {e}")
                    
    except subprocess.CalledProcessError:
        logger.warning("Could not find thermal zone files")
    
    return temperatures

def save_temperature_data(temperatures):
    """保存温度数据到数据库"""
    if not temperatures:
        logger.warning("No temperature data to save")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for temp_data in temperatures:
            cursor.execute('''
                INSERT INTO temperature_readings (timestamp, sensor_name, temperature, unit)
                VALUES (datetime('now', 'localtime'), ?, ?, ?)
            ''', (temp_data['sensor_name'], temp_data['temperature'], temp_data['unit']))
        
        conn.commit()
        conn.close()
        logger.info(f"Saved {len(temperatures)} temperature readings")
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")

def get_gpu_temperature():
    """获取NVIDIA GPU温度"""
    temperatures = []
    
    try:
        # NVIDIA GPU
        result = subprocess.run(['nvidia-smi', '--query-gpu=temperature.gpu', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, check=True)
        gpu_temps = result.stdout.strip().split('\n')
        
        for i, temp_str in enumerate(gpu_temps):
            if temp_str.strip():
                try:
                    temp = float(temp_str.strip())
                    temperatures.append({
                        'sensor_name': f"nvidia_gpu_{i}",
                        'temperature': temp,
                        'unit': 'C'
                    })
                except ValueError:
                    continue
                    
    except (subprocess.CalledProcessError, FileNotFoundError):
        # nvidia-smi不可用或无NVIDIA GPU
        pass
    
    try:
        # AMD GPU (如果存在)
        result = subprocess.run(['sensors'], capture_output=True, text=True, check=True)
        lines = result.stdout.split('\n')
        
        for line in lines:
            if 'amdgpu' in line.lower() and '°C' in line:
                # 解析AMD GPU温度行
                temp_match = re.search(r'(\d+\.?\d*)\s*°C', line)
                if temp_match:
                    temp = float(temp_match.group(1))
                    temperatures.append({
                        'sensor_name': "amd_gpu",
                        'temperature': temp,
                        'unit': 'C'
                    })
                    
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    return temperatures

def collect_temperatures():
    """主函数：收集所有温度数据"""
    all_temperatures = []
    
    # 从sensors获取数据
    sensors_data = get_sensors_data()
    sensors_temps = parse_temperature_data(sensors_data)
    all_temperatures.extend(sensors_temps)
    
    # 从thermal zones获取数据
    thermal_temps = get_thermal_zone_data()
    all_temperatures.extend(thermal_temps)
    
    # 获取GPU温度
    gpu_temps = get_gpu_temperature()
    all_temperatures.extend(gpu_temps)
    
    # 去重（相同传感器名称只保留一个）
    seen_sensors = set()
    unique_temperatures = []
    for temp in all_temperatures:
        if temp['sensor_name'] not in seen_sensors:
            seen_sensors.add(temp['sensor_name'])
            unique_temperatures.append(temp)
    
    logger.info(f"Collected {len(unique_temperatures)} unique temperature readings")
    for temp in unique_temperatures:
        logger.info(f"{temp['sensor_name']}: {temp['temperature']:.1f}°{temp['unit']}")
    
    # 检查温度告警
    check_temperature_alerts(unique_temperatures)
    
    save_temperature_data(unique_temperatures)

if __name__ == "__main__":
    collect_temperatures()