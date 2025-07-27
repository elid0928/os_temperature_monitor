#!/usr/bin/env python3
import sqlite3
import os

DB_PATH = 'temperature_monitor.db'

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS temperature_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            sensor_name TEXT NOT NULL,
            temperature REAL NOT NULL,
            unit TEXT DEFAULT 'C'
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON temperature_readings(timestamp)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_sensor_name ON temperature_readings(sensor_name)
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized: {os.path.abspath(DB_PATH)}")

if __name__ == "__main__":
    init_database()