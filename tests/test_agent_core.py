# ~/benchmaster/tests/test_agent_core.py

import sys
import os
import time
import unittest
from datetime import datetime

from PyQt6.QtCore import QCoreApplication

# Add benchmaster to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_tool_ui import HardwareScanner, AgentCore

class TestAgentCore(unittest.TestCase):
    def test_hardware_scanner(self):
        print("\n[Testing HardwareScanner...]")
        info = HardwareScanner.get_system_info()
        print(f"Detected Info: {info}")
        self.assertIn('OS', info)
        self.assertIn('CPU', info)
        self.assertIn('RAM', info)
        print("✅ HardwareScanner: SUCCESS")

    def test_worker_logic(self):
        print("\n[Testing AgentCore Threading...]")
        app = QCoreApplication(sys.argv)
        
        # Create worker with dummy params
        worker = AgentCore("http://localhost:8000", "fake_token")
        finished_event = False
        scanned_info = {}

        def on_hw_scanned(info):
            nonlocal finished_event, scanned_info
            scanned_info = info
            finished_event = True

        def on_status_change(status, msg):
            print(f"  [Worker Status]: {status} - {msg}")

        worker.hardware_scanned.connect(on_hw_scanned)
        worker.status_updated.connect(on_status_change)
        
        # START THE WORKER
        worker.start()
        
        # Wait for the scan to complete or timeout
        start_time = time.time()
        while not finished_event and (time.time() - start_time < 20):
            app.processEvents()
            time.sleep(0.1)

        # Clean up
        worker.stop()
        app.processEvents()
        time.sleep(1)

        # Assertions
        self.assertTrue(finished_event, "Worker failed to complete hardware scan within timeout!")
        self.assertIn('CPU', scanned_info)
        print("✅ AgentCore: SUCCESS")
        app.exit()

if __name__ == "__main__":
    unittest.main()
