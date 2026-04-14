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
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTextEdit, QLineEdit, QFormLayout, 
    QGroupBox, QProgressBar, QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("AgentTool")

# Constants for UDP Discovery
DISCOVERY_PORT = 55555
DISCOVERY_MSG_REQ = b"BENCHMASTER_DISCOVER_REQ"
DISCOVERY_MSG_RES_PREFIX = b"BENCHMASTER_DISCOVER_RES:"

class HardwareScanner:
    """
    Handles automatic hardware discovery. 
    Environment-aware: uses wmic on Windows, and platform/proc on Linux/WSL.
    """
    @staticmethod
    def get_system_info():
        info = {}
        try:
            info['OS'] = f"{platform.system()} {platform.release()} ({platform.version()})"
            info['Hostname'] = platform.node()
            
            if platform.system() == "Windows":
                try:
                    cpu_cmd = "wmic cpu get name"
                    info['CPU'] = subprocess.check_output(cpu_cmd, shell=True).decode().split('\n')[1].strip()
                    gpu_cmd = "wmic path win32_VideoController get name"
                    info['GPU'] = subprocess.check_output(gpu_cmd, shell=True).decode().split('\n')[1].strip()
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

class UDPDiscoveryWorker(QThread):
    """
    Scans the local network for the BenchMaster Controller using UDP broadcast.
    """
    discovered = pyqtSignal(str)  # Emits the IP address of the controller
    finished = pyqtSignal()

    def __init__(self, timeout=5):
        super().__init__()
        self.timeout = timeout
        self.is_running = True

    def run(self):
        logger.info("Starting UDP Discovery...")
        
        # 1. Start a listener thread to wait for the response
        listener_thread = threading.Thread(target=self._listen_for_response)
        listener_thread.daemon = True
        listener_thread.start()

        # 2. Broadcast the discovery request
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.settimeout(self.timeout)
                sock.sendto(DISCOVERY_MSG_REQ, ('<broadcast>', DISCOVERY_PORT))
                logger.info("Broadcasted discovery request.")
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")

        # Wait for discovery signal or timeout
        start_time = time.time()
        while self.is_running and (time.time() - start_time < self.timeout):
            if hasattr(self, '_found_ip'):
                self.discovered.emit(self._found_ip)
                break
            time.sleep(0.5)
        
        self.finished.emit()
        logger.info("Discovery process ended.")

    def _listen_for_response(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(('', DISCOVERY_PORT))
                sock.settimeout(self.timeout + 2)
                while self.is_running:
                    data, addr = sock.recvfrom(1024)
                    if data.startswith(DISCOVERY_MSG_RES_PREFIX):
                        ip_addr = data.decode().split(':')[1]
                        self._found_ip = ip_addr
                        logger.info(f"Controller found at {ip_addr}")
                        break
        except Exception as e:
            logger.error(f"Listener error: {e}")

    def stop(self):
        self.is_running = False

class AgentCore(QThread):
    """
    Background worker for heartbeat, polling, and task execution.
    """
    status_updated = pyqtSignal(str, str)  # status, message
    log_signal = pyqtSignal(str)
    hardware_scanned = pyqtSignal(dict)
    task_received = pyqtSignal(dict)

    def __init__(self, controller_url, auth_token):
        super().__init__()
        self.controller_url = controller_url.rstrip('/')
        self.auth_token = auth_token
        self.is_running = True
        self.is_online = False
        self.machine_id = None
        self.hostname = platform.node()

    def run(self):
        self.log_signal.emit("Agent Core Started.")
        self.log_signal.emit(f"Target Controller: {self.controller_url}")
        
        # 1. Auto-Hardware Scan
        self.log_signal.emit("Scanning hardware...")
        hw_info = HardwareScanner.get_system_info()
        self.hardware_scanned.emit(hw_info)
        
        # 2. Connection/Heartbeat Loop
        while self.is_running:
            if not self.is_online:
                self._attempt_connection(hw_info)
            else:
                self._perform_heartbeat()
                self._poll_tasks()
            
            time.sleep(10)

    def _attempt_connection(self, hw_info):
        self.log_signal.emit("Attempting to connect to controller...")
        headers = {"X-Agent-Token": self.auth_token}
        
        try:
            resp = requests.post(
                f"{self.controller_url}/machines/", 
                json={
                    "hostname": self.hostname,
                    "ip": "127.0.0.1", 
                    "cpu": hw_info.get('CPU'),
                    "gpu": hw_info.get('GPU'),
                    "ram": hw_info.get('RAM'),
                    "os": hw_info.get('OS')
                },
                headers=headers,
                timeout=5
            )
            
            if resp.status_code in [200, 201]:
                machine_data = resp.json()
                self.machine_id = machine_data['id']
                self.is_online = True
                self.status_updated.emit("Online", f"Connected as Machine ID: {self.machine_id}")
                self.log_signal.emit(f"Successfully registered! ID: {self.machine_id}")
            else:
                self.status_updated.emit("Offline", f"Connection failed: {resp.status_code}")
                self.log_signal.emit(f"Failed to register: {resp.text}")
                time.sleep(15)
        except Exception as e:
            self.is_online = False
            self.status_updated.emit("Offline", "Controller unreachable")
            self.log_signal.emit(f"Connection error: {str(e)}")
            time.sleep(10)

    def _perform_heartbeat(self):
        headers = {"X-Agent-Token": self.auth_token}
        try:
            resp = requests.get(f"{self.controller_url}/api/health", headers=headers, timeout=5)
            if resp.status_code == 200:
                self.status_updated.emit("Online", f"Connected (Last heartbeat: {datetime.now().strftime('%H:%M:%S')})")
            else:
                self.is_online = False
                self.status_updated.emit("Offline", "Lost connection to controller")
        except:
            self.is_online = False
            self.status_updated.emit("Offline", "Connection lost")

    def _poll_tasks(self):
        headers = {"X-Agent-Token": self.auth_token}
        try:
            resp = requests.get(f"{self.controller_url}/jobs/", headers=headers, timeout=5)
            if resp.status_code == 200:
                jobs = resp.json()
                for job in jobs:
                    if job['status'] == 'PENDING' and job['machine_id'] == self.machine_id:
                        self.log_signal.emit(f"New task received: {job['benchmark']} (ID: {job['id']})")
                        self.task_received.emit(job)
        except Exception as e:
            self.log_signal.emit(f"Polling error: {str(e)}")

    def stop(self):
        self.is_running = False

class AgentMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BenchMaster Agent Lite")
        self.resize(800, 600)
        self.setup_ui()
        self.apply_styles()
        
        self.core = None
        self.discovery_worker = None

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)

        # --- Header ---
        header_layout = QHBoxLayout()
        self.status_label = QLabel("Status: Standby")
        self.status_label.setObjectName("status_label")
        header_layout.addWidget(self.status_label)
        
        self.title_label = QLabel("BenchMaster Agent")
        self.title_label.setObjectName("title_label")
        header_layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignRight)
        self.main_layout.addLayout(header_layout)

        # --- Main Content (Stacked Widget) ---
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        # Page 1: Dashboard
        self.dash_page = QWidget()
        self.setup_dashboard_page()
        self.stack.addWidget(self.dash_page)

        # Page 2: Settings
        self.settings_page = QWidget()
        self.setup_settings_page()
        self.stack.addWidget(self.settings_page)

        # --- Bottom Log Area ---
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("log_output")
        self.log_output.setMaximumHeight(150)
        self.main_layout.addWidget(self.log_output)

        # --- Navigation ---
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
        
        # Hardware Card
        hw_group = QGroupBox("System Information")
        hw_layout = QFormLayout()
        self.hw_labels = {
            'OS': QLabel("-"),
            'Hostname': QLabel("-"),
            'CPU': QLabel("-"),
            'GPU': QLabel("-"),
            'RAM': QLabel("-")
        }
        for key, label in self.hw_labels.items():
            hw_layout.addRow(f"{key}:", label)
        hw_group.setLayout(hw_layout)
        layout.addWidget(hw_group)

        # Task Status Card
        task_group = QGroupBox("Current Task")
        task_layout = QVBoxLayout()
        self.task_label = QLabel("No active task")
        self.task_label.setObjectName("task_label")
        self.task_progress = QProgressBar()
        task_layout.addWidget(self.task_label)
        task_layout.addWidget(self.task_progress)
        task_group.setLayout(task_layout)
        layout.addWidget(task_group)
        layout.addStretch()

    def setup_settings_page(self):
        layout = QFormLayout(self.settings_page)
        
        self.url_input = QLineEdit("http://localhost:8000")
        self.token_input = QLineEdit("BM-AGENT-DEFAULT-SECRET-2026")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.btn_start = QPushButton("Start Agent")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self.toggle_agent)
        
        layout.addRow("Controller URL:", self.url_input)
        layout.addRow("Security Token:", self.token_input)
        layout.addRow("", self.btn_start)
        layout.addStretch()

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
        if status == "Online":
            self.status_label.setStyleSheet("color: #a6e3a1;")
        elif status == "Offline":
            self.status_label.setStyleSheet("color: #f38ba8;")
        elif status == "Searching":
            self.status_label.setStyleSheet("color: #fab387;")
        else:
            self.status_label.setStyleSheet("color: #cdd6f4;")
        self.log(message)

    def update_hw_display(self, info):
        for key, val in info.items():
            if key in self.hw_labels:
                self.hw_labels[key].setText(str(val))

    def toggle_agent(self):
        if self.core and self.core.isRunning():
            self.stop_agent()
        else:
            self.start_agent()

    def start_agent(self):
        url = self.url_input.text()
        token = self.token_input.text()
        
        # 1. Start Discovery
        self.update_status("Searching", "Searching for Controller on local network...")
        self.discovery_worker = UDPDiscoveryWorker()
        self.discovery_worker.discovered.connect(self.on_controller_found)
        self.discovery_worker.finished.connect(self.on_discovery_finished)
        self.discovery_worker.start()
        
        self.btn_start.setText("Stop Agent")
        self.btn_start.setStyleSheet("background-color: #f38ba8; color: #11111b;")

    def on_controller_found(self, ip_addr):
        self.log(f"Found Controller at {ip_addr}!")
        new_url = f"http://{ip_addr}:8000"
        self.url_input.setText(new_url)
        self.discovery_worker.stop()
        # Automatically start the core after finding the controller
        self.start_core_engine(new_url)

    def on_discovery_finished(self):
        if not hasattr(self, '_is_discovering') or not self._is_discovering:
            # If discovery ended without finding anything, fallback to manual URL
            if self.core is None or not self.core.isRunning():
                self.update_status("Offline", "No controller found via broadcast. Use manual URL.")

    def start_core_engine(self, url):
        token = self.token_input.text()
        self.core = AgentCore(url, token)
        self.core.status_updated.connect(self.update_status)
        self.core.log_signal.connect(self.log)
        self.core.hardware_scanned.connect(self.update_hw_display)
        self.core.task_received.connect(self.on_task_received)
        self.core.start()

    def stop_agent(self):
        if self.core:
            self.core.stop()
        if self.discovery_worker:
            self.discovery_worker.stop()
        self.btn_start.setText("Start Agent")
        self.btn_start.setStyleSheet("")
        self.update_status("Offline", "Agent stopped.")

    def on_task_received(self, job):
        self.task_label.setText(f"Running: {job['benchmark']} (ID: {job['id']})")
        self.task_progress.setRange(0, 100)
        self.task_progress.setValue(20)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AgentMainWindow()
    window.show()
    sys.exit(app.exec())
