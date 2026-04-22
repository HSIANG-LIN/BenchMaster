import sys
import os
import time
import json
import subprocess
import platform
import requests
import re
from datetime import datetime

# =================================================================
# 1. 自動化依賴安裝 (Self-Installing Dependencies)
# =================================================================
def install_dependencies():
    required = ['requests', 'paho-mqtt', 'psutil']
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            print(f"[*] Installing missing dependency: {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

install_dependencies()
import psutil
import paho.mqtt.client as mqtt

# =================================================================
# 2. 內建解析器 (Embedded Parser - For Self-Containment)
# =================================================================
class ThreeDMarkParser:
    """解析 3DMark 產生的 Log 或 XML 內容"""
    @staticmethod
    def parse(content: str):
        metrics = {}
        patterns = {
            "graphics_score": r"Graphics\s+score:\s*([\d\.]+)",
            "cpu_score": r"CPU\s+score:\s*([\d\.]+)",
            "total_score": r"Total\s+score:\s*([\d\.]+)"
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    metrics[key] = float(match.group(1))
                except ValueError:
                    pass
        return metrics

# =================================================================
# 3. 核心執行引擎 (Core Execution Engine)
# =================================================================
class BenchAutoRunner:
    def __init__(self, config):
        self.config = config
        self.controller_url = config['url'].rstrip('/')
        self.auth_token = config['token']
        self.machine_id = config['machine_id']
        self.benchmark_name = "threedmark"
        self.exe_path = config['exe_path']

    def run(self, mode="real"):
        if mode == "mock":
            self._run_mock()
        else:
            self._run_real()

    def _run_mock(self):
        print("\n[MODE] Running in MOCK mode (Simulating 3DMark...)")
        time.sleep(2) 
        mock_log = """
        [3DMark Time Spy]
        -------------------------
        Graphics score: 15432.8
        CPU score: 9210.4
        Total score: 12345.6
        -------------------------
        """
        print(f"Simulated Log:\n{mock_log}")
        self._report_results(ThreeDMarkParser().parse(mock_log))

    def _run_real(self):
        print(f"\n[MODE] Running in REAL mode (Executing: {self.exe_path})")
        if not os.path.exists(self.exe_path):
            print(f"❌ Error: Cannot find 3DMark at {self.exe_path}")
            return
        try:
            print("Executing benchmark... Please wait (this may take minutes).")
            process = subprocess.Popen(
                [self.exe_path, "--run", "Time Spy"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                shell=True
            )
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                print(f"❌ Benchmark failed: {stderr}")
                return
            print("Benchmark finished. Parsing results...")
            metrics = ThreeDMarkParser().parse(stdout)
            if not metrics:
                print("❌ Parsing failed: No scores found in output.")
                return
            self._report_results(metrics)
        except Exception as e:
            print(f"❌ Error during execution: {str(e)}")

    def _report_results(self, metrics):
        print(f"Reporting results: {metrics}")
        payload = {
            "job_id": 1, 
            "machine_id": self.machine_id,
            "benchmark": self.benchmark_name,
            "scores_json": metrics,
            "system_snapshot_json": {
                "cpu": platform.processor(),
                "gpu": "Detected via HardwareScanner", 
                "ram": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB"
            },
            "pass_fail": "PASS"
        }
        headers = {"X-Agent-Token": self.auth_token}
        try:
            resp = requests.post(f"{self.controller_url}/results/", json=payload, headers=headers)
            if resp.status_code in [200, 201]:
                print("✅ Success! Results sent to server.")
            else:
                print(f"❌ Failed to report: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"❌ Reporting error: {str(e)}")

def main():
    print("==========================================")
    print("   BenchMaster 3DMark Auto-Runner Tool    ")
    print("==========================================")
    url = input("Enter Controller URL (e.g. http://192.168.1.100:8000): ").strip()
    token = input("Enter Agent Security Token: ").strip()
    m_id = input("Enter Machine ID (e.g. 1): ").strip()
    exe = input("Enter 3DMark EXE Path (or press Enter to skip): ").strip()
    print("\n1. [REAL] Run actual 3DMark\n2. [MOCK] Run simulated 3DMark")
    choice = input("Select mode (1/2): ").strip()
    runner = BenchAutoRunner({"url":url, "token":token, "machine_id":int(m_id), "exe_path":exe})
    runner.run(mode="real" if choice=="1" else "mock")

if __name__ == "__main__":
    main()
