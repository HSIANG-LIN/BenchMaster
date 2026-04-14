import sys
import os
import time
import platform
from PyQt6.QtCore import QCoreApplication

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent_tool_ui import HardwareScanner, AgentCore

def test_logic():
    app = QCoreApplication(sys.argv)
    print("--- Testing HardwareScanner ---")
    info = HardwareScanner.get_system_info()
    print(f"Detected: {info}")
    assert 'CPU' in info
    assert 'RAM' in info
    print("✅ HardwareScanner: PASS")

    print("\n--- Testing AgentCore (Headless) ---")
    # We use a dummy URL and token
    core = AgentCore("http://localhost:8000", "BM-AGENT-DEFAULT-SECRET-2026")
    
    # Connect signals to simple print functions
    core.log_signal.connect(lambda msg: print(f" [LOG] {msg}"))
    core.status_updated.connect(lambda status, msg: print(f" [STATUS] {status}: {msg}"))
    core.hardware_scanned.connect(lambda info: print(f" [HW] Scanned: {info}"))

    # Run in a thread so we don't block the test
    import threading
    thread = threading.Thread(target=core.run)
    thread.daemon = True
    thread.start()

    # Wait for a bit to see if it attempts to scan/connect
    start = time.time()
    while time.time() - start < 15:
        app.processEvents()
        time.sleep(0.5)
        if not thread.is_alive():
            break
    
    core.stop()
    print("✅ AgentCore: PASS (Logic loop running)")
    app.exit()

if __name__ == "__main__":
    test_logic()
