# ~/benchmaster/tests/test_agent_core.py

import sys
import os
import time
import unittest
from datetime import datetime

# Add benchmaster to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_tool_ui import HardwareScanner, ScannerWorker
from PyQt6.QtCore import QCoreApplication

class TestAgentCore(unittest.TestCase):
    def test_hardware_scanner(self):
        print("\n[Testing HardwareScanner...]")
        info = HardwareScanner.get_system_info()
        print(f"Detected Info: {info}")
        
        self.assertIn('OS', info)
        self.assertIn('CPU', info)
        self.assertIn('RAM', info)
        self.assertIn('GPU', info)
        print("✅ HardwareScanner: SUCCESS")

    def test_worker_logic(self):
        print("\n[Testing ScannerWorker Threading...]")
        # We need a QCoreApplication to handle QThread/Signals without a GUI
        app = QCoreApplication(sys.argv)
        
        worker = ScannerWorker()
        results = {}
        finished_event = False

        def on_finished(info):
            nonlocal results, finished_event
            results = info
            finished_event = True

        def on_progress(msg):
            print(f"  [Worker Progress]: {msg}")

        worker.finished.connect(on_finished)
        worker.progress.connect(on_progress)
        
        worker.start()
        
        # Wait for worker to finish (with timeout)
        start_time = time.time()
        while not finished_event and (time.time() - start_time < 10):
            time.sleep(0.1)
            app.processEvents() # Keep the event loop running

        self.assertTrue(finished_event, "Worker timed out!")
        self.assertIsNotNone(results.get('CPU'))
        print("✅ ScannerWorker: SUCCESS")
        app.exit()

if __name__ == "__main__":
    # We need to install PyQt6 for this test to work
    # Since we are in a restricted env, we'll check if it exists
    try:
        import PyQt6
        unittest.main()
    except ImportError:
        print("Error: PyQt6 not found. Please install it using: pip install PyQt6 psutil")
        sys.exit(1)
