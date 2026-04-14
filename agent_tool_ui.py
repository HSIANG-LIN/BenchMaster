# ~/benchmaster/agent_tool_ui.py

import sys
import os
import time
import socket
import threading
import platform
import subprocess
import psutil
import requests
import json
import logging
from datetime import datetime

import paho.mqtt.client as mqtt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTextEdit, QLineEdit, QFormLayout, 
    QGroupBox, QProgressBar, QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("AgentTool")

# Default MQTT Broker (Publicly accessible for testing)
DEFAULT_MQTT_BROKER = "broker.emqx.io"
DEFAULT_MQTT_PORT = 1883

class HardwareScanner:
    @staticmethod
    def get_system_info():
        info = {}
        try:
            info['OS'] = f"{platform.system()} {platform.release()} ({platform.version()})"
            info['Hostname'] = platform.node()
            if platform.system() == "Windows":
                try:
                    cpu_cmd = "wmic cpu get name"
                    info['CPU'] = subprocess.check_output(cpu_cmd, shell=True).decode().split('\\n')[1].strip()
                    gpu_cmd = "wmic path win32_VideoController get name"
                    info['GPU'] = subprocess.check_output(gpu_cmd, shell=True).decode().split('\\n')[1].strip()
                except:
                    info['CPU'] = "Unknown Windows CPU"
                    info['GPU'] = "Unknown Windows GPU"
            else:
                try:
                    info['CPU'] = platform.processor() or "Unknown Linux CPU"
                    info['GPU'] = "Generic Linux GPU (wmic unavailable)"
                except:
                    info['CPU'] = "Unknown Linux CPU"
                    info['GPU'] = "Unknown Linux GPU"
            ram_gb = psutil.virtual_memory().total / (1024**3)
            info['RAM'] = f"{ram_gb:.2f} GB"
        except Exception as e:
            info['Error'] = f"Scan failed: {str(e)}"
        return info

class AgentCore(QThread):
    """
    Hybrid Communication Agent Core.
    Uses MQTT for real-time control & status, and REST for heavy data.
    """
    status_updated = pyqtSignal(str, str)
    log_signal = pyqtSignal(str)
    hardware_scanned = pyqtSignal(dict)
    task_received = pyqtSignal(dict)

    def __init__(self, controller_url, auth_token, mqtt_broker=DEFAULT_MQTT_BROKER):
        super().__init__()
        self.controller_url = controller_url.rstrip('/')
        self.auth_token = auth_token
        self.mqtt_broker = mqtt_broker
        self.is_running = True
        self.is_online = False
        self.machine_id = None
        self.hostname = platform.node()
        
        # MQTT Client setup
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect

    def run(self):
        self.log_signal.emit("Agent Core Started.")
        self.log_signal.emit(f"Target Controller: {self.controller_url}")
        self.log_signal.emit(f"MQTT Broker: {self.mqtt_broker}")
        
        # 1. Hardware Scan
        hw_info = HardwareScanner.get_system_info()
        self.hardware_scanned.emit(hw_info)

        # 2. Register via REST
        self._register_machine(hw_info)

        # 3. Start MQTT Connection
        try:
            self.mqtt_client.connect(self.mqtt_broker, DEFAULT_MQTT_PORT, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            self.log_signal.emit(f"MQTT Connection failed: {str(e)}")
            self.status_updated.emit("Offline", "MQTT Connection failed")

        # 4. Main Loop (Heartbeat & Monitoring)
        while self.is_running:
            if self.is_online:
                self._send_mqtt_heartbeat()
            else:
                # If offline, attempt to re-register/re-connect
                self._attempt_reconnect(hw_info)
            time.sleep(20) # Heartbeat every 20s

    def _register_machine(self, hw_info):
        headers = {"X-Agent-Token": self.auth_token}
        try:
            resp = requests.post(f"{self.controller_url}/machines/", json={
                "hostname": self.hostname, "ip": "127.0.0.1", "cpu": hw_info.get('CPU'),
                "gpu": hw_info.get('GPU'), "ram": hw_info.get('RAM'), "os": hw_info.get('OS')
            }, headers=headers, timeout=5)
            if resp.status_code in [200, 201]:
                machine_data = resp.json()
                self.machine_id = machine_data['id']
                self.is_online = True
                self.status_updated.emit("Online", f"Registered! ID: {self.machine_id}")
                self.log_signal.emit(f"Successfully registered! ID: {self.machine_id}")
            else:
                self.log_signal.emit(f"Registration failed: {resp.text}")
        except Exception as e:
            self.log_signal.emit(f"Registration error: {str(e)}")

    def _attempt_reconnect(self, hw_info):
        self.log_signal.emit("Attempting to reconnect...")
        self._register_machine(hw_info)

    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.log_signal.emit("MQTT Connected Successfully.")
            if self.machine_id:
                topic = f"benchmaster/agent/{self.machine_id}/tasks"
                self.mqtt_client.subscribe(topic)
                self.log_signal.emit(f"Subscribed to: {topic}")
        else:
            self.log_signal.emit(f"MQTT Connection failed with code {rc}")

    def _on_mqtt_disconnect(self, client, userdata, rc, properties=None):
        self.is_online = False
        self.status_updated.emit("Offline", "MQTT Disconnected")
        self.log_signal.emit("MQTT Disconnected.")

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            self.log_signal.emit(f"MQTT Task Received: {payload.get('benchmark')}")
            self.task_received.emit(payload)
        except Exception as e:
            self.log_signal.emit(f"MQTT Message Error: {str(e)}")

    def _send_mqtt_heartbeat(self):
        if not self.machine_id: return
        try:
            status_payload = {
                "machine_id": self.machine_id,
                "status": "ONLINE",
                "timestamp": datetime.now().isoformat()
            }
            topic = f"benchmaster/agent/{self.machine_id}/status"
            self.mqtt_client.publish(topic, json.dumps(status_payload), qos=1)
        except Exception as e:
            self.log_signal.emit(f"MQTT Heartbeat Error: {str(e)}")

    def stop(self):
        self.is_running = False
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()

class AgentMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BenchMaster Agent Lite (MQTT Edition)")
        self.resize(800, 600)
        self.setup_ui()
        self.apply_styles()
        self.core = None

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        header_layout = QHBoxLayout()
        self.status_label = QLabel("Status: Standby")
        self.status_label.setObjectName("status_label")
        header_layout.addWidget(self.status_label)
        self.title_label = QLabel("BenchMaster Agent")
        self.title_label.setObjectName("title_label")
        header_layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignRight)
        self.main_layout.addLayout(header_layout)
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)
        self.dash_page = QWidget()
        self.setup_dashboard_page()
        self.stack.addWidget(self.dash_page)
        self.settings_page = QWidget()
        self.setup_settings_page()
        self.stack.addWidget(self.settings_page)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("log_output")
        self.log_output.setMaximumHeight(150)
        self.main_layout.addWidget(self.log_output)
        nav_layout = QHBoxLayout()
        self.btn_dash = QPushButton("Dashboard")
        self.btn_dash.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_settings = QPushButton("Settings")
        self.btn_settings.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        nav_layout.addWidget(self.btn_dash)
        nav_layout.addWidget(self.btn_settings)
        self.main_layout.addLayout(nav_layout)

    def setup_dashboard_page(self):
        layout = QVBoxLayout(self.dash_page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        hw_group = QGroupBox("System Information")
        hw_layout = QFormLayout()
        hw_layout.setContentsMargins(15, 15, 15, 15)
        hw_layout.setVerticalSpacing(10)
        self.hw_labels = {'OS': QLabel("-"), 'Hostname': QLabel("-"), 'CPU': QLabel("-"), 'GPU': QLabel("-"), 'RAM': QLabel("-")}
        for key, label in self.hw_labels.items(): hw_layout.addRow(f"{key}:", label)
        hw_group.setLayout(hw_layout)
        layout.addWidget(hw_group)
        task_group = QGroupBox("Current Task")
        task_layout = QVBoxLayout()
        task_layout.setContentsMargins(15, 15, 15, 15)
        task_layout.setSpacing(15)
        self.task_label = QLabel("No active task")
        self.task_label.setObjectName("task_label")
        self.task_progress = QProgressBar()
        task_layout.addWidget(self.task_label)
        task_layout.addWidget(self.task_progress)
        task_group.setLayout(task_layout)
        layout.addWidget(task_group)
        layout.addStretch()

    def setup_settings_page(self):
        main_settings_layout = QVBoxLayout(self.settings_page)
        main_settings_layout.setContentsMargins(20, 20, 20, 20)
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setVerticalSpacing(15)
        self.url_input = QLineEdit("http://localhost:8000")
        self.token_input = QLineEdit("BM-AGENT-DEFAULT-SECRET-2026")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.mqtt_input = QLineEdit("broker.emqx.io")
        self.btn_start = QPushButton("Start Agent")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self.toggle_agent)
        form_layout.addRow("Controller URL:", self.url_input)
        form_layout.addRow("Security Token:", self.token_input)
        form_layout.addRow("MQTT Broker:", self.mqtt_input)
        form_layout.addRow("", self.btn_start)
        main_settings_layout.addLayout(form_layout)
        main_settings_layout.addStretch()

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e2e; }
            QWidget { color: #cdd6f4; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
            QLabel#title_label { font-size: 24px; font-weight: bold; color: #89b4fa; }
            QLabel#status_label { font-weight: bold; }
            QGroupBox { border: 2px solid #45475a; border-radius: 8px; margin-top: 10px; font-weight: bold; }
            QTextEdit#log_output { background-color: #11111b; color: #a6adc8; font-family: 'Consolas', monospace; border: none; }
            QPushButton { background-color: #45475a; border-radius: 5px; padding: 8px; min-width: 80px; }
            QPushButton:hover { background-color: #585b70; }
            QPushButton#btn_start { background-color: #a6e3a1; color: #11111b; font-weight: bold; }
            QPushButton#btn_start:hover { background-color: #94e2d5; }
            QLineEdit { background-color: #313244; border: 1px solid #45475a; padding: 5px; border-radius: 4px; color: #cdd6f4; }
            QProgressBar { border: 1px solid #45475a; border-radius: 5px; text-align: center; }
            QProgressBar::chunk { background-color: #89b4fa; }
        """)

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")

    def update_status(self, status, message):
        self.status_label.setText(f"Status: {status}")
        if status == "Online": self.status_label.setStyleSheet("color: #a6e3a1;")
        elif status == "Offline": self.status_label.setStyleSheet("color: #f38ba8;")
        else: self.status_label.setStyleSheet("color: #fab387;")
        self.log(message)

    def update_hw_display(self, info):
        for key, val in info.items():
            if key in self.hw_labels: self.hw_labels[key].setText(str(val))

    def toggle_agent(self):
        if self.core and self.core.isRunning():
            self.stop_agent()
        else:
            self.start_agent()

    def start_agent(self):
        url = self.url_input.text()
        token = self.token_input.text()
        mqtt_broker = self.mqtt_input.text()
        self.core = AgentCore(url, token, mqtt_broker)
        self.core.status_updated.connect(self.update_status)
        self.core.log_signal.connect(self.log)
        self.core.hardware_scanned.connect(self.update_hw_display)
        self.core.task_received.connect(self.on_task_received)
        self.core.start()
        self.btn_start.setText("Stop Agent")
        self.btn_start.setStyleSheet("background-color: #f38ba8; color: #11111b;")

    def stop_agent(self):
        if self.core: self.core.stop()
        self.btn_start.setText("Start Agent")
        self.btn_start.setStyleSheet("")
        self.update_status("Offline", "Agent stopped by user.")

    def on_task_received(self, job):
        self.task_label.setText(f"Running: {job['benchmark']} (ID: {job['id']})")
        self.task_progress.setRange(0, 100)
        self.task_progress.setValue(20)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AgentMainWindow()
    window.show()
    sys.exit(app.exec())
