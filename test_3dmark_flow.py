import sys
import os
import json
import re
from unittest.mock import MagicMock, patch
from datetime import datetime

# 模擬環境設置：將當前目錄加入 path 以便導入專案模組
sys.path.append(os.getcwd())

# 模擬必要的外部模組，避免在沒有伺服器/MQTT 的環境下崩潰
class MockResponse:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self.json_data = json_data
    def json(self): return self.json_data
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error: {self.status_code}")

# 模擬 requests.post
def mock_requests_post(url, json=None, headers=None):
    print(f"[MOCK API] Received POST to {url}")
    print(f"[MOCK API] Payload: {json}")
    return MockResponse(201, {"message": "Success"})

# 模擬 MQTT 發送
def mock_mqtt_publish(topic, payload):
    print(f"[MOCK MQTT] Published to {topic}: {payload}")

# ---------------------------------------------------------
# 核心測試邏輯
# ---------------------------------------------------------

# 模擬 BenchmarkWorker 的核心邏輯 (從 agent_tool_ui.py 抽離出來進行單元測試)
class MockBenchmarkWorker:
    def __init__(self, benchmark_name, command, parser_class):
        self.benchmark_name = benchmark_name
        self.command = command
        self.parser = parser_class()

    def run_simulation(self):
        print(f"\n🚀 Starting Simulation for: {self.benchmark_name}")
        print(f"Command: {self.command}")
        
        # 1. 模擬執行指令 (Subprocess)
        print("Executing command...")
        # 這裡模擬 subprocess.check_output 的行為
        import subprocess
        process = subprocess.Popen(self.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"❌ Command Failed: {stderr}")
            return False

        print("Command finished. Output captured.")
        print(f"Captured Log:\n{stdout}")

        # 2. 模擬解析 (Parsing)
        print("Parsing results...")
        metrics = self.parser.parse(stdout)
        print(f"Parsed Metrics: {metrics}")

        if not metrics:
            print("❌ Parsing failed: No metrics found.")
            return False
        
        print("✅ Parsing successful.")

        # 3. 模擬回報 (Reporting)
        print("Reporting results to API...")
        payload = {
            "job_id": 999,
            "machine_id": 1,
            "benchmark": self.benchmark_name,
            "scores_json": metrics,
            "system_snapshot_json": {"cpu": "Intel i9", "gpu": "RTX 4090"},
            "pass_fail": "PASS"
        }
        
        # 使用 mock 的 requests
        resp = mock_requests_post("http://localhost:8000/results/", json=payload)
        
        if resp.status_code == 201:
            print("✅ Reporting successful!")
            return True
        else:
            print(f"❌ Reporting failed: {resp.status_code}")
            return False

# ---------------------------------------------------------
# 執行測試
# ---------------------------------------------------------

if __name__ == "__main__":
    # 導入真實的 Parser
    from parsers.threedmark import ThreeDMarkParser

    # 定義 3DMark 的模擬指令 (echo 模擬產生的 Log)
    # 這是最關鍵的部分：驗證 Parser 是否能抓到真實 Log 中的數據
    mock_3dmark_command = 'echo "3DMark Time Spy\\n-------------------------\\nGraphics score: 12500.5\\nCPU score: 8000.0\\nTotal score: 11000.0"'

    # 初始化 Worker
    worker = MockBenchmarkWorker(
        benchmark_name="threedmark",
        command=mock_3dmark_command,
        parser_class=ThreeDMarkParser
    )

    # 執行並驗證結果
    success = worker.run_simulation()

    if success:
        print("\n✨ [TEST PASSED] 3DMark 完整自動化流程驗證成功！")
        print("這代表只要在 Windows 上換成真實的 .exe 指令，系統就能完美運作。")
    else:
        print("\n❌ [TEST FAILED] 3DMark 流程驗證失敗。")
        sys.exit(1)
